"""Trip router for TripSage API.

This module provides endpoints for trip management, including creating,
retrieving, updating, and deleting trips.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from tripsage.api.core.dependencies import get_principal_id, require_principal_dep
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.trips import (
    CreateTripRequest,
    TripResponse,
    TripSuggestionResponse,
)
from tripsage_core.services.business.trip_service import TripService, get_trip_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_request: CreateTripRequest,
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
):
    """Create a new trip.

    Args:
        trip_request: Trip creation request
        principal: Current authenticated principal

    Returns:
        Created trip
    """
    from datetime import datetime, timezone

    from tripsage_core.services.business.trip_service import (
        TripCreateRequest as ServiceTripCreateRequest,
    )
    from tripsage_core.services.business.trip_service import (
        TripLocation,
    )

    # Extract user ID from principal
    user_id = get_principal_id(principal)

    # Convert API destinations to service TripLocation format
    service_destinations = []
    for dest in trip_request.destinations:
        trip_location = TripLocation(
            name=dest.name,
            country=dest.country,
            city=dest.city,
            coordinates=dest.coordinates.model_dump() if dest.coordinates else None,
            timezone=None,  # Not provided in API request
        )
        service_destinations.append(trip_location)

    # Convert dates from date to datetime (start of day UTC)
    start_datetime = datetime.combine(
        trip_request.start_date, datetime.min.time()
    ).replace(tzinfo=timezone.utc)
    end_datetime = datetime.combine(trip_request.end_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )

    # Convert preferences to dict format expected by service
    preferences_dict = {}
    if trip_request.preferences:
        preferences_dict = trip_request.preferences.model_dump()

    # Create service layer request
    service_request = ServiceTripCreateRequest(
        title=trip_request.title,
        description=trip_request.description,
        start_date=start_datetime,
        end_date=end_datetime,
        destinations=service_destinations,
        preferences=preferences_dict,
        # Use defaults for fields not in API request
        budget=None,
        visibility="private",  # Default visibility
        tags=[],  # No tags in API request
    )

    # Call service to create trip
    trip_response = await trip_service.create_trip(user_id, service_request)

    logger.info(
        f"Trip created successfully for user {user_id}",
        extra={
            "trip_id": trip_response.id,
            "title": trip_response.title,
            "user_id": user_id,
        },
    )

    return trip_response


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
    user_id = get_principal_id(principal)

    # TODO: Implement actual trip suggestions logic using memory service
    # For now, return mock data that matches the frontend structure

    suggestions = [
        TripSuggestionResponse(
            id="suggestion-1",
            title="Tokyo Cherry Blossom Adventure",
            destination="Tokyo, Japan",
            description="Experience the magic of cherry blossom season in Japan's vibrant capital city.",
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
            description="Relax on pristine beaches and explore ancient temples in this tropical paradise.",
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
            description="Challenge yourself with breathtaking alpine hikes and stunning mountain views.",
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
            description="Watch spectacular sunsets from clifftop villages in this iconic Greek island.",
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
            description="Chase the aurora borealis and explore dramatic landscapes of fire and ice.",
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
