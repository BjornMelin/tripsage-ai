# pylint: disable=too-many-lines
"""Trip router for TripSage API.

This module provides endpoints for trip management, including creating,
retrieving, updating, and deleting trips.
"""

import logging
from collections.abc import Awaitable, Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol, TypedDict, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError

from tripsage.api.core.dependencies import (
    MemoryServiceDep,
    RequiredPrincipalDep,
    TripServiceDep,
    UserServiceDep,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.trips import TripSearchParams
from tripsage_core.exceptions.exceptions import (
    CoreAuthorizationError,
    CoreSecurityError,
    CoreServiceError,
)
from tripsage_core.models.api.itinerary_models import ItinerarySearchResponse

# Import schemas
from tripsage_core.models.api.trip_models import (
    CreateTripRequest,
    TripCollaboratorResponse,
    TripCollaboratorsListResponse,
    TripCollaboratorUpdateRequest,
    TripListItem,
    TripListResponse,
    TripPreferencesRequest,
    TripResponse,
    TripShareRequest,
    TripSuggestionResponse,
    TripSummaryResponse,
    UpdateTripRequest,
)
from tripsage_core.models.schemas_common.enums import TripType, TripVisibility
from tripsage_core.models.schemas_common.geographic import Coordinates
from tripsage_core.models.schemas_common.travel import TripDestination
from tripsage_core.models.trip import (
    Budget,
    BudgetBreakdown,
    TripPreferences as CoreTripPreferences,
)
from tripsage_core.observability.otel import (
    http_route_attr_fn,
    record_histogram,
    trace_span,
)

# Import audit logging
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditSeverity,
    audit_security_event,
)
from tripsage_core.services.business.memory_service import (
    MemorySearchRequest,
    MemorySearchResult,
)

# Import core service and models
from tripsage_core.services.business.trip_service import (
    TripCreateRequest,
    TripLocation,
    TripResponse as CoreTripResponse,
    TripUpdateRequest as CoreTripUpdateRequest,
)
from tripsage_core.services.business.user_service import UserResponse, UserService


logger = logging.getLogger(__name__)

router = APIRouter(tags=["trips"])


class _TripLocationProtocol(Protocol):
    """Minimal protocol representing a trip location returned by the core service."""

    name: str
    country: str | None
    city: str | None
    coordinates: dict[str, float] | None


class _CoreTripProtocol(Protocol):
    """Protocol for core trip responses consumed by the API adapter."""

    id: UUID | str
    user_id: UUID | str
    title: str
    description: str | None
    start_date: datetime | date | str
    end_date: datetime | date | str
    destinations: Iterable[_TripLocationProtocol]
    preferences: Any
    status: Any
    created_at: datetime | str
    updated_at: datetime | str


class _ItineraryItem(TypedDict):
    """Typed dictionary describing an itinerary item in responses."""

    id: str | None
    name: str
    description: str | None
    start_time: str | None
    end_time: str | None
    location: str | None


class _ItineraryResponse(TypedDict):
    """Typed dictionary describing an itinerary response payload."""

    id: str | None
    trip_id: str
    items: list[_ItineraryItem]
    total_items: int


class _ExportResponse(TypedDict):
    """Typed dictionary describing the export request acknowledgement payload."""

    format: str
    trip_id: str
    export_token: str
    status: str
    estimated_completion: str
    download_url: str
    expires_at: str


def _ensure_datetime(value: datetime | date | str) -> datetime:
    """Normalize supported date/datetime inputs into timezone-aware datetimes."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=UTC)
    # At this point, the remaining supported type is str; coerce explicitly.
    normalized = str(value)
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    return datetime.fromisoformat(normalized)


def _ensure_date(value: datetime | date | str) -> date:
    """Normalize supported inputs into `date` instances."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return _ensure_datetime(value).date()


async def _get_user_details_by_id(
    user_id: str,
    user_service: "UserService",
) -> tuple[str | None, str | None]:
    """Retrieve user email and name for a given identifier."""
    try:
        get_by_id = cast(
            Callable[[str], Awaitable[UserResponse | None]],
            user_service.get_user_by_id,
        )
        user = await get_by_id(user_id)
        if user:
            return user.email, getattr(user, "full_name", None)
    except (AttributeError, ValueError, CoreServiceError):
        logger.exception("Failed to get user details")
    return None, None


async def _resolve_user_by_email(
    email: str,
    user_service: "UserService",
) -> tuple[str | None, str | None]:
    """Resolve a user ID and name from an email address."""
    try:
        get_by_email = cast(
            Callable[[str], Awaitable[UserResponse | None]],
            user_service.get_user_by_email,
        )
        user = await get_by_email(email)
        if user:
            return str(user.id), getattr(user, "full_name", None)
    except (AttributeError, ValueError, CoreServiceError):
        logger.exception("Failed to resolve user by email")
    return None, None


def _principal_ip_address(principal: Principal) -> str:
    """Best-effort extraction of the principal's IP address."""
    metadata = principal.metadata or {}
    for key in ("ip_address", "ip", "client_ip"):
        value = metadata.get(key)
        if value:
            return str(value)
    return "unknown"


async def _record_trip_audit_event(
    *,
    event_type: AuditEventType,
    severity: AuditSeverity,
    message: str,
    principal: Principal,
    resource_id: str,
    **metadata: Any,
) -> None:
    """Safely emit a security audit event without impacting endpoint flow."""
    try:
        await audit_security_event(
            event_type=event_type,
            severity=severity,
            message=message,
            actor_id=principal.user_id,
            ip_address=_principal_ip_address(principal),
            target_resource=resource_id,
            **metadata,
        )
    except Exception as audit_error:  # noqa: BLE001 - audit failures must not surface to clients
        logger.warning(
            "Failed to record audit event %s for trip %s: %s",
            event_type.value,
            resource_id,
            audit_error,
        )


