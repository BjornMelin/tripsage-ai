"""
Itinerary service for comprehensive itinerary management operations.

This service consolidates itinerary-related business logic including itinerary
creation, item management, optimization, conflict detection, sharing, and
collaboration features. It provides clean abstractions over external services
while maintaining proper data relationships.
"""

import logging
from datetime import date as DateType
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import Field, field_validator

from tripsage_core.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel

logger = logging.getLogger(__name__)


class ItineraryItemType(str, Enum):
    """Itinerary item type enumeration."""

    FLIGHT = "flight"
    ACCOMMODATION = "accommodation"
    ACTIVITY = "activity"
    TRANSPORTATION = "transportation"
    MEAL = "meal"
    REST = "rest"
    MEETING = "meeting"
    OTHER = "other"


class ItineraryStatus(str, Enum):
    """Itinerary status enumeration."""

    DRAFT = "draft"
    PLANNED = "planned"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ItineraryVisibility(str, Enum):
    """Itinerary visibility enumeration."""

    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class ConflictType(str, Enum):
    """Conflict type enumeration."""

    TIME_OVERLAP = "time_overlap"
    LOCATION_CONFLICT = "location_conflict"
    BUDGET_EXCEEDED = "budget_exceeded"
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    BOOKING_CONFLICT = "booking_conflict"


class OptimizationGoal(str, Enum):
    """Optimization goal enumeration."""

    MINIMIZE_COST = "minimize_cost"
    MINIMIZE_TRAVEL_TIME = "minimize_travel_time"
    MAXIMIZE_EXPERIENCES = "maximize_experiences"
    BALANCE_ACTIVITIES = "balance_activities"
    MINIMIZE_STRESS = "minimize_stress"


class TimeSlot(TripSageModel):
    """Time slot information."""

    start_time: str = Field(
        ...,
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="Start time (HH:MM)",
    )
    end_time: str = Field(
        ..., pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="End time (HH:MM)"
    )
    duration_minutes: int = Field(..., ge=0, description="Duration in minutes")
    timezone: Optional[str] = Field(None, description="Timezone for the time slot")

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, v: int, info) -> int:
        """Validate duration matches start/end times."""
        if "start_time" in info.data and "end_time" in info.data:
            start_hour, start_minute = map(int, info.data["start_time"].split(":"))
            end_hour, end_minute = map(int, info.data["end_time"].split(":"))

            start_minutes = start_hour * 60 + start_minute
            end_minutes = end_hour * 60 + end_minute

            # Handle overnight slots
            if end_minutes < start_minutes:
                end_minutes += 24 * 60

            calculated_duration = end_minutes - start_minutes
            if abs(v - calculated_duration) > 1:  # Allow 1 minute tolerance
                v = calculated_duration

        return v


class Location(TripSageModel):
    """Location information."""

    name: str = Field(..., description="Location name")
    address: Optional[str] = Field(None, description="Full address")
    city: Optional[str] = Field(None, description="City")
    country: Optional[str] = Field(None, description="Country")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    place_id: Optional[str] = Field(
        None, description="External place ID (Google, etc.)"
    )


class ItineraryItem(TripSageModel):
    """Base itinerary item model."""

    id: str = Field(..., description="Item ID")
    item_type: ItineraryItemType = Field(..., description="Item type")
    title: str = Field(..., description="Item title")
    description: Optional[str] = Field(None, description="Item description")
    item_date: DateType = Field(..., description="Item date")
    time_slot: Optional[TimeSlot] = Field(None, description="Time slot")
    location: Optional[Location] = Field(None, description="Location")
    cost: Optional[float] = Field(None, ge=0, description="Item cost")
    currency: Optional[str] = Field(None, description="Currency code")
    booking_reference: Optional[str] = Field(None, description="Booking reference")
    notes: Optional[str] = Field(None, description="Additional notes")
    is_flexible: bool = Field(default=False, description="Whether timing is flexible")
    is_confirmed: bool = Field(default=False, description="Whether item is confirmed")
    created_by: Optional[str] = Field(None, description="User ID who created the item")

    # Type-specific data stored as dict for flexibility
    type_specific_data: Dict[str, Any] = Field(
        default_factory=dict, description="Type-specific data"
    )


class ItineraryConflict(TripSageModel):
    """Conflict information."""

    id: str = Field(..., description="Conflict ID")
    conflict_type: ConflictType = Field(..., description="Conflict type")
    severity: float = Field(..., ge=0, le=1, description="Conflict severity (0-1)")
    description: str = Field(..., description="Conflict description")
    affected_items: List[str] = Field(..., description="IDs of affected items")
    suggestions: List[str] = Field(
        default_factory=list, description="Resolution suggestions"
    )
    auto_resolvable: bool = Field(default=False, description="Whether auto-resolvable")


