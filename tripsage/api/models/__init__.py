"""Pydantic models for the TripSage API.

This package contains Pydantic V2 models for request and response validation.
"""

# Import from tripsage_core for shared types
from tripsage_core.models.schemas_common import (
    BookingStatus,
    CancellationPolicy,
)

# Accommodations models
from .common.accommodations import (
    AccommodationAmenity,
    AccommodationImage,
    AccommodationListing,
    AccommodationLocation,
)

# Auth models
from .common.auth import TokenData

# Chat models
from .common.chat import (
    ChatMessage,
    ChatSession,
    ToolCall,
)

# Destinations models
from .common.destinations import (
    Destination,
    DestinationCategory,
    DestinationImage,
    DestinationVisitSchedule,
    DestinationWeather,
    PointOfInterest,
)

# Flights models
from .common.flights import (
    Airport,
    FlightOffer,
    MultiCityFlightSegment,
)

# Itineraries models
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

# Trip models
from .common.trips import (
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

# WebSocket models
from .common.websocket import (
    WebSocketConnectionInfo,
    WebSocketEvent,
    WebSocketEventType,
)
from .requests.accommodations import (
    AccommodationDetailsRequest,
    AccommodationSearchRequest,
    SavedAccommodationRequest,
)

# API Key models
from .requests.api_keys import (
    ApiKeyCreate,
    ApiKeyRotateRequest,
    ApiKeyValidateRequest,
)
from .requests.auth import (
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
from .requests.chat import ChatRequest
from .requests.destinations import (
    DestinationDetailsRequest,
    DestinationSearchRequest,
    DestinationSuggestionRequest,
    SavedDestinationRequest,
)
from .requests.flights import (
    AirportSearchRequest,
    FlightSearchRequest,
    MultiCityFlightSearchRequest,
    SavedFlightRequest,
)
from .requests.itineraries import (
    ItineraryCreateRequest,
    ItineraryItemCreateRequest,
    ItineraryItemUpdateRequest,
    ItineraryOptimizeRequest,
    ItinerarySearchRequest,
    ItineraryUpdateRequest,
)
from .requests.trips import (
    CreateTripRequest,
    TripPreferencesRequest,
    UpdateTripRequest,
)
from .requests.websocket import (
    WebSocketAuthRequest,
    WebSocketSubscribeRequest,
)
from .responses.accommodations import (
    AccommodationDetailsResponse,
    AccommodationSearchResponse,
    SavedAccommodationResponse,
)
from .responses.api_keys import (
    ApiKeyResponse,
    ApiKeyValidateResponse,
)
from .responses.auth import (
    MessageResponse,
    PasswordResetResponse,
    Token,
    TokenResponse,
    UserPreferencesResponse,
    UserResponse,
)
from .responses.chat import (
    ChatResponse,
    ChatStreamChunk,
    SessionHistoryResponse,
)
from .responses.destinations import (
    DestinationDetailsResponse,
    DestinationSearchResponse,
    DestinationSuggestionResponse,
    SavedDestinationResponse,
)
from .responses.flights import (
    AirportSearchResponse,
    FlightSearchResponse,
    SavedFlightResponse,
)
from .responses.itineraries import (
    ItineraryConflictCheckResponse,
    ItineraryOptimizeResponse,
    ItinerarySearchResponse,
)
from .responses.trips import (
    TripListItem,
    TripListResponse,
    TripResponse,
    TripSummaryResponse,
)
from .responses.websocket import (
    WebSocketAuthResponse,
    WebSocketSubscribeResponse,
)

# Alias for backward compatibility
PropertyType = CancellationPolicy  # From accommodations
UserResponseExtended = UserResponse

__all__ = [
    # Shared types
    "BookingStatus",
    "CancellationPolicy",
    "PropertyType",
    # Accommodations models
    "AccommodationAmenity",
    "AccommodationDetailsRequest",
    "AccommodationDetailsResponse",
    "AccommodationImage",
    "AccommodationListing",
    "AccommodationLocation",
    "AccommodationSearchRequest",
    "AccommodationSearchResponse",
    "SavedAccommodationRequest",
    "SavedAccommodationResponse",
    # API Key models
    "ApiKeyCreate",
    "ApiKeyResponse",
    "ApiKeyRotateRequest",
    "ApiKeyValidateRequest",
    "ApiKeyValidateResponse",
    # Auth models
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "LoginRequest",
    "MessageResponse",
    "PasswordResetResponse",
    "RefreshToken",
    "RefreshTokenRequest",
    "RegisterUserRequest",
    "ResetPasswordRequest",
    "Token",
    "TokenData",
    "TokenResponse",
    "UserCreate",
    "UserLogin",
    "UserPreferencesResponse",
    "UserResponse",
    "UserResponseExtended",
    # Chat models
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatSession",
    "ChatStreamChunk",
    "SessionHistoryResponse",
    "ToolCall",
    # Destinations models
    "Destination",
    "DestinationCategory",
    "DestinationDetailsRequest",
    "DestinationDetailsResponse",
    "DestinationImage",
    "DestinationSearchRequest",
    "DestinationSearchResponse",
    "DestinationSuggestionRequest",
    "DestinationSuggestionResponse",
    "DestinationVisitSchedule",
    "DestinationWeather",
    "PointOfInterest",
    "SavedDestinationRequest",
    "SavedDestinationResponse",
    # Flights models
    "Airport",
    "AirportSearchRequest",
    "AirportSearchResponse",
    "FlightOffer",
    "FlightSearchRequest",
    "FlightSearchResponse",
    "MultiCityFlightSearchRequest",
    "MultiCityFlightSegment",
    "SavedFlightRequest",
    "SavedFlightResponse",
    # Itineraries models
    "AccommodationItineraryItem",
    "ActivityItineraryItem",
    "FlightItineraryItem",
    "Itinerary",
    "ItineraryConflictCheckResponse",
    "ItineraryCreateRequest",
    "ItineraryDay",
    "ItineraryItem",
    "ItineraryItemCreateRequest",
    "ItineraryItemType",
    "ItineraryItemUpdateRequest",
    "ItineraryOptimizeRequest",
    "ItineraryOptimizeResponse",
    "ItinerarySearchRequest",
    "ItinerarySearchResponse",
    "ItineraryShareSettings",
    "ItineraryStatus",
    "ItineraryUpdateRequest",
    "ItineraryVisibility",
    "Location",
    "OptimizationSetting",
    "TimeSlot",
    "TransportationItineraryItem",
    # Trip models
    "CreateTripRequest",
    "Trip",
    "TripDay",
    "TripDestination",
    "TripDestinationData",
    "TripListItem",
    "TripListResponse",
    "TripMember",
    "TripPreferenceData",
    "TripPreferences",
    "TripPreferencesRequest",
    "TripResponse",
    "TripStatus",
    "TripSummaryResponse",
    "TripVisibility",
    "UpdateTripRequest",
    # WebSocket models
    "WebSocketAuthRequest",
    "WebSocketAuthResponse",
    "WebSocketConnectionInfo",
    "WebSocketEvent",
    "WebSocketEventType",
    "WebSocketSubscribeRequest",
    "WebSocketSubscribeResponse",
]
