import math
from typing import Any, Dict, List
from app.services.routing.base import BaseRoutingProvider


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in km."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class MockRoutingProvider(BaseRoutingProvider):
    """
    Simulated routing provider using Haversine TSP (Nearest-Neighbor Heuristic).
    Guarantees that the entire flow works out-of-the-box before configuring external API keys.
    """

    async def calculate_optimized_route(
        self,
        origin: Dict[str, Any],
        pickups: List[Dict[str, Any]],
        destinations: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        stops: List[Dict[str, Any]] = []
        total_distance_km = 0.0
        total_duration_minutes = 0.0
        current_time_minutes = 0

        # 1. Start with Origin
        current_lat = origin["latitude"]
        current_lon = origin["longitude"]

        stops.append({
            "stop_order": 1,
            "stop_type": "ORIGIN",
            "name": origin.get("name", "Ponto de Partida"),
            "address": origin.get("address", "Garagem / Ponto Inicial"),
            "latitude": current_lat,
            "longitude": current_lon,
            "client_id": None,
            "client_phone": None,
            "estimated_arrival_minutes": 0,
        })

        # 2. Optimize Pickups using Nearest Neighbor Heuristic
        unvisited_pickups = list(pickups)
        order_index = 2

        while unvisited_pickups:
            nearest_idx = 0
            best_dist = float("inf")

            for i, p in enumerate(unvisited_pickups):
                dist = haversine_distance(
                    current_lat, current_lon, p["latitude"], p["longitude"]
                )
                if dist < best_dist:
                    best_dist = dist
                    nearest_idx = i

            chosen_pickup = unvisited_pickups.pop(nearest_idx)
            # Urban driving factor: 1.35x real distance vs straight line
            leg_distance_km = round(best_dist * 1.35, 2)
            # Assume average city van speed: 25 km/h + 2 min pickup dwell time
            leg_minutes = round((leg_distance_km / 25.0) * 60 + 2, 1)

            total_distance_km += leg_distance_km
            current_time_minutes += int(leg_minutes)

            stops.append({
                "stop_order": order_index,
                "stop_type": "PICKUP",
                "name": chosen_pickup["name"],
                "address": chosen_pickup["address"],
                "latitude": chosen_pickup["latitude"],
                "longitude": chosen_pickup["longitude"],
                "client_id": chosen_pickup.get("client_id"),
                "client_phone": chosen_pickup.get("phone"),
                "estimated_arrival_minutes": current_time_minutes,
            })

            current_lat = chosen_pickup["latitude"]
            current_lon = chosen_pickup["longitude"]
            order_index += 1

        # 3. Add Final Destinations in drop_order
        sorted_destinations = sorted(
            destinations, key=lambda d: d.get("drop_order", 1)
        )
        for dest in sorted_destinations:
            dist = haversine_distance(
                current_lat, current_lon, dest["latitude"], dest["longitude"]
            )
            leg_distance_km = round(dist * 1.35, 2)
            leg_minutes = round((leg_distance_km / 30.0) * 60 + 3, 1)

            total_distance_km += leg_distance_km
            current_time_minutes += int(leg_minutes)

            stops.append({
                "stop_order": order_index,
                "stop_type": "DESTINATION",
                "name": dest["destination_name"],
                "address": dest["address"],
                "latitude": dest["latitude"],
                "longitude": dest["longitude"],
                "client_id": None,
                "client_phone": None,
                "estimated_arrival_minutes": current_time_minutes,
            })

            current_lat = dest["latitude"]
            current_lon = dest["longitude"]
            order_index += 1

        total_duration_minutes = float(current_time_minutes)

        return {
            "provider": "MockHaversineOptimizer",
            "total_stops": len(stops),
            "confirmed_passengers_count": len(pickups),
            "total_distance_km": round(total_distance_km, 2),
            "total_duration_minutes": round(total_duration_minutes, 1),
            "stops": stops,
            "polyline": "mock_polyline_encoded_geometry_data",
            "cached": False,
        }
