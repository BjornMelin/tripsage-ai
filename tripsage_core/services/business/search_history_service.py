"""Search history service for managing user search history.

This service handles saving, retrieving, and managing user search history
in the database.
"""

import logging
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from tripsage.api.schemas.requests.search import UnifiedSearchRequest
from tripsage_core.exceptions import CoreServiceError
from tripsage_core.services.infrastructure.database_service import DatabaseService


logger = logging.getLogger(__name__)


class SearchHistoryService:
    """Service for managing user search history."""

    def __init__(self, db_service: DatabaseService):
        """Initialize the search history service.

        Args:
            db_service: Database service instance
        """
        self.db_service = db_service

    async def get_recent_searches(
        self, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get recent searches for a user.

        Args:
            user_id: The user ID
            limit: Maximum number of searches to return

        Returns:
            List of search history entries
        """
        try:
            # Query recent searches for the user
            rows: list[dict[str, Any]] = await self.db_service.select(
                "search_parameters",
                "id, user_id, search_type, parameter_json, created_at",
                filters={"user_id": user_id},
                limit=limit,
                order_by="created_at DESC",
            )

            searches: list[dict[str, Any]] = []
            for row in rows:
                # Extract search parameters from JSON
                params: dict[str, Any] = (
                    cast(dict[str, Any], row.get("parameter_json"))
                    if row.get("parameter_json")
                    else {}
                )

                search_entry = {
                    "id": str(row["id"]),
                    "user_id": row["user_id"],
                    "query": params.get("query", ""),
                    "resource_types": params.get("resource_types", []),
                    "filters": params.get("filters", {}),
                    "destination": params.get("destination"),
                    "created_at": cast(datetime, row["created_at"]).isoformat(),
                }
                searches.append(search_entry)

            return searches

        except Exception:
            logger.exception("Error getting recent searches for user %s", user_id)
            raise

    async def save_search(
        self, user_id: str, search_request: UnifiedSearchRequest
    ) -> dict[str, Any]:
        """Save a search to the user's history.

        Args:
            user_id: The user ID
            search_request: The search request to save

        Returns:
            The saved search entry
        """
        try:
            # Safely extract attributes to satisfy static typing
            resource_types = getattr(search_request, "resource_types", None)
            query = getattr(search_request, "query", "")
            filters_val = getattr(search_request, "filters", None)
            destination = getattr(search_request, "destination", None)
            location = getattr(search_request, "location", None)
            start_date = getattr(search_request, "start_date", None)
            end_date = getattr(search_request, "end_date", None)
            guests = getattr(search_request, "guests", None)

            # Determine search type based on resource types
            search_type = self._determine_search_type(resource_types)

            # Prepare search parameters
            search_params = {
                "query": query,
                "resource_types": resource_types,
                "filters": filters_val,
                "destination": destination,
                "location": location,
                "date_range": {
                    "start": (start_date.isoformat() if start_date else None),
                    "end": (end_date.isoformat() if end_date else None),
                },
                "guests": guests,
            }

            # Remove None values
            search_params = {k: v for k, v in search_params.items() if v is not None}

            # Insert into database
            search_id = str(uuid4())
            now = datetime.now(UTC)

            result = await self.db_service.insert(
                "search_parameters",
                {
                    "id": search_id,
                    "user_id": user_id,
                    "search_type": search_type,
                    "parameter_json": search_params,
                    "created_at": now,
                },
            )

            row = result[0] if result else None
            if not row:
                raise CoreServiceError("Failed to insert search")

            return {
                "id": str(row["id"]),
                "user_id": user_id,
                "created_at": row["created_at"].isoformat(),
                **search_params,
            }

        except Exception:
            logger.exception("Error saving search for user %s", user_id)
            raise

    async def delete_saved_search(self, user_id: str, search_id: str) -> bool:
        """Delete a saved search.

        Args:
            user_id: The user ID
            search_id: The search ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            # Delete the search if it belongs to the user
            result = await self.db_service.delete(
                "search_parameters", {"id": search_id, "user_id": user_id}
            )

            # Check if any rows were deleted
            return len(result) > 0

        except Exception:
            logger.exception("Error deleting search %s for user %s", search_id, user_id)
            raise

    def _determine_search_type(self, resource_types: list[str] | None) -> str:
        """Determine the search type based on resource types.

        Args:
            resource_types: List of resource types

        Returns:
            The search type string
        """
        if not resource_types:
            return "unified"

        # Map resource types to search types
        if len(resource_types) == 1:
            type_map = {
                "flight": "flight",
                "accommodation": "accommodation",
                "activity": "activity",
                "destination": "destination",
                "transportation": "transportation",
            }
            return type_map.get(resource_types[0], "unified")

        return "unified"
