"""Airbnb MCP Service for direct tool integration.

This module provides the Airbnb MCP facade for orchestration nodes and HTTP surfaces.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any, Final

from tripsage.tools.models.accommodations import AirbnbSearchParams
from tripsage_core.clients.airbnb_mcp_client import AirbnbMCPClient
from tripsage_core.config import get_settings
from tripsage_core.exceptions import CoreServiceError


logger = logging.getLogger(__name__)

SUPPORTED_METHODS: Final[tuple[str, ...]] = ("search_listings", "get_listing_details")


def _coerce_int_param(value: Any, default: int) -> int:
    """Convert incoming parameter to integer with a safe default."""
    if value is None or isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            parsed = default
        return parsed
    return default


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
        handler = self._get_method_handler(method_name)
        client = await self._ensure_airbnb_client()

        try:
            return await handler(client, params)
        except CoreServiceError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("MCP method '%s' failed", method_name)
            raise CoreServiceError(
                message=f"MCP method '{method_name}' failed: {exc!s}",
                service="mcp",
                details={"original_error": str(exc)},
            ) from exc

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

    def _get_method_handler(
        self, method_name: str
    ) -> Callable[[AirbnbMCPClient, dict[str, Any]], Awaitable[Any]]:
        """Resolve the async handler for a supported method or raise."""
        handlers: dict[
            str, Callable[[AirbnbMCPClient, dict[str, Any]], Awaitable[Any]]
        ] = {
            "search_listings": self._execute_search_listings,
            "get_listing_details": self._execute_get_listing_details,
        }

        try:
            return handlers[method_name]
        except KeyError as exc:
            raise CoreServiceError(
                message=f"Unsupported MCP method '{method_name}'",
                service="mcp",
                details={"supported_methods": list(SUPPORTED_METHODS)},
            ) from exc

    async def _execute_search_listings(
        self, client: AirbnbMCPClient, params: dict[str, Any]
    ) -> Any:
        """Execute the search listings handler."""
        search_payload = self._convert_to_airbnb_params(params)
        return await client.search_accommodations(**search_payload)

    async def _execute_get_listing_details(
        self, client: AirbnbMCPClient, params: dict[str, Any]
    ) -> Any:
        """Execute the get listing details handler with validation."""
        raw_listing_id = params.get("listing_id") or params.get("id")
        if raw_listing_id is None:
            raise CoreServiceError(
                message="listing_id is required for get_listing_details",
                service="mcp",
                details={"params": params},
            )

        listing_id = str(raw_listing_id)
        checkin_raw = params.get("checkin") or params.get("check_in")
        checkout_raw = params.get("checkout") or params.get("check_out")
        checkin = str(checkin_raw) if checkin_raw is not None else None
        checkout = str(checkout_raw) if checkout_raw is not None else None

        return await client.get_listing_details(
            listing_id=listing_id,
            checkin=checkin,
            checkout=checkout,
            adults=_coerce_int_param(params.get("adults"), 1),
            children=_coerce_int_param(params.get("children"), 0),
            infants=_coerce_int_param(params.get("infants"), 0),
            pets=_coerce_int_param(params.get("pets"), 0),
        )


# Default service instance for DI wiring.
default_airbnb_mcp = AirbnbMCP()

__all__ = ["AirbnbMCP", "default_airbnb_mcp"]
