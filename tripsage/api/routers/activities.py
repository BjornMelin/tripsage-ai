"""Router for activity-related endpoints in the TripSage API."""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from tripsage.api.core.dependencies import (
    ActivityServiceDep,
    get_principal_id,
    require_principal,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.requests.activities import (
    ActivitySearchRequest,
    SaveActivityRequest,
)
from tripsage.api.schemas.responses.activities import (
    ActivityResponse,
    ActivitySearchResponse,
    SavedActivityResponse,
)
from tripsage_core.services.business.activity_service import (
    ActivityServiceError,
)
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditSeverity,
    audit_security_event,
)
from tripsage_core.services.business.trip_service import TripService, get_trip_service
from tripsage_core.services.infrastructure.database_service import (
    DatabaseService,
    get_database_service,
)


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/search", response_model=ActivitySearchResponse)
async def search_activities(
    request: ActivitySearchRequest,
    activity_service: ActivityServiceDep,
):
    """Search for activities based on provided criteria using Google Maps Places API.

    This endpoint searches for activities, attractions, and points of interest
    in the specified destination using real-time data from Google Maps.
    """
    logger.info("Activity search request: %s", request.destination)

    try:
        result = await activity_service.search_activities(request)

        logger.info(
            "Found %s activities for %s", len(result.activities), request.destination
        )
        return result

    except ActivityServiceError as e:
        logger.exception("Activity service error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Activity search failed: {e.message}",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error in activity search")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while searching for activities",
        ) from e


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity_details(activity_id: str, activity_service: ActivityServiceDep):
    """Get detailed information about a specific activity.

    Retrieves comprehensive details for an activity including enhanced
    information from Google Maps Places API.
    """
    logger.info("Get activity details request: %s", activity_id)

    try:
        activity = await activity_service.get_activity_details(activity_id)

        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity with ID {activity_id} not found",
            )

        logger.info("Retrieved details for activity: %s", activity_id)
        return activity

    except ActivityServiceError as e:
        logger.exception("Activity service error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get activity details: {e.message}",
        ) from e
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception("Unexpected error getting activity details")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving activity details",
        ) from e


