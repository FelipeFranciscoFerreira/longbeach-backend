import uuid
from datetime import date
from typing import Optional, Sequence, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.trip import (
    Trip,
    TripDestination,
    TripClient,
    TripDailyAttendance,
    AttendanceStatus,
)
from app.models.enums import DayOfWeek
from app.schemas.trip import (
    TripCreate,
    TripUpdate,
    TripDestinationCreate,
)


class CRUDTrip:
    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Trip]:
        stmt = (
            select(Trip)
            .where(Trip.id == id)
            .options(
                selectinload(Trip.destinations),
                selectinload(Trip.trip_clients).selectinload(TripClient.client),
                selectinload(Trip.trip_clients).selectinload(TripClient.destination),
                selectinload(Trip.driver),
                selectinload(Trip.company),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        driver_id: Optional[uuid.UUID] = None,
        company_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Trip]:
        stmt = select(Trip).options(
            selectinload(Trip.destinations),
            selectinload(Trip.trip_clients).selectinload(TripClient.client),
            selectinload(Trip.driver),
        )
        if driver_id:
            stmt = stmt.where(Trip.driver_id == driver_id)
        if company_id:
            stmt = stmt.where(Trip.company_id == company_id)
        if is_active is not None:
            stmt = stmt.where(Trip.is_active == is_active)

        stmt = stmt.offset(skip).limit(limit).order_by(Trip.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        db: AsyncSession,
        obj_in: TripCreate,
        driver_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> Trip:
        trip = Trip(
            name=obj_in.name,
            shift=obj_in.shift,
            origin_address=obj_in.origin_address,
            origin_latitude=obj_in.origin_latitude,
            origin_longitude=obj_in.origin_longitude,
            driver_id=driver_id,
            company_id=company_id,
            is_active=obj_in.is_active,
        )
        db.add(trip)
        await db.flush()

        # Add destinations if provided
        for dest_in in obj_in.destinations:
            dest = TripDestination(
                trip_id=trip.id,
                destination_name=dest_in.destination_name,
                address=dest_in.address,
                latitude=dest_in.latitude,
                longitude=dest_in.longitude,
                drop_order=dest_in.drop_order,
            )
            db.add(dest)

        await db.commit()
        return await self.get_by_id(db, trip.id)  # type: ignore

    async def update(
        self, db: AsyncSession, db_obj: Trip, obj_in: TripUpdate
    ) -> Trip:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return await self.get_by_id(db, db_obj.id)  # type: ignore

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> Optional[Trip]:
        obj = await self.get_by_id(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    async def add_destination(
        self, db: AsyncSession, trip_id: uuid.UUID, dest_in: TripDestinationCreate
    ) -> TripDestination:
        dest = TripDestination(
            trip_id=trip_id,
            destination_name=dest_in.destination_name,
            address=dest_in.address,
            latitude=dest_in.latitude,
            longitude=dest_in.longitude,
            drop_order=dest_in.drop_order,
        )
        db.add(dest)
        await db.commit()
        await db.refresh(dest)
        return dest

    async def add_client_to_trip(
        self,
        db: AsyncSession,
        trip_id: uuid.UUID,
        client_id: uuid.UUID,
        days_of_week: List[DayOfWeek],
        destination_id: Optional[uuid.UUID] = None,
    ) -> TripClient:
        days_str = ",".join([d.value for d in days_of_week])

        # Check existing
        stmt = select(TripClient).where(
            TripClient.trip_id == trip_id, TripClient.client_id == client_id
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.days_of_week = days_str
            existing.destination_id = destination_id
            existing.is_active = True
            db.add(existing)
            await db.commit()
            await db.refresh(existing)
            return existing

        trip_client = TripClient(
            trip_id=trip_id,
            client_id=client_id,
            destination_id=destination_id,
            days_of_week=days_str,
            is_active=True,
        )
        db.add(trip_client)
        await db.commit()
        await db.refresh(trip_client)
        return trip_client

    async def set_attendance(
        self,
        db: AsyncSession,
        trip_id: uuid.UUID,
        client_id: uuid.UUID,
        trip_date: date,
        status: AttendanceStatus,
        notes: Optional[str] = None,
    ) -> TripDailyAttendance:
        stmt = select(TripDailyAttendance).where(
            TripDailyAttendance.trip_id == trip_id,
            TripDailyAttendance.client_id == client_id,
            TripDailyAttendance.trip_date == trip_date,
        )
        res = await db.execute(stmt)
        att = res.scalar_one_or_none()

        if att:
            att.status = status
            att.notes = notes
        else:
            att = TripDailyAttendance(
                trip_id=trip_id,
                client_id=client_id,
                trip_date=trip_date,
                status=status,
                notes=notes,
            )
            db.add(att)

        await db.commit()
        await db.refresh(att)
        return att

    async def get_attendance(
        self,
        db: AsyncSession,
        trip_id: uuid.UUID,
        client_id: uuid.UUID,
        trip_date: date,
    ) -> Optional[TripDailyAttendance]:
        stmt = select(TripDailyAttendance).where(
            TripDailyAttendance.trip_id == trip_id,
            TripDailyAttendance.client_id == client_id,
            TripDailyAttendance.trip_date == trip_date,
        ).options(selectinload(TripDailyAttendance.client))
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_trip_attendances(
        self, db: AsyncSession, trip_id: uuid.UUID, trip_date: date
    ) -> Sequence[TripDailyAttendance]:
        stmt = (
            select(TripDailyAttendance)
            .where(
                TripDailyAttendance.trip_id == trip_id,
                TripDailyAttendance.trip_date == trip_date,
            )
            .options(selectinload(TripDailyAttendance.client))
        )
        res = await db.execute(stmt)
        return res.scalars().all()


crud_trip = CRUDTrip()
