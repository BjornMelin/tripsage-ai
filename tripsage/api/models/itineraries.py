"""
Models related to itineraries in the TripSage API.

This module provides consolidated imports for itinerary-related models.
Models are now organized into separate modules for better maintainability:
- common/itineraries.py: Shared domain models and data structures
- requests/itineraries.py: Request models for itinerary endpoints
- responses/itineraries.py: Response models for itinerary endpoints
"""

# Import all models from the organized modules for backward compatibility
from .common.itineraries import (
    AccommodationItineraryItem,
    ActivityItineraryItem,
    FlightItineraryItem,
    Itinerary,
    ItineraryDay,
    ItineraryItem,
    ItineraryItemType,
    ItineraryShareSettings,
    ItineraryStatus,
    ItineraryVisibility,
    Location,
    OptimizationSetting,
    TimeSlot,
    TransportationItineraryItem,
)
from .requests.itineraries import (
    ItineraryCreateRequest,
    ItineraryItemCreateRequest,
    ItineraryItemUpdateRequest,
    ItineraryOptimizeRequest,
    ItinerarySearchRequest,
    ItineraryUpdateRequest,
)
from .responses.itineraries import (
    ItineraryConflictCheckResponse,
    ItineraryOptimizeResponse,
    ItinerarySearchResponse,
)

# Export all models for backward compatibility
__all__ = [
    # Common models
    "AccommodationItineraryItem",
    "ActivityItineraryItem",
    "FlightItineraryItem",
    "Itinerary",
    "ItineraryDay",
    "ItineraryItem",
    "ItineraryItemType",
    "ItineraryShareSettings",
    "ItineraryStatus",
    "ItineraryVisibility",
    "Location",
    "OptimizationSetting",
    "TimeSlot",
    "TransportationItineraryItem",
    # Request models
    "ItineraryCreateRequest",
    "ItineraryItemCreateRequest",
    "ItineraryItemUpdateRequest",
    "ItineraryOptimizeRequest",
    "ItinerarySearchRequest",
    "ItineraryUpdateRequest",
    # Response models
    "ItineraryConflictCheckResponse",
    "ItineraryOptimizeResponse",
    "ItinerarySearchResponse",
]
