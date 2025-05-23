"""Pydantic models for the TripSage API.

This package contains Pydantic V2 models for request and response validation.
"""

# Auth models
# Accommodations models
from tripsage.api.models.accommodations import (
    AccommodationAmenity,
    AccommodationDetailsRequest,
    AccommodationDetailsResponse,
    AccommodationImage,
    AccommodationListing,
    AccommodationLocation,
    AccommodationSearchRequest,
    AccommodationSearchResponse,
    BookingStatus,
    CancellationPolicy,
    PropertyType,
    SavedAccommodationRequest,
    SavedAccommodationResponse,
)
from tripsage.api.models.api_key import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyRotateRequest,
    ApiKeyValidateRequest,
    ApiKeyValidateResponse,
)
from tripsage.api.models.auth import (
    RefreshToken,
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
)

# Destinations models
from tripsage.api.models.destinations import (
    Destination,
    DestinationCategory,
    DestinationDetailsRequest,
    DestinationDetailsResponse,
    DestinationImage,
    DestinationSearchRequest,
    DestinationSearchResponse,
    DestinationSuggestionRequest,
    DestinationSuggestionResponse,
    DestinationVisitSchedule,
    DestinationWeather,
    PointOfInterest,
    SavedDestinationRequest,
    SavedDestinationResponse,
)

# Flights models
from tripsage.api.models.flights import (
    Airport,
    AirportSearchRequest,
    AirportSearchResponse,
    FlightOffer,
    FlightSearchRequest,
    FlightSearchResponse,
    MultiCityFlightSearchRequest,
    MultiCityFlightSegment,
    SavedFlightRequest,
    SavedFlightResponse,
)

# Itineraries models - temporarily commented out due to Pydantic V2 compatibility issues
# from tripsage.api.models.itineraries import (
#     AccommodationItineraryItem,
#     ActivityItineraryItem,
#     FlightItineraryItem,
#     Itinerary,
#     ItineraryConflictCheckResponse,
#     ItineraryCreateRequest,
#     ItineraryDay,
#     ItineraryItem,
#     ItineraryItemCreateRequest,
#     ItineraryItemType,
#     ItineraryItemUpdateRequest,
#     ItineraryOptimizeRequest,
#     ItineraryOptimizeResponse,
#     ItinerarySearchRequest,
#     ItinerarySearchResponse,
#     ItineraryShareSettings,
#     ItineraryStatus,
#     ItineraryUpdateRequest,
#     ItineraryVisibility,
#     Location,
#     OptimizationSetting,
#     TimeSlot,
#     TransportationItineraryItem,
# )
# Request models
from tripsage.api.models.requests.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterUserRequest,
    ResetPasswordRequest,
)
from tripsage.api.models.requests.trips import (
    CreateTripRequest,
    TripDestination,
    TripPreferences,
    TripPreferencesRequest,
    UpdateTripRequest,
)

# Response models
from tripsage.api.models.responses.auth import (
    MessageResponse,
    PasswordResetResponse,
    TokenResponse,
    UserPreferencesResponse,
)
from tripsage.api.models.responses.auth import UserResponse as UserResponseExtended
from tripsage.api.models.responses.trips import (
    TripListItem,
    TripListResponse,
    TripResponse,
    TripSummaryResponse,
)

# Trip models
from tripsage.api.models.trips import (
    Trip,
    TripDay,
    TripDestinationData,
    TripMember,
    TripPreferenceData,
    TripStatus,
    TripVisibility,
)

__all__ = [
    # Auth models
    "Token",
    "TokenData",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "RefreshToken",
    "ApiKeyCreate",
    "ApiKeyResponse",
    "ApiKeyValidateRequest",
    "ApiKeyValidateResponse",
    "ApiKeyRotateRequest",
    # Accommodations models
    "AccommodationAmenity",
    "AccommodationDetailsRequest",
    "AccommodationDetailsResponse",
    "AccommodationImage",
    "AccommodationListing",
    "AccommodationLocation",
    "AccommodationSearchRequest",
    "AccommodationSearchResponse",
    "BookingStatus",
    "CancellationPolicy",
    "PropertyType",
    "SavedAccommodationRequest",
    "SavedAccommodationResponse",
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
    # Request models
    "RegisterUserRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "TripDestination",
    "TripPreferences",
    "CreateTripRequest",
    "UpdateTripRequest",
    "TripPreferencesRequest",
    # Response models
    "TokenResponse",
    "UserResponseExtended",
    "UserPreferencesResponse",
    "MessageResponse",
    "PasswordResetResponse",
    "TripResponse",
    "TripListItem",
    "TripListResponse",
    "TripSummaryResponse",
    # Trip models
    "Trip",
    "TripDay",
    "TripDestinationData",
    "TripMember",
    "TripPreferenceData",
    "TripStatus",
    "TripVisibility",
]
