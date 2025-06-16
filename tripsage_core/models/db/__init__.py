"""Consolidated database models for TripSage.

This module provides essential business models that represent
core domain entities with validation logic, used across
different storage backends (Supabase SQL, Neo4j).
"""

# User models
# Accommodation models
from ..schemas_common.enums import TripStatus, TripType, TripVisibility
from .accommodation import (
    Accommodation,
    AccommodationType,
    CancellationPolicy,
)
from .accommodation import (
    BookingStatus as AccommodationBookingStatus,
)

# API Key models
from .api_key import ApiKeyCreate, ApiKeyDB, ApiKeyUpdate

# Chat models
from .chat import (
    ChatMessageDB,
    ChatSessionDB,
    ChatSessionWithStats,
    ChatToolCallDB,
    MessageWithTokenEstimate,
    RecentMessagesResponse,
)

# Flight models
from .flight import (
    AirlineProvider,
    DataSource,
    Flight,
)
from .flight import (
    BookingStatus as FlightBookingStatus,
)

# Memory models (Mem0 + pgvector)
from .memory import (
    Memory,
    MemoryCreate,
    MemorySearchResult,
    MemoryUpdate,
    SessionMemory,
)
from .price_history import EntityType, PriceHistory
from .saved_option import OptionType, SavedOption

# Itinerary Item models (temporarily commented out until fixed)
# from .itinerary_item import ItemType, ItineraryItem
# Search and History models
from .search_parameters import SearchParameters

# Transportation models
from .transportation import (
    BookingStatus as TransportationBookingStatus,
)
from .transportation import (
    Transportation,
    TransportationType,
)

# Trip models
from ..trip import Trip

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
    # User
    "User",
    "UserRole",
    # API Key
    "ApiKeyDB",
    "ApiKeyCreate",
    "ApiKeyUpdate",
    # Trip
    "Trip",
    "TripStatus",
    "TripType",
    "TripVisibility",
    # Flight
    "Flight",
    "AirlineProvider",
    "FlightBookingStatus",
    "DataSource",
    # Accommodation
    "Accommodation",
    "AccommodationType",
    "AccommodationBookingStatus",
    "CancellationPolicy",
    # Transportation
    "Transportation",
    "TransportationType",
    "TransportationBookingStatus",
    # Itinerary Item - temporarily commented out
    # "ItineraryItem",
    # "ItemType",
    # Search Parameters
    "SearchParameters",
    # Trip Note
    "TripNote",
    # Trip Collaborator
    "TripCollaboratorDB",
    "TripCollaboratorCreate",
    "TripCollaboratorUpdate",
    "PermissionLevel",
    # Price History
    "PriceHistory",
    "EntityType",
    # Saved Option
    "SavedOption",
    "OptionType",
    # Trip Comparison
    "TripComparison",
    # Chat models
    "ChatSessionDB",
    "ChatMessageDB",
    "ChatToolCallDB",
    "ChatSessionWithStats",
    "MessageWithTokenEstimate",
    "RecentMessagesResponse",
    # Memory models
    "Memory",
    "SessionMemory",
    "MemorySearchResult",
    "MemoryCreate",
    "MemoryUpdate",
]
