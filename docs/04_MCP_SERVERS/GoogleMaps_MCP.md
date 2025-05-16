# Google Maps MCP Server Integration Guide

This document outlines the integration details for the Google Maps MCP Server, which provides essential location-based services and mapping capabilities for the TripSage AI Travel Planning System.

## 1. Overview

The Google Maps MCP Server acts as a standardized interface between TripSage's AI agents and the Google Maps Platform API. This integration is crucial for:

* Accurate geocoding (converting addresses to coordinates and vice-versa).
* Searching for points of interest (POIs), accommodations, restaurants, and attractions.
* Retrieving detailed information about places.
* Calculating distances and travel times between locations.
* Generating directions for various modes of transport.
* Displaying static maps to visualize locations and routes.

By using an MCP server, TripSage ensures consistent interaction patterns, centralized API key management, and potential for caching and optimization of Google Maps API calls.

## 2. Technology Selection and Rationale

TripSage integrates with the **official `@modelcontextprotocol/server-google-maps`** package. This is a Node.js/TypeScript based MCP server specifically designed for Google Maps.

**Rationale for using the official server:**

* **Production-Ready Stability**: Maintained by the MCP community or a dedicated team, ensuring regular updates and reliability.
* **Standardization**: Adheres to MCP best practices and conventions.
* **Comprehensive Feature Set**: Exposes a wide range of Google Maps API functionalities relevant to travel planning.
* **Ease of Integration**: Simple to configure and integrate with MCP clients like those used in TripSage (e.g., within Claude Desktop or via Python clients for the OpenAI Agents SDK).
* **Reduced Maintenance**: TripSage does not need to develop or maintain custom code for wrapping the Google Maps API, allowing focus on core travel planning features.

## 3. Google Maps Platform API Setup

Before the MCP server can be used, the Google Maps Platform API must be set up:

1. **Google Cloud Project**: Ensure you have a Google Cloud Project.
2. **Enable APIs**: In the GCP Console, enable the following APIs for your project:
    * Geocoding API
    * Places API
    * Directions API
    * Distance Matrix API
    * Maps Static API
    * (And any other specific Maps APIs you intend to use via the MCP)
3. **API Key**: Create an API key restricted to the enabled APIs and, for production, to your application's domains or IP addresses.
4. **Billing**: Ensure billing is enabled for your Google Cloud Project, as Maps Platform APIs are pay-as-you-go (though they have a generous monthly free tier).

### Environment Variable for TripSage

```plaintext
# .env
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
GOOGLEMAPS_MCP_ENDPOINT=http://localhost:3001
```

## 4. Exposed MCP Tools via `@modelcontextprotocol/server-google-maps`

The official Google Maps MCP server typically exposes tools corresponding to the main Google Maps API services. The exact tool names and parameters should be verified from the specific version of the MCP server being used. Common tools include:

### 4.1. `maps_geocode`

* **Description**: Converts a human-readable address into geographic coordinates (latitude and longitude).
* **Input Example**: `{ "address": "1600 Amphitheatre Parkway, Mountain View, CA" }`
* **Output Example**:

    ```json
    {
      "results": [{
        "formatted_address": "1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA",
        "geometry": { "location": { "lat": 37.4224764, "lng": -122.0842499 } },
        "place_id": "ChIJ2eUgeAK6j4ARbn5u_wAGqWA"
      }]
    }
    ```

### 4.2. `maps_reverse_geocode`

* **Description**: Converts geographic coordinates into a human-readable address.
* **Input Example**: `{ "latitude": 37.4224764, "longitude": -122.0842499 }`
* **Output Example**: Similar to `maps_geocode` output, providing address components.

### 4.3. `maps_search_places` (Text Search or Nearby Search)

* **Description**: Searches for places based on a text query, optionally biased by location or within a radius.
* **Input Example**:

    ```json
    {
      "query": "restaurants in San Francisco",
      "location": { "latitude": 37.7749, "longitude": -122.4194 },
      "radius": 5000
    }
    ```

* **Output Example**: A list of places matching the query, each with name, address, location, rating, types, etc.

### 4.4. `maps_place_details`

* **Description**: Retrieves comprehensive information about a specific place using its `place_id`.
* **Input Example**: `{ "place_id": "ChIJ2eUgeAK6j4ARbn5u_wAGqWA" }`
* **Output Example**: Detailed place information including address, phone number, website, opening hours, reviews, photos, price level.

### 4.5. `maps_distance_matrix`

