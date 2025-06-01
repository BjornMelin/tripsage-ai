"""API request schemas for TripSage."""

from .accommodations import (
    AccommodationSearchRequest,
)
from .api_keys import (
    ApiKeyCreate,
    ApiKeyRotateRequest,
    ApiKeyValidateRequest,
)
from .auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from .chat import (
    ChatRequest,
)
from .destinations import (
    DestinationCategory,
    DestinationDetailsRequest,
    DestinationSearchRequest,
    DestinationSuggestionRequest,
    DestinationVisitSchedule,
    PointOfInterestSearchRequest,
    SavedDestinationRequest,
)
from .flights import (
    AirportSearchRequest,
    FlightSearchRequest,
    MultiCityFlightSearchRequest,
    MultiCityFlightSegment,
    SavedFlightRequest,
)
from .itineraries import (
    ItineraryCreateRequest,
    ItineraryItemCreateRequest,
    ItineraryItemUpdateRequest,
    ItineraryOptimizeRequest,
    ItinerarySearchRequest,
    ItineraryUpdateRequest,
)
from .trips import (
    CreateTripRequest,
    TripPreferencesRequest,
    UpdateTripRequest,
)
from .websocket import (
    WebSocketAuthRequest,
    WebSocketSubscribeRequest,
)

__all__ = [
    # Accommodations
    "AccommodationSearchRequest",
    # API Keys
    "ApiKeyCreate",
    "ApiKeyRotateRequest",
    "ApiKeyValidateRequest",
    # Auth
    "LoginRequest",
    "RefreshTokenRequest",
    "RegisterRequest",
    "ResetPasswordRequest",
    # Chat
    "ChatRequest",
    # Destinations
    "DestinationCategory",
    "DestinationDetailsRequest",
    "DestinationSearchRequest",
    "DestinationSuggestionRequest",
    "DestinationVisitSchedule",
    "PointOfInterestSearchRequest",
    "SavedDestinationRequest",
    # Flights
    "AirportSearchRequest",
    "FlightSearchRequest",
    "MultiCityFlightSearchRequest",
    "MultiCityFlightSegment",
    "SavedFlightRequest",
    # Itineraries
    "ItineraryCreateRequest",
    "ItineraryItemCreateRequest",
    "ItineraryItemUpdateRequest",
    "ItineraryOptimizeRequest",
    "ItinerarySearchRequest",
    "ItineraryUpdateRequest",
    # Trips
    "CreateTripRequest",
    "TripPreferencesRequest",
    "UpdateTripRequest",
    # WebSocket
    "WebSocketAuthRequest",
    "WebSocketSubscribeRequest",
]
