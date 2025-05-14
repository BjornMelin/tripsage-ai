"""
Google Maps function tools for TripSage.

This module provides OpenAI Agents SDK function tools for Google Maps operations,
allowing agents to geocode addresses, search for places, get directions,
calculate distances, and other location-based services.
"""

from typing import Any, Dict, List, Optional

from agents import function_tool

from tripsage.config.app_settings import settings
from tripsage.tools.schemas.googlemaps import (
    DirectionsParams,
    DirectionsResponse,
    DistanceMatrixParams,
    DistanceMatrixResponse,
    ElevationParams,
    ElevationResponse,
    GeocodeParams,
    GeocodeResponse,
    PlaceDetailsParams,
    PlaceDetailsResponse,
    PlaceField,
    PlaceSearchParams,
    PlaceSearchResponse,
    ReverseGeocodeParams,
    TimeZoneParams,
    TimeZoneResponse,
    TravelMode,
)
from tripsage.utils.client_utils import validate_and_call_mcp_tool
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


@function_tool
@with_error_handling
async def geocode_tool(
    address: Optional[str] = None,
    place_id: Optional[str] = None,
    components: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Convert an address to geographic coordinates.

    Args:
        address: Address to geocode (e.g., "1600 Amphitheatre Parkway, Mountain View, CA")
        place_id: Google Maps place ID to geocode (alternative to address)
        components: Component filters (e.g., {"country": "US"})

    Returns:
        Dictionary with geocoding results
    """
    try:
        # Validate parameters
        params = GeocodeParams(
            address=address,
            place_id=place_id,
            components=components,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Geocoding: {params.model_dump(exclude_none=True)}")

    try:
        result = await validate_and_call_mcp_tool(
            endpoint=settings.googlemaps_mcp_endpoint,
            tool_name="geocode",
            params=params.model_dump(exclude_none=True),
            response_model=GeocodeResponse,
            timeout=15.0,
            server_name="Google Maps MCP",
        )

        # Parse the response for better usability
        locations = []
        for loc in result.results:
            geometry = loc.geometry
            locations.append(
                {
                    "place_id": loc.place_id,
                    "formatted_address": loc.formatted_address,
                    "location": {
                        "lat": geometry["location"]["lat"],
                        "lng": geometry["location"]["lng"],
                    },
                    "address_components": loc.address_components,
                    "types": loc.types,
                }
            )

        formatted_result = ""
        if locations:
            formatted_result = f"Found {len(locations)} locations:\n"
            for i, loc in enumerate(locations):
                formatted_result += (
                    f"{i + 1}. {loc['formatted_address']} "
                    f"({loc['location']['lat']}, {loc['location']['lng']})\n"
                )
        else:
            formatted_result = "No locations found."

        return {
            "status": result.status,
            "locations": locations,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error geocoding address: {str(e)}")
        return {"error": f"Failed to geocode address: {str(e)}"}


@function_tool
@with_error_handling
async def reverse_geocode_tool(
    lat: float,
    lng: float,
    result_type: Optional[str] = None,
    location_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert geographic coordinates to an address.

    Args:
        lat: Latitude coordinate
        lng: Longitude coordinate
        result_type: Filter result types (e.g., "street_address")
        location_type: Filter location types (e.g., "ROOFTOP")

    Returns:
        Dictionary with reverse geocoding results
    """
    try:
        # Validate parameters
        params = ReverseGeocodeParams(
            lat=lat,
            lng=lng,
            result_type=result_type,
            location_type=location_type,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Reverse geocoding: {params.model_dump(exclude_none=True)}")

    try:
        result = await validate_and_call_mcp_tool(
            endpoint=settings.googlemaps_mcp_endpoint,
            tool_name="reverse_geocode",
            params=params.model_dump(exclude_none=True),
            response_model=GeocodeResponse,
            timeout=15.0,
            server_name="Google Maps MCP",
        )

        # Parse the response for better usability
        addresses = []
        for loc in result.results:
            addresses.append(
                {
                    "place_id": loc.place_id,
                    "formatted_address": loc.formatted_address,
                    "address_components": loc.address_components,
                    "types": loc.types,
                }
            )

        formatted_result = ""
        if addresses:
            formatted_result = (
                f"Found {len(addresses)} addresses for coordinates ({lat}, {lng}):\n"
            )
            for i, addr in enumerate(addresses):
                formatted_result += f"{i + 1}. {addr['formatted_address']}\n"
        else:
            formatted_result = f"No addresses found for coordinates ({lat}, {lng})."

        return {
            "status": result.status,
            "addresses": addresses,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error reverse geocoding coordinates: {str(e)}")
        return {"error": f"Failed to reverse geocode coordinates: {str(e)}"}


@function_tool
@with_error_handling
async def place_search_tool(
    query: Optional[str] = None,
    location: Optional[str] = None,
    radius: Optional[int] = None,
    type: Optional[str] = None,
    keyword: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    open_now: Optional[bool] = None,
    rank_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Search for places based on text query or location.

    Args:
        query: Text search query (e.g., "restaurants in Manhattan")
        location: Location to search around (lat,lng or address)
        radius: Search radius in meters (max 50000)
        type: Place type (e.g., "restaurant", "museum", "tourist_attraction")
        keyword: Keyword to match in places
        min_price: Minimum price level (0-4)
        max_price: Maximum price level (0-4)
        open_now: Whether place is open now
        rank_by: Ranking method ("prominence" or "distance")

    Returns:
        Dictionary with place search results
    """
    try:
        # Handle case when location is a string address
        location_coordinates = None
        if location and "," in location:
            try:
                lat, lng = map(float, location.split(","))
                location_coordinates = location
            except ValueError:
                # If not lat,lng format, assume it's an address and geocode it
                geocode_result = await geocode_tool(address=location)
                if "error" not in geocode_result and geocode_result.get("locations"):
                    first_location = geocode_result["locations"][0]["location"]
                    location_coordinates = (
                        f"{first_location['lat']},{first_location['lng']}"
                    )

        # Validate parameters
        try:
            params = PlaceSearchParams(
                query=query,
                location=location_coordinates,
                radius=radius,
                type=type,
                keyword=keyword,
                min_price=min_price,
                max_price=max_price,
                open_now=open_now,
                rank_by=rank_by,
            )
        except ValueError as e:
            return {"error": str(e)}

        logger.info(f"Place search: {params.model_dump(exclude_none=True)}")

        result = await validate_and_call_mcp_tool(
            endpoint=settings.googlemaps_mcp_endpoint,
            tool_name="place_search",
            params=params.model_dump(exclude_none=True),
            response_model=PlaceSearchResponse,
            timeout=15.0,
            server_name="Google Maps MCP",
        )

        # Parse the response for better usability
        places = []
        for place in result.results:
            places.append(
                {
                    "place_id": place.place_id,
                    "name": place.name,
                    "formatted_address": place.formatted_address,
                    "location": {
                        "lat": place.geometry["location"]["lat"],
                        "lng": place.geometry["location"]["lng"],
                    },
                    "types": place.types,
                    "price_level": place.price_level,
                    "rating": place.rating,
                    "user_ratings_total": place.user_ratings_total,
                    "vicinity": place.vicinity,
                }
            )

        formatted_result = ""
        if places:
            formatted_result = f"Found {len(places)} places:\n"
            for i, place in enumerate(places):
                rating_info = (
                    f" - Rating: {place['rating']}" if place.get("rating") else ""
                )
                formatted_result += (
                    f"{i + 1}. {place['name']}{rating_info}\n"
                    f"   Address: {place.get('formatted_address') or place.get('vicinity', 'N/A')}\n"
                )
        else:
            formatted_result = "No places found for the given criteria."

        return {
            "status": result.status,
            "next_page_token": result.next_page_token,
            "places": places,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error searching places: {str(e)}")
        return {"error": f"Failed to search places: {str(e)}"}


@function_tool
@with_error_handling
async def place_details_tool(
    place_id: str,
    fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get detailed information about a place.

    Args:
        place_id: Google Maps place ID
        fields: Place fields to include in response

    Returns:
        Dictionary with place details
    """
    try:
        # Convert string field names to PlaceField enum values
        converted_fields = None
        if fields:
            try:
                converted_fields = [f for f in fields if f in PlaceField.__members__]
            except Exception:
                pass

        # Validate parameters
        params = PlaceDetailsParams(
            place_id=place_id,
            fields=converted_fields,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Place details: {params.model_dump(exclude_none=True)}")

    try:
        result = await validate_and_call_mcp_tool(
            endpoint=settings.googlemaps_mcp_endpoint,
            tool_name="place_details",
            params=params.model_dump(exclude_none=True),
            response_model=PlaceDetailsResponse,
            timeout=15.0,
            server_name="Google Maps MCP",
        )

        # Create a nicely formatted response
        details = result.result or {}
        formatted_result = ""

        if details:
            name = details.get("name", "Unknown place")
            formatted_result = f"Details for {name}:\n"

            if details.get("formatted_address"):
                formatted_result += f"Address: {details['formatted_address']}\n"

            if details.get("formatted_phone_number"):
                formatted_result += f"Phone: {details['formatted_phone_number']}\n"

            if details.get("website"):
                formatted_result += f"Website: {details['website']}\n"

            if details.get("rating"):
                formatted_result += f"Rating: {details['rating']} ({details.get('user_ratings_total', 0)} reviews)\n"

            if details.get("opening_hours", {}).get("weekday_text"):
                formatted_result += "Hours:\n"
                for hours in details["opening_hours"]["weekday_text"]:
                    formatted_result += f"  {hours}\n"

            if details.get("price_level") is not None:
                price = (
                    "$" * details["price_level"]
                    if details["price_level"] > 0
                    else "Free"
                )
                formatted_result += f"Price level: {price}\n"

        else:
            formatted_result = "No details found for this place."

        return {
            "status": result.status,
            "details": details,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting place details: {str(e)}")
        return {"error": f"Failed to get place details: {str(e)}"}


@function_tool
@with_error_handling
async def directions_tool(
    origin: str,
    destination: str,
    mode: str = "driving",
    waypoints: Optional[List[str]] = None,
    alternatives: Optional[bool] = None,
    avoid: Optional[List[str]] = None,
    units: Optional[str] = None,
    arrival_time: Optional[int] = None,
    departure_time: Optional[int] = None,
) -> Dict[str, Any]:
    """Get directions between locations.

    Args:
        origin: Origin address or coordinates
        destination: Destination address or coordinates
        mode: Travel mode (driving, walking, bicycling, transit)
        waypoints: Waypoints to include in route
        alternatives: Whether to provide alternative routes
        avoid: Features to avoid (tolls, highways, ferries)
        units: Unit system (metric or imperial)
        arrival_time: Desired arrival time (unix timestamp)
        departure_time: Desired departure time (unix timestamp)

    Returns:
        Dictionary with directions information
    """
    try:
        # Validate and convert mode to TravelMode
        try:
            travel_mode = TravelMode(mode.lower()) if mode else TravelMode.DRIVING
        except ValueError:
            travel_mode = TravelMode.DRIVING

        # Validate parameters
        params = DirectionsParams(
            origin=origin,
            destination=destination,
            mode=travel_mode,
            waypoints=waypoints,
            alternatives=alternatives,
            avoid=avoid,
            units=units,
            arrival_time=arrival_time,
            departure_time=departure_time,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Getting directions: {params.model_dump(exclude_none=True)}")

    try:
        result = await validate_and_call_mcp_tool(
            endpoint=settings.googlemaps_mcp_endpoint,
            tool_name="directions",
            params=params.model_dump(exclude_none=True),
            response_model=DirectionsResponse,
            timeout=15.0,
            server_name="Google Maps MCP",
        )

        routes = []
        for route in result.routes:
            legs = []
            total_distance = 0
            total_duration = 0

            for leg in route.legs:
                leg_info = {
                    "start_address": leg.get("start_address", ""),
                    "end_address": leg.get("end_address", ""),
                    "distance": leg.get("distance", {}).get("text", ""),
                    "distance_meters": leg.get("distance", {}).get("value", 0),
                    "duration": leg.get("duration", {}).get("text", ""),
                    "duration_seconds": leg.get("duration", {}).get("value", 0),
                    "steps": [],
                }

                total_distance += leg_info["distance_meters"]
                total_duration += leg_info["duration_seconds"]

                for step in leg.get("steps", []):
                    step_info = {
                        "instructions": step.get("html_instructions", "")
                        .replace("<b>", "")
                        .replace("</b>", "")
                        .replace("<div>", " - ")
                        .replace("</div>", ""),
                        "distance": step.get("distance", {}).get("text", ""),
                        "duration": step.get("duration", {}).get("text", ""),
                    }
                    leg_info["steps"].append(step_info)

                legs.append(leg_info)

            routes.append(
                {
                    "summary": route.summary,
                    "legs": legs,
                    "total_distance": total_distance,
                    "total_distance_text": f"{total_distance / 1000:.1f} km",
                    "total_duration": total_duration,
                    "total_duration_text": format_duration(total_duration),
                    "warnings": route.warnings,
                    "fare": route.fare,
                }
            )

        # Create formatted directions
        formatted_result = ""
        if routes:
            formatted_result = f"Directions from {origin} to {destination}:\n\n"

            for i, route in enumerate(routes):
                formatted_result += f"Route {i + 1}: {route['summary']}\n"
                formatted_result += f"Distance: {route['total_distance_text']}, Duration: {route['total_duration_text']}\n"

                for j, leg in enumerate(route["legs"]):
                    if len(route["legs"]) > 1:
                        formatted_result += f"\nLeg {j + 1}: {leg['start_address']} to {leg['end_address']}\n"

                    for k, step in enumerate(leg["steps"]):
                        formatted_result += (
                            f"{k + 1}. {step['instructions']} ({step['distance']})\n"
                        )

                if route["warnings"]:
                    formatted_result += "\nWarnings:\n"
                    for warning in route["warnings"]:
                        formatted_result += f"- {warning}\n"

                if i < len(routes) - 1:
                    formatted_result += "\n---\n\n"
        else:
            formatted_result = "No routes found."

        return {
            "status": result.status,
            "routes": routes,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting directions: {str(e)}")
        return {"error": f"Failed to get directions: {str(e)}"}


@function_tool
@with_error_handling
async def distance_matrix_tool(
    origins: List[str],
    destinations: List[str],
    mode: str = "driving",
    avoid: Optional[List[str]] = None,
    units: Optional[str] = None,
    departure_time: Optional[int] = None,
) -> Dict[str, Any]:
    """Calculate distances and travel times between multiple origins and destinations.

    Args:
        origins: List of origin addresses or coordinates
        destinations: List of destination addresses or coordinates
        mode: Travel mode (driving, walking, bicycling, transit)
        avoid: Features to avoid (tolls, highways, ferries)
        units: Unit system (metric or imperial)
        departure_time: Desired departure time (unix timestamp)

    Returns:
        Dictionary with distance matrix information
    """
    try:
        # Validate and convert mode to TravelMode
        try:
            travel_mode = TravelMode(mode.lower()) if mode else TravelMode.DRIVING
        except ValueError:
            travel_mode = TravelMode.DRIVING

        # Validate parameters
        params = DistanceMatrixParams(
            origins=origins,
            destinations=destinations,
            mode=travel_mode,
            avoid=avoid,
            units=units,
            departure_time=departure_time,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Getting distance matrix: {params.model_dump(exclude_none=True)}")

    try:
        result = await validate_and_call_mcp_tool(
            endpoint=settings.googlemaps_mcp_endpoint,
            tool_name="distance_matrix",
            params=params.model_dump(exclude_none=True),
            response_model=DistanceMatrixResponse,
            timeout=15.0,
            server_name="Google Maps MCP",
        )

        # Parse the response for better usability
        matrix = []
        for i, row in enumerate(result.rows):
            matrix_row = []
            for j, element in enumerate(row.get("elements", [])):
                matrix_row.append(
                    {
                        "origin": result.origin_addresses[i]
                        if i < len(result.origin_addresses)
                        else f"Origin {i + 1}",
                        "destination": result.destination_addresses[j]
                        if j < len(result.destination_addresses)
                        else f"Destination {j + 1}",
                        "status": element.get("status", ""),
                        "distance": element.get("distance", {}).get("text", ""),
                        "distance_meters": element.get("distance", {}).get("value", 0),
                        "duration": element.get("duration", {}).get("text", ""),
                        "duration_seconds": element.get("duration", {}).get("value", 0),
                    }
                )
            matrix.append(matrix_row)

        # Create formatted output
        formatted_result = "Distance Matrix:\n\n"
        for i, row in enumerate(matrix):
            origin_name = (
                result.origin_addresses[i]
                if i < len(result.origin_addresses)
                else f"Origin {i + 1}"
            )
            formatted_result += f"From {origin_name}:\n"

            for element in row:
                if element["status"] == "OK":
                    formatted_result += f"  To {element['destination']}: {element['distance']} ({element['duration']})\n"
                else:
                    formatted_result += (
                        f"  To {element['destination']}: {element['status']}\n"
                    )

            if i < len(matrix) - 1:
                formatted_result += "\n"

        return {
            "status": result.status,
            "origin_addresses": result.origin_addresses,
            "destination_addresses": result.destination_addresses,
            "matrix": matrix,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting distance matrix: {str(e)}")
        return {"error": f"Failed to get distance matrix: {str(e)}"}


@function_tool
@with_error_handling
async def timezone_tool(
    location: str,
    timestamp: Optional[int] = None,
) -> Dict[str, Any]:
    """Get time zone information for a location.

    Args:
        location: Location coordinates (lat,lng)
        timestamp: Timestamp to use (defaults to current time)

    Returns:
        Dictionary with time zone information
    """
    try:
        # Validate parameters
        params = TimeZoneParams(
            location=location,
            timestamp=timestamp,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Getting timezone: {params.model_dump(exclude_none=True)}")

    try:
        result = await validate_and_call_mcp_tool(
            endpoint=settings.googlemaps_mcp_endpoint,
            tool_name="timezone",
            params=params.model_dump(exclude_none=True),
            response_model=TimeZoneResponse,
            timeout=15.0,
            server_name="Google Maps MCP",
        )

        # Calculate total offset in hours
        total_offset = (result.rawOffset + result.dstOffset) / 3600
        offset_sign = "+" if total_offset >= 0 else "-"
        offset_str = f"{offset_sign}{abs(total_offset):.1f}"

        formatted_result = (
            f"Time zone: {result.timeZoneName} ({result.timeZoneId})\n"
            f"UTC offset: {offset_str} hours\n"
            f"Raw offset: {result.rawOffset / 3600:.1f} hours\n"
            f"DST offset: {result.dstOffset / 3600:.1f} hours"
        )

        return {
            "status": result.status,
            "time_zone_id": result.timeZoneId,
            "time_zone_name": result.timeZoneName,
            "raw_offset": result.rawOffset,
            "dst_offset": result.dstOffset,
            "total_offset": result.rawOffset + result.dstOffset,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting timezone: {str(e)}")
        return {"error": f"Failed to get timezone: {str(e)}"}


@function_tool
@with_error_handling
async def elevation_tool(
    locations: List[str],
) -> Dict[str, Any]:
    """Get elevation data for locations.

    Args:
        locations: List of location coordinates (lat,lng)

    Returns:
        Dictionary with elevation information
    """
    try:
        # Validate parameters
        params = ElevationParams(
            locations=locations,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Getting elevation: {params.model_dump(exclude_none=True)}")

    try:
        result = await validate_and_call_mcp_tool(
            endpoint=settings.googlemaps_mcp_endpoint,
            tool_name="elevation",
            params=params.model_dump(exclude_none=True),
            response_model=ElevationResponse,
            timeout=15.0,
            server_name="Google Maps MCP",
        )

        # Parse the response for better usability
        elevations = []
        for i, elev in enumerate(result.results):
            location = locations[i] if i < len(locations) else f"Location {i + 1}"
            elevations.append(
                {
                    "location": location,
                    "elevation": elev.get("elevation", 0),
                    "resolution": elev.get("resolution", 0),
                }
            )

        # Create formatted output
        formatted_result = "Elevation data:\n\n"
        for elev in elevations:
            formatted_result += (
                f"Location {elev['location']}: {elev['elevation']:.1f} meters\n"
            )

        return {
            "status": result.status,
            "elevations": elevations,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting elevation: {str(e)}")
        return {"error": f"Failed to get elevation: {str(e)}"}


def format_duration(seconds: int) -> str:
    """Format duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable duration string
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours} hr {minutes} min"
    return f"{minutes} min"
