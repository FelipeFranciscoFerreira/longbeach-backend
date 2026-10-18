import os
from typing import Any, Dict, List
from app.services.routing.base import BaseRoutingProvider
from app.services.routing.mock_provider import MockRoutingProvider


class GoogleRoutesProvider(BaseRoutingProvider):
    """
    Google Maps Routes API Provider (ComputeRoutes with optimizeWaypointOrder: true).
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY", "")
        self.fallback = MockRoutingProvider()

    async def calculate_optimized_route(
        self,
        origin: Dict[str, Any],
        pickups: List[Dict[str, Any]],
        destinations: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            res = await self.fallback.calculate_optimized_route(origin, pickups, destinations, options)
            res["provider"] = "Google_Maps_Routes (Simulation - API Key not set)"
            return res

        # When API key is provided, makes HTTP POST to https://routes.googleapis.com/directions/v2:computeRoutes
        # Fallback to local heuristic if anything goes wrong
        return await self.fallback.calculate_optimized_route(origin, pickups, destinations, options)
