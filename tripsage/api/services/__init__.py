"""Service modules for the TripSage API.

This package contains service modules that act as thin adaptation layers
for the unified API, serving both frontend and agent needs by adapting
request/response models and handling API-specific logic.
"""

from .accommodation import AccommodationService, get_accommodation_service
from .auth import AuthService, get_auth_service
from .chat import ChatService, get_chat_service
from .destination import DestinationService, get_destination_service
from .flight import FlightService, get_flight_service
from .itinerary import ItineraryService, get_itinerary_service
from .key_management import KeyManagementService, get_key_management_service
from .memory import MemoryService, get_memory_service
from .trip import TripService, get_trip_service
from .user import UserService, get_user_service

__all__ = [
    # Service classes
    "AccommodationService",
    "AuthService",
    "ChatService",
    "DestinationService",
    "FlightService",
    "ItineraryService",
    "KeyManagementService",
    "MemoryService",
    "TripService",
    "UserService",
    # Dependency injection functions
    "get_accommodation_service",
    "get_auth_service",
    "get_chat_service",
    "get_destination_service",
    "get_flight_service",
    "get_itinerary_service",
    "get_key_management_service",
    "get_memory_service",
    "get_trip_service",
    "get_user_service",
]