class ItineraryDay(TripSageModel):
    """Itinerary day model."""

    date: DateType = Field(..., description="Day date")
    items: List[ItineraryItem] = Field(default_factory=list, description="Day items")
    notes: Optional[str] = Field(None, description="Day notes")
    budget_allocated: Optional[float] = Field(
        None, ge=0, description="Budget allocated for the day"
    )
    budget_spent: Optional[float] = Field(
        None, ge=0, description="Budget spent for the day"
    )

    @property
    def sorted_items(self) -> List[ItineraryItem]:
        """Return items sorted by time."""

        def get_sort_key(item: ItineraryItem) -> str:
            if not item.time_slot:
                return "24:00"  # Put items without time at the end
            return item.time_slot.start_time

        return sorted(self.items, key=get_sort_key)


class ItineraryShareSettings(TripSageModel):
    """Itinerary sharing settings."""

    visibility: ItineraryVisibility = Field(
        default=ItineraryVisibility.PRIVATE, description="Visibility level"
    )
    shared_with: List[str] = Field(
        default_factory=list, description="User IDs with access"
    )
    editable_by: List[str] = Field(
        default_factory=list, description="User IDs with edit access"
    )
    share_link: Optional[str] = Field(None, description="Public share link")
    password_protected: bool = Field(
        default=False, description="Whether password protected"
    )
    expires_at: Optional[datetime] = Field(None, description="Share link expiration")


class ItineraryCreateRequest(TripSageModel):
    """Request model for creating an itinerary."""

    title: str = Field(..., min_length=1, max_length=200, description="Itinerary title")
    description: Optional[str] = Field(None, description="Itinerary description")
    start_date: DateType = Field(..., description="Start date")
    end_date: DateType = Field(..., description="End date")
    destinations: List[str] = Field(default_factory=list, description="Destination IDs")
    total_budget: Optional[float] = Field(None, ge=0, description="Total budget")
    currency: Optional[str] = Field(None, description="Currency code")
    tags: List[str] = Field(default_factory=list, description="Tags")
    trip_id: Optional[str] = Field(None, description="Associated trip ID")
    template_id: Optional[str] = Field(None, description="Template to base on")

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: DateType, info) -> DateType:
        """Validate end date is after start date."""
        if info.data.get("start_date") and v < info.data["start_date"]:
            raise ValueError("End date must be after or equal to start date")
        return v


class ItineraryUpdateRequest(TripSageModel):
    """Request model for updating an itinerary."""

    title: Optional[str] = Field(
        None, min_length=1, max_length=200, description="Itinerary title"
    )
    description: Optional[str] = Field(None, description="Itinerary description")
    status: Optional[ItineraryStatus] = Field(None, description="Itinerary status")
    start_date: Optional[DateType] = Field(None, description="Start date")
    end_date: Optional[DateType] = Field(None, description="End date")
    destinations: Optional[List[str]] = Field(None, description="Destination IDs")
    total_budget: Optional[float] = Field(None, ge=0, description="Total budget")
    currency: Optional[str] = Field(None, description="Currency code")
    tags: Optional[List[str]] = Field(None, description="Tags")
    share_settings: Optional[ItineraryShareSettings] = Field(
        None, description="Share settings"
    )


class Itinerary(TripSageModel):
    """Complete itinerary model."""

    id: str = Field(..., description="Itinerary ID")
    user_id: str = Field(..., description="Owner user ID")
    trip_id: Optional[str] = Field(None, description="Associated trip ID")
    title: str = Field(..., description="Itinerary title")
    description: Optional[str] = Field(None, description="Itinerary description")
    status: ItineraryStatus = Field(default=ItineraryStatus.DRAFT, description="Status")

    start_date: DateType = Field(..., description="Start date")
    end_date: DateType = Field(..., description="End date")

    days: List[ItineraryDay] = Field(default_factory=list, description="Itinerary days")
    destinations: List[str] = Field(default_factory=list, description="Destination IDs")

    total_budget: Optional[float] = Field(None, ge=0, description="Total budget")
    budget_spent: Optional[float] = Field(None, ge=0, description="Budget spent")
    currency: Optional[str] = Field(None, description="Currency code")

    tags: List[str] = Field(default_factory=list, description="Tags")
    share_settings: ItineraryShareSettings = Field(
        default_factory=ItineraryShareSettings, description="Share settings"
    )

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Collaboration
    collaborators: List[str] = Field(
        default_factory=list, description="Collaborator user IDs"
    )
    version: int = Field(
        default=1, description="Version number for conflict resolution"
    )

    @property
    def duration_days(self) -> int:
        """Calculate duration in days."""
        return (self.end_date - self.start_date).days + 1