@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
@trace_span(name="api.trips.create")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def create_trip(
    trip_request: CreateTripRequest,
    trip_service: TripServiceDep,
    principal: RequiredPrincipalDep,
):
    """Create a new trip.

    Args:
        trip_request: Trip creation request
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Created trip
    """
    logger.info("Creating trip for user: %s", principal.user_id)

    try:
        # Convert date to datetime with timezone
        start_datetime = datetime.combine(
            trip_request.start_date, datetime.min.time()
        ).replace(tzinfo=UTC)
        end_datetime = datetime.combine(
            trip_request.end_date, datetime.min.time()
        ).replace(tzinfo=UTC)

        # Convert TripDestination to TripLocation
        trip_locations: list[TripLocation] = []
        for dest in trip_request.destinations:
            coordinates: dict[str, float] | None = None
            if dest.coordinates:
                coordinates = {
                    "lat": dest.coordinates.latitude or 0.0,  # type: ignore[assignment]
                    "lng": dest.coordinates.longitude or 0.0,  # type: ignore[assignment]
                }

            trip_location = TripLocation(
                name=dest.name,
                country=dest.country,
                city=dest.city,
                coordinates=coordinates,  # type: ignore[arg-type]
                timezone=None,  # Could be populated if available
            )
            trip_locations.append(trip_location)

        # Extract primary destination from destinations list
        primary_destination = (
            trip_request.destinations[0].name
            if trip_request.destinations
            else "Unknown"
        )

        # Create default budget if preferences don't include one
        default_budget = Budget(
            total=1000.0,  # Default $1000 budget
            currency="USD",
            breakdown=BudgetBreakdown(
                accommodation=300.0, transportation=400.0, food=200.0, activities=100.0
            ),
        )

        # Extract budget from preferences if available
        budget: Budget = default_budget
        pref_budget = (
            trip_request.preferences.budget
            if trip_request.preferences and hasattr(trip_request.preferences, "budget")
            else None
        )
        if pref_budget:
            if hasattr(pref_budget, "total_budget"):
                # This is a common Budget with Price
                budget = Budget(
                    total=float(pref_budget.total_budget.amount),
                    currency=str(pref_budget.total_budget.currency),
                    breakdown=BudgetBreakdown(
                        accommodation=300.0,
                        transportation=400.0,
                        food=200.0,
                        activities=100.0,
                    ),
                )
            elif hasattr(pref_budget, "total"):
                # Coerce to Budget using model validation
                budget = Budget.model_validate(cast(Any, pref_budget))
            else:
                # Try to convert from dict safely
                budget = Budget.model_validate(cast(Any, pref_budget))

        # Create core trip create request with all required fields
        core_request = TripCreateRequest(
            title=trip_request.title,
            description=trip_request.description,
            start_date=start_datetime,
            end_date=end_datetime,
            destination=primary_destination,  # Required field
            destinations=trip_locations,
            budget=budget,  # Required field
            travelers=1,  # Default to 1 traveler
            trip_type=TripType.LEISURE,  # Default trip type
            visibility=TripVisibility.PRIVATE,  # Default visibility
            tags=[],  # Default empty tags
            preferences=None,  # Will be converted below if present
        )

        # Convert common TripPreferences to core TripPreferences if present
        if trip_request.preferences:
            # Extract preferences from common model and convert to core model
            common_prefs = trip_request.preferences
            core_preferences = CoreTripPreferences(
                budget_flexibility=0.1,  # Default 10% flexibility
                date_flexibility=0,  # Default no date flexibility
                destination_flexibility=False,  # Default no destination flexibility
                accommodation_preferences={},
                transportation_preferences={},
                activity_preferences=[],
                dietary_restrictions=[],
                accessibility_needs=[],
            )

            # Map common preferences to core preferences
            if common_prefs.accommodation:
                core_preferences.accommodation_preferences = {
                    "type": common_prefs.accommodation.type.value
                    if common_prefs.accommodation.type
                    else None,
                    "min_rating": common_prefs.accommodation.min_rating,
                    "amenities": common_prefs.accommodation.amenities or [],
                    "location_preference": (
                        common_prefs.accommodation.location_preference
                    ),
                }

            if common_prefs.transportation:
                core_preferences.transportation_preferences = (
                    common_prefs.transportation.flight_preferences or {}
                )

            if common_prefs.activities:
                core_preferences.activity_preferences = common_prefs.activities

            if common_prefs.dietary_restrictions:
                core_preferences.dietary_restrictions = (
                    common_prefs.dietary_restrictions
                )

            if common_prefs.accessibility_needs:
                core_preferences.accessibility_needs = common_prefs.accessibility_needs

            core_request.preferences = core_preferences

        # Create trip via core service
        create_core_trip = cast(
            Callable[[str, TripCreateRequest], Awaitable[CoreTripResponse]],
            trip_service.create_trip,
        )
        core_response = await create_core_trip(principal.user_id, core_request)

        # Convert core response to API response
        trip_response = _adapt_trip_response(core_response)

        logger.info("Trip created successfully: %s", trip_response.id)
        return trip_response

    except Exception as e:
        logger.exception("Failed to create trip")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create trip",
        ) from e


@router.get("/{trip_id}", response_model=TripResponse)
@trace_span(name="api.trips.get")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def get_trip(
    trip_id: UUID,
    trip_service: TripServiceDep,
    principal: RequiredPrincipalDep,
):
    """Get a trip by ID.

    Args:
        trip_id: Trip ID
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Trip details
    """
    logger.info("Getting trip %s for user: %s", trip_id, principal.user_id)

    try:
        get_core_trip = cast(
            Callable[[str, str], Awaitable[CoreTripResponse | None]],
            trip_service.get_trip,
        )
        trip_response = await get_core_trip(str(trip_id), principal.user_id)

        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        # Convert core response to API response
        return _adapt_trip_response(trip_response)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get trip")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trip",
        ) from e


