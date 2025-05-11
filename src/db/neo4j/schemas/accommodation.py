"""
Accommodation entity schema for Neo4j.

This module defines the Accommodation entity schema for the Neo4j knowledge graph,
with validation and conversion methods for Neo4j integration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, validator

from src.db.neo4j.schemas.destination import Coordinate


class RoomType(BaseModel):
    """Room type information."""

    name: str
    capacity: int = Field(..., gt=0)
    price_per_night: float = Field(..., gt=0)
    currency: str = "USD"
    amenities: Optional[List[str]] = None


class Accommodation(BaseModel):
    """Accommodation entity schema."""

    name: str = Field(..., min_length=1)
    destination: str  # Reference to destination name
    type: str = Field(
        ...,
        regex="^(hotel|hostel|resort|apartment|vacation_rental|airbnb|guest_house|motel|camping)$",
    )
    description: Optional[str] = None
    address: Optional[str] = None
    coordinates: Optional[Coordinate] = None
    rating: Optional[float] = Field(None, ge=1, le=5)
    stars: Optional[int] = Field(None, ge=1, le=5)
    price_range: Optional[Dict[str, float]] = None  # min, max, avg
    currency: str = "USD"
    amenities: Optional[List[str]] = None
    room_types: Optional[List[RoomType]] = None
    images: Optional[List[str]] = None  # URLs
    website: Optional[str] = None
    contact_info: Optional[Dict[str, str]] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    cancellation_policy: Optional[str] = None
    sustainability_features: Optional[List[str]] = None
    accessibility_features: Optional[List[str]] = None
    reviews_count: Optional[int] = Field(None, ge=0)
    reviews_avg: Optional[float] = Field(None, ge=0, le=5)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("name")
    def name_must_be_valid(cls, v):
        """Validate accommodation name."""
        if not v.strip():
            raise ValueError("Accommodation name cannot be empty")
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
                "amenities",
                "room_types",
                "images",
                "contact_info",
                "sustainability_features",
                "accessibility_features",
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
            for key, value in self.price_range.items():
                properties[f"price_{key}"] = value

        # Handle dates (Neo4j expects ISO format strings)
        properties["created_at"] = self.created_at.isoformat()
        properties["updated_at"] = self.updated_at.isoformat()

        # Arrays are handled directly by Neo4j driver
        if self.amenities:
            properties["amenities"] = self.amenities

        if self.sustainability_features:
            properties["sustainability_features"] = self.sustainability_features

        if self.accessibility_features:
            properties["accessibility_features"] = self.accessibility_features

        if self.images:
            properties["images"] = self.images

        # Nested objects need to be serialized
        if self.room_types:
            import json

            properties["room_types"] = json.dumps(
                [room.dict() for room in self.room_types]
            )

        if self.contact_info:
            import json

            properties["contact_info"] = json.dumps(self.contact_info)

        return properties

    @classmethod
    def from_neo4j_node(cls, node: Dict[str, Any]) -> "Accommodation":
        """Create Accommodation from Neo4j node.

        Args:
            node: Node data from Neo4j

        Returns:
            Accommodation instance
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
        price_range = {}
        price_keys = [k for k in properties.keys() if k.startswith("price_")]
        for key in price_keys:
            # Skip currency which is separate
            if key == "price_currency":
                continue
            # Extract suffix after price_
            suffix = key[6:]
            price_range[suffix] = properties.pop(key)

        # Handle nested objects
        if "room_types" in properties and isinstance(properties["room_types"], str):
            import json

            room_types_data = json.loads(properties.pop("room_types"))
            properties["room_types"] = [RoomType(**room) for room in room_types_data]

        if "contact_info" in properties and isinstance(properties["contact_info"], str):
            import json

            properties["contact_info"] = json.loads(properties["contact_info"])

        # Handle dates
        if "created_at" in properties and isinstance(properties["created_at"], str):
            properties["created_at"] = datetime.fromisoformat(properties["created_at"])

        if "updated_at" in properties and isinstance(properties["updated_at"], str):
            properties["updated_at"] = datetime.fromisoformat(properties["updated_at"])

        # Remove any Neo4j-specific properties
        properties.pop("elementId", None)

        # Add back complex objects
        properties["coordinates"] = coordinates
        if price_range:
            properties["price_range"] = price_range

        return cls(**properties)