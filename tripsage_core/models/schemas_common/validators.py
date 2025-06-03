"""
Shared validator functions for TripSage AI.

This module contains reusable validation functions used across
the application for consistent data validation.

Note: This module is deprecated. Use CommonValidators from common_validators.py instead.
Kept for backwards compatibility during migration.
"""

import warnings

from .common_validators import CommonValidators


# Backward compatibility imports with deprecation warnings
def validate_password_strength(password: str) -> str:
    """
    Validate password strength according to TripSage security requirements.

    DEPRECATED: Use CommonValidators.password_strength or PasswordStrength type instead.
    """
    warnings.warn(
        "validate_password_strength is deprecated. Use CommonValidators.password_strength instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return CommonValidators.password_strength(password)


def validate_passwords_match(password: str, password_confirm: str) -> tuple[str, str]:
    """
    Validate that two passwords match.

    DEPRECATED: Use CommonValidators.passwords_match instead.
    """
    warnings.warn(
        "validate_passwords_match is deprecated. Use CommonValidators.passwords_match instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return CommonValidators.passwords_match(password, password_confirm)


def validate_passwords_different(
    current_password: str, new_password: str
) -> tuple[str, str]:
    """
    Validate that new password is different from current password.

    DEPRECATED: Use CommonValidators.passwords_different instead.
    """
    warnings.warn(
        "validate_passwords_different is deprecated. Use CommonValidators.passwords_different instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return CommonValidators.passwords_different(current_password, new_password)