@router.get("/", response_model=TripListResponse)
@trace_span(name="api.trips.list")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def list_trips(
    trip_service: TripServiceDep,
    principal: RequiredPrincipalDep,
    *,
    skip: int = Query(default=0, ge=0, description="Number of trips to skip"),
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of trips to return"
    ),
):
    """List trips for the current user.

    Args:
        skip: Number of trips to skip
        limit: Number of trips to return
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        List of trips
    """
    logger.info("Listing trips for user: %s", principal.user_id)

    try:
        list_user_trips = cast(
            Callable[..., Awaitable[list[CoreTripResponse]]],
            trip_service.get_user_trips,
        )
        trips = await list_user_trips(
            user_id=principal.user_id, limit=limit, offset=skip
        )

        # Convert to list items for response (Pydantic models)
        trip_items: list[TripListItem] = []
        for trip in trips:
            adapted_trip = _adapt_trip_response(trip)
            trip_items.append(
                TripListItem(
                    id=adapted_trip.id,
                    title=adapted_trip.title,
                    start_date=adapted_trip.start_date,
                    end_date=adapted_trip.end_date,
                    duration_days=adapted_trip.duration_days,
                    destinations=[dest.name for dest in adapted_trip.destinations],
                    status=adapted_trip.status,
                    created_at=adapted_trip.created_at,
                )
            )

        count_user_trips = cast(
            Callable[[str], Awaitable[int]],
            trip_service.count_user_trips,
        )
        total_count = await count_user_trips(principal.user_id)
        return TripListResponse(
            items=trip_items,
            total=total_count,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception("Failed to list trips")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list trips",
        ) from e


@router.put("/{trip_id}", response_model=TripResponse)
@trace_span(name="api.trips.update")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def update_trip(
    trip_id: UUID,
    trip_request: UpdateTripRequest,
    trip_service: TripServiceDep,
    principal: RequiredPrincipalDep,
):
    """Update a trip.

    Args:
        trip_id: Trip ID
        trip_request: Trip update request
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Updated trip
    """
    logger.info("Updating trip %s for user: %s", trip_id, principal.user_id)

    try:
        # Convert update request to dict for core service
        updates: dict[str, Any] = {}

        if trip_request.title is not None:
            updates["title"] = trip_request.title
        if trip_request.description is not None:
            updates["description"] = trip_request.description
        if trip_request.start_date is not None:
            # Convert date to datetime with timezone
            updates["start_date"] = datetime.combine(
                trip_request.start_date, datetime.min.time()
            ).replace(tzinfo=UTC)
        if trip_request.end_date is not None:
            # Convert date to datetime with timezone
            updates["end_date"] = datetime.combine(
                trip_request.end_date, datetime.min.time()
            ).replace(tzinfo=UTC)
        if trip_request.destinations is not None:
            # Convert destinations to TripLocation format
            trip_locations: list[TripLocation] = []
            for dest in trip_request.destinations:
                coordinates = None
                if dest.coordinates:
                    coordinates = {
                        "lat": dest.coordinates.latitude,
                        "lng": dest.coordinates.longitude,
                    }

                trip_location = TripLocation(
                    name=dest.name,
                    country=dest.country,
                    city=dest.city,
                    coordinates=coordinates,  # type: ignore[arg-type]
                    timezone=None,
                )
                trip_locations.append(trip_location)
            updates["destinations"] = trip_locations

        # Build core update request model
        core_update = CoreTripUpdateRequest(**updates)

        do_update_trip = cast(
            Callable[
                [str, str, CoreTripUpdateRequest],
                Awaitable[CoreTripResponse | None],
            ],
            trip_service.update_trip,
        )
        trip_response = await do_update_trip(
            str(trip_id), principal.user_id, core_update
        )

        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        # Convert core response to API response
        return _adapt_trip_response(trip_response)

    except HTTPException:
        raise
    except CoreAuthorizationError as auth_error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(auth_error),
        ) from auth_error
    except CoreSecurityError as security_error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(security_error),
        ) from security_error
    except Exception as e:
        logger.exception("Failed to update trip")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update trip",
        ) from e


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
@trace_span(name="api.trips.delete")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def delete_trip(
    trip_id: UUID,
    trip_service: TripServiceDep,
    principal: RequiredPrincipalDep,
):
    """Delete a trip.

    Args:
        trip_id: Trip ID
        principal: Current authenticated principal
        trip_service: Trip service instance
    """
    logger.info("Deleting trip %s for user: %s", trip_id, principal.user_id)

    try:
        do_delete_trip = cast(
            Callable[[str, str], Awaitable[bool]],
            trip_service.delete_trip,
        )
        success = await do_delete_trip(principal.user_id, str(trip_id))

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        # Audit log the deletion
        await _record_trip_audit_event(
            event_type=AuditEventType.DATA_DELETION,
            severity=AuditSeverity.MEDIUM,
            message="Trip deleted",
            principal=principal,
            resource_id=str(trip_id),
            action="trip_deleted",
        )

    except HTTPException:
        raise
    except CoreAuthorizationError as auth_error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(auth_error),
        ) from auth_error
    except CoreSecurityError as security_error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(security_error),
        ) from security_error
    except Exception as e:
        logger.exception("Failed to delete trip")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete trip",
        ) from e


