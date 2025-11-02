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
    DataSource,
    EntityType,
    Flight,
    FlightBookingStatus,
    Memory,
    MemoryCreate,
    MemoryUpdate,
    # Removed: MessageWithTokenEstimate,
    OptionType,
    PriceHistory,
    # Removed: RecentMessagesResponse,
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
    Entity,
    FlightOffer,
    FlightSegment,
    PropertyType,
    Relation,
    SessionMemory,
    TravelMemory,
)
from .schemas_common.enums import CabinClass


__all__ = [
    # Database models - Accommodation DB
    "Accommodation",
    "AccommodationAmenity",
    "AccommodationBookingStatus",
    "AccommodationImage",
    # Domain models - Accommodation
    "AccommodationListing",
    "AccommodationLocation",
    "AccommodationType",
    "Airport",
    "ApiKeyCreate",
    "ApiKeyDB",
    "ApiKeyUpdate",
    "CabinClass",
    "CancellationPolicy",
    # Chat DB models removed
    "DataSource",
    # Domain models - Memory
    "Entity",
    "EntityType",
    # Database models - Flight DB
    "Flight",
    "FlightBookingStatus",
    # Domain models - Flight
    "FlightOffer",
    "FlightSegment",
    # Database models - Memory
    "Memory",
    "MemoryCreate",
    "MemoryUpdate",
    # Removed: MessageWithTokenEstimate,
    "OptionType",
    "PriceHistory",
    "PropertyType",
    # Removed: RecentMessagesResponse,
    "Relation",
    "SavedOption",
    # Database models - Search & History
    "SearchParameters",
    "SessionMemory",
    # Database models - Transportation
    "Transportation",
    "TransportationBookingStatus",
    "TransportationType",
    "TravelMemory",
    # Database models - Trip Management
    "Trip",
    "TripComparison",
    "TripNote",
    "TripSageBaseResponse",
    "TripSageDBModel",
    "TripSageDomainModel",
    # Base models
    "TripSageModel",
    "TripStatus",
    "TripType",
    # Database models - User & Auth
    "User",
    "UserRole",
]
