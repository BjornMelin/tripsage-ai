"""Trip service for comprehensive trip management operations.

This service handles all trip-related business logic including trip creation,
retrieval, updates, sharing, and collaboration features.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from tripsage_core.exceptions import (
    CoreAuthorizationError as PermissionError,
)
from tripsage_core.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.models.schemas_common.enums import (
    TripStatus,
    TripType,
    TripVisibility,
)
from tripsage_core.models.trip import (
    EnhancedBudget,
    Trip,
    TripPreferences,
)

logger = logging.getLogger(__name__)


class TripLocation(TripSageModel):
    """Trip location information."""

    name: str = Field(..., description="Location name")
    country: Optional[str] = Field(None, description="Country")
    city: Optional[str] = Field(None, description="City")
    coordinates: Optional[Dict[str, float]] = Field(
        None, description="Lat/lng coordinates"
    )
    timezone: Optional[str] = Field(None, description="Location timezone")


class TripCreateRequest(TripSageModel):
    """Request model for trip creation."""

    title: str = Field(..., min_length=1, max_length=200, description="Trip title")
    description: Optional[str] = Field(
        None, max_length=2000, description="Trip description"
    )
    start_date: datetime = Field(..., description="Trip start date")
    end_date: datetime = Field(..., description="Trip end date")
    destination: str = Field(..., description="Primary destination")
    destinations: List[TripLocation] = Field(
        default_factory=list, description="Trip destinations"
    )
    budget: EnhancedBudget = Field(..., description="Trip budget with breakdown")
    travelers: int = Field(default=1, ge=1, description="Number of travelers")
    trip_type: TripType = Field(default=TripType.LEISURE, description="Type of trip")
    visibility: TripVisibility = Field(
        default=TripVisibility.PRIVATE, description="Trip visibility"
    )
    tags: List[str] = Field(default_factory=list, description="Trip tags")
    preferences: Optional[TripPreferences] = Field(None, description="Trip preferences")

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v, info):
        """Validate that end_date is after start_date."""
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class TripUpdateRequest(TripSageModel):
    """Request model for trip updates."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_date: Optional[datetime] = Field(None)
    end_date: Optional[datetime] = Field(None)
    destination: Optional[str] = Field(None)
    destinations: Optional[List[TripLocation]] = Field(None)
    budget: Optional[EnhancedBudget] = Field(None)
    travelers: Optional[int] = Field(None, ge=1)
    trip_type: Optional[TripType] = Field(None)
    visibility: Optional[TripVisibility] = Field(None)
    tags: Optional[List[str]] = Field(None)
    preferences: Optional[TripPreferences] = Field(None)
    status: Optional[TripStatus] = Field(None)


class TripResponse(TripSageModel):
    """Response model for trip data."""

    id: UUID = Field(..., description="Trip ID")
    user_id: UUID = Field(..., description="Owner user ID")
    title: str = Field(..., description="Trip title")
    description: Optional[str] = Field(None, description="Trip description")
    start_date: datetime = Field(..., description="Trip start date")
    end_date: datetime = Field(..., description="Trip end date")
    destination: str = Field(..., description="Primary destination")
    destinations: List[TripLocation] = Field(
        default_factory=list, description="Trip destinations"
    )
    budget: EnhancedBudget = Field(..., description="Trip budget with breakdown")
    travelers: int = Field(..., description="Number of travelers")
    trip_type: TripType = Field(..., description="Type of trip")
    status: TripStatus = Field(..., description="Trip status")
    visibility: TripVisibility = Field(..., description="Trip visibility")
    tags: List[str] = Field(default_factory=list, description="Trip tags")
    preferences: TripPreferences = Field(..., description="Trip preferences")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Related data counts
    note_count: int = Field(default=0, description="Number of notes")
    attachment_count: int = Field(default=0, description="Number of attachments")
    collaborator_count: int = Field(default=0, description="Number of collaborators")
    shared_with: List[str] = Field(
        default_factory=list, description="User IDs trip is shared with"
    )


