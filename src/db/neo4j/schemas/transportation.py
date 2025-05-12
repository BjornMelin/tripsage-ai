"""
Transportation entity schema for Neo4j.

This module defines the Transportation entity schema for the Neo4j knowledge graph,
with validation and conversion methods for Neo4j integration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class RoutePoint(BaseModel):
    """Route point information."""

    name: str
    coordinates: Optional[Dict[str, float]] = None
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None
    stop_duration_minutes: Optional[int] = None


class Schedule(BaseModel):
    """Schedule information."""

    days: List[str]  # Monday, Tuesday, etc.
    start_time: str
    end_time: str
    frequency_minutes: Optional[int] = None


class Transportation(BaseModel):
    """Transportation entity schema."""

    name: str = Field(..., min_length=1)
    type: str = Field(
        ...,
        regex=("^(flight|train|bus|ferry|taxi|rideshare|bike|" 
               "subway|tram|car_rental|walking_tour)$"),
    )
    provider: Optional[str] = None
    description: Optional[str] = None
    origin: str
    destination: str
    route_points: Optional[List[RoutePoint]] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    distance_km: Optional[float] = Field(None, ge=0)
    price: Optional[float] = Field(None, ge=0)
    currency: str = "USD"
    schedule: Optional[List[Schedule]] = None
    amenities: Optional[List[str]] = None
    accessibility_features: Optional[List[str]] = None
    booking_url: Optional[str] = None
    rating: Optional[float] = Field(None, ge=1, le=5)
    popularity_score: Optional[float] = Field(None, ge=0, le=100)
    sustainability_score: Optional[float] = Field(None, ge=0, le=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("name")
    def name_must_be_valid(cls, v):
        """Validate transportation name."""
        if not v.strip():
            raise ValueError("Transportation name cannot be empty")
        return v.strip()

    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j properties.

        Returns:
            Properties dictionary for Neo4j node
        """
        import json

        properties = self.dict(
            exclude={
                "route_points",
                "schedule",
                "amenities",
                "accessibility_features",
                "created_at",
                "updated_at",
            }
        )

        # Handle complex objects
        if self.route_points:
            properties["route_points"] = json.dumps(
                [point.dict() for point in self.route_points]
            )

        if self.schedule:
            properties["schedule"] = json.dumps(
                [sched.dict() for sched in self.schedule]
            )

        # Handle arrays
        if self.amenities:
            properties["amenities"] = self.amenities

        if self.accessibility_features:
            properties["accessibility_features"] = self.accessibility_features

        # Handle dates
        properties["created_at"] = self.created_at.isoformat()
        properties["updated_at"] = self.updated_at.isoformat()

        return properties

    @classmethod
    def from_neo4j_node(cls, node: Dict[str, Any]) -> "Transportation":
        """Create Transportation from Neo4j node.

        Args:
            node: Node data from Neo4j

        Returns:
            Transportation instance
        """
        import json
        properties = dict(node)

        # Handle complex objects
        if "route_points" in properties and isinstance(properties["route_points"], str):
            route_points_data = json.loads(properties.pop("route_points"))
            properties["route_points"] = [RoutePoint(**point) for point in route_points_data]

        if "schedule" in properties and isinstance(properties["schedule"], str):
            schedule_data = json.loads(properties.pop("schedule"))
            properties["schedule"] = [Schedule(**sched) for sched in schedule_data]

        # Handle dates
        if "created_at" in properties and isinstance(properties["created_at"], str):
            properties["created_at"] = datetime.fromisoformat(properties["created_at"])

        if "updated_at" in properties and isinstance(properties["updated_at"], str):
            properties["updated_at"] = datetime.fromisoformat(properties["updated_at"])

        # Remove any Neo4j-specific properties
        properties.pop("elementId", None)

        return cls(**properties)