@router.post("/save", response_model=SavedActivityResponse)
async def save_activity(
    request: SaveActivityRequest,
    principal: Principal = Depends(require_principal),
    db_service: DatabaseService = Depends(get_database_service),
    trip_service: TripService = Depends(get_trip_service),
):
    """Save an activity for a user.

    Security features:
    - User authentication required
    - Trip access verification if trip_id provided
    - Audit logging for save operations
    - Database persistence with user isolation
    """
    logger.info("Save activity request: %s", request.activity_id)

    try:
        user_id = get_principal_id(principal)

        # Verify trip access if trip_id is provided
        if request.trip_id:
            trip = await trip_service.get_trip(trip_id=request.trip_id, user_id=user_id)
            if not trip:
                await audit_security_event(
                    event_type=AuditEventType.ACCESS_DENIED,
                    severity=AuditSeverity.MEDIUM,
                    message=(
                        f"Trip access denied for user {user_id} to trip "
                        f"{request.trip_id}"
                    ),
                    actor_id=user_id,
                    ip_address="unknown",
                    target_resource=f"trip:{request.trip_id}",
                    resource_type="trip",
                    resource_id=request.trip_id,
                    action="save_activity",
                    reason="trip_not_found_or_access_denied",
                )

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Trip not found or access denied",
                )

        # Save activity to itinerary_items table
        saved_at = datetime.now(UTC)
        itinerary_data = {
            "id": str(uuid4()),
            "trip_id": request.trip_id,
            "user_id": user_id,
            "title": f"Saved Activity: {request.activity_id}",
            "description": request.notes or "Activity saved from search results",
            "item_type": "activity",
            "external_id": request.activity_id,
            "metadata": {
                "activity_id": request.activity_id,
                "saved_from": "activity_search",
                "notes": request.notes,
            },
            "created_at": saved_at.isoformat(),
            "booking_status": "planned",
        }

        # Insert into database
        await db_service.insert(
            table="itinerary_items",
            data=itinerary_data,
            user_id=user_id,
        )

        # Log successful save
        await audit_security_event(
            event_type=AuditEventType.DATA_MODIFICATION,
            severity=AuditSeverity.LOW,
            message=f"Activity {request.activity_id} saved for user {user_id}",
            actor_id=user_id,
            ip_address="unknown",
            target_resource=f"saved_activity:{request.activity_id}",
            resource_type="saved_activity",
            resource_id=request.activity_id,
            action="save_activity",
            trip_id=request.trip_id,
        )

        logger.info("Activity %s saved for user %s", request.activity_id, user_id)

        return SavedActivityResponse(
            activity_id=request.activity_id,
            trip_id=request.trip_id,
            user_id=user_id,
            saved_at=saved_at.isoformat(),
            notes=request.notes,
            activity=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to save activity %s", request.activity_id)

        # Log system error
        await audit_security_event(
            event_type=AuditEventType.SYSTEM_ERROR,
            severity=AuditSeverity.HIGH,
            message=f"System error saving activity {request.activity_id}",
            actor_id=user_id,
            ip_address="unknown",
            target_resource=f"saved_activity:{request.activity_id}",
            resource_type="saved_activity",
            resource_id=request.activity_id,
            action="save_activity",
            error=str(e),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save activity",
        ) from e


@router.get("/saved", response_model=list[SavedActivityResponse])
async def get_saved_activities(
    principal: Principal = Depends(require_principal),
    db_service: DatabaseService = Depends(get_database_service),
    limit: int = 50,
    offset: int = 0,
):
    """Get all activities saved by a user.

    Security features:
    - User authentication required
    - User data isolation (only returns user's saved activities)
    - Audit logging for data access
    - Pagination support
    """
    logger.info("Get saved activities request")

    try:
        user_id = get_principal_id(principal)

        # Query saved activities from itinerary_items table
        filters = {
            "user_id": user_id,
            "item_type": "activity",
        }

        saved_items = await db_service.select(
            table="itinerary_items",
            columns="*",
            filters=filters,
            order_by="-created_at",  # Most recent first
            limit=limit,
            offset=offset,
            user_id=user_id,
        )

        # Convert to SavedActivityResponse format
        saved_activities = []
        for item in saved_items:
            metadata = item.get("metadata", {})
            saved_activities.append(
                SavedActivityResponse(
                    activity_id=metadata.get(
                        "activity_id", item.get("external_id", "")
                    ),
                    trip_id=item.get("trip_id"),
                    user_id=user_id,
                    saved_at=item.get("created_at", datetime.now(UTC).isoformat()),
                    notes=metadata.get("notes"),
                    activity=None,
                )
            )

        # Log successful access
        await audit_security_event(
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.LOW,
            message=f"User {user_id} accessed saved activities list",
            actor_id=user_id,
            ip_address="unknown",
            target_resource="saved_activities",
            resource_type="saved_activities",
            action="list_saved_activities",
            count=len(saved_activities),
            limit=limit,
            offset=offset,
        )

        logger.info(
            "Retrieved %s saved activities for user %s", len(saved_activities), user_id
        )

        return saved_activities

    except Exception as e:
        logger.exception("Failed to get saved activities")

        # Log system error
        await audit_security_event(
            event_type=AuditEventType.SYSTEM_ERROR,
            severity=AuditSeverity.HIGH,
            message=f"System error listing saved activities for user {user_id}",
            actor_id=user_id,
            ip_address="unknown",
            target_resource="saved_activities",
            resource_type="saved_activities",
            action="list_saved_activities",
            error=str(e),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve saved activities",
        ) from e


@router.delete("/saved/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_activity(
    activity_id: str,
    principal: Principal = Depends(require_principal),
    db_service: DatabaseService = Depends(get_database_service),
):
    """Delete a saved activity for a user.

    Security features:
    - User authentication required
    - User authorization (can only delete own saved activities)
    - Audit logging for deletion operations
    - Data integrity checks
    """
    logger.info("Delete saved activity request: %s", activity_id)

    try:
        user_id = get_principal_id(principal)

        # First, check if the saved activity exists and belongs to the user
        filters = {
            "user_id": user_id,
            "item_type": "activity",
            "external_id": activity_id,
        }

        existing_items = await db_service.select(
            table="itinerary_items",
            columns="*",
            filters=filters,
            user_id=user_id,
        )

        if not existing_items:
            # Also check by metadata.activity_id for items saved with the new format
            metadata_filter = {
                "user_id": user_id,
                "item_type": "activity",
            }

            all_items = await db_service.select(
                table="itinerary_items",
                columns="*",
                filters=metadata_filter,
                user_id=user_id,
            )

            # Find item with matching activity_id in metadata
            existing_items = [
                item
                for item in all_items
                if item.get("metadata", {}).get("activity_id") == activity_id
            ]

        if not existing_items:
            await audit_security_event(
                event_type=AuditEventType.ACCESS_DENIED,
                severity=AuditSeverity.MEDIUM,
                message=(
                    f"Access denied deleting activity {activity_id} for user {user_id}"
                ),
                actor_id=user_id,
                ip_address="unknown",
                target_resource=f"saved_activity:{activity_id}",
                resource_type="saved_activity",
                resource_id=activity_id,
                action="delete_saved_activity",
                reason="activity_not_found_or_not_owned",
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved activity not found or access denied",
            )

        # Delete the saved activity(ies)
        deleted_count = 0
        for item in existing_items:
            # Use Supabase delete with proper filters
            try:
                (
                    db_service.client.table("itinerary_items")
                    .delete()
                    .eq("id", item["id"])
                    .execute()
                )
                # Supabase client executes synchronously and returns its summary.
                deleted_count += 1
            except (OSError, RuntimeError, ValueError) as delete_error:
                # Database/network errors during Supabase delete operation
                logger.warning("Failed to delete item %s: %s", item["id"], delete_error)

        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete saved activity",
            )

        # Log successful deletion
        await audit_security_event(
            event_type=AuditEventType.DATA_DELETION,
            severity=AuditSeverity.LOW,
            message=f"Activity {activity_id} deleted for user {user_id}",
            actor_id=user_id,
            ip_address="unknown",
            target_resource=f"saved_activity:{activity_id}",
            resource_type="saved_activity",
            resource_id=activity_id,
            action="delete_saved_activity",
            deleted_count=deleted_count,
        )

        logger.info(
            "Deleted %s saved activity entries for activity %s by user %s",
            deleted_count,
            activity_id,
            user_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete saved activity %s", activity_id)

        # Log system error
        await audit_security_event(
            event_type=AuditEventType.SYSTEM_ERROR,
            severity=AuditSeverity.HIGH,
            message=f"System error deleting activity {activity_id}",
            actor_id=user_id,
            ip_address="unknown",
            target_resource=f"saved_activity:{activity_id}",
            resource_type="saved_activity",
            resource_id=activity_id,
            action="delete_saved_activity",
            error=str(e),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete saved activity",
        ) from e
