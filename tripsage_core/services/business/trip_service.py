"""Trip service for trip management operations.

This service handles all trip-related business logic including trip creation,
retrieval, updates, sharing, and collaboration features.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from pydantic import Field, ValidationInfo, field_validator

from tripsage_core.exceptions.exceptions import (
    CoreAuthorizationError,
    CoreResourceNotFoundError,
    CoreValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.models.schemas_common.enums import (
    TripStatus,
    TripType,
    TripVisibility,
)
from tripsage_core.models.trip import Budget, Trip, TripPreferences
from tripsage_core.services.infrastructure.supabase_user_ops import fetch_user_by_id
from tripsage_core.types import JSONObject, JSONValue
from tripsage_core.utils.error_handling_utils import tripsage_safe_execute


logger = logging.getLogger(__name__)


class TripLocation(TripSageModel):
    """Trip location information."""

    name: str = Field(..., description="Location name")
    country: str | None = Field(None, description="Country")
    city: str | None = Field(None, description="City")
    coordinates: dict[str, float] | None = Field(
        None, description="Lat/lng coordinates"
    )
    timezone: str | None = Field(None, description="Location timezone")


class TripCreateRequest(TripSageModel):
    """Request model for trip creation."""

    title: str = Field(..., min_length=1, max_length=200, description="Trip title")
    description: str | None = Field(
        None, max_length=2000, description="Trip description"
    )
    start_date: datetime = Field(..., description="Trip start date")
    end_date: datetime = Field(..., description="Trip end date")
    destination: str = Field(..., description="Primary destination")
    destinations: list[TripLocation] = Field(
        default_factory=lambda: cast(list[TripLocation], []),
        description="Trip destinations",
    )
    budget: Budget = Field(..., description="Trip budget with breakdown")
    travelers: int = Field(default=1, ge=1, description="Number of travelers")
    trip_type: TripType = Field(default=TripType.LEISURE, description="Type of trip")
    visibility: TripVisibility = Field(
        default=TripVisibility.PRIVATE, description="Trip visibility"
    )
    tags: list[str] = Field(default_factory=list, description="Trip tags")
    preferences: TripPreferences | None = Field(None, description="Trip preferences")

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: datetime, info: ValidationInfo) -> datetime:
        """Validate that end_date is after start_date."""
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class TripUpdateRequest(TripSageModel):
    """Request model for trip updates."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    start_date: datetime | None = Field(None)
    end_date: datetime | None = Field(None)
    destination: str | None = Field(None)
    destinations: list[TripLocation] | None = Field(None)
    budget: Budget | None = Field(None)
    travelers: int | None = Field(None, ge=1)
    trip_type: TripType | None = Field(None)
    visibility: TripVisibility | None = Field(None)
    tags: list[str] | None = Field(None)
    preferences: TripPreferences | None = Field(None)
    status: TripStatus | None = Field(None)


class TripResponse(TripSageModel):
    """Response model for trip data."""

    id: UUID = Field(..., description="Trip ID")
    user_id: UUID = Field(..., description="Owner user ID")
    title: str = Field(..., description="Trip title")
    description: str | None = Field(None, description="Trip description")
    start_date: datetime = Field(..., description="Trip start date")
    end_date: datetime = Field(..., description="Trip end date")
    destination: str = Field(..., description="Primary destination")
    destinations: list[TripLocation] = Field(
        default_factory=lambda: cast(list[TripLocation], []),
        description="Trip destinations",
    )
    budget: Budget = Field(..., description="Trip budget with breakdown")
    travelers: int = Field(..., description="Number of travelers")
    trip_type: TripType = Field(..., description="Type of trip")
    status: TripStatus = Field(..., description="Trip status")
    visibility: TripVisibility = Field(..., description="Trip visibility")
    tags: list[str] = Field(default_factory=list, description="Trip tags")
    preferences: TripPreferences = Field(..., description="Trip preferences")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Related data counts
    note_count: int = Field(default=0, description="Number of notes")
    attachment_count: int = Field(default=0, description="Number of attachments")
    collaborator_count: int = Field(default=0, description="Number of collaborators")
    shared_with: list[str] = Field(
        default_factory=list, description="User IDs trip is shared with"
    )


