import os
import uuid
from datetime import date
from typing import Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.trip import Trip, TripDailyAttendance, AttendanceStatus
from app.models.client import Client
from app.models.driver import Driver
from app.schemas.trip import RouteCalculationResponse, CalculatedStop
from app.services.routing.base import BaseRoutingProvider
from app.services.routing.mock_provider import MockRoutingProvider
from app.services.routing.here_provider import HereRoutingProvider
from app.services.routing.google_provider import GoogleRoutesProvider


class RoutingService:
    def __init__(self):
        self.providers: Dict[str, BaseRoutingProvider] = {
            "mock": MockRoutingProvider(),
            "here": HereRoutingProvider(),
            "google": GoogleRoutesProvider(),
        }

    def get_provider(self, name: str | None = None) -> BaseRoutingProvider:
        provider_key = (name or os.getenv("ROUTING_PROVIDER", "mock")).lower()
        return self.providers.get(provider_key, self.providers["mock"])

    async def calculate_trip_route(
        self,
        db: AsyncSession,
        trip_id: uuid.UUID,
        target_date: date,
        driver_id: uuid.UUID | None = None,
        provider_name: str | None = None,
    ) -> RouteCalculationResponse:
        # 1. Fetch trip and related destinations & clients
        stmt = (
            select(Trip)
            .where(Trip.id == trip_id)
            .options(
                selectinload(Trip.destinations),
                selectinload(Trip.trip_clients).selectinload(Trip.trip_clients.property.mapper.class_.client),
                selectinload(Trip.driver),
            )
        )
        result = await db.execute(stmt)
        trip = result.scalar_one_or_none()

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found",
            )

        if driver_id and trip.driver_id != driver_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to calculate routes for this trip",
            )

        if not trip.destinations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trip has no final destinations defined. Please add at least one destination (e.g. Faculdade).",
            )

        # 2. Query attendance for this trip and target_date
        att_stmt = (
            select(TripDailyAttendance)
            .where(
                TripDailyAttendance.trip_id == trip_id,
                TripDailyAttendance.trip_date == target_date,
            )
            .options(selectinload(TripDailyAttendance.client).selectinload(Client.user))
        )
        att_res = await db.execute(att_stmt)
        attendances = att_res.scalars().all()

        # Build attendance lookup map: client_id -> status
        attendance_map = {att.client_id: att.status for att in attendances}

        # 3. Filter ONLY clients who confirmed attendance
        # Requirement: "primeiro sejam separados apenas os clientes que confirmaram que irão naquele dia"
        confirmed_clients: List[Client] = []

        for tc in trip.trip_clients:
            if not tc.is_active or not tc.client or not tc.client.is_active:
                continue

            status_for_date = attendance_map.get(tc.client_id, AttendanceStatus.PENDING)
            if status_for_date == AttendanceStatus.CONFIRMED:
                confirmed_clients.append(tc.client)

        if not confirmed_clients:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No confirmed passengers found for trip '{trip.name}' on {target_date.isoformat()}. At least 1 client must confirm attendance.",
            )

        # 4. Define Origin
        origin_lat = trip.origin_latitude
        origin_lon = trip.origin_longitude
        origin_addr = trip.origin_address or "Ponto Inicial da Rota"

        # Fallback to driver's live GPS if trip origin is unset
        if origin_lat is None or origin_lon is None:
            if trip.driver and trip.driver.current_latitude and trip.driver.current_longitude:
                origin_lat = trip.driver.current_latitude
                origin_lon = trip.driver.current_longitude
                origin_addr = "Localização Atual da Van"
            else:
                # Fallback to first confirmed passenger's location
                origin_lat = confirmed_clients[0].pickup_latitude or -23.5505
                origin_lon = confirmed_clients[0].pickup_longitude or -46.6333
                origin_addr = "Ponto de Partida Estimado"

        origin_dict = {
            "name": "Origem da Rota",
            "address": origin_addr,
            "latitude": origin_lat,
            "longitude": origin_lon,
        }

        # 5. Format Pickups
        pickups_payload: List[Dict[str, Any]] = []
        for client in confirmed_clients:
            pickups_payload.append({
                "client_id": client.id,
                "name": client.user.full_name if client.user else "Passageiro",
                "phone": client.user.phone if client.user else None,
                "address": client.pickup_address or "Endereço cadastrado",
                "latitude": client.pickup_latitude or origin_lat,
                "longitude": client.pickup_longitude or origin_lon,
            })

        # 6. Format Destinations (e.g., Faculdade A, Faculdade B, Faculdade C)
        destinations_payload: List[Dict[str, Any]] = []
        for dest in trip.destinations:
            destinations_payload.append({
                "destination_id": dest.id,
                "destination_name": dest.destination_name,
                "address": dest.address,
                "latitude": dest.latitude,
                "longitude": dest.longitude,
                "drop_order": dest.drop_order,
            })

        # 7. Call active Routing Provider
        provider = self.get_provider(provider_name)
        raw_result = await provider.calculate_optimized_route(
            origin=origin_dict,
            pickups=pickups_payload,
            destinations=destinations_payload,
        )

        # 8. Transform to API response
        stops: List[CalculatedStop] = [
            CalculatedStop(
                stop_order=s["stop_order"],
                stop_type=s["stop_type"],
                name=s["name"],
                address=s["address"],
                latitude=s["latitude"],
                longitude=s["longitude"],
                client_id=s.get("client_id"),
                client_phone=s.get("client_phone"),
                estimated_arrival_minutes=s.get("estimated_arrival_minutes"),
            )
            for s in raw_result["stops"]
        ]

        return RouteCalculationResponse(
            trip_id=trip.id,
            trip_name=trip.name,
            trip_date=target_date,
            provider=raw_result.get("provider", "UnknownProvider"),
            total_stops=raw_result.get("total_stops", len(stops)),
            confirmed_passengers_count=len(confirmed_clients),
            total_distance_km=raw_result.get("total_distance_km", 0.0),
            total_duration_minutes=raw_result.get("total_duration_minutes", 0.0),
            stops=stops,
            polyline=raw_result.get("polyline"),
            cached=raw_result.get("cached", False),
        )


routing_service = RoutingService()
