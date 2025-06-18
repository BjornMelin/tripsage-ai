"""
Core business domain models for TripSage.

This module contains the canonical business domain models that represent
core entities and concepts in the TripSage travel planning system.
These models are independent of storage implementation and API specifics.

Domain Models:
- Accommodation: AccommodationListing, AccommodationLocation, AccommodationAmenity,
  AccommodationImage, PropertyType
- Flight: FlightOffer, Airport, FlightSegment, CabinClass
- Transportation: TransportationOffer, TransportationProvider, TransportationVehicle,
  TransportationLocation
- Memory: Entity, Relation, TravelMemory, SessionMemory

Note: Trip domain models have been moved to a unified model at tripsage_core.models.trip

Usage:
    from tripsage_core.models.domain import (
        AccommodationListing,
        FlightOffer,
        TransportationOffer,
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

# Transportation domain models
from .transportation import (
    TransportationLocation,
    TransportationOffer,
    TransportationProvider,
    TransportationVehicle,
)

# Trip domain models - removed as they're now in the unified model

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
    # Transportation models
    "TransportationOffer",
    "TransportationProvider",
    "TransportationVehicle",
    "TransportationLocation",
    # Memory models
    "Entity",
    "Relation",
    "TravelMemory",
    "SessionMemory",
]
