"""Edge case tests for schema serialization and deserialization.

This module provides comprehensive testing for JSON serialization,
deserialization, and data persistence scenarios across all schema types,
focusing on edge cases that occur in production systems.
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from tripsage.api.schemas.auth import (
    AuthResponse,
    RegisterRequest,
    Token,
    UserResponse,
)
from tripsage_core.models.schemas_common.enums import CurrencyCode, TripStatus
from tripsage_core.models.schemas_common.financial import (
    Budget,
    Price,
    PriceBreakdown,
)
from tripsage_core.models.schemas_common.geographic import (
    Address,
    Coordinates,
    Place,
)


class TestSerializationEdgeCases:
    """Test serialization edge cases across all schema types."""

    def test_datetime_serialization_precision(self):
        """Test datetime serialization with various precision levels."""
        # Test datetime with microseconds
        precise_time = datetime(2024, 1, 15, 14, 30, 45, 123456)

        user = UserResponse(
            id=str(uuid4()),
            email="test@example.com",
            created_at=precise_time,
            updated_at=precise_time,
        )

        # Serialize to JSON
        json_data = user.model_dump_json()
        parsed = json.loads(json_data)

        # Deserialize back
        reconstructed = UserResponse.model_validate(parsed)

        # Verify microsecond precision is preserved
        assert reconstructed.created_at == precise_time
        assert reconstructed.updated_at == precise_time

    def test_decimal_precision_serialization(self):
        """Test Decimal serialization with high precision."""
        # Test with very precise decimal amounts
        precise_amount = Decimal("123.123456789012345")

        price = Price(amount=precise_amount, currency=CurrencyCode.USD)

        # Serialize and deserialize
        json_data = price.model_dump_json()
        parsed = json.loads(json_data)
        reconstructed = Price.model_validate(parsed)

        # Verify precision is maintained
        assert reconstructed.amount == precise_amount

    def test_unicode_serialization_comprehensive(self):
        """Test comprehensive Unicode handling across different schema types."""
        unicode_test_data = {
            "emoji": "🎉✨🌟💫🚀",
            "chinese": "这是一个测试",
            "arabic": "هذا اختبار",
            "cyrillic": "Это тест",
            "japanese": "これはテストです",
            "hindi": "यह एक परीक्षा है",
            "mixed": "Test🌟测试Тест",
        }

        # Test with RegisterRequest
        register = RegisterRequest(
            username="testuser123",
            email="test@example.com",
            password="SecurePass123!",
            password_confirm="SecurePass123!",
            full_name=unicode_test_data["mixed"],
        )

        json_data = register.model_dump_json()
        parsed = json.loads(json_data)
        reconstructed = RegisterRequest.model_validate(parsed)

        assert reconstructed.full_name == unicode_test_data["mixed"]

        # Test with Address
        unicode_address = Address(
            street=unicode_test_data["emoji"],
            city=unicode_test_data["chinese"],
            state=unicode_test_data["arabic"],
            country=unicode_test_data["cyrillic"],
        )

        address_json = unicode_address.model_dump_json()
        address_parsed = json.loads(address_json)
        address_reconstructed = Address.model_validate(address_parsed)

        assert address_reconstructed.street == unicode_test_data["emoji"]
        assert address_reconstructed.city == unicode_test_data["chinese"]

    def test_nested_model_serialization(self):
        """Test serialization of deeply nested models."""
        # Create complex nested structure
        coordinates = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=10.0)

        address = Address(
            street="123 Main St",
            city="New York",
            state="NY",
            country="USA",
            postal_code="10001",
        )

        place = Place(
            name="Test Location",
            coordinates=coordinates,
            address=address,
            place_id="test-place-id",
            place_type="landmark",
        )

        # Serialize nested structure
        json_data = place.model_dump_json()
        parsed = json.loads(json_data)

        # Verify nested structure in JSON
        assert parsed["coordinates"]["latitude"] == 40.7128
        assert parsed["coordinates"]["altitude"] == 10.0
        assert parsed["address"]["street"] == "123 Main St"
        assert parsed["address"]["postal_code"] == "10001"

        # Deserialize and verify
        reconstructed = Place.model_validate(parsed)
        assert reconstructed.coordinates.latitude == 40.7128
        assert reconstructed.coordinates.altitude == 10.0
        assert reconstructed.address.street == "123 Main St"

    def test_null_value_handling(self):
        """Test handling of null values across different fields."""
        # Test with minimal user data (many null fields)
        minimal_user = UserResponse(
            id=str(uuid4()),
            email="test@example.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            username=None,  # Explicitly None
            full_name=None,
            preferences=None,
        )

        json_data = minimal_user.model_dump_json()
        parsed = json.loads(json_data)

        # Verify null values are properly serialized
        assert parsed["username"] is None
        assert parsed["full_name"] is None
        assert parsed["preferences"] is None

        # Verify deserialization handles nulls
        reconstructed = UserResponse.model_validate(parsed)
        assert reconstructed.username is None
        assert reconstructed.full_name is None
        assert reconstructed.preferences is None

    def test_empty_collections_serialization(self):
        """Test serialization of empty collections and dictionaries."""
        # Test with empty preferences
        user_empty_prefs = UserResponse(
            id=str(uuid4()),
            email="test@example.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            preferences={},  # Empty dict
        )

        json_data = user_empty_prefs.model_dump_json()
        parsed = json.loads(json_data)
        reconstructed = UserResponse.model_validate(parsed)

        assert reconstructed.preferences == {}

    def test_large_data_serialization(self):
        """Test serialization of large data structures."""
        # Create large preferences object
        large_preferences = {}
        for i in range(1000):
            large_preferences[f"key_{i}"] = {
                "value": f"value_{i}",
                "nested": {
                    "data": list(range(10)),
                    "metadata": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "counter": i,
                    },
                },
                "counter": i,  # Add counter at top level too
            }

        user_large_data = UserResponse(
            id=str(uuid4()),
            email="test@example.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            preferences=large_preferences,
        )

        # Test serialization doesn't fail with large data
        json_data = user_large_data.model_dump_json()
        assert len(json_data) > 50000  # Should be substantial

        # Test deserialization
        parsed = json.loads(json_data)
        reconstructed = UserResponse.model_validate(parsed)

        assert len(reconstructed.preferences) == 1000
        assert reconstructed.preferences["key_999"]["counter"] == 999

    def test_special_float_values_serialization(self):
        """Test serialization of special float values."""
        # Note: Pydantic should handle/reject special float values
        coordinates_data = [
            (0.0, 0.0),  # Zero values
            (-0.0, 0.0),  # Negative zero
            (1e-10, 1e-10),  # Very small values
            (89.999999, 179.999999),  # Close to boundaries
        ]

        for lat, lon in coordinates_data:
            coords = Coordinates(latitude=lat, longitude=lon)
            json_data = coords.model_dump_json()
            parsed = json.loads(json_data)
            reconstructed = Coordinates.model_validate(parsed)

            assert abs(reconstructed.latitude - lat) < 1e-15
            assert abs(reconstructed.longitude - lon) < 1e-15

    def test_timezone_aware_datetime_serialization(self):
        """Test serialization of timezone-aware datetimes."""
        from datetime import timezone

        # Create timezone-aware datetime
        utc_time = datetime.now(timezone.utc)

        token = Token(
            access_token="test-token",
            refresh_token="refresh-token",
            expires_at=utc_time,
        )

        json_data = token.model_dump_json()
        parsed = json.loads(json_data)
        reconstructed = Token.model_validate(parsed)

        # Verify timezone information is preserved
        assert reconstructed.expires_at.tzinfo is not None

    def test_circular_reference_prevention(self):
        """Test that models handle potential circular references safely."""
        # This test ensures our models don't create circular references
        # that would break JSON serialization

        place1 = Place(name="Place 1")
        place2 = Place(name="Place 2")

        # Create a structure that could potentially be circular
        # but shouldn't be in our current models
        json_data1 = place1.model_dump_json()
        json_data2 = place2.model_dump_json()

        # Should not raise any recursion errors
        assert json_data1 is not None
        assert json_data2 is not None

    def test_model_inheritance_serialization(self):
        """Test serialization behavior with model inheritance."""
        # Test that base model behavior is consistent
        base_price = Price(amount=Decimal("100"), currency=CurrencyCode.USD)

        json_data = base_price.model_dump_json()
        parsed = json.loads(json_data)

        # Should contain base model fields
        assert "amount" in parsed
        assert "currency" in parsed

        reconstructed = Price.model_validate(parsed)
        assert reconstructed.amount == Decimal("100")
        assert reconstructed.currency == CurrencyCode.USD

    def test_enum_serialization_consistency(self):
        """Test that enums serialize consistently across contexts."""
        # Test enum in different contexts
        contexts = [
            {"status": TripStatus.PLANNING},
            {"currency": CurrencyCode.USD},
            {"combined": {"status": TripStatus.BOOKED, "currency": CurrencyCode.EUR}},
        ]

        for context in contexts:
            # Serialize using different methods
            json_str = json.dumps(context, default=str)

            # Should contain string values
            if "status" in context:
                assert TripStatus.PLANNING.value in json_str or TripStatus.BOOKED.value in json_str
            if "currency" in context:
                assert "USD" in json_str or "EUR" in json_str

    def test_validation_error_during_deserialization(self):
        """Test handling of validation errors during deserialization."""
        # Create invalid JSON data that should fail validation
        invalid_data_sets = [
            # Invalid email format
            {
                "id": str(uuid4()),
                "email": "invalid-email",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
            # Missing required fields
            {
                "email": "test@example.com",
                # Missing id, created_at, updated_at
            },
            # Invalid data types
            {
                "id": 123,  # Should be string
                "email": "test@example.com",
                "created_at": "not-a-date",
                "updated_at": datetime.utcnow().isoformat(),
            },
        ]

        for invalid_data in invalid_data_sets:
            with pytest.raises(ValidationError):
                UserResponse.model_validate(invalid_data)

    def test_partial_data_update_scenarios(self):
        """Test scenarios common in API updates with partial data."""
        # Start with complete user
        original_user = UserResponse(
            id=str(uuid4()),
            username="original_user",
            email="original@example.com",
            full_name="Original Name",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            preferences={"theme": "dark"},
        )

        # Simulate partial update (common in PATCH operations)
        partial_update = {
            "full_name": "Updated Name",
            "preferences": {"theme": "light", "language": "en"},
        }

        # Create updated user by merging data
        original_data = original_user.model_dump()
        original_data.update(partial_update)

        updated_user = UserResponse.model_validate(original_data)

        # Verify update worked correctly
        assert updated_user.id == original_user.id
        assert updated_user.email == original_user.email
        assert updated_user.full_name == "Updated Name"
        assert updated_user.preferences["theme"] == "light"
        assert updated_user.preferences["language"] == "en"

    @given(
        amount=st.decimals(min_value=0, max_value=999999, places=2),
        formatted_string=st.one_of(st.none(), st.text(max_size=50)),
    )
    @settings(max_examples=50, deadline=None)
    def test_price_serialization_property_based(self, amount: Decimal, formatted_string: str):
        """Test Price serialization with property-based testing."""
        try:
            price = Price(amount=amount, currency=CurrencyCode.USD, formatted=formatted_string)

            # Test serialization round-trip
            json_data = price.model_dump_json()
            parsed = json.loads(json_data)
            reconstructed = Price.model_validate(parsed)

            # Verify data integrity
            assert reconstructed.amount == price.amount
            assert reconstructed.currency == price.currency
            assert reconstructed.formatted == price.formatted

        except ValidationError:
            # Should only fail for invalid amounts
            assert amount < 0

    def test_complex_financial_serialization(self):
        """Test serialization of complex financial structures."""
        # Create complex price breakdown
        base = Price(amount=Decimal("100.00"), currency=CurrencyCode.USD)
        tax = Price(amount=Decimal("8.50"), currency=CurrencyCode.USD)
        fee = Price(amount=Decimal("5.99"), currency=CurrencyCode.USD)
        total = Price(amount=Decimal("114.49"), currency=CurrencyCode.USD)

        breakdown = PriceBreakdown(base_price=base, taxes=tax, fees=fee, total=total)

        # Create budget with categories
        budget_total = Price(amount=Decimal("2000.00"), currency=CurrencyCode.USD)
        categories = {
            "flights": Price(amount=Decimal("800.00"), currency=CurrencyCode.USD),
            "hotels": Price(amount=Decimal("600.00"), currency=CurrencyCode.USD),
            "food": Price(amount=Decimal("400.00"), currency=CurrencyCode.USD),
            "activities": Price(amount=Decimal("200.00"), currency=CurrencyCode.USD),
        }

        budget = Budget(total_budget=budget_total, categories=categories)

        # Test serialization of complex structures
        breakdown_json = breakdown.model_dump_json()
        budget_json = budget.model_dump_json()

        # Parse and verify structure
        breakdown_parsed = json.loads(breakdown_json)
        budget_parsed = json.loads(budget_json)

        assert breakdown_parsed["base_price"]["amount"] == "100.00"
        assert len(budget_parsed["categories"]) == 4

        # Test round-trip
        breakdown_reconstructed = PriceBreakdown.model_validate(breakdown_parsed)
        budget_reconstructed = Budget.model_validate(budget_parsed)

        assert breakdown_reconstructed.total.amount == Decimal("114.49")
        assert len(budget_reconstructed.categories) == 4

    def test_authentication_flow_serialization(self):
        """Test complete authentication flow serialization."""
        # Create complete auth response
        now = datetime.utcnow()

        user = UserResponse(
            id=str(uuid4()),
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            created_at=now,
            updated_at=now,
            preferences={
                "theme": "dark",
                "notifications": {"email": True, "push": False},
                "language": "en",
            },
        )

        token = Token(
            access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature",
            refresh_token="refresh_token_value",
            expires_at=now + timedelta(hours=1),
        )

        auth_response = AuthResponse(user=user, tokens=token)

        # Test complete flow serialization
        json_data = auth_response.model_dump_json()
        parsed = json.loads(json_data)

        # Verify structure
        assert "user" in parsed
        assert "tokens" in parsed
        assert "preferences" in parsed["user"]
        assert "notifications" in parsed["user"]["preferences"]

        # Test round-trip
        reconstructed = AuthResponse.model_validate(parsed)
        assert reconstructed.user.username == "testuser"
        assert reconstructed.tokens.access_token.startswith("eyJ0eXAi")
        assert reconstructed.user.preferences["notifications"]["email"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