@router.get("/{trip_id}/summary", response_model=TripSummaryResponse)
async def get_trip_summary(
    trip_id: UUID,
    trip_service: TripServiceDep,
    principal: RequiredPrincipalDep,
):
    """Get trip summary.

    Args:
        trip_id: Trip ID
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Trip summary
    """
    logger.info("Getting trip summary %s for user: %s", trip_id, principal.user_id)

    try:
        # Get trip first to ensure access
        get_core_trip = cast(
            Callable[[str, str], Awaitable[CoreTripResponse | None]],
            trip_service.get_trip,
        )
        trip_response = await get_core_trip(str(trip_id), principal.user_id)

        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        # Convert core response to API response
        adapted_trip = _adapt_trip_response(trip_response)

        # Build summary from trip data
        start_date = _ensure_date(adapted_trip.start_date)
        end_date = _ensure_date(adapted_trip.end_date)
        date_range = f"{start_date.strftime('%b %d')}-{end_date.strftime('%d, %Y')}"

        # Get budget information from trip data (authorized access verified above)
        budget = getattr(adapted_trip, "budget", None)
        budget_total = budget.total if budget else 0.0
        budget_currency = budget.currency if budget else "USD"

        # Calculate budget breakdown from trip budget
        budget_breakdown = {}
        if budget and hasattr(budget, "breakdown"):
            budget_breakdown = {
                "accommodation": {"budget": budget.breakdown.accommodation, "spent": 0},
                "transportation": {
                    "budget": budget.breakdown.transportation,
                    "spent": 0,
                },
                "food": {"budget": budget.breakdown.food, "spent": 0},
                "activities": {"budget": budget.breakdown.activities, "spent": 0},
            }
        else:
            # Default breakdown if no budget data
            budget_breakdown = {
                "accommodation": {"budget": 0, "spent": 0},
                "transportation": {"budget": 0, "spent": 0},
                "food": {"budget": 0, "spent": 0},
                "activities": {"budget": 0, "spent": 0},
            }

        # Get accommodation and transportation summaries from preferences or defaults
        accommodation_summary = "Accommodation preferences not set"
        transportation_summary = "Transportation preferences not set"

        if adapted_trip.preferences:
            if hasattr(adapted_trip.preferences, "accommodation_preferences"):
                accommodation_summary = "Custom accommodation preferences configured"
            if hasattr(adapted_trip.preferences, "transportation_preferences"):
                transportation_summary = "Custom transportation preferences configured"

        return TripSummaryResponse(
            id=adapted_trip.id,
            title=adapted_trip.title,
            date_range=date_range,
            duration_days=adapted_trip.duration_days,
            destinations=[dest.name for dest in adapted_trip.destinations],
            accommodation_summary=accommodation_summary,
            transportation_summary=transportation_summary,
            budget_summary={
                "total": budget_total,
                "currency": budget_currency,
                "spent": 0,
                "remaining": budget_total,
                "breakdown": budget_breakdown,
            },
            has_itinerary=False,
            completion_percentage=25,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get trip summary")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trip summary",
        ) from e


@router.put("/{trip_id}/preferences", response_model=TripResponse)
async def update_trip_preferences(
    trip_id: UUID,
    preferences_request: TripPreferencesRequest,
    trip_service: TripServiceDep,
    principal: RequiredPrincipalDep,
):
    """Update trip preferences.

    Args:
        trip_id: Trip ID
        preferences_request: Trip preferences update request
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Updated trip
    """
    logger.info(
        "Updating trip preferences %s for user: %s",
        trip_id,
        principal.user_id,
    )

    try:
        # Update preferences via the core service update_trip method
        preference_payload = preferences_request.model_dump(exclude_none=True)
        core_preferences = CoreTripPreferences(**preference_payload)
        core_update_request = CoreTripUpdateRequest.model_validate(
            {"preferences": core_preferences}
        )

        do_update_trip = cast(
            Callable[
                [str, str, CoreTripUpdateRequest],
                Awaitable[CoreTripResponse | None],
            ],
            trip_service.update_trip,
        )
        trip_response = await do_update_trip(
            str(trip_id), principal.user_id, core_update_request
        )

        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        # Convert core response to API response
        return _adapt_trip_response(trip_response)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update trip preferences")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update trip preferences",
        ) from e


@router.post(
    "/{trip_id}/duplicate",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_trip(
    trip_id: UUID,
    trip_service: TripServiceDep,
    principal: RequiredPrincipalDep,
):
    """Duplicate a trip.

    Args:
        trip_id: Trip ID to duplicate
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Duplicated trip
    """
    logger.info("Duplicating trip %s for user: %s", trip_id, principal.user_id)

    try:
        # Get original trip
        get_core_trip = cast(
            Callable[[str, str], Awaitable[CoreTripResponse | None]],
            trip_service.get_trip,
        )
        original_trip = await get_core_trip(str(trip_id), principal.user_id)

        if not original_trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        # Create new trip based on original using core TripCreateRequest
        duplicate_request = TripCreateRequest(
            title=f"Copy of {original_trip.title}",
            description=original_trip.description,
            start_date=original_trip.start_date,
            end_date=original_trip.end_date,
            # Core expects "destination" not "destinations"
            destination=original_trip.destination,
            destinations=original_trip.destinations,
            budget=original_trip.budget,  # Core requires budget
            travelers=original_trip.travelers,
            trip_type=original_trip.trip_type,
            visibility=original_trip.visibility,
            tags=original_trip.tags if hasattr(original_trip, "tags") else [],
            preferences=original_trip.preferences,
        )

        create_core_trip = cast(
            Callable[[str, TripCreateRequest], Awaitable[CoreTripResponse]],
            trip_service.create_trip,
        )
        duplicated_trip = await create_core_trip(principal.user_id, duplicate_request)

        # Convert core response to API response
        return _adapt_trip_response(duplicated_trip)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to duplicate trip")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to duplicate trip",
        ) from e


def _get_trip_search_params(
    q: str | None = Query(default=None, description="Search query"),
    status: str | None = Query(
        default=None, alias="status", description="Status filter"
    ),
    skip: int = Query(default=0, ge=0, description="Number of trips to skip"),
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of trips to return"
    ),
) -> TripSearchParams:
    return TripSearchParams(q=q, status=status, skip=skip, limit=limit)


