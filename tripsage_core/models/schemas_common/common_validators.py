"""
Common validators for TripSage AI using Pydantic V2 best practices.

This module provides reusable validators using the latest Pydantic V2 patterns including
Annotated types, BeforeValidator, AfterValidator, and WrapValidator for maximum
code reuse and consistency across the application.
"""

import re
from typing import Annotated, Any, Optional

from pydantic import (
    AfterValidator,
    BeforeValidator,
)


def validate_airport_code(value: str) -> str:
    """
    Validate and standardize IATA airport codes.

    Args:
        value: The airport code to validate

    Returns:
        The standardized airport code in uppercase

    Raises:
        ValueError: If the airport code is invalid
    """
    if not isinstance(value, str):
        raise ValueError("Airport code must be a string")

    value = value.strip().upper()

    if len(value) != 3:
        raise ValueError("Airport code must be exactly 3 characters (IATA code)")

    if not value.isalpha():
        raise ValueError("Airport code must contain only letters")

    return value


def validate_rating_range(value: Optional[float]) -> Optional[float]:
    """
    Validate that rating is between 0.0 and 5.0.

    Args:
        value: The rating value to validate

    Returns:
        The validated rating value

    Raises:
        ValueError: If rating is outside valid range
    """
    if value is None:
        return None

    if not isinstance(value, (int, float)):
        raise ValueError("Rating must be a number")

    if not 0.0 <= value <= 5.0:
        raise ValueError("Rating must be between 0.0 and 5.0")

    return float(value)


def validate_email_lowercase(value: Optional[str]) -> Optional[str]:
    """
    Validate and normalize email addresses to lowercase.

    Args:
        value: The email address to validate

    Returns:
        The normalized email address in lowercase
    """
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError("Email must be a string")

    return value.strip().lower()


def validate_positive_integer(value: Optional[int]) -> Optional[int]:
    """
    Validate that value is a positive integer.

    Args:
        value: The integer value to validate

    Returns:
        The validated positive integer

    Raises:
        ValueError: If value is not a positive integer
    """
    if value is None:
        return None

    if not isinstance(value, int):
        raise ValueError("Value must be an integer")

    if value < 1:
        raise ValueError("Value must be positive (greater than 0)")

    return value


def validate_non_negative_number(value: Optional[float]) -> Optional[float]:
    """
    Validate that value is a non-negative number.

    Args:
        value: The number value to validate

    Returns:
        The validated non-negative number

    Raises:
        ValueError: If value is negative
    """
    if value is None:
        return None

    if not isinstance(value, (int, float)):
        raise ValueError("Value must be a number")

    if value < 0:
        raise ValueError("Value must be non-negative (>= 0)")

    return float(value)


def validate_currency_code(value: str) -> str:
    """
    Validate and standardize currency codes (ISO 4217).

    Args:
        value: The currency code to validate

    Returns:
        The standardized currency code in uppercase

    Raises:
        ValueError: If currency code is invalid
    """
    if not isinstance(value, str):
        raise ValueError("Currency code must be a string")

    value = value.strip().upper()

    if len(value) != 3:
        raise ValueError("Currency code must be exactly 3 characters (ISO 4217)")

    if not value.isalpha():
        raise ValueError("Currency code must contain only letters")

    return value


