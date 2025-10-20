"""TripSage Core Models.

This module provides centralized access to all core TripSage models including:
- Base models for consistent configuration
- Domain models for core business entities
- Database models for persistence
- Common schemas and utilities

Model Categories:
- Base: TripSageModel, TripSageBaseResponse, TripSageDomainModel, TripSageDBModel
- Domain: AccommodationListing, FlightOffer, Entity, TravelMemory, etc.
- Database: All database-specific models from db/ directory

Usage:
    # Import base models
    from tripsage_core.models import TripSageModel, TripSageDomainModel

    # Import domain models
    from tripsage_core.models.domain import AccommodationListing, FlightOffer

    # Import database models
    from tripsage_core.models.db import User, Trip, ApiKeyDB
"""

# Base models - centralized model foundation
from .base_core_model import (
    TripSageBaseResponse,
    TripSageDBModel,
    TripSageDomainModel,
    TripSageModel,
)

# Database models - persistence layer
from .db import (
    Accommodation,
    AccommodationBookingStatus,
    AccommodationType,
    ApiKeyCreate,
    ApiKeyDB,
    ApiKeyUpdate,
    CancellationPolicy,
    ChatMessageDB,
    ChatSessionDB,
    ChatSessionWithStats,
    ChatToolCallDB,
    DataSource,
    EntityType,
    Flight,
    FlightBookingStatus,
    Memory,
    MemoryCreate,
    MemorySearchResult,
    MemoryUpdate,
    MessageWithTokenEstimate,
    OptionType,
    PriceHistory,
    RecentMessagesResponse,
    SavedOption,
    SearchParameters,
    Transportation,
    TransportationBookingStatus,
    TransportationType,
    Trip,
    TripComparison,
    TripNote,
    TripStatus,
    TripType,
    User,
    UserRole,
)

# Domain models - core business entities
from .domain import (
    AccommodationAmenity,
    AccommodationImage,
    AccommodationListing,
    AccommodationLocation,
    Airport,
    CabinClass,
    Entity,
    FlightOffer,
    FlightSegment,
    PropertyType,
    Relation,
    SessionMemory,
    TravelMemory,
)


__all__ = [
    # Base models
    "TripSageModel",
    "TripSageBaseResponse",
    "TripSageDomainModel",
    "TripSageDBModel",
    # Domain models - Accommodation
    "AccommodationListing",
    "AccommodationLocation",
    "AccommodationAmenity",
    "AccommodationImage",
    "PropertyType",
    # Domain models - Flight
    "FlightOffer",
    "Airport",
    "FlightSegment",
    "CabinClass",
    # Domain models - Memory
    "Entity",
    "Relation",
    "TravelMemory",
    "SessionMemory",
    # Database models - User & Auth
    "User",
    "UserRole",
    "ApiKeyDB",
    "ApiKeyCreate",
    "ApiKeyUpdate",
    # Database models - Trip Management
    "Trip",
    "TripStatus",
    "TripType",
    "TripNote",
    "TripComparison",
    # Database models - Accommodation DB
    "Accommodation",
    "AccommodationType",
    "AccommodationBookingStatus",
    "CancellationPolicy",
    # Database models - Flight DB
    "Flight",
    "FlightBookingStatus",
    "DataSource",
    # Database models - Transportation
    "Transportation",
    "TransportationType",
    "TransportationBookingStatus",
    # Database models - Search & History
    "SearchParameters",
    "PriceHistory",
    "EntityType",
    "SavedOption",
    "OptionType",
    # Database models - Chat
    "ChatSessionDB",
    "ChatMessageDB",
    "ChatToolCallDB",
    "ChatSessionWithStats",
    "MessageWithTokenEstimate",
    "RecentMessagesResponse",
    # Database models - Memory
    "Memory",
    "MemoryCreate",
    "MemoryUpdate",
    "MemorySearchResult",
]
