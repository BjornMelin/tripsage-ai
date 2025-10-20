"""Fixed comprehensive tests for Pydantic v2 common validators."""

import pytest
from hypothesis import given, strategies as st

from tripsage_core.models.schemas_common.common_validators import (
    validate_airport_code,
    validate_latitude,
    validate_longitude,
    validate_password_strength,
    validate_rating_range,
)


class TestPasswordStrengthValidation:
    """Test password strength validation with fixed error messages."""

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
