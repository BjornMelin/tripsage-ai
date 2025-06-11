"""
Trip service for comprehensive trip management operations.

This service handles all trip-related business logic including trip creation,
retrieval, updates, sharing, and collaboration features. It integrates with
external services and maintains proper data relationships.
"""

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

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
from tripsage_core.utils.schema_adapters import (
    SchemaAdapter,
    log_schema_usage,
    validate_schema_compatibility,
)

logger = logging.getLogger(__name__)


class TripStatus(str, Enum):
    """Trip status enumeration."""

    PLANNING = "planning"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TripVisibility(str, Enum):
    """Trip visibility enumeration."""

    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class TripBudget(TripSageModel):
    """Trip budget information."""

    total_budget: Optional[float] = Field(None, ge=0, description="Total trip budget")
    currency: str = Field(default="USD", description="Budget currency")
    spent_amount: float = Field(default=0.0, ge=0, description="Amount spent so far")
    categories: Dict[str, float] = Field(
        default_factory=dict, description="Budget by category"
    )


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
    destinations: List[TripLocation] = Field(
        default_factory=list, description="Trip destinations"
    )
    budget: Optional[TripBudget] = Field(None, description="Trip budget")
    visibility: TripVisibility = Field(
        default=TripVisibility.PRIVATE, description="Trip visibility"
    )
    tags: List[str] = Field(default_factory=list, description="Trip tags")
    preferences: Dict[str, Any] = Field(
        default_factory=dict, description="Trip preferences"
    )

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v, info):
        """Validate that end date is after start date."""
        if info.data.get("start_date") and v <= info.data["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class TripUpdateRequest(TripSageModel):
    """Request model for trip updates."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_date: Optional[datetime] = Field(None)
    end_date: Optional[datetime] = Field(None)
    destinations: Optional[List[TripLocation]] = Field(None)
    budget: Optional[TripBudget] = Field(None)
    status: Optional[TripStatus] = Field(None)
    visibility: Optional[TripVisibility] = Field(None)
    tags: Optional[List[str]] = Field(None)
    preferences: Optional[Dict[str, Any]] = Field(None)


class TripResponse(TripSageModel):
    """Response model for trip data."""

    id: str = Field(..., description="Trip ID")
    user_id: str = Field(..., description="Owner user ID")
    title: str = Field(..., description="Trip title")
    description: Optional[str] = Field(None, description="Trip description")
    start_date: datetime = Field(..., description="Trip start date")
    end_date: datetime = Field(..., description="Trip end date")
    destinations: List[TripLocation] = Field(
        default_factory=list, description="Trip destinations"
    )
    budget: Optional[TripBudget] = Field(None, description="Trip budget")
    status: TripStatus = Field(..., description="Trip status")
    visibility: TripVisibility = Field(..., description="Trip visibility")
    tags: List[str] = Field(default_factory=list, description="Trip tags")
    preferences: Dict[str, Any] = Field(
        default_factory=dict, description="Trip preferences"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    shared_with: List[str] = Field(
        default_factory=list, description="User IDs with access"
    )
    itinerary_count: int = Field(default=0, description="Number of itinerary items")
    flight_count: int = Field(default=0, description="Number of flights")
    accommodation_count: int = Field(default=0, description="Number of accommodations")


class TripShareRequest(TripSageModel):
    """Request model for trip sharing."""

    user_emails: List[str] = Field(..., description="Email addresses to share with")
    permission_level: str = Field(
        default="view", description="Permission level (view/edit)"
    )
    message: Optional[str] = Field(None, description="Optional message")


class TripCollaborator(TripSageModel):
    """Trip collaborator information."""

    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    permission_level: str = Field(..., description="Permission level")
    added_at: datetime = Field(..., description="When access was granted")


class TripService:
    """
    Comprehensive trip management service.

    This service handles:
    - Trip CRUD operations
    - Trip sharing and collaboration
    - Budget tracking
    - Status management
    - Search and filtering
    - Integration with other services (flights, accommodations, etc.)
    """

    def __init__(self, database_service=None, user_service=None):
        """
        Initialize the trip service.

        Args:
            database_service: Database service for persistence
            user_service: User service for user operations
        """
        # Import here to avoid circular imports
        if database_service is None:
            from tripsage_core.services.infrastructure import get_database_service

            database_service = get_database_service()

        if user_service is None:
            from tripsage_core.services.business.user_service import UserService

            user_service = UserService()

        self.db = database_service
        self.user_service = user_service

    async def create_trip(
        self, user_id: str, trip_data: TripCreateRequest
    ) -> TripResponse:
        """
        Create a new trip.

        Args:
            user_id: Owner user ID
            trip_data: Trip creation data

        Returns:
            Created trip information

        Raises:
            ValidationError: If trip data is invalid
        """
        try:
            # Generate trip ID
            trip_id = str(uuid.uuid4())

            # Prepare trip data for database using schema adapter
            api_trip_data = {
                "id": trip_id,
                "user_id": user_id,
                "title": trip_data.title,
                "name": trip_data.title,  # Map title to name for database
                "description": trip_data.description,
                "start_date": trip_data.start_date.isoformat(),
                "end_date": trip_data.end_date.isoformat(),
                "destinations": [dest.model_dump() for dest in trip_data.destinations],
                "budget": trip_data.budget.model_dump() if trip_data.budget else None,
                "status": TripStatus.PLANNING.value,
                "visibility": trip_data.visibility.value,
                "tags": trip_data.tags,
                "preferences": trip_data.preferences,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Convert to database format
            db_trip_data = SchemaAdapter.convert_api_trip_to_db(api_trip_data)

            # Store in database
            result = await self.db.create_trip(db_trip_data)

            logger.info(
                "Trip created successfully",
                extra={
                    "trip_id": trip_id,
                    "user_id": user_id,
                    "title": trip_data.title,
                },
            )

            return await self._build_trip_response(result)

        except Exception as e:
            logger.error(
                "Failed to create trip", extra={"user_id": user_id, "error": str(e)}
            )
            raise

    async def get_trip(self, trip_id: str, user_id: str) -> Optional[TripResponse]:
        """
        Get trip by ID.

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
        limit: int = 50,
        offset: int = 0,
    ) -> List[TripResponse]:
        """
        Get trips for a user.

        Args:
            user_id: User ID
            status: Optional status filter
            limit: Maximum number of trips to return
            offset: Number of trips to skip

        Returns:
            List of user's trips
        """
        try:
            filters = {"user_id": user_id}
            if status:
                filters["status"] = status.value

            results = await self.db.get_trips(filters, limit, offset)

            trips = []
            for result in results:
                trip = await self._build_trip_response(result)
                trips.append(trip)

            return trips

        except Exception as e:
            logger.error(
                "Failed to get user trips", extra={"user_id": user_id, "error": str(e)}
            )
            return []

    async def update_trip(
        self, trip_id: str, user_id: str, update_data: TripUpdateRequest
    ) -> TripResponse:
        """
        Update trip information.

        Args:
            trip_id: Trip ID
            user_id: Requesting user ID
            update_data: Update data

        Returns:
            Updated trip information

        Raises:
            NotFoundError: If trip not found
            PermissionError: If user doesn't have edit access
        """
        try:
            # Check edit permissions
            if not await self._check_trip_edit_access(trip_id, user_id):
                raise PermissionError("No permission to edit this trip")

            # Validate date constraints if both dates are being updated
            if update_data.start_date and update_data.end_date:
                if update_data.end_date <= update_data.start_date:
                    raise ValidationError("End date must be after start date")

            # Prepare update data
            db_update_data = update_data.model_dump(exclude_unset=True)

            # Convert datetime objects to ISO strings
            if "start_date" in db_update_data:
                db_update_data["start_date"] = db_update_data["start_date"].isoformat()
            if "end_date" in db_update_data:
                db_update_data["end_date"] = db_update_data["end_date"].isoformat()

            # Convert enum values to strings
            if "status" in db_update_data:
                db_update_data["status"] = db_update_data["status"].value
            if "visibility" in db_update_data:
                db_update_data["visibility"] = db_update_data["visibility"].value

            # Convert Pydantic models to dicts
            if "destinations" in db_update_data:
                db_update_data["destinations"] = [
                    dest.model_dump() for dest in db_update_data["destinations"]
                ]
            if "budget" in db_update_data and db_update_data["budget"]:
                db_update_data["budget"] = db_update_data["budget"].model_dump()

            db_update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Update in database
            result = await self.db.update_trip(trip_id, db_update_data)

            logger.info(
                "Trip updated successfully",
                extra={
                    "trip_id": trip_id,
                    "user_id": user_id,
                    "updated_fields": list(db_update_data.keys()),
                },
            )

            return await self._build_trip_response(result)

        except (NotFoundError, PermissionError, ValidationError):
            raise
        except Exception as e:
            logger.error(
                "Failed to update trip",
                extra={"trip_id": trip_id, "user_id": user_id, "error": str(e)},
            )
            raise

    async def delete_trip(self, trip_id: str, user_id: str) -> bool:
        """
        Delete a trip.

        Args:
            trip_id: Trip ID
            user_id: Requesting user ID

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If trip not found
            PermissionError: If user doesn't own the trip
        """
        try:
            # Check ownership
            trip = await self.get_trip(trip_id, user_id)
            if not trip:
                raise NotFoundError("Trip not found")

            if trip.user_id != user_id:
                raise PermissionError("Only trip owner can delete the trip")

            # Delete from database (cascade deletes related data)
            success = await self.db.delete_trip(trip_id)

            if success:
                logger.info(
                    "Trip deleted successfully",
                    extra={"trip_id": trip_id, "user_id": user_id},
                )

            return success

        except (NotFoundError, PermissionError):
            raise
        except Exception as e:
            logger.error(
                "Failed to delete trip",
                extra={"trip_id": trip_id, "user_id": user_id, "error": str(e)},
            )
            return False

    async def duplicate_trip(self, user_id: str, trip_id: str) -> TripResponse:
        """
        Duplicate an existing trip.

        Creates a copy of the specified trip with a "Copy of " prefix in the title.
        The new trip will be owned by the requesting user and will have the same
        destinations, budget, tags, and preferences as the original.

        Args:
            user_id: User ID who is duplicating the trip
            trip_id: ID of the trip to duplicate

        Returns:
            The newly created duplicate trip

        Raises:
            NotFoundError: If the original trip is not found
            PermissionError: If user doesn't have access to the original trip
            ValidationError: If trip data is invalid
        """
        try:
            # Get the original trip and check access
            original_trip = await self.get_trip(trip_id, user_id)
            if not original_trip:
                raise NotFoundError(
                    f"Trip with ID {trip_id} not found or not accessible"
                )

            # Create trip data for the duplicate
            duplicate_data = TripCreateRequest(
                title=f"Copy of {original_trip.title}",
                description=original_trip.description,
                start_date=original_trip.start_date,
                end_date=original_trip.end_date,
                destinations=original_trip.destinations,
                budget=original_trip.budget,
                visibility=TripVisibility.PRIVATE,  # New copies are private by default
                tags=original_trip.tags,
                preferences=original_trip.preferences,
            )

            # Create the duplicate trip
            duplicate_trip = await self.create_trip(user_id, duplicate_data)

            logger.info(
                "Trip duplicated successfully",
                extra={
                    "original_trip_id": trip_id,
                    "duplicate_trip_id": duplicate_trip.id,
                    "user_id": user_id,
                },
            )

            return duplicate_trip

        except (NotFoundError, PermissionError, ValidationError):
            raise
        except Exception as e:
            logger.error(
                "Failed to duplicate trip",
                extra={"trip_id": trip_id, "user_id": user_id, "error": str(e)},
            )
            raise

    async def share_trip(
        self, trip_id: str, owner_id: str, share_request: TripShareRequest
    ) -> List[TripCollaborator]:
        """
        Share trip with other users.

        Args:
            trip_id: Trip ID
            owner_id: Trip owner ID
            share_request: Share request data

        Returns:
            List of collaborators added

        Raises:
            NotFoundError: If trip not found
            PermissionError: If user doesn't own the trip
        """
        try:
            # Check ownership
            trip = await self.get_trip(trip_id, owner_id)
            if not trip or trip.user_id != owner_id:
                raise PermissionError("Only trip owner can share the trip")

            collaborators = []

            for email in share_request.user_emails:
                # Find user by email
                user = await self.user_service.get_user_by_email(email)
                if not user:
                    logger.warning(
                        "User not found for sharing",
                        extra={"email": email, "trip_id": trip_id},
                    )
                    continue

                # Add collaborator
                collaborator_data = {
                    "trip_id": trip_id,
                    "user_id": user.id,
                    "permission_level": share_request.permission_level,
                    "added_at": datetime.now(timezone.utc).isoformat(),
                    "added_by": owner_id,
                }

                await self.db.add_trip_collaborator(collaborator_data)

                collaborators.append(
                    TripCollaborator(
                        user_id=user.id,
                        email=user.email,
                        permission_level=share_request.permission_level,
                        added_at=datetime.now(timezone.utc),
                    )
                )

                logger.info(
                    "Trip shared with user",
                    extra={
                        "trip_id": trip_id,
                        "shared_with": user.id,
                        "permission": share_request.permission_level,
                    },
                )

            # Update trip visibility if sharing
            if collaborators and trip.visibility == TripVisibility.PRIVATE:
                await self.update_trip(
                    trip_id,
                    owner_id,
                    TripUpdateRequest(visibility=TripVisibility.SHARED),
                )

            return collaborators

        except (NotFoundError, PermissionError):
            raise
        except Exception as e:
            logger.error(
                "Failed to share trip",
                extra={"trip_id": trip_id, "owner_id": owner_id, "error": str(e)},
            )
            raise

    async def get_trip_collaborators(
        self, trip_id: str, user_id: str
    ) -> List[TripCollaborator]:
        """
        Get trip collaborators.

        Args:
            trip_id: Trip ID
            user_id: Requesting user ID

        Returns:
            List of trip collaborators
        """
        try:
            # Check access
            if not await self._check_trip_access(trip_id, user_id):
                return []

            results = await self.db.get_trip_collaborators(trip_id)

            collaborators = []
            for result in results:
                # Get user info
                user = await self.user_service.get_user_by_id(result["user_id"])
                if user:
                    collaborators.append(
                        TripCollaborator(
                            user_id=result["user_id"],
                            email=user.email,
                            permission_level=result["permission_level"],
                            added_at=datetime.fromisoformat(result["added_at"]),
                        )
                    )

            return collaborators

        except Exception as e:
            logger.error(
                "Failed to get trip collaborators",
                extra={"trip_id": trip_id, "user_id": user_id, "error": str(e)},
            )
            return []

    async def search_trips(
        self,
        user_id: str,
        query: Optional[str] = None,
        destinations: Optional[List[str]] = None,
        date_range: Optional[Dict[str, datetime]] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[TripResponse]:
        """
        Search trips with various filters.

        Args:
            user_id: User ID
            query: Text query for title/description
            destinations: Destination names to filter by
            date_range: Date range filter (start_date, end_date)
            tags: Tags to filter by
            limit: Maximum number of results

        Returns:
            List of matching trips
        """
        try:
            search_filters = {
                "user_id": user_id,
                "query": query,
                "destinations": destinations,
                "date_range": date_range,
                "tags": tags,
            }

            # Remove None values
            search_filters = {k: v for k, v in search_filters.items() if v is not None}

            results = await self.db.search_trips(search_filters, limit)

            trips = []
            for result in results:
                trip = await self._build_trip_response(result)
                trips.append(trip)

            return trips

        except Exception as e:
            logger.error(
                "Failed to search trips",
                extra={"user_id": user_id, "query": query, "error": str(e)},
            )
            return []

    async def update_collaborator_permissions(
        self, trip_id: str, collaborator_id: str, permission_level: str
    ) -> bool:
        """
        Update collaborator permissions for a trip.

        Args:
            trip_id: Trip ID
            collaborator_id: Collaborator user ID
            permission_level: New permission level

        Returns:
            True if updated successfully
        """
        try:
            # Update in database
            success = await self.db.update_trip_collaborator(
                trip_id=trip_id,
                user_id=collaborator_id,
                permission_level=permission_level,
            )

            if success:
                logger.info(
                    "Collaborator permissions updated",
                    extra={
                        "trip_id": trip_id,
                        "collaborator_id": collaborator_id,
                        "permission_level": permission_level,
                    },
                )

            return success

        except Exception as e:
            logger.error(
                "Failed to update collaborator permissions",
                extra={
                    "trip_id": trip_id,
                    "collaborator_id": collaborator_id,
                    "error": str(e),
                },
            )
            return False

    async def remove_collaborator(self, trip_id: str, collaborator_id: str) -> bool:
        """
        Remove a collaborator from a trip.

        Args:
            trip_id: Trip ID
            collaborator_id: Collaborator user ID to remove

        Returns:
            True if removed successfully
        """
        try:
            # Remove from database
            success = await self.db.remove_trip_collaborator(
                trip_id=trip_id, user_id=collaborator_id
            )

            if success:
                logger.info(
                    "Collaborator removed from trip",
                    extra={"trip_id": trip_id, "collaborator_id": collaborator_id},
                )

            return success

        except Exception as e:
            logger.error(
                "Failed to remove collaborator",
                extra={
                    "trip_id": trip_id,
                    "collaborator_id": collaborator_id,
                    "error": str(e),
                },
            )
            return False

    async def _check_trip_access(self, trip_id: str, user_id: str) -> bool:
        """
        Check if user has access to trip.

        Args:
            trip_id: Trip ID
            user_id: User ID

        Returns:
            True if user has access
        """
        try:
            # Check if user owns the trip
            trip_data = await self.db.get_trip_by_id(trip_id)
            if not trip_data:
                return False

            if trip_data["user_id"] == user_id:
                return True

            # Check if trip is shared with user
            collaborator = await self.db.get_trip_collaborator(trip_id, user_id)
            if collaborator:
                return True

            # Check if trip is public
            if trip_data.get("visibility") == TripVisibility.PUBLIC.value:
                return True

            return False

        except Exception:
            return False

    async def _check_trip_edit_access(self, trip_id: str, user_id: str) -> bool:
        """
        Check if user has edit access to trip.

        Args:
            trip_id: Trip ID
            user_id: User ID

        Returns:
            True if user has edit access
        """
        try:
            # Check if user owns the trip
            trip_data = await self.db.get_trip_by_id(trip_id)
            if not trip_data:
                return False

            if trip_data["user_id"] == user_id:
                return True

            # Check if user has edit permission as collaborator
            collaborator = await self.db.get_trip_collaborator(trip_id, user_id)
            if collaborator and collaborator["permission_level"] == "edit":
                return True

            return False

        except Exception:
            return False

    async def _build_trip_response(self, trip_data: Dict[str, Any]) -> TripResponse:
        """
        Build trip response from database data.

        Args:
            trip_data: Raw trip data from database

        Returns:
            Trip response model
        """
        # Validate schema compatibility
        if not validate_schema_compatibility(trip_data):
            logger.warning(
                f"Schema compatibility issues with trip {trip_data.get('id')}"
            )

        # Convert database format to API format using schema adapter
        api_trip_data = SchemaAdapter.convert_db_trip_to_api(trip_data)

        # Log schema usage for monitoring
        id_type = "uuid" if SchemaAdapter.is_uuid(api_trip_data["id"]) else "bigint"
        log_schema_usage(
            "build_trip_response",
            id_type,
            {
                "title_source": "title" if trip_data.get("title") else "name",
                "has_uuid": bool(trip_data.get("uuid_id")),
            },
        )

        # Get the proper trip ID for related data queries
        db_trip_id = trip_data.get("id") or trip_data.get("id_bigint")

        # Get related counts
        counts = await self.db.get_trip_related_counts(db_trip_id)

        # Get shared user IDs
        collaborators = await self.db.get_trip_collaborators(db_trip_id)
        shared_with = [c["user_id"] for c in collaborators]

        # Build destinations
        destinations = []
        for dest_data in api_trip_data.get("destinations", []):
            if isinstance(dest_data, dict):
                destinations.append(TripLocation(**dest_data))
            else:
                # Handle legacy destination format
                destinations.append(TripLocation(name=str(dest_data)))

        # Build budget
        budget = None
        budget_data = api_trip_data.get("budget")
        if budget_data and isinstance(budget_data, dict):
            budget = TripBudget(**budget_data)

        return TripResponse(
            id=api_trip_data["id"],
            user_id=api_trip_data["user_id"],
            title=api_trip_data["title"],
            description=api_trip_data.get("description"),
            start_date=datetime.fromisoformat(api_trip_data["start_date"])
            if isinstance(api_trip_data["start_date"], str)
            else api_trip_data["start_date"],
            end_date=datetime.fromisoformat(api_trip_data["end_date"])
            if isinstance(api_trip_data["end_date"], str)
            else api_trip_data["end_date"],
            destinations=destinations,
            budget=budget,
            status=TripStatus(api_trip_data["status"]),
            visibility=TripVisibility(api_trip_data["visibility"]),
            tags=api_trip_data.get("tags", []),
            preferences=api_trip_data.get("preferences", {}),
            created_at=datetime.fromisoformat(api_trip_data["created_at"])
            if isinstance(api_trip_data["created_at"], str)
            else api_trip_data["created_at"],
            updated_at=datetime.fromisoformat(api_trip_data["updated_at"])
            if isinstance(api_trip_data["updated_at"], str)
            else api_trip_data["updated_at"],
            shared_with=shared_with,
            itinerary_count=counts.get("itinerary_count", 0),
            flight_count=counts.get("flight_count", 0),
            accommodation_count=counts.get("accommodation_count", 0),
        )


# Dependency function for FastAPI
async def get_trip_service() -> TripService:
    """
    Get trip service instance for dependency injection.

    Returns:
        TripService instance
    """
    from tripsage_core.services.business.user_service import UserService
    from tripsage_core.services.infrastructure.database_service import (
        get_database_service,
    )

    database_service = await get_database_service()
    user_service = UserService(database_service=database_service)
    return TripService(database_service=database_service, user_service=user_service)
