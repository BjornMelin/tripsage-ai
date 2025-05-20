"""PriceHistory model for TripSage.

This module provides the PriceHistory model for tracking
price changes over time for various entities.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field, field_validator

from tripsage.models.base import TripSageModel


class EntityType(str, Enum):
    """Enum for entity type values."""

    FLIGHT = "flight"
    ACCOMMODATION = "accommodation"
    TRANSPORTATION = "transportation"
    ACTIVITY = "activity"


class PriceHistory(TripSageModel):
    """PriceHistory model for TripSage.

    Attributes:
        id: Unique identifier for the price history record
        entity_type: Type of entity this price is for
        entity_id: ID of the entity this price is for
        timestamp: When the price was recorded
        price: The price value in default currency
    """

    id: Optional[int] = Field(None, description="Unique identifier")
    entity_type: EntityType = Field(..., description="Type of entity this price is for")
    entity_id: int = Field(..., description="ID of the entity this price is for")
    timestamp: datetime = Field(..., description="When the price was recorded")
    price: float = Field(..., description="The price value in default currency")

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate that price is a positive number."""
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @property
    def is_recent(self) -> bool:
        """Check if the price was recorded recently (within 24 hours)."""
        from datetime import datetime as datetime_type, timedelta
        return datetime_type.now() - self.timestamp < timedelta(hours=24)
    
    @property
    def formatted_timestamp(self) -> str:
        """Get the formatted timestamp for display."""
        return self.timestamp.strftime("%Y-%m-%d %H:%M")
    
    @property
    def formatted_price(self) -> str:
        """Get the formatted price with currency symbol."""
        return f"${self.price:.2f}"
    
    @property
    def is_flight_price(self) -> bool:
        """Check if this is a flight price."""
        return self.entity_type == EntityType.FLIGHT
    
    @property
    def is_accommodation_price(self) -> bool:
        """Check if this is an accommodation price."""
        return self.entity_type == EntityType.ACCOMMODATION
    
    @property
    def is_transportation_price(self) -> bool:
        """Check if this is a transportation price."""
        return self.entity_type == EntityType.TRANSPORTATION
    
    @property
    def is_activity_price(self) -> bool:
        """Check if this is an activity price."""
        return self.entity_type == EntityType.ACTIVITY