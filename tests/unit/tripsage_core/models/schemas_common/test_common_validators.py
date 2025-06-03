"""
Comprehensive tests for CommonValidators.

This module tests all validation functions and Annotated types to ensure
consistent behavior across the application.
"""

import pytest
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ValidationError

from tripsage_core.models.schemas_common.common_validators import (
    AirportCode,
    CommonValidators,
    CurrencyCode,
    EmailLowercase,
    Latitude,
    Longitude,
    NonNegativeFloat,
    PasswordStrength,
    PositiveInt,
    Rating,
    ShortString,
    MediumString,
    TruncatedShortString,
    TruncatedMediumString,
)


class TestAirportCodeValidator:
    """Test airport code validation."""

    def test_valid_airport_codes(self):
        """Test valid airport codes."""
        assert CommonValidators.airport_code("LAX") == "LAX"
        assert CommonValidators.airport_code("jfk") == "JFK"
        assert CommonValidators.airport_code(" CDG ") == "CDG"

    def test_invalid_airport_codes(self):
        """Test invalid airport codes."""
        with pytest.raises(ValueError, match="Airport code must be a string"):
            CommonValidators.airport_code(123)

        with pytest.raises(ValueError, match="exactly 3 characters"):
            CommonValidators.airport_code("LAXE")
        
        with pytest.raises(ValueError, match="exactly 3 characters"):
            CommonValidators.airport_code("LA")

        with pytest.raises(ValueError, match="contain only letters"):
            CommonValidators.airport_code("LA1")

    def test_airport_code_annotated_type(self):
        """Test AirportCode Annotated type."""
        class TestModel(BaseModel):
            code: AirportCode

        # Valid cases
        model = TestModel(code="LAX")
        assert model.code == "LAX"

        model = TestModel(code="jfk")
        assert model.code == "JFK"

        # Invalid cases
        with pytest.raises(ValidationError):
            TestModel(code="INVALID")


class TestRatingValidator:
    """Test rating validation."""

    def test_valid_ratings(self):
        """Test valid rating values."""
        assert CommonValidators.rating_range(None) is None
        assert CommonValidators.rating_range(0.0) == 0.0
        assert CommonValidators.rating_range(3.5) == 3.5
        assert CommonValidators.rating_range(5.0) == 5.0
        assert CommonValidators.rating_range(4) == 4.0

    def test_invalid_ratings(self):
        """Test invalid rating values."""
        with pytest.raises(ValueError, match="Rating must be a number"):
            CommonValidators.rating_range("invalid")

        with pytest.raises(ValueError, match="between 0.0 and 5.0"):
            CommonValidators.rating_range(-1.0)

        with pytest.raises(ValueError, match="between 0.0 and 5.0"):
            CommonValidators.rating_range(6.0)

    def test_rating_annotated_type(self):
        """Test Rating Annotated type."""
        class TestModel(BaseModel):
            rating: Rating

        # Valid cases
        model = TestModel(rating=4.5)
        assert model.rating == 4.5

        model = TestModel(rating=None)
        assert model.rating is None

        # Invalid cases
        with pytest.raises(ValidationError):
            TestModel(rating=10.0)


class TestEmailValidator:
    """Test email validation."""

    def test_valid_emails(self):
        """Test valid email addresses."""
        assert CommonValidators.email_lowercase(None) is None
        assert CommonValidators.email_lowercase("TEST@EXAMPLE.COM") == "test@example.com"
        assert CommonValidators.email_lowercase(" User@Domain.org ") == "user@domain.org"

    def test_invalid_emails(self):
        """Test invalid email addresses."""
        with pytest.raises(ValueError, match="Email must be a string"):
            CommonValidators.email_lowercase(123)

    def test_email_annotated_type(self):
        """Test EmailLowercase Annotated type."""
        class TestModel(BaseModel):
            email: EmailLowercase

        # Valid cases
        model = TestModel(email="TEST@EXAMPLE.COM")
        assert model.email == "test@example.com"

        model = TestModel(email=None)
        assert model.email is None


