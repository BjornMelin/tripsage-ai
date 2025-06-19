"""Tests for SavedOption model following modern pytest patterns."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from tripsage_core.models.db.saved_option import OptionType, SavedOption


class TestSavedOptionModel:
    """Test SavedOption model creation, validation, and methods."""

    @pytest.fixture
    def base_saved_option_data(self):
        """Base data for creating SavedOption instances."""
        return {
            "id": 1,
            "trip_id": 1,
            "option_type": OptionType.FLIGHT,
            "option_id": 1,
            "timestamp": datetime.now(timezone.utc),
            "notes": "Best price found so far",
        }

    def test_saved_option_creation_with_full_data(self, base_saved_option_data):
        """Test creating SavedOption with all fields."""
        saved_option = SavedOption(**base_saved_option_data)

        assert saved_option.id == 1
        assert saved_option.trip_id == 1
        assert saved_option.option_type == OptionType.FLIGHT
        assert saved_option.option_id == 1
        assert saved_option.notes == "Best price found so far"

    def test_saved_option_creation_minimal_data(self):
        """Test creating SavedOption with minimal required fields."""
        minimal_data = {
            "trip_id": 1,
            "option_type": OptionType.FLIGHT,
            "option_id": 1,
            "timestamp": datetime.now(timezone.utc),
        }
        saved_option = SavedOption(**minimal_data)

        assert saved_option.trip_id == 1
        assert saved_option.id is None
        assert saved_option.option_type == OptionType.FLIGHT
        assert saved_option.option_id == 1
        assert saved_option.notes is None

    @pytest.mark.parametrize(
        "option_type,expected_flight,expected_accommodation,expected_transportation,expected_activity",
        [
            (OptionType.FLIGHT, True, False, False, False),
            (OptionType.ACCOMMODATION, False, True, False, False),
            (OptionType.TRANSPORTATION, False, False, True, False),
            (OptionType.ACTIVITY, False, False, False, True),
        ],
    )
    def test_saved_option_type_properties(
        self,
        base_saved_option_data,
        option_type,
        expected_flight,
        expected_accommodation,
        expected_transportation,
        expected_activity,
    ):
        """Test option type property methods."""
        saved_option = SavedOption(
            **{**base_saved_option_data, "option_type": option_type}
        )

        assert saved_option.is_flight == expected_flight
        assert saved_option.is_accommodation == expected_accommodation
        assert saved_option.is_transportation == expected_transportation
        assert saved_option.is_activity == expected_activity

    @pytest.mark.parametrize(
        "option_type,expected_display_name",
        [
            (OptionType.FLIGHT, "Flight"),
            (OptionType.ACCOMMODATION, "Accommodation"),
            (OptionType.TRANSPORTATION, "Transportation"),
            (OptionType.ACTIVITY, "Activity"),
        ],
    )
    def test_saved_option_type_display_name(
        self, base_saved_option_data, option_type, expected_display_name
    ):
        """Test type_display_name property."""
        saved_option = SavedOption(
            **{**base_saved_option_data, "option_type": option_type}
        )
        assert saved_option.type_display_name == expected_display_name

    def test_saved_option_formatted_timestamp(self, base_saved_option_data):
        """Test formatted_timestamp property."""
        saved_option = SavedOption(**base_saved_option_data)

        # Basic validation that it returns a non-empty string
        assert isinstance(saved_option.formatted_timestamp, str)
        assert len(saved_option.formatted_timestamp) > 0

    @pytest.mark.parametrize(
        "notes,expected_has_notes",
        [
            ("Best price found so far", True),
            ("", False),
            (None, False),
            ("   ", False),  # Only whitespace should be False
        ],
    )
    def test_saved_option_has_notes_property(
        self, base_saved_option_data, notes, expected_has_notes
    ):
        """Test has_notes property with various note values."""
        saved_option = SavedOption(**{**base_saved_option_data, "notes": notes})
        assert saved_option.has_notes == expected_has_notes

    def test_saved_option_model_dump(self, base_saved_option_data):
        """Test model_dump method serialization."""
        saved_option = SavedOption(**base_saved_option_data)
        option_dict = saved_option.model_dump()

        assert option_dict["trip_id"] == 1
        assert option_dict["option_type"] == OptionType.FLIGHT
        assert option_dict["option_id"] == 1
        assert option_dict["notes"] == "Best price found so far"

    def test_saved_option_dynamic_type_change(self, base_saved_option_data):
        """Test that properties update correctly when option_type changes."""
        saved_option = SavedOption(**base_saved_option_data)

        # Initially FLIGHT
        assert saved_option.is_flight is True
        assert saved_option.type_display_name == "Flight"

        # Change to ACCOMMODATION
        saved_option.option_type = OptionType.ACCOMMODATION
        assert saved_option.is_flight is False
        assert saved_option.is_accommodation is True
        assert saved_option.type_display_name == "Accommodation"

        # Change to TRANSPORTATION
        saved_option.option_type = OptionType.TRANSPORTATION
        assert saved_option.is_accommodation is False
        assert saved_option.is_transportation is True
        assert saved_option.type_display_name == "Transportation"

        # Change to ACTIVITY
        saved_option.option_type = OptionType.ACTIVITY
        assert saved_option.is_transportation is False
        assert saved_option.is_activity is True
        assert saved_option.type_display_name == "Activity"

    @pytest.mark.parametrize(
        "invalid_option_id",
        [0, -1, -10],
    )
    def test_saved_option_validation_option_id(
        self, base_saved_option_data, invalid_option_id
    ):
        """Test validation for invalid option_id values."""
        with pytest.raises(ValidationError, match="Option ID must be positive"):
            SavedOption(**{**base_saved_option_data, "option_id": invalid_option_id})

    def test_saved_option_update_notes(self, base_saved_option_data):
        """Test update_notes method."""
        saved_option = SavedOption(**base_saved_option_data)

        # Update to new notes
        saved_option.update_notes("Updated notes")
        assert saved_option.notes == "Updated notes"
        assert saved_option.has_notes is True

        # Clear notes
        saved_option.update_notes(None)
        assert saved_option.notes is None
        assert saved_option.has_notes is False

        # Set empty notes
        saved_option.update_notes("")
        assert saved_option.notes == ""
        assert saved_option.has_notes is False


class TestOptionTypeEnum:
    """Test OptionType enum values and behavior."""

    def test_option_type_values(self):
        """Test that OptionType enum has expected values."""
        assert OptionType.FLIGHT == "flight"
        assert OptionType.ACCOMMODATION == "accommodation"
        assert OptionType.TRANSPORTATION == "transportation"
        assert OptionType.ACTIVITY == "activity"

    def test_option_type_iteration(self):
        """Test that all expected option types are present."""
        expected_types = {"flight", "accommodation", "transportation", "activity"}
        actual_types = {option_type.value for option_type in OptionType}
        assert actual_types == expected_types

    @pytest.mark.parametrize(
        "option_type",
        [
            OptionType.FLIGHT,
            OptionType.ACCOMMODATION,
            OptionType.TRANSPORTATION,
            OptionType.ACTIVITY,
        ],
    )
    def test_option_type_string_representation(self, option_type):
        """Test that OptionType enum values are proper strings."""
        assert isinstance(option_type.value, str)
        assert len(option_type.value) > 0
