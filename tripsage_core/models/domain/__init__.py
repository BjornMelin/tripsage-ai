"""
Core business domain models for TripSage.

This module contains the canonical business domain models that represent
core entities and concepts in the TripSage travel planning system.
These models are independent of storage implementation and API specifics.

Domain Models:
- Accommodation: AccommodationListing, AccommodationLocation, AccommodationAmenity, AccommodationImage, PropertyType
- Flight: FlightOffer, Airport, FlightSegment, CabinClass
- Memory: Entity, Relation, TravelMemory, SessionMemory

Usage:
    from tripsage_core.models.domain import (
        AccommodationListing,
        FlightOffer,
        Entity,
        TravelMemory
    )
"""

# Accommodation domain models
from .accommodation import (
    AccommodationAmenity,
    AccommodationImage,
    AccommodationListing,
    AccommodationLocation,
    PropertyType,
)

# Flight domain models
from .flight import (
    Airport,
    CabinClass,
    FlightOffer,
    FlightSegment,
)

# Memory and knowledge graph domain models
from .memory import (
    Entity,
    Relation,
    SessionMemory,
    TravelMemory,
)

__all__ = [
    # Accommodation models
    "AccommodationListing",
    "AccommodationLocation",
    "AccommodationAmenity",
    "AccommodationImage",
    "PropertyType",
    # Flight models
    "FlightOffer",
    "Airport",
    "FlightSegment",
    "CabinClass",
    # Memory models
    "Entity",
    "Relation",
    "TravelMemory",
    "SessionMemory",
]