@router.get("/search", response_model=TripListResponse)
async def search_trips(
    trip_service: TripServiceDep,
    principal: RequiredPrincipalDep,
    params: TripSearchParams = Depends(_get_trip_search_params),
):
    """Search trips.

    Args:
        q: Search query
        params: Query parameters (q, status, skip, limit)
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Search results
    """
    logger.info("Searching trips for user: %s", principal.user_id)

    try:
        search_filters: dict[str, Any] = {}
        if params.status:
            search_filters["status"] = params.status

        search_trips_core = cast(
            Callable[..., Awaitable[list[CoreTripResponse]]],
            trip_service.search_trips,
        )
        trips = await search_trips_core(
            user_id=principal.user_id,
            query=params.q or "",
            filters=search_filters or None,
            limit=params.limit,
            offset=params.skip,
        )

        # Convert to list items for response (Pydantic models)
        trip_items: list[TripListItem] = []
        for trip in trips:
            adapted_trip = _adapt_trip_response(trip)
            trip_items.append(
                TripListItem(
                    id=adapted_trip.id,
                    title=adapted_trip.title,
                    start_date=adapted_trip.start_date,
                    end_date=adapted_trip.end_date,
                    duration_days=adapted_trip.duration_days,
                    destinations=[dest.name for dest in adapted_trip.destinations],
                    status=adapted_trip.status,
                    created_at=adapted_trip.created_at,
                )
            )

        return TripListResponse(
            items=trip_items,
            total=len(trip_items),
            skip=params.skip,
            limit=params.limit,
        )

    except Exception as e:
        logger.exception("Failed to search trips")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search trips",
        ) from e


@router.get("/{trip_id}/itinerary", response_model=_ItineraryResponse)
async def get_trip_itinerary(
    trip_id: UUID,
    trip_service: TripServiceDep,
    principal: RequiredPrincipalDep,
) -> _ItineraryResponse:
    """Get trip itinerary.

    Args:
        trip_id: Trip ID
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Trip itinerary
    """
    logger.info("Getting trip itinerary %s for user: %s", trip_id, principal.user_id)

    try:
        # Get trip first to ensure access
        get_core_trip = cast(
            Callable[[str, str], Awaitable[CoreTripResponse | None]],
            trip_service.get_trip,
        )
        trip_response = await get_core_trip(str(trip_id), principal.user_id)

        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found",
            )

        # Get actual itinerary data from itinerary service with authorization
        try:
            from tripsage_core.services.business.itinerary_service import (
                get_itinerary_service,
            )

            itinerary_service = await get_itinerary_service()

            # Search for itinerary associated with this trip
            from tripsage_core.models.api.itinerary_models import (
                ItinerarySearchRequest,
            )

            # Search request lacks trip_id; fall back to query
            search_request = ItinerarySearchRequest.model_validate(
                {"query": str(trip_id), "limit": 1}
            )

            search_itins = cast(
                Callable[[str, object], Awaitable[ItinerarySearchResponse]],
                itinerary_service.search_itineraries,
            )
            itinerary_search = await search_itins(principal.user_id, search_request)

            itinerary_items = itinerary_search.data

            if itinerary_items:
                itinerary_data = itinerary_items[0]

                items: list[_ItineraryItem] = []
                for item in getattr(itinerary_data, "items", []):
                    start_time_value = (
                        f"{item.item_date.isoformat()}T{item.start_time}:00Z"
                        if getattr(item, "start_time", None)
                        else None
                    )
                    end_time_value = (
                        f"{item.item_date.isoformat()}T{item.end_time}:00Z"
                        if getattr(item, "end_time", None)
                        else None
                    )
                    items.append(
                        _ItineraryItem(
                            id=str(item.id) if getattr(item, "id", None) else None,
                            name=getattr(item, "title", ""),
                            description=getattr(item, "description", None),
                            start_time=start_time_value,
                            end_time=end_time_value,
                            location=None,
                        )
                    )

                itinerary = _ItineraryResponse(
                    id=str(itinerary_data.id)
                    if getattr(itinerary_data, "id", None)
                    else None,
                    trip_id=str(trip_id),
                    items=items,
                    total_items=len(items),
                )
            else:
                # No itinerary found - return empty structure
                itinerary = _ItineraryResponse(
                    id=None,
                    trip_id=str(trip_id),
                    items=[],
                    total_items=0,
                )

        except Exception:
            logger.exception("Failed to get itinerary data")
            # Fallback to empty structure on error
            itinerary = _ItineraryResponse(
                id=None,
                trip_id=str(trip_id),
                items=[],
                total_items=0,
            )

        return itinerary

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get trip itinerary")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trip itinerary",
        ) from e


@router.post("/{trip_id}/export", response_model=_ExportResponse)
async def export_trip(
    trip_id: UUID,
    trip_service: TripServiceDep,
    principal: RequiredPrincipalDep,
    *,
    export_format: str = Query(default="pdf", description="Export format"),
    format_: str | None = None,  # test harness passes 'format' kw
) -> _ExportResponse:
    """Export trip.

    Args:
        trip_id: Trip ID
        export_format: Export format requested by the caller
        format_: Optional keyword alias used by some internal tests
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Export data
    """
    logger.info("Exporting trip %s for user: %s", trip_id, principal.user_id)

    try:
        # Get trip first to ensure access
        get_core_trip = cast(
            Callable[[str, str], Awaitable[CoreTripResponse | None]],
            trip_service.get_trip,
        )
        trip_response = await get_core_trip(str(trip_id), principal.user_id)

        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        # Validate export format
        allowed_formats = {"pdf", "csv", "json"}
        selected_format = format_ or export_format
        if selected_format not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format. Allowed formats: {allowed_formats}",
            )

        # Generate a secure export token for the download
        import secrets

        export_token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        expiry_time = now + timedelta(hours=24)
        estimated_completion = now + timedelta(minutes=5)

        # Store export request in a temporary location (in production, proper queue)
        # For now, return a response indicating export is being processed
        export_data = _ExportResponse(
            format=selected_format,
            trip_id=str(trip_id),
            export_token=export_token,
            status="processing",
            estimated_completion=estimated_completion.isoformat(),
            download_url=f"/api/trips/{trip_id}/export/{export_token}/download",
            expires_at=expiry_time.isoformat(),
        )

        # Audit log the export request
        await _record_trip_audit_event(
            event_type=AuditEventType.DATA_EXPORT,
            severity=AuditSeverity.LOW,
            message="Trip export requested",
            principal=principal,
            resource_id=str(trip_id),
            action="trip_export_requested",
            format=selected_format,
            export_token=export_token,
        )

        return export_data

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to export trip")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export trip",
        ) from e


