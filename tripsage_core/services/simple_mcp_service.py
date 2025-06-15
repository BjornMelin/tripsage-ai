"""
Simplified MCP Service for direct tool integration.

This module provides a direct interface to MCP services without abstraction layers,
replacing the over-engineered 677-line abstraction system with simple direct calls.
"""

import json
import logging
from typing import Any, Dict, Optional

from tripsage_core.clients.airbnb_mcp_client import AirbnbMCPClient
from tripsage_core.config.base_app_settings import get_settings

logger = logging.getLogger(__name__)


class SimpleMCPService:
    """Direct MCP service without abstraction layers."""

    def __init__(self):
        """Initialize the simplified MCP service."""
        self._airbnb_client: Optional[AirbnbMCPClient] = None

    async def _get_airbnb_client(self) -> Optional[AirbnbMCPClient]:
        """Get or create the Airbnb client."""
        if self._airbnb_client is None:
            try:
                settings = get_settings()
                if hasattr(settings, "airbnb") and not settings.airbnb.enabled:
                    logger.info("Airbnb MCP is disabled")
                    return None
                
                self._airbnb_client = AirbnbMCPClient()
                await self._airbnb_client.connect()
                logger.info("Airbnb MCP client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Airbnb client: {e}")
                return None
        
        return self._airbnb_client

    async def invoke(self, method_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Invoke an MCP method directly.
        
        Args:
            method_name: Name of the method to invoke
            params: Parameters for the method
            
        Returns:
            Result from the method call
            
        Raises:
            Exception: If the method call fails
        """
        params = params or {}
        
        # Get the Airbnb client
        client = await self._get_airbnb_client()
        if client is None:
            raise Exception("Airbnb MCP client is not available")
        
        # Map method names to actual client methods
        method_mapping = {
            "search_flights": self._mock_flight_search,
            "search_listings": client.search_accommodations,
            "search_accommodations": client.search_accommodations,
            "search": client.search_accommodations,
            "get_listing_details": client.get_listing_details,
            "get_listing": client.get_listing_details,
            "get_details": client.get_listing_details,
            "geocode": self._mock_geocode,
            "get_current_weather": self._mock_weather,
            "add_memory": self._mock_add_memory,
            "search_memories": self._mock_search_memories,
            "health_check": self._health_check,
        }
        
        method = method_mapping.get(method_name)
        if method is None:
            raise Exception(f"Method '{method_name}' not found")
        
        try:
            # Call the method
            if method_name in ["search_listings", "search_accommodations", "search"]:
                # Convert params to Airbnb format
                airbnb_params = self._convert_to_airbnb_params(params)
                result = await method(**airbnb_params)
            elif method_name in ["get_listing_details", "get_listing", "get_details"]:
                # Get listing details
                listing_id = params.get("listing_id", params.get("id"))
                if not listing_id:
                    raise Exception("listing_id is required")
                result = await method(listing_id)
            else:
                # Other methods
                result = await method(**params)
            
            return result
            
        except Exception as e:
            logger.error(f"MCP method '{method_name}' failed: {e}")
            raise Exception(f"MCP method '{method_name}' failed: {str(e)}")

    def _convert_to_airbnb_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert generic params to Airbnb-specific format."""
        airbnb_params = {}
        
        # Map common fields
        if "location" in params:
            airbnb_params["location"] = params["location"]
        if "check_in" in params:
            airbnb_params["checkin"] = params["check_in"]
        if "check_out" in params:
            airbnb_params["checkout"] = params["check_out"]
        if "guests" in params:
            airbnb_params["adults"] = params["guests"]
        if "adults" in params:
            airbnb_params["adults"] = params["adults"]
        if "children" in params:
            airbnb_params["children"] = params["children"]
        if "price_min" in params:
            airbnb_params["minPrice"] = int(params["price_min"])
        if "price_max" in params:
            airbnb_params["maxPrice"] = int(params["price_max"])
        
        return airbnb_params

    async def _mock_flight_search(self, **params) -> Dict[str, Any]:
        """Mock flight search (not implemented via MCP)."""
        return {
            "flights": [],
            "message": "Flight search not implemented in MCP layer",
            "params": params
        }

    async def _mock_geocode(self, **params) -> Dict[str, Any]:
        """Mock geocoding (not implemented via MCP)."""
        location = params.get("location", "Unknown")
        return {
            "latitude": 0.0,
            "longitude": 0.0,
            "address": location,
            "message": "Geocoding not implemented in MCP layer"
        }

    async def _mock_weather(self, **params) -> Dict[str, Any]:
        """Mock weather data (not implemented via MCP)."""
        return {
            "temperature": 20,
            "condition": "Unknown",
            "message": "Weather data not implemented in MCP layer"
        }

    async def _mock_add_memory(self, **params) -> Dict[str, Any]:
        """Mock memory addition (not implemented via MCP)."""
        return {
            "success": True,
            "id": "mock_memory_id",
            "message": "Memory not implemented in MCP layer"
        }

    async def _mock_search_memories(self, **params) -> Dict[str, Any]:
        """Mock memory search (not implemented via MCP)."""
        return {
            "memories": [],
            "message": "Memory search not implemented in MCP layer"
        }

    async def _health_check(self, **params) -> Dict[str, Any]:
        """Perform health check."""
        client = await self._get_airbnb_client()
        if client is None:
            return {"status": "unhealthy", "message": "Airbnb client not available"}
        
        try:
            # Try a simple operation
            await client.search_accommodations(location="test", checkin="2025-01-01", checkout="2025-01-02")
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global instance
_mcp_service: Optional[SimpleMCPService] = None


def get_mcp_service() -> SimpleMCPService:
    """Get the global MCP service instance."""
    global _mcp_service
    if _mcp_service is None:
        _mcp_service = SimpleMCPService()
    return _mcp_service


# Backwards compatibility alias
mcp_manager = get_mcp_service()