"""
Activity entity schema for Neo4j.

This module defines the Activity entity schema for the Neo4j knowledge graph,
with validation and conversion methods for Neo4j integration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from src.db.neo4j.schemas.destination import Coordinate


class PriceRange(BaseModel):
    """Price range information."""

    min_price: float = Field(..., ge=0)
    max_price: float = Field(..., ge=0)
    currency: str = "USD"

    @validator("max_price")
    def max_price_must_be_greater_than_min(cls, v, values):
        """Validate max price is greater than min price."""
        if "min_price" in values and v < values["min_price"]:
            raise ValueError("max_price must be greater than or equal to min_price")
        return v


class Activity(BaseModel):
    """Activity entity schema."""

    name: str = Field(..., min_length=1)
    destination: str  # Reference to destination name
    type: str = Field(
        ...,
        regex="^(attraction|tour|event|dining|shopping|outdoor|cultural|entertainment)$",
    )
    description: Optional[str] = None
    address: Optional[str] = None
    coordinates: Optional[Coordinate] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    price_range: Optional[PriceRange] = None
    tags: Optional[List[str]] = None
    opening_hours: Optional[Dict[str, str]] = None  # Day -> hours
    website: Optional[str] = None
    rating: Optional[float] = Field(None, ge=1, le=5)
    popularity_score: Optional[float] = Field(None, ge=0, le=100)
    accessibility_features: Optional[List[str]] = None
    best_time_to_visit: Optional[List[str]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("name")
    def name_must_be_valid(cls, v):
        """Validate activity name."""
        if not v.strip():
            raise ValueError("Activity name cannot be empty")
        return v.strip()

    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j properties.

        Returns:
            Properties dictionary for Neo4j node
        """
        properties = self.dict(
            exclude={
                "coordinates",
                "price_range",
                "tags",
                "opening_hours",
                "accessibility_features",
                "best_time_to_visit",
                "created_at",
                "updated_at",
            }
        )

        # Add flattened coordinates
        if self.coordinates:
            properties["latitude"] = self.coordinates.latitude
            properties["longitude"] = self.coordinates.longitude

        # Handle price range
        if self.price_range:
            properties["price_min"] = self.price_range.min_price
            properties["price_max"] = self.price_range.max_price
            properties["price_currency"] = self.price_range.currency

        # Handle dates (Neo4j expects ISO format strings)
        properties["created_at"] = self.created_at.isoformat()
        properties["updated_at"] = self.updated_at.isoformat()

        # Arrays are handled directly by Neo4j driver
        if self.tags:
            properties["tags"] = self.tags

        if self.accessibility_features:
            properties["accessibility_features"] = self.accessibility_features

        if self.best_time_to_visit:
            properties["best_time_to_visit"] = self.best_time_to_visit

        # Dictionaries need to be serialized
        if self.opening_hours:
            import json

            properties["opening_hours"] = json.dumps(self.opening_hours)

        return properties

    @classmethod
    def from_neo4j_node(cls, node: Dict[str, Any]) -> "Activity":
        """Create Activity from Neo4j node.

        Args:
            node: Node data from Neo4j

        Returns:
            Activity instance
        """
        properties = dict(node)

        # Handle coordinates
        coordinates = None
        if "latitude" in properties and "longitude" in properties:
            coordinates = Coordinate(
                latitude=properties.pop("latitude"),
                longitude=properties.pop("longitude"),
            )

        # Handle price range
        price_range = None
        if "price_min" in properties and "price_max" in properties:
            price_range = PriceRange(
                min_price=properties.pop("price_min"),
                max_price=properties.pop("price_max"),
                currency=properties.pop("price_currency", "USD"),
            )

        # Handle opening hours
        if "opening_hours" in properties and isinstance(
            properties["opening_hours"], str
        ):
            import json

            properties["opening_hours"] = json.loads(properties["opening_hours"])

        # Handle dates
        if "created_at" in properties and isinstance(properties["created_at"], str):
            properties["created_at"] = datetime.fromisoformat(properties["created_at"])

        if "updated_at" in properties and isinstance(properties["updated_at"], str):
            properties["updated_at"] = datetime.fromisoformat(properties["updated_at"])

        # Remove any Neo4j-specific properties
        properties.pop("elementId", None)

        # Add back complex objects
        properties["coordinates"] = coordinates
        properties["price_range"] = price_range

        return cls(**properties)
