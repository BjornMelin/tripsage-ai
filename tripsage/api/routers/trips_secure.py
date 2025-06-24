"""
Enhanced Trip Router with Integrated Security System.

This module demonstrates how to integrate the new trip access verification system
with existing trip endpoints, providing secure, audited access control.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from tripsage.api.core.dependencies import (
    RequiredPrincipalDep,
    TripServiceDep,
)
from tripsage.api.core.trip_security import (
    TripAccessLevel,
    TripAccessPermission,
    TripEditPermissionDep,
    TripManagePermissionDep,
    TripOwnerAccessDep,
    TripReadAccessDep,
    get_user_trip_permissions,
    require_trip_access,
)

# Import schemas
from tripsage.api.schemas.trips import (
    CreateTripRequest,
    TripCollaboratorResponse,
    TripCollaboratorsListResponse,
    TripListResponse,
    TripResponse,
    TripShareRequest,
    TripSummaryResponse,
    UpdateTripRequest,
)
from tripsage_core.models.schemas_common.enums import TripType, TripVisibility
from tripsage_core.models.schemas_common.geographic import Coordinates
from tripsage_core.models.schemas_common.travel import TripDestination
from tripsage_core.models.trip import BudgetBreakdown, EnhancedBudget

# Import core service and models
from tripsage_core.services.business.trip_service import (
    TripCreateRequest as CoreTripCreateRequest,
)
from tripsage_core.services.business.trip_service import (
    TripLocation,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["trips-secure"], prefix="/api/v1/trips-secure")


# Helper function (reused from original trips router)
def _adapt_trip_response(core_response) -> TripResponse:
    """Adapt core trip response to API response."""
    return TripResponse(
        id=core_response.id,
        user_id=core_response.user_id,
        title=core_response.title,
        description=core_response.description,
        start_date=core_response.start_date.date(),
        end_date=core_response.end_date.date(),
        destinations=[
            TripDestination(
                name=dest.name,
                country=dest.country,
                city=dest.city,
                coordinates=Coordinates(
                    latitude=dest.coordinates["lat"], longitude=dest.coordinates["lng"]
                )
                if dest.coordinates
                else None,
            )
            for dest in core_response.destinations
        ],
        budget=core_response.budget.total,
        currency=core_response.budget.currency,
        travelers=core_response.travelers,
        trip_type=core_response.trip_type,
        status=core_response.status,
        visibility=core_response.visibility,
        tags=core_response.tags,
        note_count=core_response.note_count,
        attachment_count=core_response.attachment_count,
        collaborator_count=core_response.collaborator_count,
        shared_with=core_response.shared_with,
        created_at=core_response.created_at,
        updated_at=core_response.updated_at,
    )


@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_request: CreateTripRequest,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """
    Create a new trip.

    No access verification needed as any authenticated user can create trips.

    Args:
        trip_request: Trip creation request
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Created trip details
    """
    logger.info(f"Creating trip for user: {principal.user_id}")

    try:
        # Convert date to datetime with timezone
        start_datetime = datetime.combine(
            trip_request.start_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(
            trip_request.end_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc)

        # Convert TripDestination to TripLocation
        trip_locations = []
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
                coordinates=coordinates,
                timezone=None,
            )
            trip_locations.append(trip_location)

        # Extract primary destination from destinations list
        primary_destination = (
            trip_request.destinations[0].name
            if trip_request.destinations
            else "Unknown"
        )

        # Create default budget
        default_budget = EnhancedBudget(
            total=1000.0,
            currency="USD",
            breakdown=BudgetBreakdown(
                accommodation=300.0, transportation=400.0, food=200.0, activities=100.0
            ),
        )

        # Create core trip create request
        core_request = CoreTripCreateRequest(
            title=trip_request.title,
            description=trip_request.description,
            start_date=start_datetime,
            end_date=end_datetime,
            destination=primary_destination,
            destinations=trip_locations,
            budget=default_budget,
            travelers=1,
            trip_type=TripType.LEISURE,
            visibility=TripVisibility.PRIVATE,
            tags=[],
            preferences=None,
        )

        # Create trip using service
        trip_response = await trip_service.create_trip(core_request, principal.user_id)

        # Convert to API response
        return _adapt_trip_response(trip_response)

    except Exception as e:
        logger.error(f"Failed to create trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create trip",
        ) from e


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: UUID,
    access_result: TripReadAccessDep,  # Automatic access verification
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """
    Get trip details by ID.

    Requires read access to the trip (owner, collaborator, or public trip).

    Args:
        trip_id: Trip ID
        access_result: Access verification result (injected by dependency)
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Trip details with access information
    """
    logger.info(
        f"Getting trip {trip_id} for user {principal.user_id} "
        f"(access level: {access_result.access_level})"
    )

    try:
        trip_response = await trip_service.get_trip(
            trip_id=str(trip_id), user_id=principal.user_id
        )

        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        # Convert core response to API response
        api_response = _adapt_trip_response(trip_response)

        # Add access information to response for client use
        api_response.user_access_level = access_result.access_level
        api_response.user_permission = access_result.permission_granted
        api_response.is_owner = access_result.is_owner

        return api_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trip",
        ) from e


@router.get("/", response_model=TripListResponse)
async def list_trips(
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
    skip: int = Query(default=0, ge=0, description="Number of trips to skip"),
    limit: int = Query(
        default=10, ge=1, le=100, description="Number of trips to return"
    ),
):
    """
    List trips for the current user.

    No access verification needed as users can only see their own trips
    and trips shared with them.

    Args:
        skip: Number of trips to skip
        limit: Number of trips to return
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        List of trips accessible to the user
    """
    logger.info(f"Listing trips for user: {principal.user_id}")

    try:
        trips_response = await trip_service.get_user_trips(
            user_id=principal.user_id, limit=limit, offset=skip
        )

        # Convert core responses to API responses
        adapted_trips = [_adapt_trip_response(trip) for trip in trips_response]

        return TripListResponse(
            trips=adapted_trips,
            total=len(adapted_trips),
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Failed to list trips: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list trips",
        ) from e


@router.put("/{trip_id}", response_model=TripResponse)
async def update_trip(
    trip_id: UUID,
    trip_request: UpdateTripRequest,
    access_result: TripEditPermissionDep,  # Requires edit permission
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """
    Update trip details.

    Requires edit permission (owner or collaborator with edit access).

    Args:
        trip_id: Trip ID
        trip_request: Trip update request
        access_result: Access verification result
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Updated trip details
    """
    logger.info(
        f"Updating trip {trip_id} for user {principal.user_id} "
        f"(permission: {access_result.permission_granted})"
    )

    try:
        # Convert UpdateTripRequest to core format (simplified for example)
        update_data = {}

        if trip_request.title is not None:
            update_data["title"] = trip_request.title
        if trip_request.description is not None:
            update_data["description"] = trip_request.description
        if trip_request.start_date is not None:
            update_data["start_date"] = datetime.combine(
                trip_request.start_date, datetime.min.time()
            ).replace(tzinfo=timezone.utc)
        if trip_request.end_date is not None:
            update_data["end_date"] = datetime.combine(
                trip_request.end_date, datetime.min.time()
            ).replace(tzinfo=timezone.utc)

        # Update trip using service
        updated_trip = await trip_service.update_trip(
            trip_id=str(trip_id),
            user_id=principal.user_id,
            update_data=update_data,
        )

        if not updated_trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        return _adapt_trip_response(updated_trip)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update trip",
        ) from e


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    trip_id: UUID,
    access_result: TripOwnerAccessDep,  # Requires owner access
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """
    Delete a trip.

    Requires owner access - only the trip owner can delete trips.

    Args:
        trip_id: Trip ID
        access_result: Access verification result
        principal: Current authenticated principal
        trip_service: Trip service instance
    """
    logger.info(f"Deleting trip {trip_id} for owner {principal.user_id}")

    try:
        success = await trip_service.delete_trip(
            trip_id=str(trip_id), user_id=principal.user_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        logger.info(f"Trip {trip_id} successfully deleted by {principal.user_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete trip",
        ) from e


# Collaboration endpoints with enhanced security


@router.get("/{trip_id}/collaborators", response_model=TripCollaboratorsListResponse)
@require_trip_access(TripAccessLevel.COLLABORATOR)  # Any collaborator can view
async def list_collaborators(
    trip_id: UUID,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """
    List trip collaborators.

    Requires collaborator access (owner or any collaborator can view).
    """
    logger.info(f"Listing collaborators for trip {trip_id}")

    try:
        collaborators = await trip_service.get_trip_collaborators(str(trip_id))

        # Convert to API response format
        collaborator_responses = [
            TripCollaboratorResponse(
                user_id=collab["user_id"],
                permission=collab["permission"],
                added_at=collab["added_at"],
                added_by=collab["added_by"],
            )
            for collab in collaborators
        ]

        return TripCollaboratorsListResponse(
            trip_id=trip_id,
            collaborators=collaborator_responses,
            total=len(collaborator_responses),
        )

    except Exception as e:
        logger.error(f"Failed to list collaborators: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list collaborators",
        ) from e


@router.post("/{trip_id}/collaborators", response_model=TripCollaboratorResponse)
async def add_collaborator(
    trip_id: UUID,
    share_request: TripShareRequest,
    access_result: TripManagePermissionDep,  # Requires manage permission
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """
    Add a collaborator to the trip.

    Requires manage permission (owner or collaborator with manage access).
    """
    logger.info(
        f"Adding collaborator to trip {trip_id} by user {principal.user_id} "
        f"(permission: {access_result.permission_granted})"
    )

    try:
        success = await trip_service.share_trip(
            trip_id=str(trip_id),
            owner_id=principal.user_id,
            share_with_user_id=share_request.user_id,
            permission=share_request.permission,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add collaborator",
            )

        return TripCollaboratorResponse(
            user_id=share_request.user_id,
            permission=share_request.permission,
            added_at=datetime.now(timezone.utc),
            added_by=principal.user_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add collaborator: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add collaborator",
        ) from e


@router.delete(
    "/{trip_id}/collaborators/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_collaborator(
    trip_id: UUID,
    user_id: str,
    access_result: TripOwnerAccessDep,  # Only owner can remove collaborators
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """
    Remove a collaborator from the trip.

    Requires owner access - only the trip owner can remove collaborators.
    """
    logger.info(f"Removing collaborator {user_id} from trip {trip_id}")

    try:
        success = await trip_service.unshare_trip(
            trip_id=str(trip_id),
            owner_id=principal.user_id,
            unshare_user_id=user_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Collaborator not found"
            )

        logger.info(f"Collaborator {user_id} removed from trip {trip_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove collaborator: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove collaborator",
        ) from e


@router.get("/{trip_id}/permissions")
async def get_trip_permissions(
    trip_id: UUID,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """
    Get detailed permission information for the current user on this trip.

    This endpoint doesn't require pre-verification as it's used to check permissions.
    """
    logger.info(f"Getting permissions for trip {trip_id} and user {principal.user_id}")

    try:
        permissions = await get_user_trip_permissions(
            str(trip_id), principal, trip_service
        )

        return {
            "trip_id": trip_id,
            "user_id": principal.user_id,
            **permissions,
        }

    except Exception as e:
        logger.error(f"Failed to get trip permissions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trip permissions",
        ) from e


@router.get("/{trip_id}/summary", response_model=TripSummaryResponse)
@require_trip_access(TripAccessLevel.READ)  # Minimal read access required
async def get_trip_summary(
    trip_id: UUID,
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """
    Get a summary of trip information.

    Requires read access (public trips, collaborators, or owner).
    """
    logger.info(f"Getting summary for trip {trip_id}")

    try:
        trip_response = await trip_service.get_trip(
            trip_id=str(trip_id), user_id=principal.user_id
        )

        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        return TripSummaryResponse(
            id=trip_response.id,
            title=trip_response.title,
            start_date=trip_response.start_date.date(),
            end_date=trip_response.end_date.date(),
            destination=trip_response.destination,
            travelers=trip_response.travelers,
            status=trip_response.status,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trip summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trip summary",
        ) from e


# Example of conditional logic based on access level
@router.post("/{trip_id}/conditional-action")
async def conditional_action(
    trip_id: UUID,
    access_result: TripReadAccessDep,  # Minimum read access
    principal: RequiredPrincipalDep,
    trip_service: TripServiceDep,
):
    """
    Demonstrate conditional logic based on user's access level.

    Different actions are available based on the user's permission level.
    """
    logger.info(
        f"Conditional action for trip {trip_id} by user {principal.user_id} "(
            f"(level: {access_result.access_level}, "
            f"permission: {access_result.permission_granted})"
        )
    )

    response = {
        "trip_id": trip_id,
        "user_id": principal.user_id,
        "access_level": access_result.access_level,
        "permission": access_result.permission_granted,
        "available_actions": [],
    }

    # Owner can do everything
    if access_result.is_owner:
        response["available_actions"].extend(
            [
                "view_details",
                "edit_content",
                "manage_collaborators",
                "delete_trip",
                "transfer_ownership",
            ]
        )
        response["message"] = "Full owner access granted"

    # Collaborators have different actions based on permission level
    elif access_result.is_collaborator:
        response["available_actions"].append("view_details")

        if access_result.permission_granted in [
            TripAccessPermission.EDIT,
            TripAccessPermission.MANAGE,
        ]:
            response["available_actions"].append("edit_content")

        if access_result.permission_granted == TripAccessPermission.MANAGE:
            response["available_actions"].append("manage_collaborators")

        response["message"] = (
            f"Collaborator access with {access_result.permission_granted} permission"
        )

    # Public or read-only access
    else:
        response["available_actions"].append("view_details")
        response["message"] = "Read-only access granted"

    return response
