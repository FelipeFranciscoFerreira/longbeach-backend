from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseRoutingProvider(ABC):
    """
    Abstract Base Class for external and internal routing providers
    (HERE, Google Maps, Mapbox, OSRM, Mock).
    """

    @abstractmethod
    async def calculate_optimized_route(
        self,
        origin: Dict[str, Any],
        pickups: List[Dict[str, Any]],
        destinations: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Calculate the optimal route order:
        Origin -> [Ordered Pickups] -> [Ordered Destinations]

        :param origin: dict with name, address, latitude, longitude
        :param pickups: list of dicts with client_id, name, address, latitude, longitude, phone
        :param destinations: list of dicts with destination_id, name, address, latitude, longitude, drop_order
        :param options: additional routing parameters (traffic, van dimensions, etc.)
        :return: dict with provider, total_distance_km, total_duration_minutes, stops, polyline
        """
        pass