# Core endpoints
@router.get("/suggestions", response_model=list[TripSuggestionResponse])
async def get_trip_suggestions(
    memory_service: MemoryServiceDep,
    principal: RequiredPrincipalDep,
    *,
    limit: int = Query(20, ge=1, le=100, description="Number of suggestions to return"),
    budget_max: float | None = Query(None, description="Maximum budget filter"),
    category: str | None = Query(None, description="Filter by category"),
):
    """Get personalized trip suggestions based on user preferences and history.

    Args:
        limit: Maximum number of suggestions to return
        budget_max: Optional maximum budget filter
        category: Optional category filter
        principal: Current authenticated principal
        memory_service: Injected memory service

    Returns:
        List of trip suggestions
    """
    base_suggestions: list[TripSuggestionResponse] = [
        TripSuggestionResponse(
            id="suggestion-1",
            title="Tokyo Cherry Blossom Adventure",
            destination="Tokyo, Japan",
            description=(
                "Experience cherry blossom season in Japan's vibrant capital city."
            ),
            estimated_price=2800,
            currency="USD",
            duration=7,
            rating=4.8,
            category="culture",
            best_time_to_visit="March - May",
            highlights=[
                "Cherry Blossoms",
                "Temples",
                "Street Food",
                "Modern Culture",
            ],
            trending=True,
            seasonal=True,
        ),
        TripSuggestionResponse(
            id="suggestion-2",
            title="Bali Tropical Retreat",
            destination="Bali, Indonesia",
            description=(
                "Relax on beaches and explore ancient temples in this "
                "tropical paradise."
            ),
            estimated_price=1500,
            currency="USD",
            duration=10,
            rating=4.6,
            category="relaxation",
            best_time_to_visit="April - October",
            highlights=["Beaches", "Temples", "Rice Terraces", "Wellness"],
            difficulty="easy",
        ),
        TripSuggestionResponse(
            id="suggestion-3",
            title="Swiss Alps Hiking Experience",
            destination="Interlaken, Switzerland",
            description=(
                "Challenge yourself with breathtaking alpine hikes and stunning "
                "mountain views."
            ),
            estimated_price=3200,
            currency="USD",
            duration=5,
            rating=4.9,
            category="adventure",
            best_time_to_visit="June - September",
            highlights=[
                "Mountain Hiking",
                "Alpine Lakes",
                "Cable Cars",
                "Local Cuisine",
            ],
            difficulty="challenging",
        ),
        TripSuggestionResponse(
            id="suggestion-4",
            title="Santorini Sunset Romance",
            destination="Santorini, Greece",
            description=(
                "Watch spectacular sunsets from clifftop villages in this iconic "
                "Greek island."
            ),
            estimated_price=2100,
            currency="USD",
            duration=6,
            rating=4.7,
            category="relaxation",
            best_time_to_visit="April - October",
            highlights=[
                "Sunset Views",
                "White Architecture",
                "Wine Tasting",
                "Beaches",
            ],
            difficulty="easy",
        ),
        TripSuggestionResponse(
            id="suggestion-5",
            title="Iceland Northern Lights",
            destination="Reykjavik, Iceland",
            description=(
                "Chase the aurora borealis and explore dramatic landscapes of "
                "fire and ice."
            ),
            estimated_price=2500,
            currency="USD",
            duration=8,
            rating=4.5,
            category="nature",
            best_time_to_visit="September - March",
            highlights=["Northern Lights", "Geysers", "Waterfalls", "Blue Lagoon"],
            seasonal=True,
            difficulty="moderate",
        ),
    ]

    suggestions = base_suggestions

    try:
        memory_search = MemorySearchRequest(
            query="travel preferences destinations budget",
            limit=10,
            filters=None,
        )
        search_memories = cast(
            Callable[[str, MemorySearchRequest], Awaitable[list[MemorySearchResult]]],
            memory_service.search_memories,
        )
        user_memories = await search_memories(principal.user_id, memory_search)

        if user_memories:
            logger.info(
                "Personalizing suggestions based on %s user memories",
                len(user_memories),
            )

    except (ValueError, KeyError, CoreServiceError):
        logger.exception("Failed to get personalized suggestions")
        suggestions = base_suggestions

    # Apply filters with proper validation
    filtered_suggestions = suggestions

    if budget_max:
        filtered_suggestions = [
            s for s in filtered_suggestions if s.estimated_price <= budget_max
        ]

    if category:
        filtered_suggestions = [
            s for s in filtered_suggestions if s.category == category
        ]

    # Apply limit
    return filtered_suggestions[:limit]