class TestPositiveIntValidator:
    """Test positive integer validation."""

    def test_valid_positive_integers(self):
        """Test valid positive integers."""
        assert CommonValidators.positive_integer(None) is None
        assert CommonValidators.positive_integer(1) == 1
        assert CommonValidators.positive_integer(100) == 100

    def test_invalid_positive_integers(self):
        """Test invalid positive integers."""
        with pytest.raises(ValueError, match="Value must be an integer"):
            CommonValidators.positive_integer(1.5)

        with pytest.raises(ValueError, match="Value must be positive"):
            CommonValidators.positive_integer(0)

        with pytest.raises(ValueError, match="Value must be positive"):
            CommonValidators.positive_integer(-1)

    def test_positive_int_annotated_type(self):
        """Test PositiveInt Annotated type."""
        class TestModel(BaseModel):
            count: PositiveInt

        # Valid cases
        model = TestModel(count=5)
        assert model.count == 5

        model = TestModel(count=None)
        assert model.count is None

        # Invalid cases
        with pytest.raises(ValidationError):
            TestModel(count=0)


class TestNonNegativeNumberValidator:
    """Test non-negative number validation."""

    def test_valid_non_negative_numbers(self):
        """Test valid non-negative numbers."""
        assert CommonValidators.non_negative_number(None) is None
        assert CommonValidators.non_negative_number(0) == 0.0
        assert CommonValidators.non_negative_number(5.5) == 5.5
        assert CommonValidators.non_negative_number(100) == 100.0

    def test_invalid_non_negative_numbers(self):
        """Test invalid non-negative numbers."""
        with pytest.raises(ValueError, match="Value must be a number"):
            CommonValidators.non_negative_number("invalid")

        with pytest.raises(ValueError, match="Value must be non-negative"):
            CommonValidators.non_negative_number(-1.0)

    def test_non_negative_float_annotated_type(self):
        """Test NonNegativeFloat Annotated type."""
        class TestModel(BaseModel):
            amount: NonNegativeFloat

        # Valid cases
        model = TestModel(amount=10.5)
        assert model.amount == 10.5

        model = TestModel(amount=None)
        assert model.amount is None

        # Invalid cases
        with pytest.raises(ValidationError):
            TestModel(amount=-5.0)


class TestCurrencyCodeValidator:
    """Test currency code validation."""

    def test_valid_currency_codes(self):
        """Test valid currency codes."""
        assert CommonValidators.currency_code("USD") == "USD"
        assert CommonValidators.currency_code("eur") == "EUR"
        assert CommonValidators.currency_code(" GBP ") == "GBP"

    def test_invalid_currency_codes(self):
        """Test invalid currency codes."""
        with pytest.raises(ValueError, match="Currency code must be a string"):
            CommonValidators.currency_code(123)

        with pytest.raises(ValueError, match="exactly 3 characters"):
            CommonValidators.currency_code("DOLLAR")

        with pytest.raises(ValueError, match="contain only letters"):
            CommonValidators.currency_code("US1")

    def test_currency_code_annotated_type(self):
        """Test CurrencyCode Annotated type."""
        class TestModel(BaseModel):
            currency: CurrencyCode

        # Valid cases
        model = TestModel(currency="usd")
        assert model.currency == "USD"

        # Invalid cases
        with pytest.raises(ValidationError):
            TestModel(currency="DOLLAR")