class TripService:
    """Service for managing trips."""

    if TYPE_CHECKING:
        # Imported for typing only to avoid import cycles at runtime
        from tripsage_core.services.infrastructure.database_service import (
            DatabaseService,
        )

    def __init__(
        self,
        database_service: DatabaseService | None = None,
    ) -> None:
        """Initialize trip service with dependencies.

        Args:
            database_service: Database service instance
        """
        if database_service is None:
            from tripsage_core.services.infrastructure.database_service import (
                DatabaseService,
            )

            database_service = DatabaseService()

        # Explicit typing helps pyright infer method return types
        self.db: DatabaseService = database_service

    @tripsage_safe_execute()
    async def create_trip(
        self, user_id: str, trip_data: TripCreateRequest
    ) -> TripResponse:
        """Create a new trip.

        Args:
            user_id: Owner user ID
            trip_data: Trip creation data

        Returns:
            Created trip information

        Raises:
            ValidationError: If trip data is invalid
        """
        try:
            # Create Trip model instance
            trip = Trip(
                user_id=UUID(user_id),
                title=trip_data.title,
                description=trip_data.description,
                start_date=trip_data.start_date.date(),
                end_date=trip_data.end_date.date(),
                destination=trip_data.destination,
                budget_breakdown=trip_data.budget,
                travelers=trip_data.travelers,
                trip_type=trip_data.trip_type,
                visibility=trip_data.visibility,
                tags=trip_data.tags,
                preferences_extended=(
                    trip_data.preferences
                    if trip_data.preferences is not None
                    else TripPreferences()  # type: ignore
                ),
            )

            # Store in database
            result = await self.db.create_trip(trip.model_dump())

            logger.info(
                "Trip created successfully",
                extra={
                    "trip_id": str(trip.id),
                    "user_id": user_id,
                    "title": trip.title,
                },
            )

            return await self._build_trip_response(result)

        except Exception as e:
            logger.exception(
                "Failed to create trip", extra={"user_id": user_id, "error": str(e)}
            )
            raise

    @tripsage_safe_execute()
    async def get_trip(self, trip_id: str, user_id: str) -> TripResponse | None:
        """Get trip by ID.

        Args:
            trip_id: Trip ID
            user_id: Requesting user ID

        Returns:
            Trip information or None if not found/accessible
        """
        try:
            # Check access permissions
            if not await self._check_trip_access(trip_id, user_id):
                return None

            result = await self.db.get_trip_by_id(trip_id)
            if not result:
                return None

            return await self._build_trip_response(result)

        except Exception as e:
            logger.exception(
                "Failed to get trip",
                extra={"trip_id": trip_id, "user_id": user_id, "error": str(e)},
            )
            return None

    @tripsage_safe_execute()
    async def get_user_trips(
        self,
        user_id: str,
        *,
        status: TripStatus | None = None,
        visibility: TripVisibility | None = None,
        tag: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TripResponse]:
        """Get trips for a user with optional filters.

        Args:
            user_id: User ID
            status: Filter by trip status
            visibility: Filter by visibility
            tag: Filter by tag
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of trips
        """
        try:
            filters = {
                "user_id": user_id,
                "status": status.value if status else None,
                "visibility": visibility.value if visibility else None,
                "tag": tag,
            }

            # Remove None values
            filters = {k: v for k, v in filters.items() if v is not None}

            results = await self.db.select(
                "trips",
                "*",
                filters=filters,
                limit=limit,
                offset=offset,
                order_by="-created_at",
            )

            trips: list[TripResponse] = []
            for result in results:
                trip = await self._build_trip_response(result)
                trips.append(trip)

            return trips

        except Exception as e:
            logger.exception(
                "Failed to get user trips",
                extra={"user_id": user_id, "error": str(e)},
            )
            return []

    @tripsage_safe_execute()
    async def count_user_trips(self, user_id: str) -> int:
        """Count total trips for a user.

        Args:
            user_id: User ID

        Returns:
            Total count of user's trips
        """
        try:
            filters = {"user_id": user_id}
            return await self.db.count("trips", filters=filters)

        except Exception as e:
            logger.exception(
                "Failed to count user trips",
                extra={"user_id": user_id, "error": str(e)},
            )
            return 0

    @tripsage_safe_execute()
    async def update_trip(
        self, trip_id: str, user_id: str, update_data: TripUpdateRequest
    ) -> TripResponse | None:
        """Update a trip.

        Args:
            trip_id: Trip ID
            user_id: User ID making the update
            update_data: Update data

        Returns:
            Updated trip or None if not found/unauthorized

        Raises:
            PermissionError: If user doesn't have permission
            ValidationError: If update data is invalid
        """
        try:
            # Check access permissions
            if not await self._check_trip_access(trip_id, user_id, require_owner=True):
                raise CoreAuthorizationError(
                    "You don't have permission to update this trip"
                )

            # Get existing trip
            existing = await self.db.get_trip_by_id(trip_id)
            if not existing:
                return None

            # Prepare update dict
            updates = update_data.model_dump(exclude_unset=True)

            # Convert datetime to date for date fields
            if "start_date" in updates:
                updates["start_date"] = updates["start_date"].date()
            if "end_date" in updates:
                updates["end_date"] = updates["end_date"].date()

            # Validate date range if dates are being updated
            if "start_date" in updates or "end_date" in updates:
                start = updates.get("start_date", existing["start_date"])
                end = updates.get("end_date", existing["end_date"])
                if end < start:
                    raise CoreValidationError("End date must be after start date")

            # Update timestamp
            updates["updated_at"] = datetime.now(UTC)

            # Perform update
            result = await self.db.update_trip(trip_id, updates)

            logger.info(
                "Trip updated successfully",
                extra={
                    "trip_id": trip_id,
                    "user_id": user_id,
                    "updates": list(updates.keys()),
                },
            )

            return await self._build_trip_response(result)

        except PermissionError:
            raise
        except Exception as e:
            logger.exception(
                "Failed to update trip",
                extra={"trip_id": trip_id, "user_id": user_id, "error": str(e)},
            )
            raise

    @tripsage_safe_execute()
    async def delete_trip(self, trip_id: str, user_id: str) -> bool:
        """Delete a trip.

        Args:
            trip_id: Trip ID
            user_id: User ID making the deletion

        Returns:
            True if deleted, False if not found

        Raises:
            PermissionError: If user doesn't have permission
        """
        try:
            # Check access permissions
            if not await self._check_trip_access(trip_id, user_id, require_owner=True):
                raise CoreAuthorizationError(
                    "You don't have permission to delete this trip"
                )

            result = await self.db.delete_trip(trip_id)

            if result:
                logger.info(
                    "Trip deleted successfully",
                    extra={"trip_id": trip_id, "user_id": user_id},
                )

            return result

        except PermissionError:
            raise
        except Exception as e:
            logger.exception(
                "Failed to delete trip",
                extra={"trip_id": trip_id, "user_id": user_id, "error": str(e)},
            )
            return False

    @tripsage_safe_execute()
    async def share_trip(
        self,
        trip_id: str,
        owner_id: str,
        share_with_user_id: str,
        permission: str = "view",
    ) -> bool:
        """Share a trip with another user.

        Args:
            trip_id: Trip ID
            owner_id: Owner user ID
            share_with_user_id: User ID to share with
            permission: Permission level (view, edit)

        Returns:
            True if shared successfully

        Raises:
            PermissionError: If user doesn't have permission
            NotFoundError: If trip or user not found
        """
        try:
            # Verify owner
            if not await self._check_trip_access(trip_id, owner_id, require_owner=True):
                raise CoreAuthorizationError("Only the trip owner can share the trip")

            # Verify target user exists
            target_user = await fetch_user_by_id(share_with_user_id)
            if not target_user:
                raise CoreResourceNotFoundError("User not found")

            # Create collaborator record
            collaborator_data: JSONObject = {
                "trip_id": trip_id,
                "user_id": share_with_user_id,
                "permission": permission,
                "added_by": owner_id,
                "added_at": datetime.now(UTC).isoformat(),
            }

            result = await self.db.add_trip_collaborator(collaborator_data)

            if result:
                logger.info(
                    "Trip shared successfully",
                    extra={
                        "trip_id": trip_id,
                        "owner_id": owner_id,
                        "shared_with": share_with_user_id,
                        "permission": permission,
                    },
                )

            return bool(result)

        except (PermissionError, CoreResourceNotFoundError):
            raise
        except Exception as e:
            logger.exception(
                "Failed to share trip",
                extra={
                    "trip_id": trip_id,
                    "owner_id": owner_id,
                    "share_with": share_with_user_id,
                    "error": str(e),
                },
            )
            return False

    @tripsage_safe_execute()
    async def unshare_trip(
        self, trip_id: str, owner_id: str, unshare_user_id: str
    ) -> bool:
        """Remove trip sharing with a user.

        Args:
            trip_id: Trip ID
            owner_id: Owner user ID
            unshare_user_id: User ID to remove sharing

        Returns:
            True if unshared successfully

        Raises:
            PermissionError: If user doesn't have permission
        """
        try:
            # Verify owner
            if not await self._check_trip_access(trip_id, owner_id, require_owner=True):
                raise CoreAuthorizationError("Only the trip owner can unshare the trip")

            result = await self.db.delete(
                "trip_collaborators", {"trip_id": trip_id, "user_id": unshare_user_id}
            )

            if result:
                logger.info(
                    "Trip unshared successfully",
                    extra={
                        "trip_id": trip_id,
                        "owner_id": owner_id,
                        "unshared_from": unshare_user_id,
                    },
                )

            return bool(result)

        except PermissionError:
            raise
        except Exception as e:
            logger.exception(
                "Failed to unshare trip",
                extra={
                    "trip_id": trip_id,
                    "owner_id": owner_id,
                    "unshare_from": unshare_user_id,
                    "error": str(e),
                },
            )
            return False

    @tripsage_safe_execute()
    async def get_shared_trips(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[TripResponse]:
        """Get trips shared with a user.

        Args:
            user_id: User ID
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of shared trips
        """
        try:
            # Get trips where user is a collaborator
            collaborations = await self.db.select(
                "trip_collaborators", "*", filters={"user_id": user_id}
            )

            trips: list[TripResponse] = []
            for collab in collaborations:
                trip_id_value = collab.get("trip_id")
                if isinstance(trip_id_value, (str, UUID)):
                    trip_id_str = str(trip_id_value)
                else:
                    logger.warning(
                        "Collaboration record missing trip_id",
                        extra={"collaboration": collab},
                    )
                    continue

                result = await self.db.get_trip_by_id(trip_id_str)
                if result:
                    trip = await self._build_trip_response(result)
                    trips.append(trip)

            # Apply pagination
            return trips[offset : offset + limit]

        except Exception as e:
            logger.exception(
                "Failed to get shared trips",
                extra={"user_id": user_id, "error": str(e)},
            )
            return []

    @tripsage_safe_execute()
    async def search_trips(
        self,
        user_id: str,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TripResponse]:
        """Search trips by query and filters.

        Args:
            user_id: User ID
            query: Search query
            filters: Additional filters
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of matching trips
        """
        try:
            # Build search filters
            search_filters: JSONObject = {
                "user_id": user_id,
                "query": query,
            }
            if filters:
                for key, value in filters.items():
                    search_filters[str(key)] = self._coerce_json_value(value)

            # Perform search
            results = await self.db.search_trips(
                search_filters, limit=limit, offset=offset
            )

            trips: list[TripResponse] = []
            for result in results:
                # Check access
                trip_id_value = result.get("id")
                if isinstance(trip_id_value, (str, UUID)):
                    trip_id = str(trip_id_value)
                else:
                    continue

                if await self._check_trip_access(trip_id, user_id):
                    trip = await self._build_trip_response(result)
                    trips.append(trip)

            return trips

        except Exception as e:
            logger.exception(
                "Failed to search trips",
                extra={"user_id": user_id, "query": query, "error": str(e)},
            )
            return []

    @staticmethod
    def _coerce_json_value(value: Any) -> JSONValue:
        """Convert arbitrary values to JSONValue for database filtering."""
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, (list, tuple)):
            return [
                TripService._coerce_json_value(element)
                for element in cast(Sequence[Any], value)
            ]
        if isinstance(value, dict):
            generic_mapping = cast(dict[Any, Any], value)
            coerced: dict[str, JSONValue] = {}
            for key_obj, item_obj in generic_mapping.items():
                coerced[str(key_obj)] = TripService._coerce_json_value(item_obj)
            return coerced
        return str(value)

    async def _check_trip_access(
        self, trip_id: str, user_id: str, require_owner: bool = False
    ) -> bool:
        """Check if user has access to a trip.

        Args:
            trip_id: Trip ID
            user_id: User ID
            require_owner: Whether to require owner access

        Returns:
            True if user has access
        """
        trip = await self.db.get_trip_by_id(trip_id)
        if not trip:
            return False

        # Check if owner
        if str(trip["user_id"]) == user_id:
            return True

        # If owner access required, deny
        if require_owner:
            return False

        # Check if collaborator
        collaborators: list[dict[str, Any]] = await self.db.get_trip_collaborators(
            trip_id
        )
        for collab in collaborators:
            if collab["user_id"] == user_id:
                return True

        # Check if public
        return trip.get("visibility") == TripVisibility.PUBLIC

    async def _build_trip_response(self, trip_data: dict[str, Any]) -> TripResponse:
        """Build trip response from database data.

        Args:
            trip_data: Raw trip data from database

        Returns:
            Trip response model
        """
        # Get related counts
        counts: dict[str, int] = await self.db.get_trip_related_counts(trip_data["id"])

        # Get shared user IDs
        collaborators: list[dict[str, Any]] = await self.db.get_trip_collaborators(
            trip_data["id"]
        )
        shared_with: list[str] = [c["user_id"] for c in collaborators]

        # Build destinations
        destinations: list[TripLocation] = []
        raw_destinations = trip_data.get("destinations", [])
        if isinstance(raw_destinations, list):
            for dest_data in cast(list[Any], raw_destinations):
                if isinstance(dest_data, TripLocation):
                    destinations.append(dest_data)
                    continue

                if isinstance(dest_data, dict):
                    destination_payload = cast(dict[str, Any], dest_data)
                    destinations.append(TripLocation(**destination_payload))

        return TripResponse(
            id=UUID(trip_data["id"]),
            user_id=UUID(trip_data["user_id"]),
            title=trip_data["title"],
            description=trip_data.get("description"),
            start_date=trip_data["start_date"],
            end_date=trip_data["end_date"],
            destination=trip_data["destination"],
            destinations=destinations,
            budget=Budget(**trip_data["budget_breakdown"]),
            travelers=trip_data["travelers"],
            trip_type=TripType(trip_data["trip_type"]),
            status=TripStatus(trip_data["status"]),
            visibility=TripVisibility(trip_data["visibility"]),
            tags=trip_data.get("tags", []),
            preferences=TripPreferences(**trip_data.get("preferences_extended", {})),
            created_at=trip_data["created_at"],
            updated_at=trip_data["updated_at"],
            # Map known keys with safe fallbacks
            note_count=int(counts.get("notes", counts.get("messages", 0))),
            attachment_count=int(counts.get("attachments", 0)),
            collaborator_count=int(counts.get("collaborators", 0)),
            shared_with=shared_with,
        )


async def get_trip_service() -> TripService:
    """Get a configured TripService instance.

    Returns:
        TripService: Configured trip service instance
    """
    return TripService()


__all__ = [
    "TripCreateRequest",
    "TripResponse",
    "TripService",
    "TripUpdateRequest",
    "get_trip_service",
]
