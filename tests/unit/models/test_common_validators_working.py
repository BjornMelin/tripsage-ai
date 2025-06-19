"""Working comprehensive tests for Pydantic v2 common validators."""

import pytest
from hypothesis import given, settings, strategies as st, assume
from decimal import Decimal

from tripsage_core.models.schemas_common.common_validators import (
    validate_airport_code,
    validate_rating_range,
    validate_password_strength,
    validate_latitude,
    validate_longitude,
    validate_email_lowercase,
    validate_positive_integer,
    validate_non_negative_number,
    validate_currency_code,
    validate_string_length_range,
)


class TestPasswordStrengthValidation:
    """Test password strength validation with correct error messages."""

    def test_missing_uppercase(self):
        """Test that passwords without uppercase letters are rejected."""
        with pytest.raises(ValueError, match="at least one uppercase letter"):
            validate_password_strength("lowercase123!")

    def test_missing_lowercase(self):
        """Test that passwords without lowercase letters are rejected."""
        with pytest.raises(ValueError, match="at least one lowercase letter"):
            validate_password_strength("UPPERCASE123!")

    def test_missing_digit(self):
        """Test that passwords without digits are rejected."""
        with pytest.raises(ValueError, match="at least one number"):
            validate_password_strength("Password!")

    def test_missing_special(self):
        """Test that passwords without special characters are rejected."""
        with pytest.raises(ValueError, match="at least one special character"):
            validate_password_strength("Password123")

    def test_valid_password(self):
        """Test that valid passwords are accepted."""
        valid_password = "ValidPass123!"
        result = validate_password_strength(valid_password)
        assert result == valid_password

    def test_short_password(self):
        """Test that short passwords are rejected."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            validate_password_strength("Pass1!")


class TestAirportCodeValidation:
    """Test airport code validation."""

    def test_valid_airport_codes(self):
        """Test valid IATA airport codes."""
        valid_codes = ["LAX", "JFK", "LHR", "CDG", "NRT"]
        for code in valid_codes:
            result = validate_airport_code(code)
            assert result == code
            assert len(result) == 3
            assert result.isupper()

    def test_airport_code_normalization(self):
        """Test that airport codes are properly normalized to uppercase."""
        assert validate_airport_code("lax") == "LAX"
        assert validate_airport_code("jfk") == "JFK"
        assert validate_airport_code("LaX") == "LAX"
        assert validate_airport_code(" lax ") == "LAX"  # Test whitespace stripping

    def test_invalid_airport_codes(self):
        """Test invalid airport codes."""
        with pytest.raises(ValueError, match="exactly 3 characters"):
            validate_airport_code("LA")
        
        with pytest.raises(ValueError, match="exactly 3 characters"):
            validate_airport_code("LAXX")
        
        with pytest.raises(ValueError, match="contain only letters"):
            validate_airport_code("L1X")


class TestRatingValidation:
    """Test rating validation."""

    @given(st.floats(min_value=0.0, max_value=5.0))
    def test_valid_ratings(self, rating: float):
        """Test that valid ratings are accepted."""
        result = validate_rating_range(rating)
        assert result == rating
        assert 0.0 <= result <= 5.0

    @given(st.floats().filter(lambda x: x < 0.0 or x > 5.0))
    def test_invalid_ratings(self, rating: float):
        """Test that out-of-range ratings are rejected."""
        with pytest.raises(ValueError, match="must be between 0.0 and 5.0"):
            validate_rating_range(rating)

    def test_rating_none_handling(self):
        """Test that None ratings are handled correctly."""
        assert validate_rating_range(None) is None


class TestCoordinateValidation:
    """Test geographic coordinate validation."""

    @given(st.floats(min_value=-90.0, max_value=90.0))
    def test_valid_latitude(self, lat: float):
        """Test valid latitude values."""
        result = validate_latitude(lat)
        assert result == lat

    @given(st.floats(min_value=-180.0, max_value=180.0))
    def test_valid_longitude(self, lng: float):
        """Test valid longitude values."""
        result = validate_longitude(lng)
        assert result == lng

    @given(st.floats().filter(lambda x: x < -90.0 or x > 90.0))
    def test_invalid_latitude(self, lat: float):
        """Test invalid latitude values."""
        with pytest.raises(ValueError, match="must be between -90.0 and 90.0"):
            validate_latitude(lat)

    @given(st.floats().filter(lambda x: x < -180.0 or x > 180.0))
    def test_invalid_longitude(self, lng: float):
        """Test invalid longitude values."""
        with pytest.raises(ValueError, match="must be between -180.0 and 180.0"):
            validate_longitude(lng)


class TestEmailValidation:
    """Test email validation."""

    def test_email_normalization(self):
        """Test that emails are normalized to lowercase."""
        test_cases = [
            ("TEST@EXAMPLE.COM", "test@example.com"),
            ("User@Domain.ORG", "user@domain.org"),
            ("MixedCase@Test.Net", "mixedcase@test.net"),
        ]
        
        for input_email, expected in test_cases:
            result = validate_email_lowercase(input_email)
            assert result == expected

    def test_email_none_handling(self):
        """Test that None emails are handled correctly."""
        assert validate_email_lowercase(None) is None


class TestPositiveIntegerValidation:
    """Test positive integer validation."""

    @given(st.integers(min_value=1))
    def test_valid_positive_integers(self, value: int):
        """Test valid positive integers."""
        result = validate_positive_integer(value)
        assert result == value
        assert result > 0

    @given(st.integers(max_value=0))
    def test_invalid_positive_integers(self, value: int):
        """Test invalid positive integers."""
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive_integer(value)

    def test_positive_integer_none_handling(self):
        """Test that None values are handled correctly."""
        assert validate_positive_integer(None) is None


class TestNonNegativeNumberValidation:
    """Test non-negative number validation."""

    @given(st.floats(min_value=0.0, max_value=float('inf')))
    def test_valid_non_negative_numbers(self, value: float):
        """Test valid non-negative numbers."""
        assume(not (value != value))  # Filter out NaN
        result = validate_non_negative_number(value)
        assert result == value
        assert result >= 0

    @given(st.floats(max_value=-0.001))
    def test_invalid_non_negative_numbers(self, value: float):
        """Test invalid non-negative numbers."""
        with pytest.raises(ValueError, match="must be non-negative"):
            validate_non_negative_number(value)

    def test_non_negative_number_none_handling(self):
        """Test that None values are handled correctly."""
        assert validate_non_negative_number(None) is None


class TestCurrencyCodeValidation:
    """Test currency code validation."""

    def test_valid_currency_codes(self):
        """Test valid ISO currency codes."""
        valid_codes = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]
        for code in valid_codes:
            result = validate_currency_code(code)
            assert result == code
            assert len(result) == 3
            assert result.isupper()

    def test_currency_code_normalization(self):
        """Test that currency codes are normalized to uppercase."""
        assert validate_currency_code("usd") == "USD"
        assert validate_currency_code("eur") == "EUR"
        assert validate_currency_code("GbP") == "GBP"

    def test_invalid_currency_codes(self):
        """Test invalid currency codes."""
        with pytest.raises(ValueError, match="exactly 3 characters"):
            validate_currency_code("US")
        
        with pytest.raises(ValueError, match="exactly 3 characters"):
            validate_currency_code("USDX")
        
        with pytest.raises(ValueError, match="contain only letters"):
            validate_currency_code("U1D")


class TestStringLengthValidation:
    """Test string length validation."""

    def test_string_length_validator_creation(self):
        """Test creating string length validators."""
        validator = validate_string_length_range(5, 10)
        assert callable(validator)

    def test_valid_string_lengths(self):
        """Test strings within valid length ranges."""
        validator = validate_string_length_range(3, 10)
        
        test_strings = ["abc", "hello", "test123", "1234567890"]
        for test_str in test_strings:
            result = validator(test_str)
            assert result == test_str

    def test_string_too_short(self):
        """Test strings that are too short."""
        validator = validate_string_length_range(5, 10)
        
        with pytest.raises(ValueError, match="at least 5 characters"):
            validator("ab")

    def test_string_too_long(self):
        """Test strings that are too long."""
        validator = validate_string_length_range(5, 10)
        
        with pytest.raises(ValueError, match="no more than 10 characters"):
            validator("this_is_too_long")

    def test_none_handling(self):
        """Test that None values are handled correctly."""
        validator = validate_string_length_range(5, 10)
        assert validator(None) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])