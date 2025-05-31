"""Response models for the TripSage API.

This package contains Pydantic V2 models for API response validation.
"""

from .accommodations import (
    AccommodationDetailsResponse,
    AccommodationSearchResponse,
    SavedAccommodationResponse,
)
from .api_keys import (
    ApiKeyResponse,
    ApiKeyValidateResponse,
)
from .auth import (
    MessageResponse,
    PasswordResetResponse,
    Token,
    TokenResponse,
    UserPreferencesResponse,
    UserResponse,
)
from .chat import (
    ChatResponse,
    ChatStreamChunk,
    SessionHistoryResponse,
)
from .destinations import (
    DestinationDetailsResponse,
    DestinationSearchResponse,
    DestinationSuggestionResponse,
    SavedDestinationResponse,
)
from .flights import (
    AirportSearchResponse,
    FlightSearchResponse,
    SavedFlightResponse,
)
from .itineraries import (
    ItineraryConflictCheckResponse,
    ItineraryOptimizeResponse,
    ItinerarySearchResponse,
)
from .trips import (
    TripListItem,
    TripListResponse,
    TripResponse,
    TripSummaryResponse,
)
from .websocket import (
    WebSocketAuthResponse,
    WebSocketSubscribeResponse,
)

__all__ = [
    # Accommodations
    "AccommodationDetailsResponse",
    "AccommodationSearchResponse",
    "SavedAccommodationResponse",
    # API Keys
    "ApiKeyResponse",
    "ApiKeyValidateResponse",
    # Auth
    "MessageResponse",
    "PasswordResetResponse",
    "Token",
    "TokenResponse",
    "UserPreferencesResponse",
    "UserResponse",
    # Chat
    "ChatResponse",
    "ChatStreamChunk",
    "SessionHistoryResponse",
    # Destinations
    "DestinationDetailsResponse",
    "DestinationSearchResponse",
    "DestinationSuggestionResponse",
    "SavedDestinationResponse",
    # Flights
    "AirportSearchResponse",
    "FlightSearchResponse",
    "SavedFlightResponse",
    # Itineraries
    "ItineraryConflictCheckResponse",
    "ItineraryOptimizeResponse",
    "ItinerarySearchResponse",
    # Trips
    "TripListItem",
    "TripListResponse",
    "TripResponse",
    "TripSummaryResponse",
    # WebSocket
    "WebSocketAuthResponse",
    "WebSocketSubscribeResponse",
]
