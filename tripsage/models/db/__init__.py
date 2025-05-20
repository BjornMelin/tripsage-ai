"""Database models for TripSage.

This module provides essential business models that represent
core domain entities with validation logic, used across
different storage backends (Supabase SQL, Neo4j).
"""

from tripsage.models.db.accommodation import (
    Accommodation,
    AccommodationType,
    BookingStatus as AccommodationBookingStatus,
    CancellationPolicy,
)
from tripsage.models.db.flight import (
    AirlineProvider,
    BookingStatus as FlightBookingStatus,
    DataSource,
    Flight,
)
from tripsage.models.db.itinerary_item import ItemType, ItineraryItem
from tripsage.models.db.price_history import EntityType, PriceHistory
from tripsage.models.db.saved_option import OptionType, SavedOption
from tripsage.models.db.search_parameters import SearchParameters
from tripsage.models.db.transportation import (
    BookingStatus as TransportationBookingStatus,
    Transportation,
    TransportationType,
)
from tripsage.models.db.trip import Trip, TripStatus, TripType
from tripsage.models.db.trip_comparison import TripComparison
from tripsage.models.db.trip_note import TripNote
from tripsage.models.db.user import User

__all__ = [
    # User
    "User",
    
    # Trip
    "Trip",
    "TripStatus",
    "TripType",
    
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
    
    # Itinerary Item
    "ItineraryItem",
    "ItemType",
    
    # Search Parameters
    "SearchParameters",
    
    # Trip Note
    "TripNote",
    
    # Price History
    "PriceHistory",
    "EntityType",
    
    # Saved Option
    "SavedOption",
    "OptionType",
    
    # Trip Comparison
    "TripComparison",
]