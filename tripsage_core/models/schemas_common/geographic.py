"""
Geographic models and schemas for TripSage AI.

This module contains location-related models including coordinates,
addresses, places, and geographic utilities used across the application.
"""

from typing import Optional

from pydantic import Field, field_validator

from tripsage_core.models.base_core_model import TripSageModel


class Coordinates(TripSageModel):
    """Geographic coordinates."""

    latitude: float = Field(description="Latitude in decimal degrees", ge=-90, le=90)
    longitude: float = Field(
        description="Longitude in decimal degrees", ge=-180, le=180
    )
    altitude: Optional[float] = Field(None, description="Altitude in meters")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        """Validate latitude is within valid range."""
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        """Validate longitude is within valid range."""
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180 degrees")
        return v

    def distance_to(self, other: "Coordinates") -> float:
        """Calculate the Haversine distance to another coordinate in kilometers."""
        import math

        # Convert to radians
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)

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

    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State or province")
    country: Optional[str] = Field(None, description="Country name")
    postal_code: Optional[str] = Field(None, description="Postal or ZIP code")
    formatted: Optional[str] = Field(None, description="Formatted address string")

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
    coordinates: Optional[Coordinates] = Field(
        None, description="Geographic coordinates"
    )
    address: Optional[Address] = Field(None, description="Structured address")
    place_id: Optional[str] = Field(
        None, description="External place identifier (e.g., Google Place ID)"
    )
    place_type: Optional[str] = Field(
        None, description="Type of place (e.g., city, airport, hotel)"
    )
    timezone: Optional[str] = Field(None, description="IANA timezone identifier")

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        """Validate timezone format."""
        if v is None:
            return v

        # Basic validation for IANA timezone format
        if "/" not in v:
            raise ValueError(
                "Timezone must be in IANA format (e.g., 'America/New_York')"
            )

        return v


class BoundingBox(TripSageModel):
    """Geographic bounding box."""

    north: float = Field(description="Northern latitude boundary", ge=-90, le=90)
    south: float = Field(description="Southern latitude boundary", ge=-90, le=90)
    east: float = Field(description="Eastern longitude boundary", ge=-180, le=180)
    west: float = Field(description="Western longitude boundary", ge=-180, le=180)

    @field_validator("north", "south", "east", "west")
    @classmethod
    def validate_coordinates(cls, v: float, info) -> float:
        """Validate coordinate values."""
        field_name = info.field_name

        if field_name in ("north", "south"):
            if not -90 <= v <= 90:
                raise ValueError(f"{field_name} must be between -90 and 90 degrees")
        else:  # east, west
            if not -180 <= v <= 180:
                raise ValueError(f"{field_name} must be between -180 and 180 degrees")

        return v

    def contains(self, coordinates: Coordinates) -> bool:
        """Check if coordinates are within this bounding box."""
        return (
            self.south <= coordinates.latitude <= self.north
            and self.west <= coordinates.longitude <= self.east
        )

    def center(self) -> Coordinates:
        """Get the center coordinates of the bounding box."""
        center_lat = (self.north + self.south) / 2
        center_lon = (self.east + self.west) / 2
        return Coordinates(latitude=center_lat, longitude=center_lon)


class Region(TripSageModel):
    """Geographic region with metadata."""

    name: str = Field(description="Region name")
    code: Optional[str] = Field(
        None, description="Region code (e.g., ISO country code)"
    )
    bounding_box: Optional[BoundingBox] = Field(None, description="Region boundaries")
    center: Optional[Coordinates] = Field(None, description="Region center point")
    population: Optional[int] = Field(None, description="Population count", ge=0)
    area_km2: Optional[float] = Field(
        None, description="Area in square kilometers", ge=0
    )


class Airport(TripSageModel):
    """Airport information."""

    code: str = Field(description="IATA airport code", min_length=3, max_length=3)
    icao_code: Optional[str] = Field(
        None, description="ICAO airport code", min_length=4, max_length=4
    )
    name: str = Field(description="Airport name")
    city: str = Field(description="City name")
    country: str = Field(description="Country name")
    coordinates: Optional[Coordinates] = Field(None, description="Airport coordinates")
    timezone: Optional[str] = Field(None, description="Airport timezone")

    @field_validator("code")
    @classmethod
    def validate_iata_code(cls, v: str) -> str:
        """Validate IATA airport code format."""
        if not v.isalpha() or len(v) != 3:
            raise ValueError("IATA code must be exactly 3 letters")
        return v.upper()

    @field_validator("icao_code")
    @classmethod
    def validate_icao_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate ICAO airport code format."""
        if v is None:
            return v

        if not v.isalpha() or len(v) != 4:
            raise ValueError("ICAO code must be exactly 4 letters")
        return v.upper()


class Route(TripSageModel):
    """Geographic route between two places."""

    origin: Place = Field(description="Starting place")
    destination: Place = Field(description="Ending place")
    distance_km: Optional[float] = Field(
        None, description="Distance in kilometers", ge=0
    )
    duration_minutes: Optional[int] = Field(
        None, description="Estimated duration in minutes", ge=0
    )
    waypoints: Optional[list[Place]] = Field(None, description="Intermediate waypoints")

    def total_distance(self) -> Optional[float]:
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
