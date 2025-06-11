"""Trip router for TripSage API.

This module provides endpoints for trip management, including creating,
retrieving, updating, and deleting trips.

Supports both simple implementation (hardcoded responses) and enhanced 
service layer implementation with full CRUD operations.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from tripsage.api.core.dependencies import get_principal_id, require_principal_dep
from tripsage.api.middlewares.authentication import Principal

# Try to import enhanced service layer schemas, fall back to simple schemas
try:
    from tripsage.api.schemas.requests.trips import (
        CreateTripRequest,
        TripPreferencesRequest,
        UpdateTripRequest,
    )
    from tripsage.api.schemas.responses.trips import (
        TripListResponse,
        TripResponse,
        TripSummaryResponse,
    )
    ENHANCED_SCHEMAS_AVAILABLE = True
except ImportError:
    # Fall back to simple schemas
    from tripsage.api.schemas.trips import (
        CreateTripRequest,
        TripResponse,
    )
    ENHANCED_SCHEMAS_AVAILABLE = False

# Always import these schemas (they exist in both approaches)
from tripsage.api.schemas.trips import TripSuggestionResponse

# Try to import enhanced service layer, fall back to core service
try:
    from tripsage.api.services.trip import TripService as EnhancedTripService, get_trip_service as get_enhanced_trip_service
    ENHANCED_SERVICE_AVAILABLE = True
except ImportError:
    ENHANCED_SERVICE_AVAILABLE = False

# Always import core service
from tripsage_core.services.business.trip_service import TripService, get_trip_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["trips"])


@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_request: CreateTripRequest,
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
):
    """Create a new trip.
    
    Uses enhanced service layer if available, otherwise uses simple implementation.

    Args:
        trip_request: Trip creation request
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Created trip
    """
    if ENHANCED_SERVICE_AVAILABLE:
        # Use enhanced service layer implementation
        logger.info(f"Creating trip for user: {principal.user_id} (enhanced service)")
        
        try:
            enhanced_service = get_enhanced_trip_service()
            trip_response = await enhanced_service.create_trip(
                user_id=principal.user_id, request=trip_request
            )
            
            logger.info(f"Trip created successfully: {trip_response.id}")
            return trip_response
            
        except Exception as e:
            logger.error(f"Failed to create trip: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create trip",
            )
    else:
        # Simple implementation (currently not implemented)
        logger.info(f"Creating trip for user: {principal.user_id} (simple implementation)")
        # TODO: Implement simple trip creation logic
        pass


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: UUID,
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
):
    """Get a trip by ID.

    Args:
        trip_id: Trip ID
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Trip details
    """
    logger.info(f"Getting trip {trip_id} for user: {principal.user_id}")

    try:
        trip_response = await trip_service.get_trip(
            user_id=principal.user_id, trip_id=trip_id
        )

        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        return trip_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trip",
        )


@router.get("/", response_model=TripListResponse)
async def list_trips(
    skip: int = Query(default=0, ge=0, description="Number of trips to skip"),
    limit: int = Query(
        default=10, ge=1, le=100, description="Number of trips to return"
    ),
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
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
    logger.info(f"Listing trips for user: {principal.user_id}")

    try:
        trips = await trip_service.list_trips(
            user_id=principal.user_id, limit=limit, offset=skip
        )

        # Convert to list items for response
        trip_items = []
        for trip in trips:
            trip_items.append(
                {
                    "id": trip.id,
                    "title": trip.title,
                    "start_date": trip.start_date,
                    "end_date": trip.end_date,
                    "duration_days": trip.duration_days,
                    "destinations": [dest.name for dest in trip.destinations],
                    "status": trip.status,
                    "created_at": trip.created_at,
                }
            )

        return {
            "items": trip_items,
            "total": len(trip_items),  # TODO: Get actual total from service
            "skip": skip,
            "limit": limit,
        }

    except Exception as e:
        logger.error(f"Failed to list trips: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list trips",
        )


@router.put("/{trip_id}", response_model=TripResponse)
async def update_trip(
    trip_id: UUID,
    trip_request: UpdateTripRequest,
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
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
    logger.info(f"Updating trip {trip_id} for user: {principal.user_id}")

    try:
        trip_response = await trip_service.update_trip(
            user_id=principal.user_id, trip_id=trip_id, request=trip_request
        )

        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        return trip_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update trip",
        )


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    trip_id: UUID,
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
):
    """Delete a trip.

    Args:
        trip_id: Trip ID
        principal: Current authenticated principal
        trip_service: Trip service instance
    """
    logger.info(f"Deleting trip {trip_id} for user: {principal.user_id}")

    try:
        success = await trip_service.delete_trip(
            user_id=principal.user_id, trip_id=trip_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete trip",
        )


@router.get("/{trip_id}/summary", response_model=TripSummaryResponse)
async def get_trip_summary(
    trip_id: UUID,
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
):
    """Get trip summary.

    Args:
        trip_id: Trip ID
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Trip summary
    """
    logger.info(f"Getting trip summary {trip_id} for user: {principal.user_id}")

    try:
        summary = await trip_service.get_trip_summary(
            user_id=principal.user_id, trip_id=trip_id
        )

        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trip summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trip summary",
        )


@router.put("/{trip_id}/preferences", response_model=TripResponse)
async def update_trip_preferences(
    trip_id: UUID,
    preferences_request: TripPreferencesRequest,
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
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
    logger.info(f"Updating trip preferences {trip_id} for user: {principal.user_id}")

    try:
        trip_response = await trip_service.update_trip_preferences(
            user_id=principal.user_id, trip_id=trip_id, preferences=preferences_request
        )

        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        return trip_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update trip preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update trip preferences",
        )


@router.post(
    "/{trip_id}/duplicate",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_trip(
    trip_id: UUID,
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
):
    """Duplicate a trip.

    Args:
        trip_id: Trip ID to duplicate
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Duplicated trip
    """
    logger.info(f"Duplicating trip {trip_id} for user: {principal.user_id}")

    try:
        trip_response = await trip_service.duplicate_trip(
            user_id=principal.user_id, trip_id=trip_id
        )

        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        return trip_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to duplicate trip",
        )


@router.get("/search", response_model=TripListResponse)
async def search_trips(
    q: Optional[str] = Query(default=None, description="Search query"),
    status_filter: Optional[str] = Query(
        default=None, alias="status", description="Status filter"
    ),
    skip: int = Query(default=0, ge=0, description="Number of trips to skip"),
    limit: int = Query(
        default=10, ge=1, le=100, description="Number of trips to return"
    ),
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
):
    """Search trips.

    Args:
        q: Search query
        status_filter: Status filter
        skip: Number of trips to skip
        limit: Number of trips to return
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Search results
    """
    logger.info(f"Searching trips for user: {principal.user_id}")

    try:
        trips = await trip_service.search_trips(
            user_id=principal.user_id, query=q, limit=limit
        )

        # Convert to list items for response
        trip_items = []
        for trip in trips:
            trip_items.append(
                {
                    "id": trip.id,
                    "title": trip.title,
                    "start_date": trip.start_date,
                    "end_date": trip.end_date,
                    "duration_days": trip.duration_days,
                    "destinations": [dest.name for dest in trip.destinations],
                    "status": trip.status,
                    "created_at": trip.created_at,
                }
            )

        return {
            "items": trip_items,
            "total": len(trip_items),
            "skip": skip,
            "limit": limit,
        }

    except Exception as e:
        logger.error(f"Failed to search trips: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search trips",
        )


@router.get("/{trip_id}/itinerary")
async def get_trip_itinerary(
    trip_id: UUID,
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
):
    """Get trip itinerary.

    Args:
        trip_id: Trip ID
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Trip itinerary
    """
    logger.info(f"Getting trip itinerary {trip_id} for user: {principal.user_id}")

    try:
        itinerary = await trip_service.get_trip_itinerary(
            user_id=principal.user_id, trip_id=trip_id
        )

        if not itinerary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip or itinerary not found",
            )

        return itinerary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trip itinerary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trip itinerary",
        )


@router.post("/{trip_id}/export")
async def export_trip(
    trip_id: UUID,
    format: str = Query(default="pdf", description="Export format"),
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
):
    """Export trip.

    Args:
        trip_id: Trip ID
        format: Export format
        principal: Current authenticated principal
        trip_service: Trip service instance

    Returns:
        Export data
    """
    logger.info(f"Exporting trip {trip_id} for user: {principal.user_id}")

    try:
        export_data = await trip_service.export_trip(
            user_id=principal.user_id, trip_id=trip_id, format=format
        )

        if not export_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )

        return export_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export trip",
        )


# Enhanced endpoints (only available when enhanced service layer is present)
if ENHANCED_SERVICE_AVAILABLE:
    
    @router.get("/{trip_id}", response_model=TripResponse)
    async def get_trip(
        trip_id: UUID,
        principal: Principal = require_principal_dep,
    ):
        """Get a trip by ID (enhanced service layer)."""
        enhanced_service = get_enhanced_trip_service()
        trip_response = await enhanced_service.get_trip(
            user_id=principal.user_id, trip_id=trip_id
        )
        
        if not trip_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
            )
        
        return trip_response


# Core endpoints (always available)
@router.get("/suggestions", response_model=List[TripSuggestionResponse])
async def get_trip_suggestions(
    limit: int = Query(4, ge=1, le=20, description="Number of suggestions to return"),
    budget_max: Optional[float] = Query(None, description="Maximum budget filter"),
    category: Optional[str] = Query(None, description="Filter by category"),
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
):
    """Get personalized trip suggestions based on user preferences and history.

    Args:
        limit: Maximum number of suggestions to return
        budget_max: Optional maximum budget filter
        category: Optional category filter
        principal: Current authenticated principal
        trip_service: Injected trip service

    Returns:
        List of trip suggestions
    """
    _user_id = get_principal_id(principal)

    # TODO: Implement actual trip suggestions logic using memory service
    # For now, return mock data that matches the frontend structure

    suggestions = [
        TripSuggestionResponse(
            id="suggestion-1",
            title="Tokyo Cherry Blossom Adventure",
            destination="Tokyo, Japan",
            description=(
                "Experience the magic of cherry blossom season in Japan's vibrant "
                "capital city."
            ),
            estimated_price=2800,
            currency="USD",
            duration=7,
            rating=4.8,
            category="culture",
            best_time_to_visit="March - May",
            highlights=["Cherry Blossoms", "Temples", "Street Food", "Modern Culture"],
            trending=True,
            seasonal=True,
        ),
        TripSuggestionResponse(
            id="suggestion-2",
            title="Bali Tropical Retreat",
            destination="Bali, Indonesia",
            description=(
                "Relax on pristine beaches and explore ancient temples in this "
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
                "Chase the aurora borealis and explore dramatic landscapes of fire "
                "and ice."
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

    # Apply filters
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
    filtered_suggestions = filtered_suggestions[:limit]

    return filtered_suggestions
