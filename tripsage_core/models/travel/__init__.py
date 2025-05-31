"""Travel domain models.

This module contains all travel-related domain models following modern Pydantic v2
patterns and domain-driven design principles.

Exports:
    Accommodation models: Accommodation, AccommodationListing
    Flight models: Flight, FlightOffer
    Trip models: Trip, TripPlan
    Transportation models: Transportation, TransportationOffer
"""

from .accommodations import Accommodation, AccommodationListing
from .flights import Flight, FlightOffer
from .transportation import Transportation, TransportationOffer
from .trips import Trip, TripPlan

__all__ = [
    # Accommodations
    "Accommodation",
    "AccommodationListing",
    # Flights
    "Flight",
    "FlightOffer",
    # Transportation
    "Transportation",
    "TransportationOffer",
    # Trips
    "Trip",
    "TripPlan",
]
