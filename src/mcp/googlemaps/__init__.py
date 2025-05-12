"""
Google Maps MCP clients for the TripSage travel planning system.

This package provides MCP clients for the Google Maps Platform APIs,
enabling geocoding, place searches, directions, and other mapping functionality.
"""

from .client import GoogleMapsMCPClient, get_client, store_location_in_knowledge_graph
from .factory import create_googlemaps_client
from .models import (
    DirectionsParams,
    DirectionsResponse,
    DistanceMatrixParams,
    DistanceMatrixResponse,
    ElevationParams,
    ElevationResponse,
    GeocodeParams,
    GeocodeResponse,
    GeocodeResult,
    PlaceDetailsParams,
    PlaceDetailsResponse,
    PlaceResult,
    PlaceSearchParams,
    PlaceSearchResponse,
    ReverseGeocodeParams,
    Route,
    TimeZoneParams,
    TimeZoneResponse,
)

__all__ = [
    # Clients and functions
    "GoogleMapsMCPClient",
    "get_client",
    "store_location_in_knowledge_graph",
    "create_googlemaps_client",
    # Parameter models
    "GeocodeParams",
    "ReverseGeocodeParams",
    "PlaceSearchParams",
    "PlaceDetailsParams",
    "DirectionsParams",
    "DistanceMatrixParams",
    "TimeZoneParams",
    "ElevationParams",
    # Response models
    "GeocodeResult",
    "GeocodeResponse",
    "PlaceResult",
    "PlaceSearchResponse",
    "PlaceDetailsResponse",
    "Route",
    "DirectionsResponse",
    "DistanceMatrixResponse",
    "TimeZoneResponse",
    "ElevationResponse",
]