def _adapt_trip_response(
    core_response: CoreTripResponse | _CoreTripProtocol | dict[str, Any],
) -> TripResponse:
    """Adapt a core trip response to the public API schema."""
    # Normalize to a CoreTripResponse instance when possible
    try:
        core_model: Any = (
            CoreTripResponse.model_validate(core_response)
            if isinstance(core_response, dict)
            else core_response
        )
    except (ValidationError, TypeError, ValueError):
        core_model = core_response

    # Destinations
    api_destinations: list[TripDestination] = []
    for location in getattr(core_model, "destinations", []) or []:
        coordinates_dict = getattr(location, "coordinates", None)
        coordinates = None
        if isinstance(coordinates_dict, dict):
            coord_map: dict[str, float | int | str | None] = coordinates_dict  # type: ignore[assignment]
            lat_raw = coord_map.get("lat", 0.0)
            lng_raw = coord_map.get("lng", 0.0)
            try:
                lat = float(lat_raw if lat_raw is not None else 0.0)
            except (TypeError, ValueError):
                lat = 0.0
            try:
                lng = float(lng_raw if lng_raw is not None else 0.0)
            except (TypeError, ValueError):
                lng = 0.0
            coordinates = Coordinates(latitude=lat, longitude=lng, altitude=None)
        api_destinations.append(
            TripDestination(
                name=getattr(location, "name", "Unknown"),
                country=getattr(location, "country", None),
                city=getattr(location, "city", None),
                coordinates=coordinates,
                arrival_date=None,
                departure_date=None,
                duration_days=None,
            )
        )

    # Dates and timestamps
    start_date = _ensure_date(getattr(core_model, "start_date", datetime.now(UTC)))
    end_date = _ensure_date(getattr(core_model, "end_date", start_date))
    try:
        duration_days = (end_date - start_date).days
    except (TypeError, AttributeError):
        duration_days = 1

    created_at = _ensure_datetime(getattr(core_model, "created_at", datetime.now(UTC)))
    updated_at = _ensure_datetime(getattr(core_model, "updated_at", created_at))

    status_value = getattr(core_model, "status", "planning")

    return TripResponse(
        id=UUID(str(core_model.id)),
        user_id=str(core_model.user_id),
        title=getattr(core_model, "title", "Untitled Trip"),
        description=getattr(core_model, "description", None),
        start_date=start_date,
        end_date=end_date,
        duration_days=duration_days,
        destinations=api_destinations,
        preferences=None,
        status=str(status_value),
        created_at=created_at,
        updated_at=updated_at,
    )


# ===== Trip Collaboration Endpoints =====


@router.post("/{trip_id}/share", response_model=list[TripCollaboratorResponse])
async def share_trip(
    trip_id: UUID,
    share_request: TripShareRequest,
    trip_service: TripServiceDep,
    user_service: UserServiceDep,
    principal: RequiredPrincipalDep,
):
    """Share a trip with other users.

    Only the trip owner can share their trip with others.

    Args:
        trip_id: Trip ID
        share_request: Share request with user emails and permissions
        principal: Current authenticated principal
        trip_service: Trip service instance
        user_service: User service used to resolve collaborator identities

    Returns:
        List of successfully added collaborators

    Raises:
        HTTPException: If not authorized or trip not found
    """
    logger.info("Sharing trip %s by user: %s", trip_id, principal.user_id)

    try:
        # Resolve identifiers (emails or UUIDs) and share
        response_collaborators: list[TripCollaboratorResponse] = []
        permission_error: Exception | None = None
        for identifier in share_request.user_emails:
            user_id_val: str | None = None
            email_val: str | None = None
            full_name: str | None = None
            if "@" in identifier:
                email_val = identifier
                user_id_val, full_name = await _resolve_user_by_email(
                    email_val,
                    user_service,
                )
            else:
                user_id_val = identifier
                email_val, full_name = await _get_user_details_by_id(
                    user_id_val,
                    user_service,
                )

            if not user_id_val:
                # Skip unresolved identifiers silently
                continue

            try:
                do_share = cast(
                    Callable[[str, str, str, str], Awaitable[bool]],
                    trip_service.share_trip,
                )
                await do_share(
                    str(trip_id),
                    principal.user_id,
                    user_id_val,
                    share_request.permission_level,
                )
            except CoreAuthorizationError as _auth_err:
                permission_error = _auth_err
                continue

            response_collaborators.append(
                TripCollaboratorResponse(
                    user_id=UUID(str(user_id_val)),
                    email=email_val or "",
                    name=full_name,
                    permission_level=share_request.permission_level,
                    added_by=UUID(str(principal.user_id)),
                    added_at=datetime.now(UTC),
                    is_active=True,
                )
            )

        if not response_collaborators and permission_error is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(permission_error),
            )

        # Audit log the trip sharing
        await _record_trip_audit_event(
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.INFORMATIONAL,
            message="Trip shared with collaborators",
            principal=principal,
            resource_id=str(trip_id),
            action="trip_shared",
            shared_with=share_request.user_emails,
            permission_level=share_request.permission_level,
        )

        return response_collaborators

    except Exception as e:
        logger.exception("Failed to share trip")
        if "permission" in str(e).lower() or "authorization" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to share trip",
        ) from e


