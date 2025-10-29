"""Service responsible for persisting and retrieving unified search history."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from tripsage.api.schemas.search import UnifiedSearchRequest
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.types import JSONObject, JSONValue
from tripsage_core.utils.error_handling_utils import tripsage_safe_execute


logger = logging.getLogger(__name__)


class SearchHistoryService:
    """Service for managing user search history."""

    def __init__(self, db_service: DatabaseService):
        """Initialize the search history service.

        Args:
            db_service: Database service instance.
        """
        self.db_service = db_service

    def _jsonify(self, obj: Any) -> JSONValue:
        """Coerce arbitrary objects into JSONValue recursively for storage."""
        result = None

        # Simple types
        if obj is None or isinstance(obj, (str, int, float, bool)):
            result = obj

        # DateTime handling
        elif isinstance(obj, datetime):
            result = obj.astimezone(UTC).isoformat()

        # Mapping types
        elif isinstance(obj, Mapping):
            mapping_obj = cast(Mapping[object, object], obj)
            temp_result: dict[str, JSONValue] = {}
            for key_obj, value_obj in mapping_obj.items():
                key_str: str = str(key_obj)
                temp_result[key_str] = self._jsonify(value_obj)
            result = temp_result

        # Sequence types
        elif isinstance(obj, (list, tuple)):
            sequence_obj = cast(tuple[Any, ...] | list[Any], obj)
            result = [self._jsonify(item) for item in sequence_obj]

        # Model objects
        elif hasattr(obj, "model_dump"):
            model_dump = getattr(obj, "model_dump", None)
            if callable(model_dump):
                try:
                    dumped = model_dump()
                    result = self._jsonify(dumped)
                except (TypeError, ValueError, AttributeError):
                    result = str(obj)
            else:
                result = str(obj)

        # Fallback
        else:
            result = str(obj)

        return result

    @tripsage_safe_execute()
    async def get_recent_searches(
        self, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Return the most recent searches for a user ordered by recency."""
        try:
            rows: list[JSONObject] = await self.db_service.select(
                "search_parameters",
                "id, user_id, search_type, parameter_json, created_at",
                filters={"user_id": user_id},
                order_by="-created_at",
                limit=limit,
            )

            searches: list[dict[str, Any]] = []
            for row in rows:
                params = self._decode_parameter_payload(row.get("parameter_json"))
                searches.append(
                    {
                        "id": str(row.get("id", "")),
                        "user_id": str(row.get("user_id", "")),
                        "search_type": row.get("search_type", "unified"),
                        "query": params.get("query", ""),
                        "resource_types": params.get("resource_types", []),
                        "filters": params.get("filters", {}),
                        "destination": params.get("destination", ""),
                        "location": params.get("location"),
                        "date_range": params.get("date_range"),
                        "guests": params.get("guests"),
                        "created_at": self._coerce_datetime_to_iso(
                            row.get("created_at")
                        ),
                    }
                )
            return searches
        except Exception:
            logger.exception("Error getting recent searches for user %s", user_id)
            raise

    @tripsage_safe_execute()
    async def save_search(
        self, user_id: str, search_request: UnifiedSearchRequest
    ) -> dict[str, Any]:
        """Persist a search request to the user's history."""
        try:
            search_type = self._determine_search_type(search_request.resource_types)

            filters_payload = (
                search_request.filters.model_dump(exclude_none=True)
                if search_request.filters is not None
                else None
            )

            search_params: JSONObject = {
                "query": search_request.query,
                "resource_types": search_request.resource_types or [],
                "filters": filters_payload or {},
                "destination": search_request.destination,
                "location": search_request.location,
                "date_range": {
                    "start": (
                        search_request.start_date.isoformat()
                        if search_request.start_date
                        else None
                    ),
                    "end": (
                        search_request.end_date.isoformat()
                        if search_request.end_date
                        else None
                    ),
                },
                "guests": search_request.guests,
            }

            # Strip None to reduce storage noise.
            search_params = cast(
                JSONObject, {k: v for k, v in search_params.items() if v is not None}
            )

            search_id = str(uuid4())
            now = datetime.now(UTC)

            parameter_json = self._jsonify(search_params)
            insert_payload: JSONObject = {
                "id": search_id,
                "user_id": user_id,
                "search_type": search_type,
                "parameter_json": parameter_json,
                "created_at": now.isoformat(),
            }
            result = await self.db_service.insert("search_parameters", insert_payload)

            if not result:
                raise RuntimeError("Database did not return inserted search row")

            row = result[0]
            response: dict[str, Any] = {
                "id": str(row.get("id", search_id)),
                "user_id": user_id,
                "search_type": search_type,
                "created_at": self._coerce_datetime_to_iso(row.get("created_at", now)),
            }
            response.update(cast(dict[str, Any], search_params))
            return response
        except Exception:
            logger.exception("Error saving search for user %s", user_id)
            raise

    @tripsage_safe_execute()
    async def delete_saved_search(self, user_id: str, search_id: str) -> bool:
        """Delete a saved search belonging to the provided user."""
        try:
            result = await self.db_service.delete(
                "search_parameters", {"id": search_id, "user_id": user_id}
            )
            return len(result) > 0
        except Exception:
            logger.exception("Error deleting search %s for user %s", search_id, user_id)
            raise

    def _determine_search_type(self, resource_types: list[str] | None) -> str:
        """Map requested resource types to a persisted search type."""
        if not resource_types:
            return "unified"

        type_map = {
            "flight": "flight",
            "accommodation": "accommodation",
            "activity": "activity",
            "destination": "destination",
            "transportation": "transportation",
        }
        if len(resource_types) == 1:
            return type_map.get(resource_types[0], "unified")
        return "unified"

    def _decode_parameter_payload(self, payload: Any) -> dict[str, Any]:
        """Normalize persisted parameter JSON into a dictionary."""
        if isinstance(payload, Mapping):
            mapping_payload = cast(Mapping[object, object], payload)
            result: dict[str, Any] = {}
            for key, value in mapping_payload.items():
                key_str: str = str(key)
                result[key_str] = value
            return result
        if isinstance(payload, str):
            try:
                decoded: Any = json.loads(payload)
                if isinstance(decoded, dict):
                    decoded_mapping = cast(Mapping[object, object], decoded)
                    result = {}
                    for key, value in decoded_mapping.items():
                        key_str = str(key)
                        result[key_str] = value
                    return result
            except json.JSONDecodeError:
                logger.debug("Failed to decode parameter_json payload: %s", payload)
        return {}

    def _coerce_datetime_to_iso(self, value: Any) -> str:
        """Convert various datetime representations into an ISO 8601 string."""
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            return value.astimezone(UTC).isoformat()
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                return parsed.astimezone(UTC).isoformat()
            except ValueError:
                return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=UTC).isoformat()
        return datetime.now(UTC).isoformat()
