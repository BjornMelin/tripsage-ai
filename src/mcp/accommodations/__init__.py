"""
Accommodations MCP clients for the TripSage travel planning system.

This package provides MCP clients for various accommodation providers,
including Airbnb, to enable searching and retrieving accommodation information.
"""

from .client import AirbnbMCPClient
from .factory import (
    airbnb_client,
    create_accommodation_client,
    create_airbnb_client,
)
from .models import (
    AccommodationSearchParams,
    AccommodationType,
    AirbnbHost,
    AirbnbListing,
    AirbnbListingDetails,
    AirbnbSearchParams,
    AirbnbSearchResult,
)

__all__ = [
    # Clients
    "AirbnbMCPClient",
    # Factory functions
    "create_airbnb_client",
    "create_accommodation_client",
    # Singleton instances
    "airbnb_client",
    # Models
    "AccommodationSearchParams",
    "AccommodationType",
    "AirbnbHost",
    "AirbnbListing",
    "AirbnbListingDetails",
    "AirbnbSearchParams",
    "AirbnbSearchResult",
]