def validate_string_length_range(min_len: int, max_len: int):
    """
    Create a validator for string length within a specific range.

    Args:
        min_len: Minimum allowed length
        max_len: Maximum allowed length

    Returns:
        A validator function for string length
    """

    def validator(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError("Value must be a string")

        value = value.strip()

        if len(value) < min_len:
            raise ValueError(f"String must be at least {min_len} characters long")

        if len(value) > max_len:
            raise ValueError(f"String must be no more than {max_len} characters long")

        return value

    return validator


def validate_password_strength(value: str) -> str:
    """
    Validate password strength according to TripSage security requirements.

    Requirements:
    - At least 8 characters long
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        value: The password to validate

    Returns:
        The validated password

    Raises:
        ValueError: If password doesn't meet strength requirements
    """
    if not isinstance(value, str):
        raise ValueError("Password must be a string")

    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter")

    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one number")

    special_chars = "!@#$%^&*()_-+=[]{}|:;,.<>?/"
    if not any(c in special_chars for c in value):
        raise ValueError("Password must contain at least one special character")

    return value


def validate_latitude(value: Optional[float]) -> Optional[float]:
    """
    Validate geographic latitude.

    Args:
        value: The latitude value to validate

    Returns:
        The validated latitude

    Raises:
        ValueError: If latitude is outside valid range
    """
    if value is None:
        return None

    if not isinstance(value, (int, float)):
        raise ValueError("Latitude must be a number")

    if not -90.0 <= value <= 90.0:
        raise ValueError("Latitude must be between -90.0 and 90.0")

    return float(value)


def validate_longitude(value: Optional[float]) -> Optional[float]:
    """
    Validate geographic longitude.

    Args:
        value: The longitude value to validate

    Returns:
        The validated longitude

    Raises:
        ValueError: If longitude is outside valid range
    """
    if value is None:
        return None

    if not isinstance(value, (int, float)):
        raise ValueError("Longitude must be a number")

    if not -180.0 <= value <= 180.0:
        raise ValueError("Longitude must be between -180.0 and 180.0")

    return float(value)


def create_enum_validator(enum_class):
    """
    Create a validator for enum values with better error messages.

    Args:
        enum_class: The enum class to validate against

    Returns:
        A validator function for the enum
    """

    def validator(value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, enum_class):
            return value

        # Try to convert string to enum
        if isinstance(value, str):
            try:
                return enum_class(value.lower())
            except ValueError:
                pass

        valid_values = [member.value for member in enum_class]
        raise ValueError(f"Value must be one of: {', '.join(valid_values)}")

    return validator


def truncate_string(max_length: int):
    """
    Create a before validator that truncates strings to max length.

    Args:
        max_length: Maximum allowed length

    Returns:
        A before validator function
    """

    def validator(value: Any) -> str:
        if value is None:
            return value
        if isinstance(value, str):
            return value[:max_length]
        return value

    return validator


# Pre-configured common validators using Annotated types for reusability
AirportCode = Annotated[str, AfterValidator(validate_airport_code)]
Rating = Annotated[Optional[float], AfterValidator(validate_rating_range)]
EmailLowercase = Annotated[Optional[str], AfterValidator(validate_email_lowercase)]
PositiveInt = Annotated[Optional[int], AfterValidator(validate_positive_integer)]
NonNegativeFloat = Annotated[Optional[float], AfterValidator(validate_non_negative_number)]
CurrencyCode = Annotated[str, AfterValidator(validate_currency_code)]
PasswordStrength = Annotated[str, AfterValidator(validate_password_strength)]
Latitude = Annotated[Optional[float], AfterValidator(validate_latitude)]
Longitude = Annotated[Optional[float], AfterValidator(validate_longitude)]

# Common string length validators
ShortString = Annotated[Optional[str], AfterValidator(validate_string_length_range(1, 50))]
MediumString = Annotated[Optional[str], AfterValidator(validate_string_length_range(1, 255))]
LongString = Annotated[Optional[str], AfterValidator(validate_string_length_range(1, 1000))]

# Truncating string validators for user input
TruncatedShortString = Annotated[str, BeforeValidator(truncate_string(50))]
TruncatedMediumString = Annotated[str, BeforeValidator(truncate_string(255))]


class CommonValidators:
    """
    Collection of common validators for TripSage models.

    This class provides static methods and pre-configured Annotated types
    for consistent validation across the application.
    """

    # Validator functions
    airport_code = validate_airport_code
    rating_range = validate_rating_range
    email_lowercase = validate_email_lowercase
    positive_integer = validate_positive_integer
    non_negative_number = validate_non_negative_number
    currency_code = validate_currency_code
    password_strength = validate_password_strength
    latitude = validate_latitude
    longitude = validate_longitude

    # Factory functions
    string_length_range = validate_string_length_range
    enum_validator = create_enum_validator
    truncation = truncate_string

    @staticmethod
    def passwords_match(password: str, password_confirm: str) -> tuple[str, str]:
        """
        Validate that two passwords match.

        Args:
            password: The primary password
            password_confirm: The confirmation password

        Returns:
            Tuple of (password, password_confirm)

        Raises:
            ValueError: If passwords don't match
        """
        if password != password_confirm:
            raise ValueError("Passwords do not match")
        return password, password_confirm

    @staticmethod
    def passwords_different(current_password: str, new_password: str) -> tuple[str, str]:
        """
        Validate that new password is different from current password.

        Args:
            current_password: The current password
            new_password: The new password

        Returns:
            Tuple of (current_password, new_password)

        Raises:
            ValueError: If passwords are the same
        """
        if current_password == new_password:
            raise ValueError("New password must be different from current password")
        return current_password, new_password
