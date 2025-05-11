"""
Destination entity schema for Neo4j.

This module defines the Destination entity schema for the Neo4j knowledge graph,
with validation and conversion methods for Neo4j integration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class Coordinate(BaseModel):
    """Geographical coordinates."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class Weather(BaseModel):
    """Weather information."""

    climate: str
    best_time_to_visit: List[str]
    average_temperature: Dict[str, float]  # Month -> temperature


class Destination(BaseModel):
    """Destination entity schema."""

    name: str = Field(..., min_length=1)
    country: str
    region: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    type: str = Field(..., regex="^(city|country|landmark|region|national_park)$")
    coordinates: Optional[Coordinate] = None
    popular_for: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    weather: Optional[Weather] = None
    safety_rating: Optional[float] = Field(None, ge=1, le=5)
    cost_level: Optional[int] = Field(None, ge=1, le=5)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("name")
    def name_must_be_valid(cls, v):
        """Validate destination name."""
        if not v.strip():
            raise ValueError("Destination name cannot be empty")
        return v.strip()

    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j properties.

        Returns:
            Properties dictionary for Neo4j node
        """
        properties = self.dict(
            exclude={
                "coordinates",
                "weather",
                "popular_for",
                "languages",
                "created_at",
                "updated_at",
            }
        )

        # Add flattened coordinates
        if self.coordinates:
            properties["latitude"] = self.coordinates.latitude
            properties["longitude"] = self.coordinates.longitude

        # Handle dates (Neo4j expects ISO format strings)
        properties["created_at"] = self.created_at.isoformat()
        properties["updated_at"] = self.updated_at.isoformat()

        # Arrays are handled directly by Neo4j driver
        if self.popular_for:
            properties["popular_for"] = self.popular_for

        if self.languages:
            properties["languages"] = self.languages

        # Nested objects need to be serialized
        if self.weather:
            properties["weather_climate"] = self.weather.climate
            properties["weather_best_time"] = self.weather.best_time_to_visit
            properties["weather_avg_temp"] = str(self.weather.average_temperature)

        return properties

    @classmethod
    def from_neo4j_node(cls, node: Dict[str, Any]) -> "Destination":
        """Create Destination from Neo4j node.

        Args:
            node: Node data from Neo4j

        Returns:
            Destination instance
        """
        properties = dict(node)

        # Handle coordinates
        coordinates = None
        if "latitude" in properties and "longitude" in properties:
            coordinates = Coordinate(
                latitude=properties.pop("latitude"),
                longitude=properties.pop("longitude"),
            )

        # Handle weather
        weather = None
        if "weather_climate" in properties and "weather_best_time" in properties:
            import json

            weather = Weather(
                climate=properties.pop("weather_climate"),
                best_time_to_visit=properties.pop("weather_best_time"),
                average_temperature=json.loads(properties.pop("weather_avg_temp")),
            )

        # Handle dates
        if "created_at" in properties and isinstance(properties["created_at"], str):
            properties["created_at"] = datetime.fromisoformat(properties["created_at"])

        if "updated_at" in properties and isinstance(properties["updated_at"], str):
            properties["updated_at"] = datetime.fromisoformat(properties["updated_at"])

        # Remove any Neo4j-specific properties
        properties.pop("elementId", None)

        # Add back complex objects
        properties["coordinates"] = coordinates
        properties["weather"] = weather

        return cls(**properties)
