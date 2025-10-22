"""Geographic models and schemas for TripSage AI.

This module contains location-related models including coordinates,
addresses, places, and geographic utilities used across the application.
"""

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageModel

from .common_validators import AirportCode, Latitude, Longitude


def _require_coordinate(value: float | None, label: str) -> float:
    """Ensure coordinate components are present before math operations."""
    if value is None:
        raise ValueError(f"{label} must be provided for geographic calculations")
    return float(value)


class Coordinates(TripSageModel):
    """Geographic coordinates."""

    latitude: Latitude = Field(description="Latitude in decimal degrees")
    longitude: Longitude = Field(description="Longitude in decimal degrees")
    altitude: float | None = Field(None, description="Altitude in meters")

    def distance_to(self, other: "Coordinates") -> float:
        """Calculate the Haversine distance to another coordinate in kilometers."""
        import math

        # Convert to radians
        lat1 = math.radians(_require_coordinate(self.latitude, "origin latitude"))
        lon1 = math.radians(_require_coordinate(self.longitude, "origin longitude"))
        lat2 = math.radians(_require_coordinate(other.latitude, "destination latitude"))
        lon2 = math.radians(
            _require_coordinate(other.longitude, "destination longitude")
        )

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Earth's radius in kilometers
        r = 6371
        return c * r


class Address(TripSageModel):
    """Structured address information."""

    street: str | None = Field(None, description="Street address")
    city: str | None = Field(None, description="City name")
    state: str | None = Field(None, description="State or province")
    country: str | None = Field(None, description="Country name")
    postal_code: str | None = Field(None, description="Postal or ZIP code")
    formatted: str | None = Field(None, description="Formatted address string")

    def to_string(self) -> str:
        """Convert address to a formatted string."""
        if self.formatted:
            return self.formatted

        parts = []
        if self.street:
            parts.append(self.street)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        if self.country:
            parts.append(self.country)

        return ", ".join(parts)


class Place(TripSageModel):
    """A geographic place with coordinates and address."""

    name: str = Field(description="Place name")
    coordinates: Coordinates | None = Field(None, description="Geographic coordinates")
    address: Address | None = Field(None, description="Structured address")
    place_id: str | None = Field(
        None, description="External place identifier (e.g., Google Place ID)"
    )
    place_type: str | None = Field(
        None, description="Type of place (e.g., city, airport, hotel)"
    )
    timezone: str | None = Field(None, description="IANA timezone identifier")


class BoundingBox(TripSageModel):
    """Geographic bounding box."""

    north: Latitude = Field(description="Northern latitude boundary")
    south: Latitude = Field(description="Southern latitude boundary")
    east: Longitude = Field(description="Eastern longitude boundary")
    west: Longitude = Field(description="Western longitude boundary")

    def contains(self, coordinates: Coordinates) -> bool:
        """Check if coordinates are within this bounding box."""
        south = _require_coordinate(self.south, "bounding box south latitude")
        north = _require_coordinate(self.north, "bounding box north latitude")
        west = _require_coordinate(self.west, "bounding box west longitude")
        east = _require_coordinate(self.east, "bounding box east longitude")
        candidate_lat = _require_coordinate(coordinates.latitude, "candidate latitude")
        candidate_lon = _require_coordinate(
            coordinates.longitude, "candidate longitude"
        )
        return south <= candidate_lat <= north and west <= candidate_lon <= east

    def center(self) -> Coordinates:
        """Get the center coordinates of the bounding box."""
        north = _require_coordinate(self.north, "bounding box north latitude")
        south = _require_coordinate(self.south, "bounding box south latitude")
        east = _require_coordinate(self.east, "bounding box east longitude")
        west = _require_coordinate(self.west, "bounding box west longitude")
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        return Coordinates(
            latitude=center_lat,
            longitude=center_lon,
            altitude=None,
        )


class Region(TripSageModel):
    """Geographic region with metadata."""

    name: str = Field(description="Region name")
    code: str | None = Field(None, description="Region code (e.g., ISO country code)")
    bounding_box: BoundingBox | None = Field(None, description="Region boundaries")
    center: Coordinates | None = Field(None, description="Region center point")
    population: int | None = Field(None, description="Population count", ge=0)
    area_km2: float | None = Field(None, description="Area in square kilometers", ge=0)


class Airport(TripSageModel):
    """Airport information."""

    code: AirportCode = Field(description="IATA airport code")
    icao_code: str | None = Field(
        None, description="ICAO airport code", min_length=4, max_length=4
    )
    name: str = Field(description="Airport name")
    city: str = Field(description="City name")
    country: str = Field(description="Country name")
    coordinates: Coordinates | None = Field(None, description="Airport coordinates")
    timezone: str | None = Field(None, description="Airport timezone")


class Route(TripSageModel):
    """Geographic route between two places."""

    origin: Place = Field(description="Starting place")
    destination: Place = Field(description="Ending place")
    distance_km: float | None = Field(None, description="Distance in kilometers", ge=0)
    duration_minutes: int | None = Field(
        None, description="Estimated duration in minutes", ge=0
    )
    waypoints: list[Place] | None = Field(None, description="Intermediate waypoints")

    def total_distance(self) -> float | None:
        """Calculate total route distance if coordinates are available."""
        if not self.origin.coordinates or not self.destination.coordinates:
            return self.distance_km

        if not self.waypoints:
            return self.origin.coordinates.distance_to(self.destination.coordinates)

        # Calculate distance through waypoints
        total = 0.0
        current = self.origin.coordinates

        for waypoint in self.waypoints:
            if waypoint.coordinates:
                total += current.distance_to(waypoint.coordinates)
                current = waypoint.coordinates

        # Add final segment to destination
        total += current.distance_to(self.destination.coordinates)

        return total
