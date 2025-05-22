"""Database models for TripSage.

This module provides essential business models that represent
core domain entities with validation logic, used across
different storage backends (Supabase SQL, Neo4j).
"""

from tripsage.models.db.accommodation import (
    Accommodation,
    AccommodationType,
    CancellationPolicy,
)
from tripsage.models.db.accommodation import (
    BookingStatus as AccommodationBookingStatus,
)
from tripsage.models.db.flight import (
    AirlineProvider,
    DataSource,
    Flight,
)
from tripsage.models.db.flight import (
    BookingStatus as FlightBookingStatus,
)

# Temporarily commented out until fixed
# from tripsage.models.db.itinerary_item import ItemType, ItineraryItem
from tripsage.models.db.price_history import EntityType, PriceHistory
from tripsage.models.db.saved_option import OptionType, SavedOption
from tripsage.models.db.search_parameters import SearchParameters
from tripsage.models.db.transportation import (
    BookingStatus as TransportationBookingStatus,
)
from tripsage.models.db.transportation import (
    Transportation,
    TransportationType,
)
from tripsage.models.db.trip import Trip, TripStatus, TripType
from tripsage.models.db.trip_comparison import TripComparison
from tripsage.models.db.trip_note import TripNote
from tripsage.models.db.user import User
from tripsage.models.db.api_key import ApiKeyDB, ApiKeyCreate, ApiKeyUpdate

__all__ = [
    # User
    "User",
    # API Key
    "ApiKeyDB",
    "ApiKeyCreate", 
    "ApiKeyUpdate",
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
    # Itinerary Item - temporarily commented out
    # "ItineraryItem",
    # "ItemType",
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