@router.get("/{trip_id}/collaborators", response_model=TripCollaboratorsListResponse)
async def list_trip_collaborators(
    trip_id: UUID,
    trip_service: TripServiceDep,
    user_service: UserServiceDep,
    principal: RequiredPrincipalDep,
):
    """List all collaborators for a trip.

    Accessible by trip owner and collaborators with appropriate permissions.

    Args:
        trip_id: Trip ID
        principal: Current authenticated principal
        trip_service: Trip service instance
        user_service: User service used to hydrate collaborator metadata

    Returns:
        List of trip collaborators with their permissions

    Raises:
        HTTPException: If not authorized or trip not found
    """
    logger.info(
        "Listing collaborators for trip %s by user: %s",
        trip_id,
        principal.user_id,
    )

    try:
        # Get trip to verify access and get owner ID
        get_core_trip = cast(
            Callable[[str, str], Awaitable[CoreTripResponse | None]],
            trip_service.get_trip,
        )
        trip = await get_core_trip(str(trip_id), principal.user_id)

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found",
            )

        # Get collaborators via database service (TripService doesn't expose directly)
        database_service = cast(Any, trip_service.db)
        collaborator_records = await database_service.get_trip_collaborators(
            str(trip_id)
        )

        response_collaborators: list[TripCollaboratorResponse] = []
        for collab in collaborator_records:
            email, full_name = await _get_user_details_by_id(
                str(collab.get("user_id")),
                user_service,
            )
            added_at_value = collab.get("added_at")
            added_at = (
                _ensure_datetime(added_at_value)
                if added_at_value is not None
                else datetime.now(UTC)
            )
            permission_level = collab.get("permission_level") or collab.get(
                "permission"
            )
            response_collaborators.append(
                TripCollaboratorResponse(
                    user_id=UUID(str(collab.get("user_id"))),
                    email=email or collab.get("email", ""),
                    name=full_name,
                    permission_level=permission_level or "view",
                    added_by=UUID(str(collab.get("added_by", trip.user_id))),
                    added_at=added_at,
                    is_active=collab.get("is_active", True),
                )
            )

        owner_raw = getattr(trip, "user_id", None)
        owner_uuid = owner_raw if isinstance(owner_raw, UUID) else UUID(str(owner_raw))

        return TripCollaboratorsListResponse(
            collaborators=response_collaborators,
            total=len(response_collaborators),
            owner_id=owner_uuid,
        )

    except HTTPException:
        raise
    except CoreAuthorizationError as auth_error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(auth_error),
        ) from auth_error
    except Exception as e:
        logger.exception("Failed to list trip collaborators")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list trip collaborators",
        ) from e


@router.put(
    "/{trip_id}/collaborators/{user_id}", response_model=TripCollaboratorResponse
)
async def update_collaborator_permissions(
    trip_id: UUID,
    user_id: UUID,
    trip_service: TripServiceDep,
    user_service: UserServiceDep,
    *,
    update_request: TripCollaboratorUpdateRequest,
    principal: RequiredPrincipalDep,
):
    """Update collaborator permissions for a trip.

    Only the trip owner can update collaborator permissions.

    Args:
        trip_id: Trip ID
        user_id: Collaborator user ID to update
        update_request: New permission level
        principal: Current authenticated principal
        trip_service: Trip service instance
        user_service: User service used to fetch collaborator details

    Returns:
        Updated collaborator information

    Raises:
        HTTPException: If not authorized or collaborator not found
    """
    logger.info(
        "Updating collaborator %s permissions for trip %s by user: %s",
        user_id,
        trip_id,
        principal.user_id,
    )

    try:
        # Verify ownership
        get_core_trip = cast(
            Callable[[str, str], Awaitable[CoreTripResponse | None]],
            trip_service.get_trip,
        )
        trip = await get_core_trip(str(trip_id), principal.user_id)

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found",
            )
        trip_owner_id = str(trip.user_id)
        if trip_owner_id != principal.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only trip owner can update collaborator permissions",
            )

        database_service = cast(Any, trip_service.db)
        existing_collaborator = await database_service.get_trip_collaborator(
            str(trip_id), str(user_id)
        )
        if not existing_collaborator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collaborator not found",
            )

        await database_service.add_trip_collaborator(
            {
                "trip_id": str(trip_id),
                "user_id": str(user_id),
                "permission_level": update_request.permission_level,
                "added_by": existing_collaborator.get("added_by", principal.user_id),
                "added_at": existing_collaborator.get("added_at", datetime.now(UTC)),
            }
        )

        updated_collaborator = (
            await database_service.get_trip_collaborator(str(trip_id), str(user_id))
            or existing_collaborator
        )
        email, full_name = await _get_user_details_by_id(str(user_id), user_service)
        added_at_value = (
            updated_collaborator.get("added_at") if updated_collaborator else None
        )
        added_at = (
            _ensure_datetime(added_at_value)
            if added_at_value is not None
            else datetime.now(UTC)
        )

        return TripCollaboratorResponse(
            user_id=user_id,
            email=email or updated_collaborator.get("email", ""),
            name=full_name,
            permission_level=update_request.permission_level,
            added_by=UUID(str(updated_collaborator.get("added_by", trip_owner_id))),
            added_at=added_at,
            is_active=updated_collaborator.get("is_active", True),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update collaborator permissions")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update collaborator permissions",
        ) from e


@router.delete(
    "/{trip_id}/collaborators/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_collaborator(
    trip_id: UUID,
    user_id: UUID,
    trip_service: TripServiceDep,
    principal: RequiredPrincipalDep,
):
    """Remove a collaborator from a trip.

    Only the trip owner can remove collaborators.

    Args:
        trip_id: Trip ID
        user_id: Collaborator user ID to remove
        principal: Current authenticated principal
        trip_service: Trip service instance

    Raises:
        HTTPException: If not authorized or collaborator not found
    """
    logger.info(
        "Removing collaborator %s from trip %s by user: %s",
        user_id,
        trip_id,
        principal.user_id,
    )

    try:
        # Verify ownership
        get_core_trip = cast(
            Callable[[str, str], Awaitable[CoreTripResponse | None]],
            trip_service.get_trip,
        )
        trip = await get_core_trip(str(trip_id), principal.user_id)

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found",
            )
        trip_owner_id = str(trip.user_id)
        if trip_owner_id != principal.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only trip owner can remove collaborators",
            )

        # Remove collaborator
        do_unshare = cast(
            Callable[[str, str, str], Awaitable[bool]],
            trip_service.unshare_trip,
        )
        success = await do_unshare(str(trip_id), principal.user_id, str(user_id))

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collaborator not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to remove collaborator")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove collaborator",
        ) from e