class TripService:
    """Service for managing trips."""

    def __init__(self, database_service=None, user_service=None):
        """Initialize trip service with dependencies.

        Args:
            database_service: Database service instance
            user_service: User service instance
        """
        if database_service is None:
            from tripsage_core.services.infrastructure.database_service import (
                DatabaseService,
            )

            database_service = DatabaseService()

        if user_service is None:
            from tripsage_core.services.business.user_service import UserService

            user_service = UserService()

        self.db = database_service
        self.user_service = user_service

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
                preferences_extended=trip_data.preferences or TripPreferences(),
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
            logger.error(
                "Failed to create trip", extra={"user_id": user_id, "error": str(e)}
            )
            raise

    async def get_trip(self, trip_id: str, user_id: str) -> Optional[TripResponse]:
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
            logger.error(
                "Failed to get trip",
                extra={"trip_id": trip_id, "user_id": user_id, "error": str(e)},
            )
            return None

    async def get_user_trips(
        self,
        user_id: str,
        status: Optional[TripStatus] = None,
        visibility: Optional[TripVisibility] = None,
        tag: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[TripResponse]:
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

            results = await self.db.get_trips(
                filters=filters, limit=limit, offset=offset
            )

            trips = []
            for result in results:
                trip = await self._build_trip_response(result)
                trips.append(trip)

            return trips

        except Exception as e:
            logger.error(
                "Failed to get user trips",
                extra={"user_id": user_id, "error": str(e)},
            )
            return []

    async def count_user_trips(self, user_id: str) -> int:
        """Count total trips for a user.

        Args:
            user_id: User ID

        Returns:
            Total count of user's trips
        """
        try:
            filters = {"user_id": user_id}
            count = await self.db.count("trips", filters=filters)
            return count

        except Exception as e:
            logger.error(
                "Failed to count user trips",
                extra={"user_id": user_id, "error": str(e)},
            )
            return 0

    async def update_trip(
        self, trip_id: str, user_id: str, update_data: TripUpdateRequest
    ) -> Optional[TripResponse]:
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
                raise PermissionError("You don't have permission to update this trip")

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
                    raise ValidationError("End date must be after start date")

            # Update timestamp
            updates["updated_at"] = datetime.now(timezone.utc)

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
            logger.error(
                "Failed to update trip",
                extra={"trip_id": trip_id, "user_id": user_id, "error": str(e)},
            )
            raise

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
                raise PermissionError("You don't have permission to delete this trip")

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
            logger.error(
                "Failed to delete trip",
                extra={"trip_id": trip_id, "user_id": user_id, "error": str(e)},
            )
            return False

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
                raise PermissionError("Only the trip owner can share the trip")

            # Verify target user exists
            target_user = await self.user_service.get_user(share_with_user_id)
            if not target_user:
                raise NotFoundError("User not found")

            # Create collaborator record
            collaborator_data = {
                "trip_id": trip_id,
                "user_id": share_with_user_id,
                "permission": permission,
                "added_by": owner_id,
                "added_at": datetime.now(timezone.utc),
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

            return result

        except (PermissionError, NotFoundError):
            raise
        except Exception as e:
            logger.error(
                "Failed to share trip",
                extra={
                    "trip_id": trip_id,
                    "owner_id": owner_id,
                    "share_with": share_with_user_id,
                    "error": str(e),
                },
            )
            return False

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
                raise PermissionError("Only the trip owner can unshare the trip")

            result = await self.db.remove_trip_collaborator(trip_id, unshare_user_id)

            if result:
                logger.info(
                    "Trip unshared successfully",
                    extra={
                        "trip_id": trip_id,
                        "owner_id": owner_id,
                        "unshared_from": unshare_user_id,
                    },
                )

            return result

        except PermissionError:
            raise
        except Exception as e:
            logger.error(
                "Failed to unshare trip",
                extra={
                    "trip_id": trip_id,
                    "owner_id": owner_id,
                    "unshare_from": unshare_user_id,
                    "error": str(e),
                },
            )
            return False

    async def get_shared_trips(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[TripResponse]:
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
            collaborations = await self.db.get_user_collaborations(user_id)

            trips = []
            for collab in collaborations:
                result = await self.db.get_trip_by_id(collab["trip_id"])
                if result:
                    trip = await self._build_trip_response(result)
                    trips.append(trip)

            # Apply pagination
            return trips[offset : offset + limit]

        except Exception as e:
            logger.error(
                "Failed to get shared trips",
                extra={"user_id": user_id, "error": str(e)},
            )
            return []

    async def search_trips(
        self,
        user_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[TripResponse]:
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
            search_filters = {"user_id": user_id}
            if filters:
                search_filters.update(filters)

            # Perform search
            results = await self.db.search_trips(
                query=query, filters=search_filters, limit=limit, offset=offset
            )

            trips = []
            for result in results:
                # Check access
                if await self._check_trip_access(result["id"], user_id):
                    trip = await self._build_trip_response(result)
                    trips.append(trip)

            return trips

        except Exception as e:
            logger.error(
                "Failed to search trips",
                extra={"user_id": user_id, "query": query, "error": str(e)},
            )
            return []

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
        collaborators = await self.db.get_trip_collaborators(trip_id)
        for collab in collaborators:
            if collab["user_id"] == user_id:
                return True

        # Check if public
        if trip.get("visibility") == TripVisibility.PUBLIC:
            return True

        return False

    async def _build_trip_response(self, trip_data: Dict[str, Any]) -> TripResponse:
        """Build trip response from database data.

        Args:
            trip_data: Raw trip data from database

        Returns:
            Trip response model
        """
        # Get related counts
        counts = await self.db.get_trip_related_counts(trip_data["id"])

        # Get shared user IDs
        collaborators = await self.db.get_trip_collaborators(trip_data["id"])
        shared_with = [c["user_id"] for c in collaborators]

        # Build destinations
        destinations = []
        for dest_data in trip_data.get("destinations", []):
            if isinstance(dest_data, dict):
                destinations.append(TripLocation(**dest_data))

        return TripResponse(
            id=UUID(trip_data["id"]),
            user_id=UUID(trip_data["user_id"]),
            title=trip_data["title"],
            description=trip_data.get("description"),
            start_date=trip_data["start_date"],
            end_date=trip_data["end_date"],
            destination=trip_data["destination"],
            destinations=destinations,
            budget=EnhancedBudget(**trip_data["budget_breakdown"]),
            travelers=trip_data["travelers"],
            trip_type=TripType(trip_data["trip_type"]),
            status=TripStatus(trip_data["status"]),
            visibility=TripVisibility(trip_data["visibility"]),
            tags=trip_data.get("tags", []),
            preferences=TripPreferences(**trip_data.get("preferences_extended", {})),
            created_at=trip_data["created_at"],
            updated_at=trip_data["updated_at"],
            note_count=counts.get("notes", 0),
            attachment_count=counts.get("attachments", 0),
            collaborator_count=counts.get("collaborators", 0),
            shared_with=shared_with,
        )


async def get_trip_service() -> TripService:
    """Get a configured TripService instance.

    Returns:
        TripService: Configured trip service instance
    """
    return TripService()


__all__ = [
    "TripService",
    "TripCreateRequest",
    "TripUpdateRequest",
    "TripResponse",
    "get_trip_service",
]
