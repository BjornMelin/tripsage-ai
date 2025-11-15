"""Database models for TripSage.

This module provides essential business models that represent
core domain entities with validation logic, used across
different storage backends (Supabase SQL, Neo4j).
"""

# User models
# Accommodation models
from ..schemas_common.enums import TripStatus, TripType, TripVisibility

# Trip models
from ..trip import Trip
from .accommodation import (
    Accommodation,
    AccommodationType,
    BookingStatus as AccommodationBookingStatus,
    CancellationPolicy,
)

# API Key models
from .api_key import ApiKeyCreate, ApiKeyDB, ApiKeyUpdate

# Chat DB models removed; chat endpoints are implemented in Next.js.
# Flight models
from .flight import (
    AirlineProvider,
    BookingStatus as FlightBookingStatus,
    DataSource,
    Flight,
)

# Memory models removed; handled via frontend AI SDK v6
from .price_history import EntityType, PriceHistory
from .saved_option import OptionType, SavedOption

# Itinerary Item models (temporarily commented out until fixed)
# from .itinerary_item import ItemType, ItineraryItem
# Search and History models
from .search_parameters import SearchParameters

# Transportation models
from .transportation import (
    BookingStatus as TransportationBookingStatus,
    Transportation,
    TransportationType,
)

# Trip management models
from .trip_collaborator import (
    PermissionLevel,
    TripCollaboratorCreate,
    TripCollaboratorDB,
    TripCollaboratorUpdate,
)
from .trip_comparison import TripComparison
from .trip_note import TripNote
from .user import User, UserRole


__all__ = [
    # Accommodation
    "Accommodation",
    "AccommodationBookingStatus",
    "AccommodationType",
    "AirlineProvider",
    "ApiKeyCreate",
    # API Key
    "ApiKeyDB",
    "ApiKeyUpdate",
    "CancellationPolicy",
    # Chat DB models removed
    "DataSource",
    "EntityType",
    # Flight
    "Flight",
    "FlightBookingStatus",
    # Memory models removed; handled via frontend AI SDK v6
    # Removed: MessageWithTokenEstimate
    "OptionType",
    "PermissionLevel",
    # Price History
    "PriceHistory",
    # Removed: RecentMessagesResponse
    # Saved Option
    "SavedOption",
    # Itinerary Item - temporarily commented out
    # "ItineraryItem",
    # "ItemType",
    # Search Parameters
    "SearchParameters",
    # Transportation
    "Transportation",
    "TransportationBookingStatus",
    "TransportationType",
    # Trip
    "Trip",
    "TripCollaboratorCreate",
    # Trip Collaborator
    "TripCollaboratorDB",
    "TripCollaboratorUpdate",
    # Trip Comparison
    "TripComparison",
    # Trip Note
    "TripNote",
    "TripStatus",
    "TripType",
    "TripVisibility",
    # User
    "User",
    "UserRole",
]
