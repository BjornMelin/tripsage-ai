"""Common models for the TripSage API.

This package contains shared Pydantic V2 models used across the API.
"""

from .accommodations import (
    AccommodationAmenity,
    AccommodationImage,
    AccommodationListing,
    AccommodationLocation,
)
from .auth import TokenData
from .chat import (
    ChatMessage,
    ChatSession,
    ToolCall,
)
from .destinations import (
    Destination,
    DestinationCategory,
    DestinationImage,
    DestinationVisitSchedule,
    DestinationWeather,
    PointOfInterest,
)
from .flights import (
    Airport,
    FlightOffer,
    MultiCityFlightSegment,
)
from .itineraries import (
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
from .trips import (
    Trip,
    TripDay,
    TripDestination,
    TripDestinationData,
    TripMember,
    TripPreferenceData,
    TripPreferences,
    TripStatus,
    TripVisibility,
)
from .websocket import (
    WebSocketConnectionInfo,
    WebSocketEvent,
    WebSocketEventType,
)

__all__ = [
    # Accommodations
    "AccommodationAmenity",
    "AccommodationImage",
    "AccommodationListing",
    "AccommodationLocation",
    # Auth
    "TokenData",
    # Chat
    "ChatMessage",
    "ChatSession",
    "ToolCall",
    # Destinations
    "Destination",
    "DestinationCategory",
    "DestinationImage",
    "DestinationVisitSchedule",
    "DestinationWeather",
    "PointOfInterest",
    # Flights
    "Airport",
    "FlightOffer",
    "MultiCityFlightSegment",
    # Itineraries
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
    # Trips
    "Trip",
    "TripDay",
    "TripDestination",
    "TripDestinationData",
    "TripMember",
    "TripPreferenceData",
    "TripPreferences",
    "TripStatus",
    "TripVisibility",
    # WebSocket
    "WebSocketConnectionInfo",
    "WebSocketEvent",
    "WebSocketEventType",
]