class ItineraryItemCreateRequest(TripSageModel):
    """Request model for creating an itinerary item."""

    item_type: ItineraryItemType = Field(..., description="Item type")
    title: str = Field(..., min_length=1, max_length=200, description="Item title")
    description: Optional[str] = Field(None, description="Item description")
    item_date: DateType = Field(..., description="Item date")
    time_slot: Optional[TimeSlot] = Field(None, description="Time slot")
    location: Optional[Location] = Field(None, description="Location")
    cost: Optional[float] = Field(None, ge=0, description="Item cost")
    currency: Optional[str] = Field(None, description="Currency code")
    booking_reference: Optional[str] = Field(None, description="Booking reference")
    notes: Optional[str] = Field(None, description="Additional notes")
    is_flexible: bool = Field(default=False, description="Whether timing is flexible")
    type_specific_data: Optional[Dict[str, Any]] = Field(
        None, description="Type-specific data"
    )


class OptimizationSettings(TripSageModel):
    """Itinerary optimization settings."""

    goals: List[OptimizationGoal] = Field(..., description="Optimization goals")
    prioritize_cost: bool = Field(default=False, description="Prioritize cost savings")
    minimize_travel_time: bool = Field(default=True, description="Minimize travel time")
    include_breaks: bool = Field(default=True, description="Include breaks")
    break_duration_minutes: int = Field(default=30, ge=0, description="Break duration")
    start_day_time: Optional[str] = Field(None, description="Preferred day start time")
    end_day_time: Optional[str] = Field(None, description="Preferred day end time")
    meal_preferences: Optional[Dict[str, str]] = Field(
        None, description="Meal time preferences"
    )
    max_daily_budget: Optional[float] = Field(
        None, ge=0, description="Maximum daily budget"
    )


class ItineraryOptimizeRequest(TripSageModel):
    """Request model for optimizing an itinerary."""

    itinerary_id: str = Field(..., description="Itinerary ID to optimize")
    settings: OptimizationSettings = Field(..., description="Optimization settings")
    preserve_confirmed: bool = Field(
        default=True, description="Preserve confirmed items"
    )


class ItineraryOptimizeResponse(TripSageModel):
    """Response model for itinerary optimization."""

    original_itinerary: Itinerary = Field(..., description="Original itinerary")
    optimized_itinerary: Itinerary = Field(..., description="Optimized itinerary")
    changes: List[Dict[str, Any]] = Field(..., description="Changes made")
    optimization_score: float = Field(..., ge=0, le=1, description="Optimization score")
    estimated_savings: Optional[Dict[str, float]] = Field(
        None, description="Estimated savings"
    )


class ItinerarySearchRequest(TripSageModel):
    """Request model for searching itineraries."""

    query: Optional[str] = Field(None, description="Search query")
    status: Optional[ItineraryStatus] = Field(None, description="Status filter")
    start_date_from: Optional[DateType] = Field(
        None, description="Start date filter (from)"
    )
    start_date_to: Optional[DateType] = Field(
        None, description="Start date filter (to)"
    )
    destinations: Optional[List[str]] = Field(None, description="Destination filters")
    tags: Optional[List[str]] = Field(None, description="Tag filters")
    shared_only: bool = Field(default=False, description="Only shared itineraries")
    limit: int = Field(default=20, ge=1, le=100, description="Result limit")
    offset: int = Field(default=0, ge=0, description="Result offset")


