"""Airbnb MCP Service for direct tool integration.

This module provides the Airbnb MCP facade for orchestration nodes and HTTP surfaces.
"""

import logging
from typing import Any, Final

from tripsage.tools.models.accommodations import AirbnbSearchParams
from tripsage_core.clients.airbnb_mcp_client import AirbnbMCPClient
from tripsage_core.config import get_settings
from tripsage_core.exceptions import CoreServiceError


logger = logging.getLogger(__name__)

SUPPORTED_METHODS: Final[tuple[str, ...]] = ("search_listings", "get_listing_details")


class AirbnbMCP:
    """Concrete MCP facade that currently proxies Airbnb operations."""

    def __init__(self) -> None:
        """Initialize the Airbnb MCP facade."""
        self._airbnb_client: AirbnbMCPClient | None = None
        self._airbnb_enabled: bool | None = None

    async def initialize(self) -> None:
        """Eagerly initialize all enabled MCP integrations."""
        if self._airbnb_enabled is False:
            logger.info("Skipping Airbnb MCP initialization (disabled via settings)")
            return

        try:
            await self._ensure_airbnb_client()
        except CoreServiceError:
            # Surface log but do not raise during startup so callers can decide.
            logger.exception("Airbnb MCP initialization failed")
            raise

    async def invoke(
        self,
        method_name: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Invoke a supported MCP method."""
        params = params or {}
        if method_name not in SUPPORTED_METHODS:
            raise CoreServiceError(
                message=f"Unsupported MCP method '{method_name}'",
                service="mcp",
                details={"supported_methods": list(SUPPORTED_METHODS)},
            )

        client = await self._ensure_airbnb_client()

        try:
            if method_name == "search_listings":
                search_payload = self._convert_to_airbnb_params(params)
                return await client.search_accommodations(**search_payload)

            if method_name == "get_listing_details":
                listing_id = params.get("listing_id") or params.get("id")
                if not listing_id:
                    raise CoreServiceError(
                        message="listing_id is required for get_listing_details",
                        service="mcp",
                        details={"params": params},
                    )

                lookup_kwargs = {
                    "listing_id": listing_id,
                    "checkin": params.get("checkin") or params.get("check_in"),
                    "checkout": params.get("checkout") or params.get("check_out"),
                    "adults": params.get("adults", 1),
                    "children": params.get("children", 0),
                    "infants": params.get("infants", 0),
                    "pets": params.get("pets", 0),
                }
                return await client.get_listing_details(**lookup_kwargs)

        except CoreServiceError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("MCP method '%s' failed", method_name)
            raise CoreServiceError(
                message=f"MCP method '{method_name}' failed: {exc!s}",
                service="mcp",
                details={"original_error": str(exc)},
            ) from exc

        raise CoreServiceError(
            message=f"Unhandled MCP method '{method_name}'",
            service="mcp",
        )

    async def health_check(self) -> dict[str, Any]:
        """Run a lightweight health check against enabled MCP integrations."""
        if self._airbnb_enabled is False:
            return {"status": "disabled", "service": "airbnb"}

        try:
            client = await self._ensure_airbnb_client()
            await client.search_accommodations(
                location="health-check", checkin="2025-01-01", checkout="2025-01-02"
            )
            return {"status": "healthy", "service": "airbnb"}
        except CoreServiceError as exc:
            return {"status": "unavailable", "service": "airbnb", "error": str(exc)}
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Airbnb MCP health check failed")
            return {"status": "error", "service": "airbnb", "error": str(exc)}

    def get_available_methods(self) -> list[str]:
        """Return the list of supported MCP methods."""
        return list(SUPPORTED_METHODS)

    def available_services(self) -> list[str]:
        """Return the list of available MCP-backed services."""
        if self._airbnb_enabled is False:
            return []
        return ["airbnb"]

    def initialized_services(self) -> list[str]:
        """Return the list of services with active clients."""
        return ["airbnb"] if self._airbnb_client is not None else []

    async def shutdown(self) -> None:
        """Tear down any active MCP clients."""
        if self._airbnb_client:
            try:
                await self._airbnb_client.disconnect()
            finally:
                self._airbnb_client = None

    async def _ensure_airbnb_client(self) -> AirbnbMCPClient:
        """Ensure an Airbnb MCP client is available or raise."""
        if self._airbnb_client is not None:
            return self._airbnb_client

        if self._airbnb_enabled is False:
            raise CoreServiceError(
                message="Airbnb MCP integration disabled",
                service="mcp",
                details={"integration": "airbnb"},
            )

        settings = get_settings()
        airbnb_settings = getattr(settings, "airbnb", None)
        if airbnb_settings and not getattr(airbnb_settings, "enabled", True):
            self._airbnb_enabled = False
            raise CoreServiceError(
                message="Airbnb MCP integration disabled via configuration",
                service="mcp",
                details={"integration": "airbnb"},
            )

        client = AirbnbMCPClient()
        await client.connect()
        self._airbnb_client = client
        self._airbnb_enabled = True
        logger.info("Airbnb MCP client initialized")
        return client

    def _convert_to_airbnb_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Normalize search parameters to the Airbnb schema."""
        candidate: dict[str, Any] = {}
        if "location" in params:
            candidate["location"] = params["location"]
        if checkin := params.get("checkin") or params.get("check_in"):
            candidate["checkin"] = checkin
        if checkout := params.get("checkout") or params.get("check_out"):
            candidate["checkout"] = checkout

        if "adults" in params:
            candidate["adults"] = params["adults"]
        elif "guests" in params:
            candidate["adults"] = params["guests"]

        for field in ("children", "infants", "pets"):
            if field in params:
                candidate[field] = params[field]

        if "price_min" in params:
            candidate["min_price"] = int(params["price_min"])
        if "price_max" in params:
            candidate["max_price"] = int(params["price_max"])

        if "amenities" in params:
            candidate["amenities"] = params["amenities"]
        if "property_type" in params:
            candidate["property_type"] = params["property_type"]

        search_params = AirbnbSearchParams(**candidate)
        return search_params.model_dump(exclude_none=True)


# Default service instance for DI wiring.
default_airbnb_mcp = AirbnbMCP()

__all__ = ["AirbnbMCP", "default_airbnb_mcp"]