class TestPasswordStrengthValidator:
    """Test password strength validation."""

    def test_valid_passwords(self):
        """Test valid strong passwords."""
        valid_password = "StrongP@ss123"
        assert CommonValidators.password_strength(valid_password) == valid_password

    def test_invalid_passwords(self):
        """Test invalid passwords."""
        with pytest.raises(ValueError, match="Password must be a string"):
            CommonValidators.password_strength(123)

        with pytest.raises(ValueError, match="at least 8 characters"):
            CommonValidators.password_strength("Sh0rt!")

        with pytest.raises(ValueError, match="uppercase letter"):
            CommonValidators.password_strength("lowercase123!")

        with pytest.raises(ValueError, match="lowercase letter"):
            CommonValidators.password_strength("UPPERCASE123!")

        with pytest.raises(ValueError, match="one number"):
            CommonValidators.password_strength("NoNumbers!")

        with pytest.raises(ValueError, match="special character"):
            CommonValidators.password_strength("NoSpecial123")

    def test_password_strength_annotated_type(self):
        """Test PasswordStrength Annotated type."""
        class TestModel(BaseModel):
            password: PasswordStrength

        # Valid cases
        model = TestModel(password="ValidP@ss123")
        assert model.password == "ValidP@ss123"

        # Invalid cases
        with pytest.raises(ValidationError):
            TestModel(password="weak")


class TestCoordinateValidator:
    """Test coordinate validation."""

    def test_valid_latitude(self):
        """Test valid latitude values."""
        assert CommonValidators.latitude(None) is None
        assert CommonValidators.latitude(0.0) == 0.0
        assert CommonValidators.latitude(45.5) == 45.5
        assert CommonValidators.latitude(-90.0) == -90.0
        assert CommonValidators.latitude(90.0) == 90.0

    def test_invalid_latitude(self):
        """Test invalid latitude values."""
        with pytest.raises(ValueError, match="Latitude must be a number"):
            CommonValidators.latitude("invalid")

        with pytest.raises(ValueError, match="between -90.0 and 90.0"):
            CommonValidators.latitude(91.0)

        with pytest.raises(ValueError, match="between -90.0 and 90.0"):
            CommonValidators.latitude(-91.0)

    def test_valid_longitude(self):
        """Test valid longitude values."""
        assert CommonValidators.longitude(None) is None
        assert CommonValidators.longitude(0.0) == 0.0
        assert CommonValidators.longitude(45.5) == 45.5
        assert CommonValidators.longitude(-180.0) == -180.0
        assert CommonValidators.longitude(180.0) == 180.0

    def test_invalid_longitude(self):
        """Test invalid longitude values."""
        with pytest.raises(ValueError, match="Longitude must be a number"):
            CommonValidators.longitude("invalid")

        with pytest.raises(ValueError, match="between -180.0 and 180.0"):
            CommonValidators.longitude(181.0)

        with pytest.raises(ValueError, match="between -180.0 and 180.0"):
            CommonValidators.longitude(-181.0)

    def test_coordinate_annotated_types(self):
        """Test Latitude and Longitude Annotated types."""
        class TestModel(BaseModel):
            lat: Latitude
            lon: Longitude

        # Valid cases
        model = TestModel(lat=45.5, lon=120.0)
        assert model.lat == 45.5
        assert model.lon == 120.0

        model = TestModel(lat=None, lon=None)
        assert model.lat is None
        assert model.lon is None

        # Invalid cases - latitude
        with pytest.raises(ValidationError):
            TestModel(lat=91.0, lon=120.0)

        # Invalid cases - longitude
        with pytest.raises(ValidationError):
            TestModel(lat=45.5, lon=181.0)


class TestStringLengthValidators:
    """Test string length validation."""

    def test_string_length_range_factory(self):
        """Test string length range validator factory."""
        validator = CommonValidators.string_length_range(5, 10)
        
        # Valid cases
        assert validator(None) is None
        assert validator("hello") == "hello"
        assert validator("  hello  ") == "hello"
        assert validator("1234567890") == "1234567890"

        # Invalid cases
        with pytest.raises(ValueError, match="at least 5 characters"):
            validator("hi")

        with pytest.raises(ValueError, match="no more than 10 characters"):
            validator("this is too long")

    def test_predefined_string_types(self):
        """Test predefined string length types."""
        class TestModel(BaseModel):
            short: ShortString
            medium: MediumString

        # Valid cases
        model = TestModel(short="hello", medium="medium length string")
        assert model.short == "hello"
        assert model.medium == "medium length string"

        # Test None values
        model = TestModel(short=None, medium=None)
        assert model.short is None
        assert model.medium is None