* **Description**: Calculates travel distance and duration between one or more origins and destinations.
* **Input Example**:

    ```json
    {
      "origins": ["San Francisco, CA", "Oakland, CA"],
      "destinations": ["Los Angeles, CA", "San Diego, CA"],
      "mode": "driving"
    }
    ```

* **Output Example**: A matrix of distances and durations for each origin-destination pair.

### 4.6. `maps_directions`

* **Description**: Retrieves step-by-step directions between an origin and a destination.
* **Input Example**:

    ```json
    {
      "origin": "Disneyland Park, Anaheim, CA",
      "destination": "Universal Studios Hollywood, Universal City, CA",
      "mode": "driving"
    }
    ```

* **Output Example**: Detailed route information including legs, steps, distance, duration, and polyline for map plotting.

### 4.7. `maps_elevation` (If supported by the MCP server version)

* **Description**: Gets elevation data for specified locations.
* **Input Example**: `{ "locations": [{ "latitude": 37.7749, "longitude": -122.4194 }] }`
* **Output Example**: Elevation data for each location.

## 5. TripSage `GoogleMapsMCPClient`

TripSage interacts with the Google Maps MCP Server via a Python client (`src/mcp/googlemaps/client.py`).

### 5.1. Client Implementation Highlights

```python
# src/mcp/googlemaps/client.py (Simplified Snippet)
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from ..base_mcp_client import BaseMCPClient
from ...utils.config import settings
from ...utils.logging import get_module_logger
from agents import function_tool

logger = get_module_logger(__name__)

class GeocodeParams(BaseModel):
    address: str

class ReverseGeocodeParams(BaseModel):
    latitude: float
    longitude: float

class PlaceSearchParams(BaseModel):
    query: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[int] = Field(None, ge=0)

class GoogleMapsMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_name="googlemaps",
            endpoint=settings.mcp_servers.googlemaps.endpoint,
            api_key=settings.mcp_servers.googlemaps.api_key.get_secret_value() if settings.mcp_servers.googlemaps.api_key else None
        )
        logger.info("Initialized Google Maps MCP Client.")

    @function_tool
    async def geocode_address(self, address: str) -> Dict[str, Any]:
        validated_params = GeocodeParams(address=address)
        return await self.invoke_tool("maps_geocode", validated_params.model_dump())

    @function_tool
    async def reverse_geocode_coordinates(self, latitude: float, longitude: float) -> Dict[str, Any]:
        validated_params = ReverseGeocodeParams(latitude=latitude, longitude=longitude)
        return await self.invoke_tool("maps_reverse_geocode", validated_params.model_dump())

    @function_tool
    async def search_places(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius: Optional[int] = None
    ) -> Dict[str, Any]:
        payload = {"query": query}
        if latitude is not None and longitude is not None:
            payload["location"] = {"latitude": latitude, "longitude": longitude}
        if radius is not None:
            payload["radius"] = radius

        return await self.invoke_tool("maps_search_places", payload)
```

## 6. Integration with TripSage Components

* **Travel Planning Agent** uses `maps_geocode` for coordinates, `maps_search_places` for nearby POIs, `maps_place_details` for detailed info.
* **Itinerary Agent** uses `maps_directions` and `maps_distance_matrix` to plan routes and estimate travel times.
* **Dual Storage** can store geocoded coordinates and place details (like `place_id`) in Supabase, and relationships in Neo4j via Memory MCP.

## 7. Deployment and Configuration of `@modelcontextprotocol/server-google-maps`

**Starting the Server (Example)**:

```bash
export GOOGLE_MAPS_API_KEY="YOUR_GOOGLE_MAPS_API_KEY"
npx -y @modelcontextprotocol/server-google-maps --port 3001
```

Or Docker:

```bash
docker run -d -p 3001:3000 --rm \
  -e GOOGLE_MAPS_API_KEY="YOUR_GOOGLE_MAPS_API_KEY" \
  mcp/google-maps
```

TripSage includes scripts (e.g., `scripts/start_googlemaps_mcp.sh`) to manage this.

## 8. Cost Management and Quotas

* Google Maps Platform APIs are pay-as-you-go with a free monthly credit.
* TripSage implements caching (via Redis) to minimize API calls.
* Monitor usage in Google Cloud Console.

## 9. Testing

* **Client Unit Tests**: Mock `invoke_tool` in `GoogleMapsMCPClient`.
* **Integration Tests**: Test against a live instance of `@modelcontextprotocol/server-google-maps`.

## 10. Conclusion

Integrating the official Google Maps MCP Server provides TripSage with robust, standardized, and well-maintained access to essential geospatial services. This allows TripSage to focus on core travel planning logic while leveraging the global coverage of the Google Maps Platform.
