"""Tests for PriceHistory model."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from tripsage_core.models.db.price_history import EntityType, PriceHistory

def test_price_history_creation(sample_price_history_dict):
    """Test creating a PriceHistory model with valid data."""
    price_history = PriceHistory(**sample_price_history_dict)
    assert price_history.id == 1
    assert price_history.entity_type == EntityType.FLIGHT
    assert price_history.entity_id == 1
    assert price_history.price == 1200.00
    assert price_history.currency == "USD"

def test_price_history_optional_fields():
    """Test creating a PriceHistory model with minimal required fields."""
    now = datetime.now(timezone.utc)
    minimal_price_history = PriceHistory(
        entity_type=EntityType.FLIGHT,
        entity_id=1,
        timestamp=now,
        price=1200.00,
    )

    assert minimal_price_history.entity_type == EntityType.FLIGHT
    assert minimal_price_history.id is None
    assert minimal_price_history.timestamp == now
    assert minimal_price_history.currency == "USD"  # Default value

def test_price_history_validation_price():
    """Test price validation."""
    now = datetime.now(timezone.utc)

    # Test negative price
    with pytest.raises(ValidationError) as excinfo:
        PriceHistory(
            entity_type=EntityType.FLIGHT,
            entity_id=1,
            timestamp=now,
            price=-100.00,  # Negative price
        )
    assert "ensure this value is greater than 0" in str(excinfo.value)

def test_price_history_validation_currency():
    """Test currency validation."""
    now = datetime.now(timezone.utc)

    # Test invalid currency code
    with pytest.raises(ValidationError) as excinfo:
        PriceHistory(
            entity_type=EntityType.FLIGHT,
            entity_id=1,
            timestamp=now,
            price=1200.00,
            currency="INVALID",  # Invalid currency code
        )
    assert "Currency code must be a 3-letter code" in str(excinfo.value)

    # Test valid currency codes
    valid_currencies = ["USD", "EUR", "JPY", "GBP", "AUD", "CAD"]
    for currency in valid_currencies:
        price_history = PriceHistory(
            entity_type=EntityType.FLIGHT,
            entity_id=1,
            timestamp=now,
            price=1200.00,
            currency=currency,
        )
        assert price_history.currency == currency

def test_price_history_is_flight_price_property(sample_price_history_dict):
    """Test the is_flight_price property."""
    price_history = PriceHistory(**sample_price_history_dict)
    assert price_history.is_flight_price is True

    price_history.entity_type = EntityType.ACCOMMODATION
    assert price_history.is_flight_price is False

def test_price_history_is_accommodation_price_property(sample_price_history_dict):
    """Test the is_accommodation_price property."""
    price_history = PriceHistory(**sample_price_history_dict)
    assert price_history.is_accommodation_price is False

    price_history.entity_type = EntityType.ACCOMMODATION
    assert price_history.is_accommodation_price is True

def test_price_history_is_transportation_price_property(sample_price_history_dict):
    """Test the is_transportation_price property."""
    price_history = PriceHistory(**sample_price_history_dict)
    assert price_history.is_transportation_price is False

    price_history.entity_type = EntityType.TRANSPORTATION
    assert price_history.is_transportation_price is True

def test_price_history_is_activity_price_property(sample_price_history_dict):
    """Test the is_activity_price property."""
    price_history = PriceHistory(**sample_price_history_dict)
    assert price_history.is_activity_price is False

    price_history.entity_type = EntityType.ACTIVITY
    assert price_history.is_activity_price is True

def test_price_history_formatted_price(sample_price_history_dict):
    """Test the formatted_price property."""
    price_history = PriceHistory(**sample_price_history_dict)
    assert price_history.formatted_price == "$1,200.00"

    price_history.currency = "EUR"
    assert price_history.formatted_price == "€1,200.00"

    price_history.currency = "JPY"
    assert price_history.formatted_price == "¥1,200"  # No decimal places for JPY

    price_history.currency = "GBP"
    assert price_history.formatted_price == "£1,200.00"

def test_price_history_formatted_timestamp(sample_price_history_dict):
    """Test the formatted_timestamp property."""
    price_history = PriceHistory(**sample_price_history_dict)
    # This is a basic check since the exact format depends on the implementation
    assert isinstance(price_history.formatted_timestamp, str)
    assert len(price_history.formatted_timestamp) > 0

def test_price_history_model_dump(sample_price_history_dict):
    """Test model_dump method."""
    price_history = PriceHistory(**sample_price_history_dict)
    history_dict = price_history.model_dump()

    assert history_dict["entity_type"] == EntityType.FLIGHT
    assert history_dict["entity_id"] == 1
    assert history_dict["price"] == 1200.00
    assert history_dict["currency"] == "USD"
