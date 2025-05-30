"""Service modules for the TripSage API.

This package contains service modules for interacting with databases,
external services, and other resources.
"""

from .accommodation import AccommodationService
from .auth import AuthService
from .destination import DestinationService
from .flight import FlightService
from .itinerary import ItineraryService
from .key import KeyService as APIKeyService
from .trip import TripService
from .user import UserService

__all__ = [
    "AccommodationService",
    "AuthService",
    "DestinationService",
    "FlightService",
    "ItineraryService",
    "APIKeyService",
    "TripService",
    "UserService",
]
