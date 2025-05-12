"""
Event entity schema for Neo4j.

This module defines the Event entity schema for the Neo4j knowledge graph,
with validation and conversion methods for Neo4j integration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from src.db.neo4j.schemas.destination import Coordinate


class EventTicket(BaseModel):
    """Event ticket information."""

    category: str = Field(..., min_length=1)
    price: float = Field(..., ge=0)
    currency: str = "USD"
    availability: Optional[str] = None


class Event(BaseModel):
    """Event entity schema."""

    name: str = Field(..., min_length=1)
    destination: str  # Reference to destination name
    type: str = Field(
        ...,
        regex=(
            "^(concert|festival|exhibition|conference|"
            "sports|cultural|food|performance|workshop|market)$"
        ),
    )
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue: Optional[str] = None
    address: Optional[str] = None
    coordinates: Optional[Coordinate] = None
    organizer: Optional[str] = None
    tickets: Optional[List[EventTicket]] = None
    website: Optional[str] = None
    image_url: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    tags: Optional[List[str]] = None
    capacity: Optional[int] = Field(None, gt=0)
    popularity_score: Optional[float] = Field(None, ge=0, le=100)
    accessibility_features: Optional[List[str]] = None
    covid_restrictions: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("name")
    def name_must_be_valid(cls, v):
        """Validate event name."""
        if not v.strip():
            raise ValueError("Event name cannot be empty")
        return v.strip()

    @validator("end_date")
    def end_date_must_be_after_start(cls, v, values):
        """Validate end date is after start date."""
        if v and "start_date" in values and v < values["start_date"]:
            raise ValueError("End date must be after start date")
        return v

    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j properties.

        Returns:
            Properties dictionary for Neo4j node
        """
        properties = self.dict(
            exclude={
                "coordinates",
                "tickets",
                "tags",
                "accessibility_features",
                "created_at",
                "updated_at",
            }
        )

        # Add flattened coordinates
        if self.coordinates:
            properties["latitude"] = self.coordinates.latitude
            properties["longitude"] = self.coordinates.longitude

        # Handle dates (Neo4j expects ISO format strings)
        properties["start_date"] = self.start_date.isoformat()
        if self.end_date:
            properties["end_date"] = self.end_date.isoformat()

        properties["created_at"] = self.created_at.isoformat()
        properties["updated_at"] = self.updated_at.isoformat()

        # Arrays are handled directly by Neo4j driver
        if self.tags:
            properties["tags"] = self.tags

        if self.accessibility_features:
            properties["accessibility_features"] = self.accessibility_features

        # Nested objects need to be serialized
        if self.tickets:
            import json

            properties["tickets"] = json.dumps(
                [ticket.dict() for ticket in self.tickets]
            )

        return properties

    @classmethod
    def from_neo4j_node(cls, node: Dict[str, Any]) -> "Event":
        """Create Event from Neo4j node.

        Args:
            node: Node data from Neo4j

        Returns:
            Event instance
        """
        properties = dict(node)

        # Handle coordinates
        coordinates = None
        if "latitude" in properties and "longitude" in properties:
            coordinates = Coordinate(
                latitude=properties.pop("latitude"),
                longitude=properties.pop("longitude"),
            )

        # Handle tickets
        if "tickets" in properties and isinstance(properties["tickets"], str):
            import json

            tickets_data = json.loads(properties.pop("tickets"))
            properties["tickets"] = [EventTicket(**ticket) for ticket in tickets_data]

        # Handle dates
        if "start_date" in properties and isinstance(properties["start_date"], str):
            properties["start_date"] = datetime.fromisoformat(properties["start_date"])

        if "end_date" in properties and isinstance(properties["end_date"], str):
            properties["end_date"] = datetime.fromisoformat(properties["end_date"])

        if "created_at" in properties and isinstance(properties["created_at"], str):
            properties["created_at"] = datetime.fromisoformat(properties["created_at"])

        if "updated_at" in properties and isinstance(properties["updated_at"], str):
            properties["updated_at"] = datetime.fromisoformat(properties["updated_at"])

        # Remove any Neo4j-specific properties
        properties.pop("elementId", None)

        # Add back complex objects
        properties["coordinates"] = coordinates

        return cls(**properties)
