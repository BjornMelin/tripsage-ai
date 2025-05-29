"""Tests for TripNote model."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from tripsage_core.models.db.trip_note import TripNote


def test_trip_note_creation(sample_trip_note_dict):
    """Test creating a TripNote model with valid data."""
    trip_note = TripNote(**sample_trip_note_dict)
    assert trip_note.id == 1
    assert trip_note.trip_id == 1
    assert trip_note.content == "Remember to exchange currency before departure"


def test_trip_note_optional_fields():
    """Test creating a TripNote model with minimal required fields."""
    now = datetime.now(datetime.UTC)
    minimal_trip_note = TripNote(
        trip_id=1,
        timestamp=now,
        content="Remember to exchange currency before departure",
    )

    assert minimal_trip_note.trip_id == 1
    assert minimal_trip_note.id is None
    assert minimal_trip_note.timestamp == now


def test_trip_note_validation_content():
    """Test content validation."""
    now = datetime.now(datetime.UTC)

    # Test empty content
    with pytest.raises(ValidationError) as excinfo:
        TripNote(
            trip_id=1,
            timestamp=now,
            content="",  # Empty content
        )
    assert "ensure this value has at least 1 character" in str(excinfo.value)


def test_trip_note_content_snippet(sample_trip_note_dict):
    """Test the content_snippet property."""
    trip_note = TripNote(**sample_trip_note_dict)
    assert trip_note.content_snippet == "Remember to exchange currency before departure"

    # Test with long content
    long_content = (
        "This is a very long note that should be truncated for the snippet. " * 5
    )
    trip_note.content = long_content
    assert len(trip_note.content_snippet) <= 100
    assert trip_note.content_snippet.endswith("...")


def test_trip_note_formatted_timestamp(sample_trip_note_dict):
    """Test the formatted_timestamp property."""
    trip_note = TripNote(**sample_trip_note_dict)
    # This is a basic check since the exact format depends on the implementation
    assert isinstance(trip_note.formatted_timestamp, str)
    assert len(trip_note.formatted_timestamp) > 0


def test_trip_note_model_dump(sample_trip_note_dict):
    """Test model_dump method."""
    trip_note = TripNote(**sample_trip_note_dict)
    note_dict = trip_note.model_dump()

    assert note_dict["trip_id"] == 1
    assert note_dict["content"] == "Remember to exchange currency before departure"
