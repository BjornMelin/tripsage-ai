"""Request models for the TripSage API.

This package contains Pydantic V2 models for API request validation.
"""

from .accommodations import (
    AccommodationDetailsRequest,
    AccommodationSearchRequest,
    SavedAccommodationRequest,
)
from .api_keys import (
    ApiKeyCreate,
    ApiKeyRotateRequest,
    ApiKeyValidateRequest,
)
from .auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshToken,
    RefreshTokenRequest,
    RegisterUserRequest,
    ResetPasswordRequest,
    UserCreate,
    UserLogin,
)
from .chat import ChatRequest
from .destinations import (
    DestinationDetailsRequest,
    DestinationSearchRequest,
    DestinationSuggestionRequest,
    SavedDestinationRequest,
)
from .flights import (
    AirportSearchRequest,
    FlightSearchRequest,
    MultiCityFlightSearchRequest,
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
    "AccommodationDetailsRequest",
    "AccommodationSearchRequest",
    "SavedAccommodationRequest",
    # API Keys
    "ApiKeyCreate",
    "ApiKeyRotateRequest",
    "ApiKeyValidateRequest",
    # Auth
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "LoginRequest",
    "RefreshToken",
    "RefreshTokenRequest",
    "RegisterUserRequest",
    "ResetPasswordRequest",
    "UserCreate",
    "UserLogin",
    # Chat
    "ChatRequest",
    # Destinations
    "DestinationDetailsRequest",
    "DestinationSearchRequest",
    "DestinationSuggestionRequest",
    "SavedDestinationRequest",
    # Flights
    "AirportSearchRequest",
    "FlightSearchRequest",
    "MultiCityFlightSearchRequest",
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
