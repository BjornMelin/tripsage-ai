"""
Shared validator functions for TripSage AI.

This module contains reusable validation functions used across
the application for consistent data validation.
"""


def validate_password_strength(password: str) -> str:
    """
    Validate password strength according to TripSage security requirements.

    Requirements:
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: The password to validate

    Returns:
        The validated password

    Raises:
        ValueError: If password doesn't meet strength requirements
    """
    # Check for at least one uppercase letter
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")

    # Check for at least one lowercase letter
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")

    # Check for at least one digit
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one number")

    # Check for at least one special character
    special_chars = "!@#$%^&*()_-+=[]{}|:;,.<>?/"
    if not any(c in special_chars for c in password):
        raise ValueError("Password must contain at least one special character")

    return password


def validate_passwords_match(password: str, password_confirm: str) -> tuple[str, str]:
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


def validate_passwords_different(
    current_password: str, new_password: str
) -> tuple[str, str]:
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
