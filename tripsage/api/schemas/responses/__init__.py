"""API response schemas for TripSage."""

from .accommodations import (
    AccommodationDetailsResponse,
    AccommodationListing,
    AccommodationLocation,
    AccommodationSearchResponse,
    SavedAccommodationResponse,
)
from .api_keys import (
    ApiKeyListResponse,
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
    DestinationRecommendation,
    DestinationSearchResponse,
    DestinationSuggestionResponse,
    SavedDestinationResponse,
)
from .flights import (
    Airport,
    AirportSearchResponse,
    FlightOffer,
    FlightSearchResponse,
    SavedFlightResponse,
)
from .itineraries import (
    ItineraryConflictCheckResponse,
    ItineraryOptimizeResponse,
    ItineraryResponse,
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
    "AccommodationListing",
    "AccommodationLocation",
    "AccommodationSearchResponse",
    "SavedAccommodationResponse",
    # API Keys
    "ApiKeyListResponse",
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
    "DestinationRecommendation",
    "DestinationSearchResponse",
    "DestinationSuggestionResponse",
    "SavedDestinationResponse",
    # Flights
    "Airport",
    "AirportSearchResponse",
    "FlightOffer",
    "FlightSearchResponse",
    "SavedFlightResponse",
    # Itineraries
    "ItineraryConflictCheckResponse",
    "ItineraryOptimizeResponse",
    "ItineraryResponse",
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
