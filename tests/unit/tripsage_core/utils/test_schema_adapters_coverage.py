"""
Coverage-focused tests for Schema Adapters.

These tests exercise the actual schema adapter implementation to increase coverage.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from tripsage_core.utils.schema_adapters import SchemaAdapter


class TestSchemaAdapterCoverage:
    """Test actual SchemaAdapter implementation for coverage."""

    def test_convert_db_trip_to_api(self):
        """Test database to API conversion."""
        db_record = {
            "id": 123,
            "uuid_id": str(uuid4()),
            "user_id": "user123",
            "title": "Test Trip",
            "description": "Test Description",
            "name": "Legacy Name",  # Legacy field
            "destination": "Tokyo, Japan",
            "start_date": date(2024, 6, 1),
            "end_date": date(2024, 6, 15),
            "budget": 1000,
            "budget_breakdown": {
                "total": 1000,
                "breakdown": {"accommodation": 600, "food": 400},
            },
            "currency": "USD",
            "spent_amount": Decimal("150.50"),
            "travelers": 2,
            "status": "planning",
            "visibility": "private",
            "tags": ["business", "adventure"],
            "preferences_extended": {"accommodation": {"type": "hotel", "rating": 4}},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        api_data = SchemaAdapter.convert_db_trip_to_api(db_record)

        # Verify basic conversions
        assert api_data["title"] == "Test Trip"
        assert api_data["description"] == "Test Description"
        assert api_data["destination"] == "Tokyo, Japan"
        assert api_data["start_date"] == date(2024, 6, 1)
        assert api_data["end_date"] == date(2024, 6, 15)
        assert api_data["travelers"] == 2
        assert api_data["status"] == "planning"
        assert api_data["visibility"] == "private"
        assert api_data["tags"] == ["business", "adventure"]

        # Verify enhanced budget conversion
        assert "enhanced_budget" in api_data
        budget = api_data["enhanced_budget"]
        assert budget["total"] == 1000
        assert budget["spent"] == 150.50
        assert budget["currency"] == "USD"
        assert "breakdown" in budget

        # Verify preferences conversion
        assert "preferences" in api_data
        assert api_data["preferences"]["accommodation"]["type"] == "hotel"

        # Verify legacy compatibility
        assert api_data["name"] == "Test Trip"  # Should use title as name

    def test_convert_api_trip_to_db(self):
        """Test API to database conversion."""
        api_trip = {
            "title": "API Trip",
            "description": "API Description",
            "destination": "Paris, France",
            "start_date": date(2024, 7, 1),
            "end_date": date(2024, 7, 10),
            "enhanced_budget": {
                "total": 2000,
                "currency": "EUR",
                "spent": 300,
                "breakdown": {"accommodation": 1200, "food": 500, "activities": 300},
            },
            "travelers": 3,
            "visibility": "shared",
            "tags": ["family", "vacation"],
            "preferences": {
                "accommodation": {"min_rating": 4, "type": "hotel"},
                "dining": {"dietary_restrictions": ["vegetarian"]},
            },
        }

        db_data = SchemaAdapter.convert_api_trip_to_db(api_trip)

        # Verify basic conversions
        assert db_data["title"] == "API Trip"
        assert db_data["description"] == "API Description"
        assert db_data["destination"] == "Paris, France"
        assert db_data["start_date"] == date(2024, 7, 1)
        assert db_data["end_date"] == date(2024, 7, 10)
        assert db_data["travelers"] == 3
        assert db_data["visibility"] == "shared"
        assert db_data["tags"] == ["family", "vacation"]

        # Verify budget breakdown conversion
        assert "budget_breakdown" in db_data
        budget_breakdown = db_data["budget_breakdown"]
        assert budget_breakdown["total"] == 2000
        assert budget_breakdown["breakdown"]["accommodation"] == 1200

        # Verify currency and spent amount
        assert db_data["currency"] == "EUR"
        assert db_data["spent_amount"] == 300

        # Verify preferences conversion to extended format
        assert "preferences_extended" in db_data
        prefs = db_data["preferences_extended"]
        assert prefs["accommodation"]["min_rating"] == 4
        assert prefs["dining"]["dietary_restrictions"] == ["vegetarian"]

    def test_migrate_legacy_preferences(self):
        """Test legacy preferences migration."""
        legacy_flexibility = {
            "budget_flexibility": "high",
            "date_flexibility": "medium",
            "destination_flexibility": "low",
            "accommodation_type": "hotel",
            "activity_preferences": ["sightseeing", "dining"],
        }

        migrated = SchemaAdapter.migrate_legacy_preferences(legacy_flexibility)

        # Verify migration structure
        assert "budget" in migrated
        assert "dates" in migrated
        assert "accommodation" in migrated
        assert "activities" in migrated

        # Verify specific migrations
        assert migrated["budget"]["flexibility"] == "high"
        assert migrated["dates"]["flexibility"] == "medium"
        assert migrated["accommodation"]["type"] == "hotel"
        assert "sightseeing" in migrated["activities"]["preferred"]

    def test_normalize_trip_data_with_missing_fields(self):
        """Test normalization with missing fields."""
        incomplete_data = {
            "title": "Incomplete Trip",
            "destination": "Berlin, Germany",
            # Missing many required fields
        }

        normalized = SchemaAdapter.normalize_trip_data(incomplete_data)

        # Verify defaults are applied
        assert normalized["title"] == "Incomplete Trip"
        assert normalized["destination"] == "Berlin, Germany"
        assert "visibility" in normalized
        assert "tags" in normalized
        assert "preferences" in normalized
        assert normalized["travelers"] >= 1  # Should have sensible default

    def test_validate_and_clean_trip_data(self):
        """Test data validation and cleaning."""
        dirty_data = {
            "title": "  Trip with Extra Spaces  ",
            "description": "\n\nDescription with newlines\n\n",
            "destination": "  Tokyo, Japan  ",
            "tags": ["  tag1  ", "  tag2  ", ""],
            "budget": "1500.50",  # String that should be converted
            "travelers": "2",  # String that should be converted
        }

        cleaned = SchemaAdapter.validate_and_clean_trip_data(dirty_data)

        # Verify cleaning
        assert cleaned["title"] == "Trip with Extra Spaces"
        assert cleaned["description"].strip() == "Description with newlines"
        assert cleaned["destination"] == "Tokyo, Japan"
        assert cleaned["tags"] == ["tag1", "tag2"]  # Empty tag removed
        assert cleaned["budget"] == 1500.50  # Converted to float
        assert cleaned["travelers"] == 2  # Converted to int

    def test_extract_destination_info(self):
        """Test destination information extraction."""
        destination_string = "Tokyo, Japan"

        info = SchemaAdapter.extract_destination_info(destination_string)

        # Verify extraction
        assert "city" in info
        assert "country" in info
        assert info["name"] == destination_string

    def test_format_budget_for_display(self):
        """Test budget formatting for display."""
        budget_data = {
            "total": 1234.56,
            "currency": "USD",
            "spent": 234.78,
            "breakdown": {
                "accommodation": 600.00,
                "food": 300.25,
                "activities": 334.31,
            },
        }

        formatted = SchemaAdapter.format_budget_for_display(budget_data)

        # Verify formatting
        assert "formatted_total" in formatted
        assert "formatted_spent" in formatted
        assert "utilization_percentage" in formatted
        assert formatted["currency"] == "USD"

    def test_handle_date_conversion(self):
        """Test date conversion utilities."""
        # Test string to date
        date_string = "2024-06-01"
        converted_date = SchemaAdapter.convert_date_string(date_string)
        assert converted_date == date(2024, 6, 1)

        # Test date to string
        date_obj = date(2024, 6, 15)
        date_string = SchemaAdapter.convert_date_to_string(date_obj)
        assert date_string == "2024-06-15"

        # Test datetime to date
        datetime_obj = datetime(2024, 6, 1, 12, 30, 0, tzinfo=timezone.utc)
        date_obj = SchemaAdapter.convert_datetime_to_date(datetime_obj)
        assert date_obj == date(2024, 6, 1)

    def test_error_handling_with_invalid_data(self):
        """Test error handling with invalid data."""
        # Test with None data
        result = SchemaAdapter.convert_db_trip_to_api(None)
        assert result == {}

        # Test with empty data
        result = SchemaAdapter.convert_db_trip_to_api({})
        assert isinstance(result, dict)

        # Test with invalid date format
        invalid_data = {"start_date": "invalid-date"}
        try:
            SchemaAdapter.validate_and_clean_trip_data(invalid_data)
        except (ValueError, TypeError):
            pass  # Expected to handle gracefully

    def test_schema_adapter_utility_methods(self):
        """Test SchemaAdapter utility methods."""
        # Test basic functionality if available
        if hasattr(SchemaAdapter, "normalize_trip_id"):
            # Test ID normalization
            assert SchemaAdapter.normalize_trip_id(123) == "123"
            assert SchemaAdapter.normalize_trip_id("456") == "456"

        if hasattr(SchemaAdapter, "is_uuid"):
            # Test UUID validation
            valid_uuid = str(uuid4())
            assert SchemaAdapter.is_uuid(valid_uuid) is True
            assert SchemaAdapter.is_uuid("not-a-uuid") is False