class TestTruncationValidators:
    """Test truncation validators."""

    def test_truncated_strings(self):
        """Test truncated string types."""
        class TestModel(BaseModel):
            short: TruncatedShortString
            medium: TruncatedMediumString

        # Valid cases - within limits
        model = TestModel(short="hello", medium="medium string")
        assert model.short == "hello"
        assert model.medium == "medium string"

        # Test truncation
        long_string = "a" * 300  # Longer than both limits
        model = TestModel(short=long_string, medium=long_string)
        assert len(model.short) == 50
        assert len(model.medium) == 255


class TestEnumValidator:
    """Test enum validator factory."""

    def test_enum_validator_factory(self):
        """Test enum validator creation."""
        class TestEnum(Enum):
            OPTION_A = "a"
            OPTION_B = "b"

        validator = CommonValidators.enum_validator(TestEnum)

        # Valid cases
        assert validator(None) is None
        assert validator(TestEnum.OPTION_A) == TestEnum.OPTION_A
        assert validator("a") == TestEnum.OPTION_A
        assert validator("A") == TestEnum.OPTION_A

        # Invalid cases
        with pytest.raises(ValueError, match="Value must be one of"):
            validator("invalid")


class TestUtilityMethods:
    """Test utility methods in CommonValidators."""

    def test_passwords_match(self):
        """Test password matching validation."""
        # Valid case
        result = CommonValidators.passwords_match("password123", "password123")
        assert result == ("password123", "password123")

        # Invalid case
        with pytest.raises(ValueError, match="Passwords do not match"):
            CommonValidators.passwords_match("password123", "different")

    def test_passwords_different(self):
        """Test password difference validation."""
        # Valid case
        result = CommonValidators.passwords_different("old123", "new456")
        assert result == ("old123", "new456")

        # Invalid case
        with pytest.raises(ValueError, match="New password must be different"):
            CommonValidators.passwords_different("same123", "same123")


class TestIntegrationWithPydantic:
    """Test integration with Pydantic models."""

    def test_complex_model_validation(self):
        """Test comprehensive model with multiple validators."""
        class FlightModel(BaseModel):
            origin: AirportCode
            destination: AirportCode
            price: NonNegativeFloat
            currency: CurrencyCode
            rating: Rating
            duration_minutes: PositiveInt

        # Valid model
        model = FlightModel(
            origin="LAX",
            destination="jfk",
            price=299.99,
            currency="usd",
            rating=4.5,
            duration_minutes=360
        )

        assert model.origin == "LAX"
        assert model.destination == "JFK"
        assert model.price == 299.99
        assert model.currency == "USD"
        assert model.rating == 4.5
        assert model.duration_minutes == 360

        # Test validation errors
        with pytest.raises(ValidationError) as exc_info:
            FlightModel(
                origin="INVALID",  # Invalid airport code
                destination="JFK",
                price=-100,  # Negative price
                currency="DOLLAR",  # Invalid currency
                rating=10,  # Invalid rating
                duration_minutes=0  # Invalid duration
            )

        # Should have multiple validation errors
        errors = exc_info.value.errors()
        assert len(errors) >= 4  # At least 4 validation errors

    def test_backward_compatibility(self):
        """Test that old validator functions still work with deprecation warnings."""
        from tripsage_core.models.schemas_common.validators import (
            validate_password_strength,
            validate_passwords_match,
            validate_passwords_different,
        )

        # Test with warnings
        with pytest.warns(DeprecationWarning):
            result = validate_password_strength("ValidP@ss123")
            assert result == "ValidP@ss123"

        with pytest.warns(DeprecationWarning):
            result = validate_passwords_match("pass123", "pass123")
            assert result == ("pass123", "pass123")

        with pytest.warns(DeprecationWarning):
            result = validate_passwords_different("old123", "new456")
            assert result == ("old123", "new456")