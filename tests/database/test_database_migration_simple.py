"""Simplified database migration tests that avoid settings loading issues."""

import pytest
from tripsage.models.db.user import User
from tripsage.models.db.trip import Trip, TripStatus


class TestModelMigration:
    """Test that business models are properly migrated."""
    
    def test_user_model_validation(self):
        """Test User model validation and business logic."""
        user = User(email="test@example.com")
        assert user.email == "test@example.com"
        assert user.preferences_json is None
        
        # Test preference validation using full_preferences property
        assert user.full_preferences["theme"] == "light"  # default value
        
        # Update preferences
        user.update_preferences({"theme": "dark", "currency": "USD"})
        assert user.full_preferences["theme"] == "dark"
        
        # Test admin validation  
        user.is_admin = True
        assert user.is_admin
    
    def test_trip_model_validation(self):
        """Test Trip model validation and business logic."""
        trip = Trip(
            name="Summer Trip",
            start_date="2024-07-01",
            end_date="2024-07-15",
            destination="Paris",
            budget=1400,
            travelers=2,
            status=TripStatus.PLANNING
        )
        
        # Check basic fields
        assert trip.name == "Summer Trip"
        assert trip.status == TripStatus.PLANNING
        assert trip.budget == 1400
        assert trip.travelers == 2
    
    def test_trip_status_enum(self):
        """Test TripStatus enum values."""
        assert TripStatus.PLANNING.value == "planning"
        assert TripStatus.BOOKED.value == "booked"
        assert TripStatus.COMPLETED.value == "completed"
        assert TripStatus.CANCELED.value == "canceled"
    
    def test_trip_type_enum(self):
        """Test TripType enum values."""
        from tripsage.models.db.trip import TripType
        
        assert TripType.LEISURE.value == "leisure"
        assert TripType.BUSINESS.value == "business"
        assert TripType.FAMILY.value == "family"
        assert TripType.SOLO.value == "solo"
        assert TripType.OTHER.value == "other"


class TestMissingModels:
    """Test to document missing models."""
    
    def test_missing_flight_model(self):
        """Verify that Flight model is not in the database models."""
        import tripsage.models.db as db_models
        assert not hasattr(db_models, "Flight")
    
    def test_existing_models(self):
        """Verify that migrated models exist."""
        import tripsage.models.db as db_models
        assert hasattr(db_models, "User")
        assert hasattr(db_models, "Trip")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])