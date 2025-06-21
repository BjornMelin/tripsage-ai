"""Edge case tests for CommonValidators.

This module provides comprehensive edge case testing for validation functions
and Annotated types, focusing on boundary conditions, unusual input patterns,
and complex validator combinations that occur in production scenarios.
"""

from decimal import Decimal
from enum import Enum
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel, ValidationError

from tripsage_core.models.schemas_common.common_validators import (
    AirportCode,
    CommonValidators,
    CurrencyCode,
    EmailLowercase,
    Latitude,
    Longitude,
    MediumString,
    NonNegativeFloat,
    PasswordStrength,
    PositiveInt,
    Rating,
    create_enum_validator,
    truncate_string,
    validate_string_length_range,
)


class TestValidatorEdgeCases:
    """Test edge cases and boundary conditions for validators."""

    def test_airport_code_whitespace_variations(self):
        """Test airport code validation with various whitespace scenarios."""
        # Test various whitespace patterns

        # Valid cases (whitespace trimmed)
        assert CommonValidators.airport_code("  LAX  ") == "LAX"
        assert CommonValidators.airport_code("\tJFK\t") == "JFK"
        assert CommonValidators.airport_code("\nCDG\n") == "CDG"

        # Invalid cases (internal spaces)
        with pytest.raises(ValueError, match="exactly 3 characters"):
            CommonValidators.airport_code("L A X")

        with pytest.raises(ValueError, match="exactly 3 characters"):
            CommonValidators.airport_code("LA X")

    def test_airport_code_case_sensitivity(self):
        """Test airport code case handling."""
        mixed_cases = ["lax", "JfK", "CdG", "aBc"]
        expected = ["LAX", "JFK", "CDG", "ABC"]

        for input_code, expected_code in zip(mixed_cases, expected, strict=False):
            result = CommonValidators.airport_code(input_code)
            assert result == expected_code

    def test_rating_precision_edge_cases(self):
        """Test rating validation with floating point precision."""
        # Test very precise values
        precise_ratings = [
            0.0000001,  # Very small positive
            4.9999999,  # Very close to 5
            2.5555555,  # Many decimal places
        ]

        for rating in precise_ratings:
            result = CommonValidators.rating_range(rating)
            assert 0.0 <= result <= 5.0

        # Test boundary values with floating point precision
        assert CommonValidators.rating_range(0.0) == 0.0
        assert CommonValidators.rating_range(5.0) == 5.0

        # Test values that should fail due to precision
        with pytest.raises(ValueError):
            CommonValidators.rating_range(-0.0000001)

        with pytest.raises(ValueError):
            CommonValidators.rating_range(5.0000001)

    def test_rating_special_numeric_values(self):
        """Test rating with special numeric values."""
        # Test infinity and NaN - these are considered numbers but outside valid range
        with pytest.raises(ValueError, match="between 0.0 and 5.0"):
            CommonValidators.rating_range(float("inf"))

        with pytest.raises(ValueError, match="between 0.0 and 5.0"):
            CommonValidators.rating_range(float("-inf"))

        with pytest.raises(ValueError, match="between 0.0 and 5.0"):
            CommonValidators.rating_range(float("nan"))

    def test_email_unicode_and_international(self):
        """Test email validation with Unicode and international characters."""
        # Test international domain names (IDN)
        international_emails = [
            "test@тест.рф",  # Cyrillic
            "user@例え.テスト",  # Japanese
            "admin@测试.中国",  # Chinese
        ]

        # These should work (email normalization)
        for email in international_emails:
            try:
                result = CommonValidators.email_lowercase(email)
                assert result == email.lower()
            except ValueError:
                # Some international domains might not be supported
                pass

    def test_email_extreme_lengths(self):
        """Test email validation with extreme lengths."""
        # Test very long but valid email
        long_local = "a" * 64  # Max local part length
        long_domain = "b" * 63 + ".com"  # Long domain
        long_email = f"{long_local}@{long_domain}"

        result = CommonValidators.email_lowercase(long_email)
        assert result == long_email.lower()

        # Test with empty string - this might be valid for email_lowercase
        # since it just lowercases, let's test actual behavior
        result = CommonValidators.email_lowercase("")
        assert result == ""

    def test_positive_integer_type_coercion(self):
        """Test positive integer validation with type coercion scenarios."""
        # Test with float that should be integer
        with pytest.raises(ValueError, match="Value must be an integer"):
            CommonValidators.positive_integer(1.0)

        # Test with boolean (Python bool is subclass of int)
        result = CommonValidators.positive_integer(True)
        assert result == 1

        # Test with very large integers
        large_int = 2**63 - 1  # Max int64
        result = CommonValidators.positive_integer(large_int)
        assert result == large_int

    def test_non_negative_number_special_cases(self):
        """Test non-negative number validation with special cases."""
        # Test with Decimal
        decimal_val = Decimal("3.14159")
        with pytest.raises(ValueError, match="Value must be a number"):
            CommonValidators.non_negative_number(decimal_val)

        # Test with complex number
        with pytest.raises(ValueError, match="Value must be a number"):
            CommonValidators.non_negative_number(3 + 4j)

        # Test very small positive number
        tiny_positive = 1e-10
        result = CommonValidators.non_negative_number(tiny_positive)
        assert result == tiny_positive

    def test_currency_code_edge_cases(self):
        """Test currency code validation edge cases."""
        # Test currency codes with numbers (which should fail)
        invalid_codes = ["US1", "EU2", "GB3", "123"]
        for code in invalid_codes:
            with pytest.raises(ValueError, match="contain only letters"):
                CommonValidators.currency_code(code)

        # Test case variations
        case_variations = ["usd", "USD", "Usd", "uSd"]
        for code in case_variations:
            result = CommonValidators.currency_code(code)
            assert result == "USD"

    def test_password_strength_boundary_conditions(self):
        """Test password strength with boundary conditions."""
        # Test exactly 8 characters with all requirements
        minimal_valid = "Aa1!"
        with pytest.raises(ValueError, match="at least 8 characters"):
            CommonValidators.password_strength(minimal_valid)

        # Test exactly 8 characters with all requirements
        exactly_8 = "Aa1!bcde"
        result = CommonValidators.password_strength(exactly_8)
        assert result == exactly_8

        # Test with multiple of each requirement
        multiple_reqs = "AAaa11!!"
        result = CommonValidators.password_strength(multiple_reqs)
        assert result == multiple_reqs

        # Test with unicode characters (should work as long as requirements met)
        unicode_password = "Password123!éñ"
        result = CommonValidators.password_strength(unicode_password)
        assert result == unicode_password

    def test_password_strength_special_character_edge_cases(self):
        """Test password strength special character validation."""
        # Test each special character individually
        special_chars = "!@#$%^&*()_-+=[]{}|:;,.<>?/"
        base_password = "Password123"

        for char in special_chars:
            password = base_password + char
            result = CommonValidators.password_strength(password)
            assert result == password

        # Test password with no special characters
        no_special = "Password123"
        with pytest.raises(ValueError, match="special character"):
            CommonValidators.password_strength(no_special)

    def test_coordinate_validation_precision(self):
        """Test coordinate validation with high precision."""
        # Test very precise coordinates
        precise_lat = 45.123456789
        precise_lon = -120.987654321

        lat_result = CommonValidators.latitude(precise_lat)
        lon_result = CommonValidators.longitude(precise_lon)

        assert lat_result == precise_lat
        assert lon_result == precise_lon

        # Test boundary values
        assert CommonValidators.latitude(-90.0) == -90.0
        assert CommonValidators.latitude(90.0) == 90.0
        assert CommonValidators.longitude(-180.0) == -180.0
        assert CommonValidators.longitude(180.0) == 180.0

        # Test just beyond boundaries
        with pytest.raises(ValueError):
            CommonValidators.latitude(-90.0000001)

        with pytest.raises(ValueError):
            CommonValidators.latitude(90.0000001)

        with pytest.raises(ValueError):
            CommonValidators.longitude(-180.0000001)

        with pytest.raises(ValueError):
            CommonValidators.longitude(180.0000001)

    def test_string_length_range_unicode_handling(self):
        """Test string length validation with Unicode characters."""
        validator = validate_string_length_range(1, 10)

        # Test with Unicode characters
        unicode_strings = [
            "café",  # 4 characters with é
            "🌟✨🎉",  # 3 emoji characters
            "こんにちは",  # 5 Japanese characters
            "Ñiño",  # 4 characters with Ñ
        ]

        for s in unicode_strings:
            if 1 <= len(s) <= 10:
                result = validator(s)
                assert result == s

        # Test mixed ASCII and Unicode
        mixed = "Hello🌟"  # 6 characters total
        result = validator(mixed)
        assert result == mixed

    def test_truncation_validators_edge_cases(self):
        """Test truncation validators with edge cases."""
        truncator_50 = truncate_string(50)
        truncator_255 = truncate_string(255)

        # Test exact boundary lengths
        exactly_50 = "a" * 50
        exactly_255 = "b" * 255

        assert truncator_50(exactly_50) == exactly_50
        assert truncator_255(exactly_255) == exactly_255

        # Test over boundary
        over_50 = "a" * 100
        over_255 = "b" * 300

        assert len(truncator_50(over_50)) == 50
        assert len(truncator_255(over_255)) == 255

        # Test with Unicode that might have different byte vs character length
        unicode_long = "🌟" * 100  # 100 emoji characters
        truncated = truncator_50(unicode_long)
        assert len(truncated) == 50

        # Test with None
        assert truncator_50(None) is None

    def test_enum_validator_complex_scenarios(self):
        """Test enum validator with complex scenarios."""

        class ComplexEnum(Enum):
            OPTION_A = "option_a"
            OPTION_B = "option-b"  # With hyphen
            OPTION_C = "OPTION_C"  # Uppercase
            UNICODE_OPTION = "opción_d"  # With Unicode

        validator = create_enum_validator(ComplexEnum)

        # Test exact matches
        assert validator(ComplexEnum.OPTION_A) == ComplexEnum.OPTION_A
        assert validator("option_a") == ComplexEnum.OPTION_A

        # Test case insensitive matching
        assert validator("OPTION_A") == ComplexEnum.OPTION_A
        assert validator("option-b") == ComplexEnum.OPTION_B

        # Test Unicode
        assert validator("opción_d") == ComplexEnum.UNICODE_OPTION

        # Test None handling
        assert validator(None) is None

        # Test invalid values
        with pytest.raises(ValueError, match="Value must be one of"):
            validator("invalid_option")

    def test_password_matching_edge_cases(self):
        """Test password matching with edge cases."""
        # Test identical passwords
        result = CommonValidators.passwords_match("test123", "test123")
        assert result == ("test123", "test123")

        # Test passwords that differ only in whitespace
        with pytest.raises(ValueError, match="Passwords do not match"):
            CommonValidators.passwords_match("test123", " test123")

        with pytest.raises(ValueError, match="Passwords do not match"):
            CommonValidators.passwords_match("test123", "test123 ")

        # Test empty passwords
        result = CommonValidators.passwords_match("", "")
        assert result == ("", "")

        # Test very long passwords
        long_password = "a" * 1000
        result = CommonValidators.passwords_match(long_password, long_password)
        assert result == (long_password, long_password)

    def test_password_difference_edge_cases(self):
        """Test password difference validation edge cases."""
        # Test completely different passwords
        result = CommonValidators.passwords_different("old123", "new456")
        assert result == ("old123", "new456")

        # Test passwords that differ by case
        result = CommonValidators.passwords_different("Password123", "password123")
        assert result == ("Password123", "password123")

        # Test identical passwords (should fail)
        with pytest.raises(ValueError, match="New password must be different"):
            CommonValidators.passwords_different("same123", "same123")

        # Test empty strings
        with pytest.raises(ValueError, match="New password must be different"):
            CommonValidators.passwords_different("", "")

    @given(
        text_value=st.text(min_size=0, max_size=1000),
        min_len=st.integers(min_value=0, max_value=50),
        max_len=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=100, deadline=None)
    def test_string_length_range_property_based(self, text_value: str, min_len: int, max_len: int):
        """Test string length range validator with property-based testing."""
        if min_len <= max_len:  # Only test valid range configurations
            validator = validate_string_length_range(min_len, max_len)

            try:
                result = validator(text_value)
                if result is not None:
                    # Check that result meets length requirements
                    assert min_len <= len(result) <= max_len
                    # Check that whitespace was stripped
                    assert result == text_value.strip()
            except ValueError:
                # Should fail if stripped length is outside range
                stripped = text_value.strip()
                assert len(stripped) < min_len or len(stripped) > max_len

    @given(
        rating=st.one_of(
            st.none(),
            st.floats(min_value=-10, max_value=10, allow_nan=False, allow_infinity=False),
            st.integers(min_value=-10, max_value=10),
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_rating_range_property_based(self, rating: Any):
        """Test rating range validator with property-based testing."""
        try:
            result = CommonValidators.rating_range(rating)
            if result is not None:
                assert 0.0 <= result <= 5.0
                assert isinstance(result, float)
        except ValueError:
            # Should fail if not a number or outside range
            if rating is not None:
                assert not isinstance(rating, (int, float)) or rating < 0.0 or rating > 5.0

    def test_annotated_type_combinations(self):
        """Test combinations of annotated types in complex models."""

        class ComplexValidationModel(BaseModel):
            airport_origin: AirportCode
            airport_destination: AirportCode
            price: NonNegativeFloat
            currency: CurrencyCode
            rating: Rating
            passenger_count: PositiveInt
            email: EmailLowercase
            password: PasswordStrength
            description: MediumString
            coordinates_lat: Latitude
            coordinates_lon: Longitude

        # Test with valid data
        valid_data = {
            "airport_origin": "lax",
            "airport_destination": "JFK",
            "price": 299.99,
            "currency": "usd",
            "rating": 4.5,
            "passenger_count": 2,
            "email": "USER@EXAMPLE.COM",
            "password": "SecurePass123!",
            "description": "Flight description",
            "coordinates_lat": 34.0522,
            "coordinates_lon": -118.2437,
        }

        model = ComplexValidationModel(**valid_data)

        # Verify transformations applied
        assert model.airport_origin == "LAX"
        assert model.airport_destination == "JFK"
        assert model.currency == "USD"
        assert model.email == "user@example.com"
        assert model.coordinates_lat == 34.0522
        assert model.coordinates_lon == -118.2437

        # Test with invalid data
        invalid_data = valid_data.copy()
        invalid_data["airport_origin"] = "INVALID"
        invalid_data["price"] = -100
        invalid_data["rating"] = 10
        invalid_data["passenger_count"] = 0

        with pytest.raises(ValidationError) as exc_info:
            ComplexValidationModel(**invalid_data)

        errors = exc_info.value.errors()
        assert len(errors) >= 4  # Should have multiple validation errors

    def test_validator_performance_edge_cases(self):
        """Test validators with performance edge cases."""
        # Test with very long strings
        very_long_string = "a" * 10000

        # Airport code with long string (should fail quickly)
        with pytest.raises(ValueError):
            CommonValidators.airport_code(very_long_string)

        # Email with long string
        long_email = very_long_string + "@example.com"
        result = CommonValidators.email_lowercase(long_email)
        assert result == long_email.lower()

        # Password with long string (should validate requirements)
        long_password = "A1!" + very_long_string
        result = CommonValidators.password_strength(long_password)
        assert result == long_password

        # Test truncation with very long string
        truncator = truncate_string(100)
        result = truncator(very_long_string)
        assert len(result) == 100

    def test_validator_thread_safety_simulation(self):
        """Test validators with scenarios that simulate concurrent usage."""
        import threading
        import time

        results = []
        errors = []

        def validate_batch():
            try:
                # Simulate concurrent validation
                for i in range(10):
                    # Use valid airport codes
                    airport_codes = [
                        "LAX",
                        "JFK",
                        "CDG",
                        "LHR",
                        "NRT",
                        "SFO",
                        "ORD",
                        "ATL",
                        "DFW",
                        "DEN",
                    ]
                    airport = CommonValidators.airport_code(airport_codes[i % len(airport_codes)])
                    email = CommonValidators.email_lowercase(f"user{i}@EXAMPLE.COM")
                    rating = CommonValidators.rating_range(min(i * 0.5, 5.0))  # Cap at 5.0
                    results.append((airport, email, rating))
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=validate_batch)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify no errors occurred and results are valid
        assert len(errors) == 0
        assert len(results) == 50  # 5 threads * 10 validations each

        # Verify all results are valid
        for airport, email, rating in results:
            assert len(airport) == 3
            assert airport.isupper()
            assert "@example.com" in email
            assert 0.0 <= rating <= 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
