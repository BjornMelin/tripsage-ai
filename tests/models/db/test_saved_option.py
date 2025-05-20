"""Tests for SavedOption model."""

import pytest
from datetime import datetime
from tripsage.models.db.saved_option import SavedOption, OptionType
from pydantic import ValidationError


def test_saved_option_creation(sample_saved_option_dict):
    """Test creating a SavedOption model with valid data."""
    saved_option = SavedOption(**sample_saved_option_dict)
    assert saved_option.id == 1
    assert saved_option.trip_id == 1
    assert saved_option.option_type == OptionType.FLIGHT
    assert saved_option.option_id == 1
    assert saved_option.notes == "Best price found so far"


def test_saved_option_optional_fields():
    """Test creating a SavedOption model with minimal required fields."""
    now = datetime.now()
    minimal_saved_option = SavedOption(
        trip_id=1,
        option_type=OptionType.FLIGHT,
        option_id=1,
        timestamp=now,
    )
    
    assert minimal_saved_option.trip_id == 1
    assert minimal_saved_option.id is None
    assert minimal_saved_option.option_type == OptionType.FLIGHT
    assert minimal_saved_option.option_id == 1
    assert minimal_saved_option.notes is None


def test_saved_option_is_flight_property(sample_saved_option_dict):
    """Test the is_flight property."""
    saved_option = SavedOption(**sample_saved_option_dict)
    assert saved_option.is_flight is True
    
    saved_option.option_type = OptionType.ACCOMMODATION
    assert saved_option.is_flight is False


def test_saved_option_is_accommodation_property(sample_saved_option_dict):
    """Test the is_accommodation property."""
    saved_option = SavedOption(**sample_saved_option_dict)
    assert saved_option.is_accommodation is False
    
    saved_option.option_type = OptionType.ACCOMMODATION
    assert saved_option.is_accommodation is True


def test_saved_option_is_transportation_property(sample_saved_option_dict):
    """Test the is_transportation property."""
    saved_option = SavedOption(**sample_saved_option_dict)
    assert saved_option.is_transportation is False
    
    saved_option.option_type = OptionType.TRANSPORTATION
    assert saved_option.is_transportation is True


def test_saved_option_is_activity_property(sample_saved_option_dict):
    """Test the is_activity property."""
    saved_option = SavedOption(**sample_saved_option_dict)
    assert saved_option.is_activity is False
    
    saved_option.option_type = OptionType.ACTIVITY
    assert saved_option.is_activity is True


def test_saved_option_formatted_timestamp(sample_saved_option_dict):
    """Test the formatted_timestamp property."""
    saved_option = SavedOption(**sample_saved_option_dict)
    # This is a basic check since the exact format depends on the implementation
    assert isinstance(saved_option.formatted_timestamp, str)
    assert len(saved_option.formatted_timestamp) > 0


def test_saved_option_type_display_name(sample_saved_option_dict):
    """Test the type_display_name property."""
    saved_option = SavedOption(**sample_saved_option_dict)
    assert saved_option.type_display_name == "Flight"
    
    saved_option.option_type = OptionType.ACCOMMODATION
    assert saved_option.type_display_name == "Accommodation"
    
    saved_option.option_type = OptionType.TRANSPORTATION
    assert saved_option.type_display_name == "Transportation"
    
    saved_option.option_type = OptionType.ACTIVITY
    assert saved_option.type_display_name == "Activity"


def test_saved_option_has_notes(sample_saved_option_dict):
    """Test the has_notes property."""
    saved_option = SavedOption(**sample_saved_option_dict)
    assert saved_option.has_notes is True
    
    saved_option.notes = None
    assert saved_option.has_notes is False
    
    saved_option.notes = ""
    assert saved_option.has_notes is False


def test_saved_option_model_dump(sample_saved_option_dict):
    """Test model_dump method."""
    saved_option = SavedOption(**sample_saved_option_dict)
    option_dict = saved_option.model_dump()
    
    assert option_dict["trip_id"] == 1
    assert option_dict["option_type"] == OptionType.FLIGHT
    assert option_dict["option_id"] == 1
    assert option_dict["notes"] == "Best price found so far"