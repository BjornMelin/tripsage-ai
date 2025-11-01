"""Common validators for TripSage AI using Pydantic v2.

This module exposes small, typed validator functions and reusable Annotated
aliases. Signatures accept ``object`` where runtime ``isinstance`` checks are
performed to avoid Pyright "unnecessary isinstance" diagnostics while keeping
robust runtime validation.
"""

import re
from collections.abc import Callable
from enum import Enum
from typing import Annotated, TypeVar

from pydantic import (
    AfterValidator,
    BeforeValidator,
)


E = TypeVar("E", bound=Enum)


def validate_airport_code(value: object) -> str:
    """Validate and standardize IATA airport codes.

    Args:
        value: The airport code to validate

    Returns:
        The standardized airport code in uppercase

    Raises:
        ValueError: If the airport code is invalid
    """
    if not isinstance(value, str):
        raise TypeError("Airport code must be a string")

    value = value.strip().upper()

    if len(value) != 3:
        raise ValueError("Airport code must be exactly 3 characters (IATA code)")

    if not value.isalpha():
        raise ValueError("Airport code must contain only letters")

    return value


def validate_rating_range(value: object | None) -> float | None:
    """Validate that rating is between 0.0 and 5.0.

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
        raise TypeError("Rating must be a number")

    if not 0.0 <= value <= 5.0:
        raise ValueError("Rating must be between 0.0 and 5.0")

    return float(value)


def validate_email_lowercase(value: object | None) -> str | None:
    """Validate and normalize email addresses to lowercase.

    Args:
        value: The email address to validate

    Returns:
        The normalized email address in lowercase
    """
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError("Email must be a string")

    return value.strip().lower()


def validate_positive_integer(value: object | None) -> int | None:
    """Validate that value is a positive integer.

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
        raise TypeError("Value must be an integer")

    if value < 1:
        raise ValueError("Value must be positive (greater than 0)")

    return value


def validate_non_negative_number(value: object | None) -> float | None:
    """Validate that value is a non-negative number.

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
        raise TypeError("Value must be a number")

    if value < 0:
        raise ValueError("Value must be non-negative (>= 0)")

    return float(value)


def validate_currency_code(value: object) -> str:
    """Validate and standardize currency codes (ISO 4217).

    Args:
        value: The currency code to validate

    Returns:
        The standardized currency code in uppercase

    Raises:
        ValueError: If currency code is invalid
    """
    if not isinstance(value, str):
        raise TypeError("Currency code must be a string")

    value = value.strip().upper()

    if len(value) != 3:
        raise ValueError("Currency code must be exactly 3 characters (ISO 4217)")

    if not value.isalpha():
        raise ValueError("Currency code must contain only letters")

    return value


def validate_string_length_range(min_len: int, max_len: int):
    """Create a validator for string length within a specific range.

    Args:
        min_len: Minimum allowed length
        max_len: Maximum allowed length

    Returns:
        A validator function for string length
    """

    def validator(value: object | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("Value must be a string")

        value = value.strip()

        if len(value) < min_len:
            raise ValueError(f"String must be at least {min_len} characters long")

        if len(value) > max_len:
            raise ValueError(f"String must be no more than {max_len} characters long")

        return value

    return validator


def validate_password_strength(value: object) -> str:
    """Validate password strength according to TripSage security requirements.

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
        raise TypeError("Password must be a string")

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


def validate_latitude(value: object | None) -> float | None:
    """Validate geographic latitude.

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
        raise TypeError("Latitude must be a number")

    if not -90.0 <= value <= 90.0:
        raise ValueError("Latitude must be between -90.0 and 90.0")

    return float(value)


def validate_longitude(value: object | None) -> float | None:
    """Validate geographic longitude.

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
        raise TypeError("Longitude must be a number")

    if not -180.0 <= value <= 180.0:
        raise ValueError("Longitude must be between -180.0 and 180.0")

    return float(value)


def create_enum_validator[E: Enum](
    enum_class: type[E],
) -> Callable[[object | None], E | None]:
    """Create a validator for enum values with better error messages.

    Args:
        enum_class: The enum class to validate against

    Returns:
        A validator function for the enum
    """

    def validator(value: object | None) -> E | None:
        if value is None:
            return None

        if isinstance(value, enum_class):
            return value

        # Try multiple case strategies for string values
        if isinstance(value, str):
            for candidate in (value, value.lower(), value.upper()):
                try:
                    return enum_class(candidate)
                except ValueError:
                    continue

        valid_values: list[str] = [str(member.value) for member in enum_class]
        joined = ", ".join(valid_values)
        raise ValueError(f"Value must be one of: {joined}")

    return validator


def truncate_string(max_length: int):
    """Create a before validator that truncates strings to max length.

    Args:
        max_length: Maximum allowed length

    Returns:
        A before validator function
    """

    def validator(value: object) -> object:
        if value is None:
            return value
        if isinstance(value, str):
            return value[:max_length]
        return value

    return validator


def passwords_match(password: str, password_confirm: str) -> None:
    """Validate that two passwords match.

    Args:
        password: The primary password
        password_confirm: The confirmation password

    Raises:
        ValueError: If passwords don't match
    """
    if password != password_confirm:
        raise ValueError("Passwords do not match")


def passwords_different(current_password: str, new_password: str) -> None:
    """Validate that new password is different from current password.

    Args:
        current_password: The current password
        new_password: The new password

    Raises:
        ValueError: If passwords are the same
    """
    if current_password == new_password:
        raise ValueError("New password must be different from current password")


# Pre-configured common validators using Annotated types for reusability
AirportCode = Annotated[str, AfterValidator(validate_airport_code)]
Rating = Annotated[float | None, AfterValidator(validate_rating_range)]
EmailLowercase = Annotated[str | None, AfterValidator(validate_email_lowercase)]
PositiveInt = Annotated[int | None, AfterValidator(validate_positive_integer)]
NonNegativeFloat = Annotated[float | None, AfterValidator(validate_non_negative_number)]
CurrencyCode = Annotated[str, AfterValidator(validate_currency_code)]
PasswordStrength = Annotated[str, AfterValidator(validate_password_strength)]
Latitude = Annotated[float | None, AfterValidator(validate_latitude)]
Longitude = Annotated[float | None, AfterValidator(validate_longitude)]

# Common string length validators
ShortString = Annotated[str | None, AfterValidator(validate_string_length_range(1, 50))]
MediumString = Annotated[
    str | None, AfterValidator(validate_string_length_range(1, 255))
]
LongString = Annotated[
    str | None, AfterValidator(validate_string_length_range(1, 1000))
]

# Truncating string validators for user input
TruncatedShortString = Annotated[str, BeforeValidator(truncate_string(50))]
TruncatedMediumString = Annotated[str, BeforeValidator(truncate_string(255))]
