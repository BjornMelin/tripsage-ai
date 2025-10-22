"""Tests for TripComparison model."""

from datetime import UTC, datetime

from tripsage_core.models.db.trip_comparison import TripComparison


def test_trip_comparison_creation(sample_trip_comparison_dict):
    """Test creating a TripComparison model with valid data."""
    trip_comparison = TripComparison(**sample_trip_comparison_dict)
    assert trip_comparison.id == 1
    assert trip_comparison.trip_id == 1
    assert trip_comparison.comparison_json["options"][0]["airline"] == "Japan Airlines"
    assert trip_comparison.comparison_json["selected_option_id"] == 1


def test_trip_comparison_optional_fields():
    """Test creating a TripComparison model with minimal required fields."""
    now = datetime.now(UTC)
    minimal_comparison = TripComparison(
        trip_id=1,
        timestamp=now,
        comparison_json={
            "options": [
                {
                    "id": 1,
                    "type": "flight",
                    "price": 1200.00,
                    "airline": "Japan Airlines",
                },
                {"id": 2, "type": "flight", "price": 1350.00, "airline": "ANA"},
            ],
        },
    )

    assert minimal_comparison.trip_id == 1
    assert minimal_comparison.id is None
    assert minimal_comparison.timestamp == now
    # selected_option_id is not required
    assert "selected_option_id" not in minimal_comparison.comparison_json


def test_trip_comparison_has_selected_option(sample_trip_comparison_dict):
    """Test the has_selected_option property."""
    trip_comparison = TripComparison(**sample_trip_comparison_dict)
    assert trip_comparison.has_selected_option is True

    # Remove selected_option_id
    del trip_comparison.comparison_json["selected_option_id"]
    assert trip_comparison.has_selected_option is False


def test_trip_comparison_selected_option_id(sample_trip_comparison_dict):
    """Test the selected_option_id property."""
    trip_comparison = TripComparison(**sample_trip_comparison_dict)
    assert trip_comparison.selected_option_id == 1

    # Remove selected_option_id
    del trip_comparison.comparison_json["selected_option_id"]
    assert trip_comparison.selected_option_id is None


def test_trip_comparison_options_count(sample_trip_comparison_dict):
    """Test the options_count property."""
    trip_comparison = TripComparison(**sample_trip_comparison_dict)
    assert trip_comparison.options_count == 2

    # Add another option
    trip_comparison.comparison_json["options"].append(
        {"id": 3, "type": "flight", "price": 1100.00, "airline": "United"}
    )
    assert trip_comparison.options_count == 3


def test_trip_comparison_comparison_type(sample_trip_comparison_dict):
    """Test the comparison_type property."""
    trip_comparison = TripComparison(**sample_trip_comparison_dict)
    assert trip_comparison.comparison_type == "flight"

    # Change the type
    trip_comparison.comparison_json["options"][0]["type"] = "accommodation"
    trip_comparison.comparison_json["options"][1]["type"] = "accommodation"
    assert trip_comparison.comparison_type == "accommodation"

    # Mix types (should return the first one)
    trip_comparison.comparison_json["options"][0]["type"] = "flight"
    trip_comparison.comparison_json["options"][1]["type"] = "accommodation"
    assert trip_comparison.comparison_type == "flight"

    # Empty options
    trip_comparison.comparison_json["options"] = []
    assert trip_comparison.comparison_type is None


def test_trip_comparison_get_option_by_id(sample_trip_comparison_dict):
    """Test the get_option_by_id method."""
    trip_comparison = TripComparison(**sample_trip_comparison_dict)

    # Get existing option
    option = trip_comparison.get_option_by_id(1)
    assert option is not None
    assert option["id"] == 1
    assert option["airline"] == "Japan Airlines"

    # Get non-existent option
    option = trip_comparison.get_option_by_id(999)
    assert option is None


def test_trip_comparison_get_selected_option(sample_trip_comparison_dict):
    """Test the get_selected_option method."""
    trip_comparison = TripComparison(**sample_trip_comparison_dict)

    # Get selected option
    option = trip_comparison.get_selected_option()
    assert option is not None
    assert option["id"] == 1
    assert option["airline"] == "Japan Airlines"

    # No selected option
    del trip_comparison.comparison_json["selected_option_id"]
    option = trip_comparison.get_selected_option()
    assert option is None


def test_trip_comparison_has_criteria(sample_trip_comparison_dict):
    """Test the has_criteria property."""
    trip_comparison = TripComparison(**sample_trip_comparison_dict)
    assert trip_comparison.has_criteria is True

    # Remove criteria
    del trip_comparison.comparison_json["criteria"]
    assert trip_comparison.has_criteria is False


def test_trip_comparison_criteria_list(sample_trip_comparison_dict):
    """Test the criteria_list property."""
    trip_comparison = TripComparison(**sample_trip_comparison_dict)
    assert trip_comparison.criteria_list == ["price", "duration", "layovers"]

    # Remove criteria
    del trip_comparison.comparison_json["criteria"]
    assert trip_comparison.criteria_list == []


def test_trip_comparison_formatted_timestamp(sample_trip_comparison_dict):
    """Test the formatted_timestamp property."""
    trip_comparison = TripComparison(**sample_trip_comparison_dict)
    # This is a basic check since the exact format depends on the implementation
    assert isinstance(trip_comparison.formatted_timestamp, str)
    assert len(trip_comparison.formatted_timestamp) > 0


def test_trip_comparison_model_dump(sample_trip_comparison_dict):
    """Test model_dump method."""
    trip_comparison = TripComparison(**sample_trip_comparison_dict)
    comparison_dict = trip_comparison.model_dump()

    assert comparison_dict["trip_id"] == 1
    assert (
        comparison_dict["comparison_json"]["options"][0]["airline"] == "Japan Airlines"
    )
    assert comparison_dict["comparison_json"]["selected_option_id"] == 1
