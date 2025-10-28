"""Unit tests for common validators."""

import pytest

from tripsage_core.models.schemas_common.common_validators import (
    passwords_different,
    passwords_match,
    validate_password_strength,
)


class TestValidatePasswordStrength:
    """Test password strength validation."""

    def test_valid_password(self) -> None:
        """Test valid password passes."""
        valid_password = "StrongPass123!"
        result = validate_password_strength(valid_password)
        assert result == valid_password

    def test_password_too_short(self) -> None:
        """Test password shorter than 8 characters fails."""
        with pytest.raises(ValueError, match="must be at least 8 characters long"):
            validate_password_strength("Short1!")

    def test_password_no_uppercase(self) -> None:
        """Test password without uppercase fails."""
        with pytest.raises(
            ValueError, match="must contain at least one uppercase letter"
        ):
            validate_password_strength("lowercase123!")

    def test_password_no_lowercase(self) -> None:
        """Test password without lowercase fails."""
        with pytest.raises(
            ValueError, match="must contain at least one lowercase letter"
        ):
            validate_password_strength("UPPERCASE123!")

    def test_password_no_digit(self) -> None:
        """Test password without digit fails."""
        with pytest.raises(ValueError, match="must contain at least one number"):
            validate_password_strength("PasswordOnly!")

    def test_password_no_special_char(self) -> None:
        """Test password without special character fails."""
        with pytest.raises(
            ValueError, match="must contain at least one special character"
        ):
            validate_password_strength("Password123")

    def test_password_type_error(self) -> None:
        """Test non-string password raises TypeError."""
        with pytest.raises(TypeError, match="Password must be a string"):
            validate_password_strength(123)  # type: ignore[arg-type]


class TestPasswordsMatch:
    """Test password matching validation."""

    def test_passwords_match(self) -> None:
        """Test matching passwords pass."""
        passwords_match("password123", "password123")

    def test_passwords_do_not_match(self) -> None:
        """Test non-matching passwords fail."""
        with pytest.raises(ValueError, match="Passwords do not match"):
            passwords_match("password123", "different456")


class TestPasswordsDifferent:
    """Test password difference validation."""

    def test_passwords_different(self) -> None:
        """Test different passwords pass."""
        passwords_different("oldpassword", "newpassword")

    def test_passwords_same(self) -> None:
        """Test same passwords fail."""
        with pytest.raises(
            ValueError, match="New password must be different from current password"
        ):
            passwords_different("samepassword", "samepassword")
