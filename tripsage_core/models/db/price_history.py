"""PriceHistory model for TripSage.

This module provides the PriceHistory model for tracking
price changes over time for various entities.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field, field_validator

from tripsage_core.models.base_core_model import TripSageModel

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

    id: int | None = Field(None, description="Unique identifier")
    entity_type: EntityType = Field(..., description="Type of entity this price is for")
    entity_id: int = Field(..., description="ID of the entity this price is for")
    timestamp: datetime = Field(..., description="When the price was recorded")
    price: float = Field(..., description="The price value in default currency")
    currency: str = Field("USD", description="Currency code for the price")

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate that price is a positive number."""
        if v <= 0:
            raise ValueError("ensure this value is greater than 0")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code format."""
        if not isinstance(v, str) or len(v) != 3 or not v.isupper():
            raise ValueError("Currency code must be a 3-letter code")
        return v

    @property
    def is_recent(self) -> bool:
        """Check if the price was recorded recently (within 24 hours)."""
        from datetime import datetime as datetime_type
        from datetime import timedelta

        return datetime_type.now() - self.timestamp < timedelta(hours=24)

    @property
    def formatted_timestamp(self) -> str:
        """Get the formatted timestamp for display."""
        return self.timestamp.strftime("%Y-%m-%d %H:%M")

    @property
    def formatted_price(self) -> str:
        """Get the formatted price with currency symbol."""
        # Currency symbol mapping
        currency_symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "AUD": "A$",
            "CAD": "C$",
            "CHF": "CHF",
            "CNY": "¥",
        }

        symbol = currency_symbols.get(self.currency, self.currency)

        # JPY doesn't use decimal places
        if self.currency == "JPY":
            return f"{symbol}{self.price:,.0f}"

        # Default formatting with 2 decimal places
        return f"{symbol}{self.price:,.2f}"

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
