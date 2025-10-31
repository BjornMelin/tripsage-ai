"""Core business logic: utilities, factory, handlers, validation, formatting."""

from __future__ import annotations

import contextlib
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, cast

from tripsage_core.services.business.tool_calling.models import ToolCallError


if TYPE_CHECKING:
    from tripsage_core.services.business.memory_service import MemoryService
    from tripsage_core.services.external_apis.duffel_provider import DuffelProvider
    from tripsage_core.services.infrastructure.database_service import (
        DatabaseService,
    )


# ============================================================================
# Utility Functions
# ============================================================================


def first_param(
    params: dict[str, Any], *keys: str, default: Any | None = None
) -> Any | None:
    """Get first available parameter value from multiple possible keys."""
    for key in keys:
        value = params.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            if value.strip():
                return value
            continue
        return value
    return default


def normalize_method(method: str, aliases: dict[str, str]) -> str:
    """Normalize method name using provided aliases."""
    return aliases.get(method.lower(), method.lower())


def to_int(value: Any, default: int) -> int:
    """Safely coerce a value to int, returning a default on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_date_like(value: Any, field_name: str) -> date | datetime:
    """Parse date-like values coming from parameters."""
    if value is None:
        raise ToolCallError(f"{field_name} must be provided")
    if isinstance(value, (date, datetime)):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            try:
                return date.fromisoformat(value)
            except ValueError as exc:
                raise ToolCallError(f"Invalid date format: {value!r}") from exc
    raise ToolCallError(f"{field_name} must be a date/datetime or ISO string")


def pack_rows(rows: list[Any], include_count: bool = False) -> dict[str, Any]:
    """Pack database rows into a standardized response format."""
    if include_count:
        return {"rows": rows, "row_count": len(rows)}
    return {"rows": rows}


def sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    """Sanitize parameters to remove potentially harmful content."""
    sanitized: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, str):
            sanitized[key] = value.replace("<", "").replace(">", "").strip()
        else:
            sanitized[key] = value
    return sanitized


# ============================================================================
# Service Factory
# ============================================================================


class ServiceFactory:
    """Factory for creating and caching service instances."""

    def __init__(self) -> None:
        """Initialize factory with empty cache."""
        self._service_cache: dict[str, Any] = {}
        self._memory_service: Any = None

    async def get_service_instance(self, service_name: str) -> Any:
        """Lazily initialize and cache external service instances."""
        if service_name in self._service_cache:
            return self._service_cache[service_name]

        if service_name == "google_maps":
            from tripsage_core.services.external_apis.google_maps_service import (
                GoogleMapsService,
            )

            instance = GoogleMapsService()
        elif service_name == "weather":
            from tripsage_core.services.external_apis.weather_service import (
                WeatherService,
            )

            instance = WeatherService()
        elif service_name == "airbnb":
            from tripsage_core.clients.airbnb_mcp_client import AirbnbMCPClient

            instance = AirbnbMCPClient()
        else:
            raise ToolCallError(f"Unknown service name for factory: {service_name}")

        self._service_cache[service_name] = instance
        return instance

    async def get_memory_service(self) -> MemoryService:
        """Lazily initialize and cache the MemoryService instance."""
        from tripsage_core.services.business.memory_service import MemoryService

        if self._memory_service is None:
            self._memory_service = MemoryService()
        return cast("MemoryService", self._memory_service)

    async def create_duffel_provider(self, params: dict[str, Any]) -> DuffelProvider:
        """Create a Duffel provider instance."""
        from tripsage_core.config import get_env_var
        from tripsage_core.services.external_apis.duffel_provider import (
            DuffelProvider,
        )

        access_token = cast(
            str | None,
            params.get("access_token")
            or params.get("api_key")
            or await get_env_var("DUFFEL_ACCESS_TOKEN")
            or await get_env_var("DUFFEL_API_KEY"),
        )
        if not access_token:
            raise ToolCallError(
                "Duffel access token is required "
                "(set access_token or DUFFEL_ACCESS_TOKEN)"
            )
        return DuffelProvider(access_token=access_token)


# ============================================================================
# Helper Functions for Handlers
# ============================================================================


def build_duffel_passengers(params: dict[str, Any]) -> list[dict[str, Any]]:
    """Build Duffel passenger list from explicit entries or counts."""
    passengers_param = cast(list[dict[str, Any]] | None, params.get("passengers"))
    if passengers_param is not None:
        return passengers_param

    adults = to_int(first_param(params, "adults", "guests", default=1), 1)
    children = to_int(first_param(params, "children", default=0), 0)
    infants = to_int(first_param(params, "infants", default=0), 0)
    return (
        [{"type": "adult"} for _ in range(max(0, adults))]
        + [{"type": "child"} for _ in range(max(0, children))]
        + [{"type": "infant"} for _ in range(max(0, infants))]
    )


def memory_build_metadata(params: dict[str, Any]) -> dict[str, Any]:
    """Build memory metadata with category."""
    metadata = cast(dict[str, Any], params.get("metadata") or {})
    category = params.get("category")
    if category:
        metadata = {**metadata, "category": category}
    return metadata


def memory_filters_with_category(params: dict[str, Any]) -> dict[str, Any]:
    """Build memory filters with category."""
    filters = cast(dict[str, Any], params.get("filters") or {})
    category = params.get("category")
    if category:
        filters = {**filters, "categories": [category]}
    return filters


# ============================================================================
# Handler Context and Handlers
# ============================================================================


class HandlerContext:
    """Context for handlers with dependencies."""

    def __init__(
        self,
        factory: ServiceFactory,
        db: DatabaseService | None = None,
        safe_tables: set[str] | None = None,
    ) -> None:
        """Initialize handler context."""
        self.factory = factory
        self.db = db
        self._safe_tables = safe_tables or {
            "users",
            "trips",
            "chat_sessions",
            "chat_messages",
            "flight_searches",
            "accommodation_searches",
            "flight_options",
            "accommodation_options",
            "trip_collaborators",
            "flights",
            "accommodations",
        }

    async def handle_google_maps(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Google Maps service calls."""
        maps_service: Any = await self.factory.get_service_instance("google_maps")
        normalized = method.lower()

        if normalized == "geocode":
            address = first_param(params, "address", "location")
            if not address:
                raise ToolCallError("Missing address/location for geocode")
            places = await maps_service.geocode(address)
            return {"places": [place.model_dump() for place in places]}

        if normalized == "search_places":
            places = await maps_service.search_places(
                query=first_param(params, "query", default="") or "",
                location=first_param(params, "location"),
                radius=first_param(params, "radius"),
            )
            return {"places": [place.model_dump() for place in places]}

        if normalized == "get_directions":
            directions = await maps_service.get_directions(
                origin=first_param(params, "origin", default="") or "",
                destination=first_param(params, "destination", default="") or "",
                mode=first_param(params, "mode", default="driving") or "driving",
            )
            return {"directions": [d.model_dump() for d in directions]}

        raise ToolCallError(f"Unsupported google_maps method: {method}")

    async def handle_weather(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle weather service calls."""
        weather_service: Any = await self.factory.get_service_instance("weather")
        normalized = normalize_method(
            method,
            {
                "current": "get_current_weather",
                "current_weather": "get_current_weather",
                "get_current_weather": "get_current_weather",
                "forecast": "get_forecast",
                "get_forecast": "get_forecast",
            },
        )

        if normalized == "get_current_weather":
            weather = await weather_service.get_current_weather(
                latitude=params.get("lat", 0),
                longitude=params.get("lon", 0),
                units=params.get("units", "metric"),
            )
            return {"weather": weather}

        if normalized == "get_forecast":
            forecast = await weather_service.get_forecast(
                latitude=params.get("lat", 0),
                longitude=params.get("lon", 0),
                days=params.get("days", 5),
            )
            return {"forecast": forecast}

        raise ToolCallError(f"Unsupported weather method: {method}")

    async def handle_airbnb(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Airbnb service calls."""
        airbnb_client: Any = await self.factory.get_service_instance("airbnb")
        normalized = normalize_method(
            method,
            {
                "search_properties": "search",
                "search_listings": "search",
                "search": "search",
                "get_listing_details": "details",
                "listing_details": "details",
            },
        )

        if normalized == "search":
            location_param = first_param(params, "location", "place")
            if not location_param:
                raise ToolCallError("location or place is required")
            listings = await airbnb_client.search_accommodations(
                location=location_param,
                checkin=first_param(params, "checkin", "check_in"),
                checkout=first_param(params, "checkout", "check_out"),
                adults=to_int(first_param(params, "adults", "guests", default=1), 1),
                children=to_int(first_param(params, "children", default=0), 0),
                infants=to_int(first_param(params, "infants", default=0), 0),
                pets=to_int(first_param(params, "pets", default=0), 0),
                min_price=first_param(params, "price_min", "min_price"),
                max_price=first_param(params, "price_max", "max_price"),
                cursor=first_param(params, "cursor"),
            )
            return {"listings": listings}

        if normalized == "details":
            listing_id_param = first_param(params, "listing_id", "id")
            if not listing_id_param:
                raise ToolCallError("listing_id is required for listing details")
            details = await airbnb_client.get_listing_details(
                listing_id=listing_id_param,
                checkin=first_param(params, "checkin", "check_in"),
                checkout=first_param(params, "checkout", "check_out"),
                adults=to_int(first_param(params, "adults", default=1), 1),
                children=to_int(first_param(params, "children", default=0), 0),
                infants=to_int(first_param(params, "infants", default=0), 0),
                pets=to_int(first_param(params, "pets", default=0), 0),
            )
            return {"details": details}

        raise ToolCallError(f"Unsupported airbnb method: {method}")

    async def handle_duffel_flights(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Duffel flights service calls."""
        normalized = normalize_method(
            method,
            {
                "get_flight_details": "offer_details",
                "get_offer_details": "offer_details",
                "offer_details": "offer_details",
                "create_order": "create_order",
                "book_flight": "create_order",
                "create_booking": "create_order",
            },
        )

        provider = await self.factory.create_duffel_provider(params)
        try:
            if normalized == "search_flights":
                return await self._duffel_search_flights(provider, params)
            if normalized == "offer_details":
                return await self._duffel_get_offer_details(provider, params)
            if normalized == "create_order":
                return await self._duffel_create_order(provider, params)
            raise ToolCallError(f"Unsupported duffel_flights method: {method}")
        except Exception as exc:
            raise ToolCallError(f"Duffel flights error: {exc!s}") from exc
        finally:
            with contextlib.suppress(Exception):
                await provider.aclose()

    async def _duffel_search_flights(
        self, provider: Any, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Duffel search flights operations."""
        from tripsage_core.models.mappers.flights_mapper import (
            duffel_offer_to_service_offer,
        )

        origin = cast(str | None, params.get("origin"))
        destination = cast(str | None, params.get("destination"))
        if not origin or not destination:
            raise ToolCallError("origin and destination are required")

        departure_date = parse_date_like(params.get("departure_date"), "departure_date")
        return_date_val = params.get("return_date")
        return_date = (
            parse_date_like(return_date_val, "return_date")
            if return_date_val is not None
            else None
        )

        passengers = build_duffel_passengers(params)

        cabin_class = cast(str | None, params.get("cabin_class"))
        max_connections = cast(
            int | None, first_param(params, "max_connections", "max_stops")
        )
        currency = cast(str, first_param(params, "currency", default="USD") or "USD")

        offers_raw = await provider.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            passengers=passengers,
            cabin_class=cabin_class,
            max_connections=max_connections,
            currency=currency,
        )
        offers = cast(list[Any], offers_raw)
        canonical = [
            duffel_offer_to_service_offer(offer).model_dump() for offer in offers
        ]
        return {"offers": canonical}

    async def _duffel_get_offer_details(
        self, provider: Any, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Duffel get offer details operations."""
        from tripsage_core.models.mappers.flights_mapper import (
            duffel_offer_to_service_offer,
        )

        offer_id = cast(str | None, first_param(params, "offer_id", "id"))
        if not offer_id:
            raise ToolCallError("offer_id is required for offer details")
        offer = await provider.get_offer_details(offer_id)
        if offer is None:
            return {"offer": None}
        return {"offer": duffel_offer_to_service_offer(offer).model_dump()}

    async def _duffel_create_order(
        self, provider: Any, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Duffel create order operations."""
        offer_id = cast(str | None, first_param(params, "offer_id", "id"))
        if not offer_id:
            raise ToolCallError("offer_id is required to create an order")
        passengers = cast(list[dict[str, Any]] | None, params.get("passengers"))
        if not passengers:
            raise ToolCallError(
                "passengers list with identity/contact is required to create an order"
            )
        payment = cast(
            dict[str, Any],
            params.get("payment", {"type": "balance", "amount": 0}),
        )
        order = await provider.create_order(
            offer_id=offer_id, passengers=passengers, payment=payment
        )
        return {"order": order}

    async def handle_supabase(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Supabase operations."""
        from tripsage_core.exceptions.exceptions import CoreDatabaseError
        from tripsage_core.services.infrastructure.database_service import (
            DatabaseService,
            get_database_service,
        )

        async def ensure_db() -> DatabaseService:
            """Ensure a database service is available."""
            if self.db is None:
                self.db = await get_database_service()
            assert isinstance(self.db, DatabaseService)
            return self.db

        def require_table() -> str:
            """Require a table for Supabase operations."""
            table = params.get("table")
            if not isinstance(table, str) or not table:
                raise ToolCallError("'table' parameter is required for supabase ops")
            if table not in self._safe_tables:
                raise ToolCallError(
                    f"Table '{table}' is not allowed for this operation"
                )
            return table

        try:
            dbi = await ensure_db()
            normalized = method.lower()
            handlers: dict[
                str,
                Callable[
                    [DatabaseService, dict[str, Any], Callable[[], str]],
                    Awaitable[dict[str, Any]],
                ],
            ] = {
                "query": self._supabase_query,
                "insert": self._supabase_insert,
                "update": self._supabase_update,
                "delete": self._supabase_delete,
                "upsert": self._supabase_upsert,
                "search": self._supabase_vector_search,
            }

            handler = handlers.get(normalized)
            if handler is None:
                raise ToolCallError(f"Unsupported supabase method: {method}")

            return await handler(dbi, params, require_table)

        except CoreDatabaseError as exc:
            message = exc.message if hasattr(exc, "message") else str(exc)
            raise ToolCallError(f"Supabase error: {message}") from exc

    async def _supabase_query(
        self,
        dbi: DatabaseService,
        params: dict[str, Any],
        require_table: Callable[[], str],
    ) -> dict[str, Any]:
        """Handle Supabase query operations."""
        table = require_table()
        columns = params.get("columns", "*")
        filters = cast(dict[str, Any], params.get("filters") or {})
        order_by = params.get("order_by")
        limit = params.get("limit")
        offset = params.get("offset")
        rows = await dbi.select(
            table,
            columns,
            filters=filters,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        return pack_rows(rows)

    async def _supabase_insert(
        self,
        dbi: DatabaseService,
        params: dict[str, Any],
        require_table: Callable[[], str],
    ) -> dict[str, Any]:
        """Handle Supabase insert operations."""
        table = require_table()
        data = cast(dict[str, Any], params.get("data") or {})
        user_id = params.get("user_id")
        rows = await dbi.insert(table, data, user_id)
        return pack_rows(rows, include_count=True)

    async def _supabase_update(
        self,
        dbi: DatabaseService,
        params: dict[str, Any],
        require_table: Callable[[], str],
    ) -> dict[str, Any]:
        """Handle Supabase update operations."""
        table = require_table()
        update_data = cast(
            dict[str, Any], params.get("data") or params.get("update") or {}
        )
        filters = cast(dict[str, Any], params.get("filters") or {})
        user_id = params.get("user_id")
        rows = await dbi.update(table, update_data, filters, user_id)
        return pack_rows(rows, include_count=True)

    async def _supabase_delete(
        self,
        dbi: DatabaseService,
        params: dict[str, Any],
        require_table: Callable[[], str],
    ) -> dict[str, Any]:
        """Handle Supabase delete operations."""
        table = require_table()
        filters = cast(dict[str, Any], params.get("filters") or {})
        user_id = params.get("user_id")
        rows = await dbi.delete(table, filters, user_id)
        return pack_rows(rows, include_count=True)

    async def _supabase_upsert(
        self,
        dbi: DatabaseService,
        params: dict[str, Any],
        require_table: Callable[[], str],
    ) -> dict[str, Any]:
        """Handle Supabase upsert operations."""
        table = require_table()
        data = cast(dict[str, Any], params.get("data") or {})
        on_conflict = params.get("on_conflict")
        user_id = params.get("user_id")
        rows = await dbi.upsert(table, data, on_conflict, user_id)
        return pack_rows(rows, include_count=True)

    async def _supabase_vector_search(
        self,
        dbi: DatabaseService,
        params: dict[str, Any],
        require_table: Callable[[], str],
    ) -> dict[str, Any]:
        """Handle Supabase vector search operations."""
        table = require_table()
        vector_column = params.get("vector_column") or params.get("embedding_column")
        if not isinstance(vector_column, str) or not vector_column:
            raise ToolCallError("'vector_column' is required for vector search")
        query_vector = params.get("query_vector") or params.get("embedding")
        if not isinstance(query_vector, list):
            raise ToolCallError("'query_vector' must be a list of numbers")
        typed_vector = cast(list[Any], query_vector)
        if not all(isinstance(value, (int, float)) for value in typed_vector):
            raise ToolCallError("'query_vector' must be a list of numbers")
        limit = params.get("limit", 10)
        similarity_threshold = params.get("similarity_threshold")
        filters = cast(dict[str, Any] | None, params.get("filters"))
        user_id = params.get("user_id")
        rows = await dbi.vector_search(
            table,
            vector_column,
            [float(x) for x in cast(list[int | float], typed_vector)],
            limit=limit,
            similarity_threshold=similarity_threshold,
            filters=filters,
            user_id=user_id,
        )
        return pack_rows(rows, include_count=True)

    async def handle_memory(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle memory operations."""
        from tripsage_core.services.business.memory_service import (
            ConversationMemoryRequest,
            MemorySearchRequest,
        )

        memory_service = cast(Any, await self.factory.get_memory_service())
        user_id_val = params.get("user_id") or params.get("uid")
        if not user_id_val or not str(user_id_val).strip():
            raise ToolCallError("'user_id' is required for memory operations")
        user_id = str(user_id_val)

        normalized = normalize_method(
            method,
            {
                "store_fact": "store",
                "add_memory": "store",
                "add_fact": "store",
                "search_memories": "search",
                "search": "search",
                "retrieve_facts": "retrieve",
                "retrieve": "retrieve",
                "delete_fact": "delete",
                "delete": "delete",
                "update_fact": "update",
                "update": "update",
            },
        )

        if normalized == "store":
            messages_param = params.get("messages")
            fact_text = first_param(params, "fact_text", "memory", "text")
            if not messages_param and not fact_text:
                raise ToolCallError("Either 'messages' or 'fact_text' must be provided")
            messages = (
                cast(list[dict[str, str]], messages_param)
                if isinstance(messages_param, list)
                else [{"role": "user", "content": str(fact_text)}]
            )
            metadata = memory_build_metadata(params)
            conv_req = ConversationMemoryRequest(
                messages=messages,
                session_id=params.get("session_id"),
                trip_id=params.get("trip_id"),
                metadata=metadata,
            )
            result = await memory_service.add_conversation_memory(
                user_id=user_id, memory_request=conv_req
            )
            return {"result": result}

        if normalized == "search":
            query = first_param(params, "query", "q")
            if not query or not str(query).strip():
                raise ToolCallError("'query' is required for search_memories")
            search_req = MemorySearchRequest(
                query=str(query),
                limit=int(params.get("limit", 5)),
                filters=memory_filters_with_category(params),
                similarity_threshold=float(params.get("similarity_threshold", 0.3)),
            )
            items = cast(
                list[Any], await memory_service.search_memories(user_id, search_req)
            )
            return {"results": [item.model_dump() for item in items]}

        if normalized == "retrieve":
            search_req = MemorySearchRequest(
                query=str(first_param(params, "query", "q", default="*") or "*"),
                limit=int(params.get("limit", 10)),
                filters=memory_filters_with_category(params),
                similarity_threshold=float(params.get("similarity_threshold", 0.0)),
            )
            items = cast(
                list[Any], await memory_service.search_memories(user_id, search_req)
            )
            return {
                "results": [item.model_dump() for item in items],
                "count": len(items),
            }

        if normalized == "delete":
            memory_ids = first_param(params, "memory_ids", "ids")
            memory_id = first_param(params, "memory_id", "id")
            ids = (
                [str(item) for item in cast(list[Any], memory_ids)]
                if isinstance(memory_ids, list)
                else [str(memory_id)]
                if memory_id
                else None
            )
            result = await memory_service.delete_user_memories(user_id, ids)
            return {"result": result}

        if normalized == "update":
            memory_id = first_param(params, "memory_id", "id")
            if not memory_id:
                raise ToolCallError("'memory_id' is required for update_fact")
            await memory_service.delete_user_memories(user_id, [str(memory_id)])
            fact_text = first_param(params, "fact_text", "memory", "text")
            if not fact_text:
                raise ToolCallError(
                    "Updated 'fact_text' (or 'memory'/'text') is required"
                )
            metadata = {
                **memory_build_metadata(params),
                "supersedes_id": str(memory_id),
            }
            conv_req = ConversationMemoryRequest(
                messages=[{"role": "user", "content": str(fact_text)}],
                session_id=params.get("session_id"),
                trip_id=params.get("trip_id"),
                metadata=metadata,
            )
            result = await memory_service.add_conversation_memory(
                user_id=user_id, memory_request=conv_req
            )
            return {"result": result}

        raise ToolCallError(f"Unsupported memory method: {method}")


# ============================================================================
# Validation Functions
# ============================================================================


async def validate_flight_params(params: dict[str, Any], method: str) -> list[str]:
    """Validate flight search parameters based on method."""
    normalized = normalize_method(
        method,
        {
            "get_flight_details": "offer_details",
            "get_offer_details": "offer_details",
            "offer_details": "offer_details",
            "create_order": "create_order",
            "book_flight": "create_order",
            "create_booking": "create_order",
            "search_flights": "search_flights",
        },
    )

    errors: list[str] = []

    if normalized == "search_flights":
        required_fields = ["origin", "destination", "departure_date"]
        errors.extend(
            f"Missing required field: {field}"
            for field in required_fields
            if field not in params
        )
    elif normalized == "offer_details":
        offer_id = first_param(params, "offer_id", "id")
        if not offer_id:
            errors.append("offer_id (or id) is required for offer details")
    elif normalized == "create_order":
        offer_id = first_param(params, "offer_id", "id")
        if not offer_id:
            errors.append("offer_id (or id) is required to create an order")
        if not params.get("passengers"):
            errors.append(
                "passengers list with identity/contact is required to create an order"
            )

    return errors


async def validate_accommodation_params(
    params: dict[str, Any], method: str
) -> list[str]:
    """Validate accommodation search parameters."""
    errors: list[str] = []

    location = first_param(params, "location", "place")
    if not location:
        errors.append("location or place is required")

    checkin = first_param(params, "checkin", "check_in")
    if not checkin:
        errors.append("checkin or check_in is required")

    checkout = first_param(params, "checkout", "check_out")
    if not checkout:
        errors.append("checkout or check_out is required")

    return errors


async def validate_maps_params(params: dict[str, Any], method: str) -> list[str]:
    """Validate maps API parameters based on method."""
    normalized = method.lower()
    errors: list[str] = []

    if normalized == "geocode":
        address = first_param(params, "address", "location")
        if not address:
            errors.append("address or location is required for geocode")
    elif normalized == "search_places":
        query = first_param(params, "query", default="")
        if not query or not str(query).strip():
            errors.append("query is required for search_places")
    elif normalized == "get_directions":
        origin = first_param(params, "origin", default="")
        destination = first_param(params, "destination", default="")
        if not origin or not str(origin).strip():
            errors.append("origin is required for get_directions")
        if not destination or not str(destination).strip():
            errors.append("destination is required for get_directions")

    return errors


async def validate_weather_params(params: dict[str, Any], method: str) -> list[str]:
    """Validate weather API parameters based on method."""
    errors: list[str] = []

    has_lat_lon = params.get("lat") is not None and params.get("lon") is not None
    location = first_param(params, "location")
    if not has_lat_lon and not location:
        errors.append(
            "Either lat/lon pair or location parameter is required for weather"
        )

    return errors


# ============================================================================
# Formatting Functions
# ============================================================================


async def format_flight_results(result: dict[str, Any] | None) -> dict[str, Any]:
    """Format flight search results for chat display."""
    data: dict[str, Any] = result or {}
    return {
        "type": "flights",
        "title": "Flight Search Results",
        "data": data,
        "actions": ["book", "compare", "save"],
    }


async def format_accommodation_results(
    result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Format accommodation search results for chat display."""
    data: dict[str, Any] = result or {}
    return {
        "type": "accommodations",
        "title": "Accommodation Options",
        "data": data,
        "actions": ["book", "favorite", "share"],
    }


async def format_maps_results(result: dict[str, Any] | None) -> dict[str, Any]:
    """Format maps API results for chat display."""
    data: dict[str, Any] = result or {}
    return {
        "type": "location",
        "title": "Location Information",
        "data": data,
        "actions": ["navigate", "save", "share"],
    }


async def format_weather_results(result: dict[str, Any] | None) -> dict[str, Any]:
    """Format weather API results for chat display."""
    data: dict[str, Any] = result or {}
    return {
        "type": "weather",
        "title": "Weather Information",
        "data": data,
        "actions": ["save", "alert"],
    }
