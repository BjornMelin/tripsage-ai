"""Database models for TripSage.

This module provides essential business models that represent
core domain entities with validation logic, used across
different storage backends (Supabase SQL, Neo4j).
"""

from tripsage_core.models.db.accommodation import (
    Accommodation,
    AccommodationType,
    CancellationPolicy,
)
from tripsage_core.models.db.accommodation import (
    BookingStatus as AccommodationBookingStatus,
)
from tripsage_core.models.db.api_key import ApiKeyCreate, ApiKeyDB, ApiKeyUpdate
from tripsage_core.models.db.flight import (
    AirlineProvider,
    DataSource,
    Flight,
)
from tripsage_core.models.db.flight import (
    BookingStatus as FlightBookingStatus,
)

# Temporarily commented out until fixed
# from tripsage_core.models.db.itinerary_item import ItemType, ItineraryItem
from tripsage_core.models.db.price_history import EntityType, PriceHistory
from tripsage_core.models.db.saved_option import OptionType, SavedOption
from tripsage_core.models.db.search_parameters import SearchParameters
from tripsage_core.models.db.transportation import (
    BookingStatus as TransportationBookingStatus,
)
from tripsage_core.models.db.transportation import (
    Transportation,
    TransportationType,
)
from tripsage_core.models.db.trip import Trip, TripStatus, TripType
from tripsage_core.models.db.trip_comparison import TripComparison
from tripsage_core.models.db.trip_note import TripNote
from tripsage_core.models.db.user import User

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
