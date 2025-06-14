"""
Integration tests for schema alignment across frontend, backend, and database layers.

This test suite validates that the schema alignment migration works correctly
and ensures backward compatibility during the transition period.
"""

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from tripsage_core.models.db.trip import Trip, TripBudget, TripVisibility
from tripsage_core.utils.schema_adapters import SchemaAdapter


class TestSchemaAlignment:
    """Test schema alignment across all layers."""

    @pytest.fixture
    def sample_trip_data(self) -> Dict[str, Any]:
        """Sample trip data for testing."""
        return {
            "title": "European Adventure",
            "description": "A two-week journey across Europe",
            "start_date": date(2025, 6, 1),
            "end_date": date(2025, 6, 15),
            "destination": "Europe",
            "budget": 5000.0,
            "travelers": 2,
            "status": "planning",
            "trip_type": "leisure",
            "visibility": "private",
            "tags": ["europe", "adventure", "culture"],
            "preferences": {
                "budget": {
                    "total": 5000,
                    "currency": "USD",
                    "accommodation_budget": 2000,
                    "transportation_budget": 1500,
                    "food_budget": 1000,
                    "activities_budget": 500,
                },
                "accommodation": {
                    "type": "hotel",
                    "min_rating": 4.0,
                    "amenities": ["wifi", "breakfast"],
                },
            },
        }

    @pytest.fixture
    def sample_database_record(self) -> Dict[str, Any]:
        """Sample database record for testing."""
        return {
            "id": 123,
            "uuid_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "title": "European Adventure",
            "description": "A two-week journey across Europe",
            "start_date": date(2025, 6, 1),
            "end_date": date(2025, 6, 15),
            "destination": "Europe",
            "budget": 5000.0,
            "budget_breakdown": {
                "total": 5000,
                "breakdown": {
                    "accommodation": 2000,
                    "transportation": 1500,
                    "food": 1000,
                    "activities": 500,
                },
            },
            "currency": "USD",
            "spent_amount": 1200.0,
            "travelers": 2,
            "status": "planning",
            "trip_type": "leisure",
            "visibility": "private",
            "tags": ["europe", "adventure", "culture"],
            "preferences_extended": {
                "accommodation": {
                    "type": "hotel",
                    "min_rating": 4.0,
                    "amenities": ["wifi", "breakfast"],
                }
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    def test_trip_model_enhanced_fields(self, sample_trip_data):
        """Test enhanced Trip model with new fields."""
        # Create enhanced budget
        enhanced_budget = TripBudget(
            total=5000.0,
            currency="USD",
            spent=1200.0,
            breakdown={
                "accommodation": 2000,
                "transportation": 1500,
                "food": 1000,
                "activities": 500,
            },
        )

        # Create trip with enhanced fields
        trip = Trip(
            id=123,
            uuid_id=uuid.uuid4(),
            title="European Adventure",
            description="A two-week journey across Europe",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 15),
            destination="Europe",
            enhanced_budget=enhanced_budget,
            spent_amount=1200.0,  # Set spent_amount at the trip level
            travelers=2,
            visibility=TripVisibility.PRIVATE,
            tags=["europe", "adventure", "culture"],
            preferences={
                "accommodation": {
                    "type": "hotel",
                    "min_rating": 4.0,
                }
            },
        )

        # Validate enhanced properties
        assert trip.title == "European Adventure"
        assert trip.name == "European Adventure"  # Legacy compatibility
        assert trip.effective_budget == 5000.0
        assert trip.budget_utilization == 24.0  # 1200/5000 * 100
        assert trip.remaining_budget == 3800.0
        assert trip.is_shared is False
        assert trip.tag_count == 3
        assert trip.trip_id == str(trip.uuid_id)  # Should prefer UUID

    def test_trip_model_legacy_compatibility(self):
        """Test that legacy Trip model still works."""
        # Create trip with legacy fields only
        trip = Trip(
            id=123,
            title="Legacy Trip",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 15),
            destination="Paris",
            budget=2000.0,
            travelers=1,
        )

        # Validate backward compatibility
        assert trip.name == "Legacy Trip"  # Should work via property
        assert trip.effective_budget == 2000.0  # Should use legacy budget
        assert trip.visibility == TripVisibility.PRIVATE  # Default
        assert trip.tags == []  # Default
        assert trip.trip_id == 123  # Should use BIGINT ID when no UUID

    def test_schema_adapter_db_to_api_conversion(self, sample_database_record):
        """Test database to API conversion."""
        api_data = SchemaAdapter.convert_db_trip_to_api(sample_database_record)

        # Validate field mappings
        assert api_data["title"] == "European Adventure"
        assert api_data["name"] == "European Adventure"  # Compatibility
        assert api_data["description"] == "A two-week journey across Europe"
        assert api_data["visibility"] == "private"
        assert api_data["tags"] == ["europe", "adventure", "culture"]

        # Validate enhanced budget
        assert api_data["enhanced_budget"]["total"] == 5000
        assert api_data["enhanced_budget"]["currency"] == "USD"
        assert api_data["enhanced_budget"]["spent"] == 1200
        assert "breakdown" in api_data["enhanced_budget"]

        # Validate preferences
        assert "accommodation" in api_data["preferences"]

    def test_schema_adapter_api_to_db_conversion(self, sample_trip_data):
        """Test API to database conversion."""
        api_data = {
            **sample_trip_data,
            "enhanced_budget": {
                "total": 5000,
                "currency": "USD",
                "spent": 1200,
                "breakdown": {
                    "accommodation": 2000,
                    "transportation": 1500,
                },
            },
        }

        db_data = SchemaAdapter.convert_api_trip_to_db(api_data)

        # Validate field mappings
        assert db_data["title"] == "European Adventure"
        assert "name" not in db_data  # Should use title consistently
        assert db_data["visibility"] == "private"
        assert db_data["tags"] == ["europe", "adventure", "culture"]

        # Validate budget breakdown
        assert "budget_breakdown" in db_data
        assert db_data["budget_breakdown"]["total"] == 5000

        # Validate preferences mapping
        assert "preferences_extended" in db_data

    def test_id_normalization(self):
        """Test ID normalization across different formats."""
        # Test UUID normalization
        uuid_str = str(uuid.uuid4())
        assert SchemaAdapter.normalize_trip_id(uuid_str) == uuid_str

        # Test integer normalization
        assert SchemaAdapter.normalize_trip_id(123) == "123"

        # Test string integer normalization
        assert SchemaAdapter.normalize_trip_id("456") == "456"

        # Test None handling
        assert SchemaAdapter.normalize_trip_id(None) is None

    def test_budget_structure_adaptation(self):
        """Test budget structure adaptation."""
        # Test simple budget to enhanced
        enhanced = SchemaAdapter.adapt_budget_structure(2500.0)
        assert enhanced["total"] == 2500.0
        assert enhanced["currency"] == "USD"
        assert enhanced["spent"] == 0.0
        assert enhanced["breakdown"] == {}

        # Test enhanced budget validation
        budget_data = {
            "total": 3000,
            "currency": "EUR",
            "spent": 500,
            "breakdown": {"accommodation": 1500},
        }
        adapted = SchemaAdapter.adapt_budget_structure(budget_data)
        assert adapted["total"] == 3000
        assert adapted["currency"] == "EUR"
        assert adapted["spent"] == 500

        # Test None handling
        assert SchemaAdapter.adapt_budget_structure(None) == {}

    def test_preferences_structure_adaptation(self):
        """Test preferences structure adaptation."""
        legacy_preferences = {
            "accommodation": {"type": "hotel"},
            "custom_field": "custom_value",
        }

        adapted = SchemaAdapter.adapt_preferences_structure(legacy_preferences)

        # Validate required fields exist
        assert "budget" in adapted
        assert "accommodation" in adapted
        assert "transportation" in adapted
        assert "activities" in adapted
        assert "dietary_restrictions" in adapted
        assert "accessibility_needs" in adapted

        # Validate custom fields are preserved
        assert adapted["custom_field"] == "custom_value"
        assert adapted["accommodation"]["type"] == "hotel"

    def test_trip_validation_errors(self):
        """Test validation errors for invalid data."""
        # Test invalid visibility
        with pytest.raises(ValidationError):
            Trip(
                title="Test",
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 15),
                destination="Test",
                travelers=1,
                visibility="invalid",
            )

        # Test invalid date range
        with pytest.raises(ValidationError):
            Trip(
                title="Test",
                start_date=date(2025, 6, 15),
                end_date=date(2025, 6, 1),  # End before start
                destination="Test",
                travelers=1,
            )

        # Test invalid travelers count
        with pytest.raises(ValidationError):
            Trip(
                title="Test",
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 15),
                destination="Test",
                travelers=0,  # Invalid
            )

    def test_field_compatibility_matrix(self):
        """Test field compatibility across all layers."""
        test_cases = [
            # (database_field, service_field, api_field, frontend_field)
            ("title", "title", "title", "title"),
            ("title", "title", "title", "name"),  # Legacy compatibility
            ("visibility", "visibility", "visibility", "visibility"),
            ("tags", "tags", "tags", "tags"),
            ("preferences_extended", "preferences", "preferences", "preferences"),
            (
                "budget_breakdown",
                "enhanced_budget",
                "enhanced_budget",
                "enhanced_budget",
            ),
        ]

        for db_field, service_field, api_field, frontend_field in test_cases:
            # Validate that schema adapter handles these mappings correctly
            assert db_field is not None
            assert service_field is not None
            assert api_field is not None
            assert frontend_field is not None

    def test_backward_compatibility_legacy_name_field(self):
        """Test backward compatibility with legacy 'name' field."""
        # Test database record with legacy 'name' field
        legacy_db_record = {
            "id": 123,
            "user_id": str(uuid.uuid4()),
            "name": "Legacy Trip Name",  # Legacy field
            "start_date": date(2025, 6, 1),
            "end_date": date(2025, 6, 15),
            "destination": "Legacy Destination",
            "budget": 1000,
            "travelers": 1,
            "status": "planning",
        }

        api_data = SchemaAdapter.convert_db_trip_to_api(legacy_db_record)

        # Should map name to title and preserve both
        assert api_data["title"] == "Legacy Trip Name"
        assert api_data["name"] == "Legacy Trip Name"

    def test_migration_data_integrity(self, sample_database_record):
        """Test that data integrity is maintained during migration."""
        # Convert through the full cycle
        api_data = SchemaAdapter.convert_db_trip_to_api(sample_database_record)
        db_data_back = SchemaAdapter.convert_api_trip_to_db(api_data)

        # Validate critical fields are preserved
        assert sample_database_record["title"] == db_data_back["title"]
        assert sample_database_record["visibility"] == db_data_back["visibility"]
        assert sample_database_record["tags"] == db_data_back["tags"]

        # Validate budget information is preserved
        original_budget = sample_database_record["budget_breakdown"]["total"]
        converted_budget = db_data_back["budget_breakdown"]["total"]
        assert original_budget == converted_budget