class ItineraryService:
    """
    Comprehensive itinerary service for creation, management, and optimization.

    This service handles:
    - Complete itinerary CRUD operations
    - Itinerary item management (flights, accommodations, activities, etc.)
    - Conflict detection and resolution
    - Itinerary optimization algorithms
    - Sharing and collaboration features
    - Budget tracking and management
    - Template creation and management
    - Real-time collaborative editing
    """

    def __init__(
        self,
        database_service=None,
        external_calendar_service=None,
        optimization_engine=None,
        cache_ttl: int = 1800,
    ):
        """
        Initialize the itinerary service.

        Args:
            database_service: Database service for persistence
            external_calendar_service: External calendar service
            optimization_engine: Optimization engine for itinerary optimization
            cache_ttl: Cache TTL in seconds
        """
        # Import here to avoid circular imports
        if database_service is None:
            from tripsage_core.services.infrastructure import get_database_service

            database_service = get_database_service()

        if external_calendar_service is None:
            try:
                from tripsage_core.services.external_apis.calendar_service import (
                    GoogleCalendarService as CalendarService,
                )

                external_calendar_service = CalendarService()
            except ImportError:
                logger.warning("External calendar service not available")
                external_calendar_service = None

        if optimization_engine is None:
            # TODO: Implement external optimization engine
            # from tripsage.services.external.optimization_engine import (
            #     OptimizationEngine
            # )
            # optimization_engine = OptimizationEngine()
            # Optimization engine is optional - will use basic optimization
            optimization_engine = None

        self.db = database_service
        self.calendar_service = external_calendar_service
        self.optimization_engine = optimization_engine
        self.cache_ttl = cache_ttl

        # In-memory cache
        self._itinerary_cache: Dict[str, tuple] = {}
        self._conflict_cache: Dict[str, tuple] = {}

    async def create_itinerary(
        self, user_id: str, create_request: ItineraryCreateRequest
    ) -> Itinerary:
        """
        Create a new itinerary.

        Args:
            user_id: User ID
            create_request: Itinerary creation request

        Returns:
            Created itinerary

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If creation fails
        """
        try:
            itinerary_id = str(uuid4())
            now = datetime.now(timezone.utc)

            # Create empty days for the date range
            days = []
            current_date: DateType = create_request.start_date
            while current_date <= create_request.end_date:
                days.append(ItineraryDay(date=current_date))
                current_date += timedelta(days=1)

            # If template specified, apply template
            if create_request.template_id:
                template_data = await self._apply_template(
                    create_request.template_id, days
                )
                if template_data:
                    days = template_data.get("days", days)

            itinerary = Itinerary(
                id=itinerary_id,
                user_id=user_id,
                trip_id=create_request.trip_id,
                title=create_request.title,
                description=create_request.description,
                start_date=create_request.start_date,
                end_date=create_request.end_date,
                days=days,
                destinations=create_request.destinations,
                total_budget=create_request.total_budget,
                currency=create_request.currency,
                tags=create_request.tags,
                created_at=now,
                updated_at=now,
            )

            # Store in database
            await self._store_itinerary(itinerary)

            logger.info(
                "Itinerary created successfully",
                extra={
                    "itinerary_id": itinerary_id,
                    "user_id": user_id,
                    "title": create_request.title,
                },
            )

            return itinerary

        except Exception as e:
            logger.error(
                "Failed to create itinerary",
                extra={
                    "user_id": user_id,
                    "title": create_request.title,
                    "error": str(e),
                },
            )
            raise ServiceError(f"Failed to create itinerary: {str(e)}") from e

    async def get_itinerary(
        self, itinerary_id: str, user_id: str, check_access: bool = True
    ) -> Optional[Itinerary]:
        """
        Get an itinerary by ID.

        Args:
            itinerary_id: Itinerary ID
            user_id: User ID for access control
            check_access: Whether to check user access

        Returns:
            Itinerary or None if not found
        """
        try:
            # Check cache first
            cache_key = f"itinerary_{itinerary_id}"
            cached_result = self._get_cached_itinerary(cache_key)

            if cached_result:
                itinerary = cached_result
            else:
                # Get from database
                itinerary_data = await self.db.get_itinerary(itinerary_id)
                if not itinerary_data:
                    return None

                itinerary = Itinerary(**itinerary_data)

                # Cache the result
                self._cache_itinerary(cache_key, itinerary)

            # Check access permissions
            if check_access and not await self._check_access(itinerary, user_id):
                raise PermissionError("Access denied to itinerary")

            return itinerary

        except PermissionError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get itinerary",
                extra={
                    "itinerary_id": itinerary_id,
                    "user_id": user_id,
                    "error": str(e),
                },
            )
            return None

    async def update_itinerary(
        self, itinerary_id: str, user_id: str, update_request: ItineraryUpdateRequest
    ) -> Itinerary:
        """
        Update an existing itinerary.

        Args:
            itinerary_id: Itinerary ID
            user_id: User ID
            update_request: Update request

        Returns:
            Updated itinerary

        Raises:
            NotFoundError: If itinerary not found
            PermissionError: If user lacks permission
            ServiceError: If update fails
        """
        try:
            itinerary = await self.get_itinerary(itinerary_id, user_id)
            if not itinerary:
                raise NotFoundError("Itinerary not found")

            # Check edit permissions
            if not await self._check_edit_access(itinerary, user_id):
                raise PermissionError("Edit access denied")

            # Update fields
            updated = False
            if update_request.title is not None:
                itinerary.title = update_request.title
                updated = True

            if update_request.description is not None:
                itinerary.description = update_request.description
                updated = True

            if update_request.status is not None:
                itinerary.status = update_request.status
                updated = True

            # Handle date changes
            if update_request.start_date or update_request.end_date:
                new_start = update_request.start_date or itinerary.start_date
                new_end = update_request.end_date or itinerary.end_date

                if new_end < new_start:
                    raise ValidationError("End date must be after start date")

                # Update days if dates changed
                if new_start != itinerary.start_date or new_end != itinerary.end_date:
                    itinerary.start_date = new_start
                    itinerary.end_date = new_end
                    itinerary.days = await self._adjust_days(
                        itinerary.days, new_start, new_end
                    )
                    updated = True

            if update_request.destinations is not None:
                itinerary.destinations = update_request.destinations
                updated = True

            if update_request.total_budget is not None:
                itinerary.total_budget = update_request.total_budget
                updated = True

            if update_request.currency is not None:
                itinerary.currency = update_request.currency
                updated = True

            if update_request.tags is not None:
                itinerary.tags = update_request.tags
                updated = True

            if update_request.share_settings is not None:
                itinerary.share_settings = update_request.share_settings
                updated = True

            if updated:
                itinerary.updated_at = datetime.now(timezone.utc)
                itinerary.version += 1

                # Store updated itinerary
                await self._store_itinerary(itinerary)

                # Clear cache
                self._clear_itinerary_cache(itinerary_id)

            return itinerary

        except (NotFoundError, PermissionError, ValidationError):
            raise
        except Exception as e:
            logger.error(
                "Failed to update itinerary",
                extra={
                    "itinerary_id": itinerary_id,
                    "user_id": user_id,
                    "error": str(e),
                },
            )
            raise ServiceError(f"Failed to update itinerary: {str(e)}") from e

    async def add_item_to_itinerary(
        self, itinerary_id: str, user_id: str, item_request: ItineraryItemCreateRequest
    ) -> ItineraryItem:
        """
        Add an item to an itinerary.

        Args:
            itinerary_id: Itinerary ID
            user_id: User ID
            item_request: Item creation request

        Returns:
            Created itinerary item

        Raises:
            NotFoundError: If itinerary not found
            ValidationError: If item data is invalid
            ServiceError: If addition fails
        """
        try:
            itinerary = await self.get_itinerary(itinerary_id, user_id)
            if not itinerary:
                raise NotFoundError("Itinerary not found")

            # Check edit permissions
            if not await self._check_edit_access(itinerary, user_id):
                raise PermissionError("Edit access denied")

            # Validate item date is within itinerary range
            if (
                item_request.item_date < itinerary.start_date
                or item_request.item_date > itinerary.end_date
            ):
                raise ValidationError("Item date is outside itinerary date range")

            # Create item
            item_id = str(uuid4())
            item = ItineraryItem(
                id=item_id,
                item_type=item_request.item_type,
                title=item_request.title,
                description=item_request.description,
                item_date=item_request.item_date,
                time_slot=item_request.time_slot,
                location=item_request.location,
                cost=item_request.cost,
                currency=item_request.currency,
                booking_reference=item_request.booking_reference,
                notes=item_request.notes,
                is_flexible=item_request.is_flexible,
                created_by=user_id,
                type_specific_data=item_request.type_specific_data or {},
            )

            # Add to appropriate day
            for day in itinerary.days:
                if day.date == item_request.item_date:
                    day.items.append(item)
                    break
            else:
                raise ValidationError(f"No day found for date {item_request.item_date}")

            # Update budget if cost specified
            if item.cost:
                if itinerary.budget_spent is None:
                    itinerary.budget_spent = 0
                itinerary.budget_spent += item.cost

            # Update itinerary
            itinerary.updated_at = datetime.now(timezone.utc)
            itinerary.version += 1

            # Store updated itinerary
            await self._store_itinerary(itinerary)

            # Clear cache
            self._clear_itinerary_cache(itinerary_id)

            logger.info(
                "Item added to itinerary",
                extra={
                    "item_id": item_id,
                    "itinerary_id": itinerary_id,
                    "user_id": user_id,
                    "item_type": item_request.item_type.value,
                },
            )

            return item

        except (NotFoundError, PermissionError, ValidationError):
            raise
        except Exception as e:
            logger.error(
                "Failed to add item to itinerary",
                extra={
                    "itinerary_id": itinerary_id,
                    "user_id": user_id,
                    "error": str(e),
                },
            )
            raise ServiceError(f"Failed to add item: {str(e)}") from e

    async def detect_conflicts(
        self, itinerary_id: str, user_id: str
    ) -> List[ItineraryConflict]:
        """
        Detect conflicts in an itinerary.

        Args:
            itinerary_id: Itinerary ID
            user_id: User ID

        Returns:
            List of detected conflicts
        """
        try:
            itinerary = await self.get_itinerary(itinerary_id, user_id)
            if not itinerary:
                return []

            # Check cache first
            cache_key = f"conflicts_{itinerary_id}_{itinerary.version}"
            cached_conflicts = self._get_cached_conflicts(cache_key)
            if cached_conflicts:
                return cached_conflicts

            conflicts = []

            # Check for time conflicts
            time_conflicts = await self._detect_time_conflicts(itinerary)
            conflicts.extend(time_conflicts)

            # Check for location conflicts
            location_conflicts = await self._detect_location_conflicts(itinerary)
            conflicts.extend(location_conflicts)

            # Check for budget conflicts
            budget_conflicts = await self._detect_budget_conflicts(itinerary)
            conflicts.extend(budget_conflicts)

            # Check for impossible travel scenarios
            travel_conflicts = await self._detect_travel_conflicts(itinerary)
            conflicts.extend(travel_conflicts)

            # Cache conflicts
            self._cache_conflicts(cache_key, conflicts)

            return conflicts

        except Exception as e:
            logger.error(
                "Failed to detect conflicts",
                extra={"itinerary_id": itinerary_id, "error": str(e)},
            )
            return []

    async def optimize_itinerary(
        self, user_id: str, optimize_request: ItineraryOptimizeRequest
    ) -> ItineraryOptimizeResponse:
        """
        Optimize an itinerary based on settings.

        Args:
            user_id: User ID
            optimize_request: Optimization request

        Returns:
            Optimization response with original and optimized itineraries

        Raises:
            NotFoundError: If itinerary not found
            ServiceError: If optimization fails
        """
        try:
            original_itinerary = await self.get_itinerary(
                optimize_request.itinerary_id, user_id
            )
            if not original_itinerary:
                raise NotFoundError("Itinerary not found")

            # Check edit permissions
            if not await self._check_edit_access(original_itinerary, user_id):
                raise PermissionError("Edit access denied")

            # Create copy for optimization
            optimized_itinerary = Itinerary(**original_itinerary.model_dump())
            changes = []

            # Apply optimization algorithms
            if self.optimization_engine:
                optimization_result = await self.optimization_engine.optimize(
                    optimized_itinerary, optimize_request.settings
                )
                optimized_itinerary = optimization_result["itinerary"]
                changes = optimization_result["changes"]
                optimization_score = optimization_result["score"]
            else:
                # Basic optimization without external engine
                optimization_result = await self._basic_optimization(
                    optimized_itinerary,
                    optimize_request.settings,
                    optimize_request.preserve_confirmed,
                )
                optimized_itinerary = optimization_result["itinerary"]
                changes = optimization_result["changes"]
                optimization_score = optimization_result["score"]

            # Calculate estimated savings
            estimated_savings = await self._calculate_savings(
                original_itinerary, optimized_itinerary
            )

            logger.info(
                "Itinerary optimized",
                extra={
                    "itinerary_id": optimize_request.itinerary_id,
                    "user_id": user_id,
                    "changes_count": len(changes),
                    "optimization_score": optimization_score,
                },
            )

            return ItineraryOptimizeResponse(
                original_itinerary=original_itinerary,
                optimized_itinerary=optimized_itinerary,
                changes=changes,
                optimization_score=optimization_score,
                estimated_savings=estimated_savings,
            )

        except (NotFoundError, PermissionError):
            raise
        except Exception as e:
            logger.error(
                "Failed to optimize itinerary",
                extra={
                    "itinerary_id": optimize_request.itinerary_id,
                    "user_id": user_id,
                    "error": str(e),
                },
            )
            raise ServiceError(f"Failed to optimize itinerary: {str(e)}") from e

    async def search_itineraries(
        self, user_id: str, search_request: ItinerarySearchRequest
    ) -> List[Itinerary]:
        """
        Search itineraries for a user.

        Args:
            user_id: User ID
            search_request: Search parameters

        Returns:
            List of matching itineraries
        """
        try:
            filters = {"user_id": user_id}

            if search_request.status:
                filters["status"] = search_request.status.value

            if search_request.start_date_from:
                filters["start_date_from"] = search_request.start_date_from

            if search_request.start_date_to:
                filters["start_date_to"] = search_request.start_date_to

            if search_request.destinations:
                filters["destinations"] = search_request.destinations

            if search_request.tags:
                filters["tags"] = search_request.tags

            if search_request.shared_only:
                filters["shared_only"] = True

            results = await self.db.search_itineraries(
                filters,
                search_request.query,
                search_request.limit,
                search_request.offset,
            )

            itineraries = []
            for result in results:
                itineraries.append(Itinerary(**result))

            return itineraries

        except Exception as e:
            logger.error(
                "Failed to search itineraries",
                extra={"user_id": user_id, "error": str(e)},
            )
            return []

    async def delete_itinerary(self, itinerary_id: str, user_id: str) -> bool:
        """
        Delete an itinerary.

        Args:
            itinerary_id: Itinerary ID
            user_id: User ID

        Returns:
            True if deleted successfully
        """
        try:
            itinerary = await self.get_itinerary(itinerary_id, user_id)
            if not itinerary:
                raise NotFoundError("Itinerary not found")

            # Check permissions (only owner can delete)
            if itinerary.user_id != user_id:
                raise PermissionError("Only owner can delete itinerary")

            # Delete from database
            success = await self.db.delete_itinerary(itinerary_id)

            if success:
                # Clear cache
                self._clear_itinerary_cache(itinerary_id)

                logger.info(
                    "Itinerary deleted",
                    extra={"itinerary_id": itinerary_id, "user_id": user_id},
                )

            return success

        except (NotFoundError, PermissionError):
            raise
        except Exception as e:
            logger.error(
                "Failed to delete itinerary",
                extra={
                    "itinerary_id": itinerary_id,
                    "user_id": user_id,
                    "error": str(e),
                },
            )
            return False

    async def _apply_template(
        self, template_id: str, days: List[ItineraryDay]
    ) -> Optional[Dict[str, Any]]:
        """Apply a template to itinerary days."""
        try:
            template_data = await self.db.get_itinerary_template(template_id)
            if not template_data:
                return None

            # Apply template logic here
            # This would populate days with template items
            return {"days": days}

        except Exception as e:
            logger.warning(
                "Failed to apply template",
                extra={"template_id": template_id, "error": str(e)},
            )
            return None

    async def _adjust_days(
        self, current_days: List[ItineraryDay], new_start: DateType, new_end: DateType
    ) -> List[ItineraryDay]:
        """Adjust days list for new date range."""
        # Create a dict of existing days by date
        existing_days = {day.date: day for day in current_days}

        # Create new days list
        new_days = []
        current_date: DateType = new_start
        while current_date <= new_end:
            if current_date in existing_days:
                new_days.append(existing_days[current_date])
            else:
                new_days.append(ItineraryDay(date=current_date))
            current_date += timedelta(days=1)

        return new_days

    async def _check_access(self, itinerary: Itinerary, user_id: str) -> bool:
        """Check if user has access to itinerary."""
        # Owner always has access
        if itinerary.user_id == user_id:
            return True

        # Check if shared with user
        if user_id in itinerary.share_settings.shared_with:
            return True

        # Check if public
        if itinerary.share_settings.visibility == ItineraryVisibility.PUBLIC:
            return True

        return False

    async def _check_edit_access(self, itinerary: Itinerary, user_id: str) -> bool:
        """Check if user has edit access to itinerary."""
        # Owner always has edit access
        if itinerary.user_id == user_id:
            return True

        # Check if user is in editable_by list
        if user_id in itinerary.share_settings.editable_by:
            return True

        return False

    async def _detect_time_conflicts(
        self, itinerary: Itinerary
    ) -> List[ItineraryConflict]:
        """Detect time-based conflicts."""
        conflicts = []

        for day in itinerary.days:
            items_with_time = [item for item in day.items if item.time_slot]
            items_with_time.sort(key=lambda x: x.time_slot.start_time)

            for i in range(len(items_with_time) - 1):
                current = items_with_time[i]
                next_item = items_with_time[i + 1]

                current_end = current.time_slot.end_time
                next_start = next_item.time_slot.start_time

                # Convert to minutes for comparison
                current_end_minutes = self._time_to_minutes(current_end)
                next_start_minutes = self._time_to_minutes(next_start)

                if next_start_minutes < current_end_minutes:
                    conflict = ItineraryConflict(
                        id=str(uuid4()),
                        conflict_type=ConflictType.TIME_OVERLAP,
                        severity=0.8,
                        description=(
                            f"Time overlap between '{current.title}' and "
                            f"'{next_item.title}'"
                        ),
                        affected_items=[current.id, next_item.id],
                        suggestions=[
                            "Adjust start/end times",
                            "Move one item to different time",
                            "Remove one of the conflicting items",
                        ],
                        auto_resolvable=True,
                    )
                    conflicts.append(conflict)

        return conflicts

    async def _detect_location_conflicts(
        self, itinerary: Itinerary
    ) -> List[ItineraryConflict]:
        """Detect location-based conflicts."""
        conflicts = []
        # Implementation for location conflict detection
        return conflicts

    async def _detect_budget_conflicts(
        self, itinerary: Itinerary
    ) -> List[ItineraryConflict]:
        """Detect budget-related conflicts."""
        conflicts = []

        if itinerary.total_budget and itinerary.budget_spent:
            if itinerary.budget_spent > itinerary.total_budget:
                conflict = ItineraryConflict(
                    id=str(uuid4()),
                    conflict_type=ConflictType.BUDGET_EXCEEDED,
                    severity=0.9,
                    description=(
                        f"Budget exceeded: spent {itinerary.budget_spent} "
                        f"of {itinerary.total_budget}"
                    ),
                    affected_items=[],
                    suggestions=[
                        "Increase total budget",
                        "Remove expensive items",
                        "Find cheaper alternatives",
                    ],
                    auto_resolvable=False,
                )
                conflicts.append(conflict)

        return conflicts

    async def _detect_travel_conflicts(
        self, itinerary: Itinerary
    ) -> List[ItineraryConflict]:
        """Detect impossible travel scenarios."""
        conflicts = []
        # Implementation for travel conflict detection
        return conflicts

    async def _basic_optimization(
        self,
        itinerary: Itinerary,
        settings: OptimizationSettings,
        preserve_confirmed: bool,
    ) -> Dict[str, Any]:
        """Basic optimization without external engine."""
        changes = []

        # Simple time-based optimization
        for day in itinerary.days:
            items_with_time = [
                item
                for item in day.items
                if item.time_slot and (not preserve_confirmed or not item.is_confirmed)
            ]

            if not items_with_time:
                continue

            # Sort by priority (confirmed items first, then by start time)
            items_with_time.sort(
                key=lambda x: (not x.is_confirmed, x.time_slot.start_time)
            )

            # Redistribute times with breaks
            if settings.start_day_time and settings.end_day_time:
                start_minutes = self._time_to_minutes(settings.start_day_time)
                current_minutes = start_minutes

                for item in items_with_time:
                    if item.is_confirmed and preserve_confirmed:
                        continue

                    old_start = item.time_slot.start_time
                    old_end = item.time_slot.end_time

                    # Set new start time
                    new_start = self._minutes_to_time(current_minutes)
                    new_end_minutes = current_minutes + item.time_slot.duration_minutes
                    new_end = self._minutes_to_time(new_end_minutes)

                    if old_start != new_start or old_end != new_end:
                        item.time_slot.start_time = new_start
                        item.time_slot.end_time = new_end

                        changes.append(
                            {
                                "item_id": item.id,
                                "type": "time_adjustment",
                                "old_start": old_start,
                                "old_end": old_end,
                                "new_start": new_start,
                                "new_end": new_end,
                            }
                        )

                    # Add break time
                    current_minutes = new_end_minutes + settings.break_duration_minutes

        # Calculate optimization score based on changes made
        optimization_score = min(1.0, len(changes) * 0.1)

        return {"itinerary": itinerary, "changes": changes, "score": optimization_score}

    async def _calculate_savings(
        self, original: Itinerary, optimized: Itinerary
    ) -> Dict[str, float]:
        """Calculate estimated savings from optimization."""
        savings = {}

        # Time savings (in minutes)
        original_time = self._calculate_total_travel_time(original)
        optimized_time = self._calculate_total_travel_time(optimized)
        savings["time_minutes"] = max(0, original_time - optimized_time)

        # Cost savings
        original_cost = original.budget_spent or 0
        optimized_cost = optimized.budget_spent or 0
        savings["cost"] = max(0, original_cost - optimized_cost)

        return savings

    def _calculate_total_travel_time(self, itinerary: Itinerary) -> int:
        """Calculate total travel time in minutes."""
        # Simplified calculation - would need actual route planning
        return 0

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert time string to minutes since midnight."""
        hour, minute = map(int, time_str.split(":"))
        return hour * 60 + minute

    def _minutes_to_time(self, minutes: int) -> str:
        """Convert minutes since midnight to time string."""
        hour = (minutes // 60) % 24
        minute = minutes % 60
        return f"{hour:02d}:{minute:02d}"

    def _get_cached_itinerary(self, cache_key: str) -> Optional[Itinerary]:
        """Get cached itinerary if still valid."""
        if cache_key in self._itinerary_cache:
            result, timestamp = self._itinerary_cache[cache_key]
            import time

            if time.time() - timestamp < self.cache_ttl:
                return result
            else:
                del self._itinerary_cache[cache_key]
        return None

    def _cache_itinerary(self, cache_key: str, itinerary: Itinerary) -> None:
        """Cache itinerary."""
        import time

        self._itinerary_cache[cache_key] = (itinerary, time.time())

    def _clear_itinerary_cache(self, itinerary_id: str) -> None:
        """Clear cache for an itinerary."""
        cache_key = f"itinerary_{itinerary_id}"
        if cache_key in self._itinerary_cache:
            del self._itinerary_cache[cache_key]

    def _get_cached_conflicts(
        self, cache_key: str
    ) -> Optional[List[ItineraryConflict]]:
        """Get cached conflicts if still valid."""
        if cache_key in self._conflict_cache:
            result, timestamp = self._conflict_cache[cache_key]
            import time

            if time.time() - timestamp < self.cache_ttl:
                return result
            else:
                del self._conflict_cache[cache_key]
        return None

    def _cache_conflicts(
        self, cache_key: str, conflicts: List[ItineraryConflict]
    ) -> None:
        """Cache conflicts."""
        import time

        self._conflict_cache[cache_key] = (conflicts, time.time())

    async def _store_itinerary(self, itinerary: Itinerary) -> None:
        """Store itinerary in database."""
        try:
            itinerary_data = itinerary.model_dump()
            await self.db.store_itinerary(itinerary_data)

        except Exception as e:
            logger.error(
                "Failed to store itinerary",
                extra={"itinerary_id": itinerary.id, "error": str(e)},
            )
            raise


# Dependency function for FastAPI
async def get_itinerary_service() -> ItineraryService:
    """
    Get itinerary service instance for dependency injection.

    Returns:
        ItineraryService instance
    """
    return ItineraryService()
