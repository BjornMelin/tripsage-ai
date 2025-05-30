"""
Tests for shared validator functions in tripsage_core.

This module tests the password validation functions used across
the application for consistent security requirements.
"""

import pytest

from tripsage_core.models.schemas_common.validators import (
    validate_password_strength,
    validate_passwords_different,
    validate_passwords_match,
)


class TestPasswordStrengthValidation:
    """Test password strength validation."""

    def test_valid_password(self):
        """Test that a valid password passes validation."""
        password = "MySecure123!"
        result = validate_password_strength(password)
        assert result == password

    def test_password_missing_uppercase(self):
        """Test that password without uppercase fails."""
        with pytest.raises(ValueError, match="at least one uppercase letter"):
            validate_password_strength("mysecure123!")

    def test_password_missing_lowercase(self):
        """Test that password without lowercase fails."""
        with pytest.raises(ValueError, match="at least one lowercase letter"):
            validate_password_strength("MYSECURE123!")

    def test_password_missing_digit(self):
        """Test that password without digit fails."""
        with pytest.raises(ValueError, match="at least one number"):
            validate_password_strength("MySecure!")

    def test_password_missing_special_char(self):
        """Test that password without special character fails."""
        with pytest.raises(ValueError, match="at least one special character"):
            validate_password_strength("MySecure123")

    def test_password_with_all_special_chars(self):
        """Test password with various special characters."""
        special_chars = "!@#$%^&*()_-+=[]{}|:;,.<>?/"
        for char in special_chars:
            password = f"MySecure123{char}"
            result = validate_password_strength(password)
            assert result == password

    def test_minimal_valid_password(self):
        """Test minimal password that meets all requirements."""
        password = "Aa1!"
        result = validate_password_strength(password)
        assert result == password


class TestPasswordMatchValidation:
    """Test password matching validation."""

    def test_passwords_match(self):
        """Test that matching passwords pass validation."""
        password = "MySecure123!"
        password_confirm = "MySecure123!"
        result = validate_passwords_match(password, password_confirm)
        assert result == (password, password_confirm)

    def test_passwords_dont_match(self):
        """Test that non-matching passwords fail validation."""
        password = "MySecure123!"
        password_confirm = "DifferentPassword456#"
        with pytest.raises(ValueError, match="Passwords do not match"):
            validate_passwords_match(password, password_confirm)

    def test_empty_passwords_match(self):
        """Test that empty passwords are considered matching."""
        password = ""
        password_confirm = ""
        result = validate_passwords_match(password, password_confirm)
        assert result == (password, password_confirm)

    def test_one_empty_password_fails(self):
        """Test that one empty password fails validation."""
        with pytest.raises(ValueError, match="Passwords do not match"):
            validate_passwords_match("MySecure123!", "")


class TestPasswordDifferenceValidation:
    """Test password difference validation."""

    def test_passwords_different(self):
        """Test that different passwords pass validation."""
        current = "OldPassword123!"
        new = "NewPassword456#"
        result = validate_passwords_different(current, new)
        assert result == (current, new)

    def test_passwords_same_fails(self):
        """Test that identical passwords fail validation."""
        password = "SamePassword123!"
        with pytest.raises(ValueError, match="New password must be different"):
            validate_passwords_different(password, password)

    def test_empty_passwords_same_fails(self):
        """Test that empty passwords fail validation."""
        with pytest.raises(ValueError, match="New password must be different"):
            validate_passwords_different("", "")

    def test_case_sensitive_comparison(self):
        """Test that password comparison is case sensitive."""
        current = "MyPassword123!"
        new = "mypassword123!"
        result = validate_passwords_different(current, new)
        assert result == (current, new)


class TestValidatorIntegration:
    """Test integration scenarios with multiple validators."""

    def test_complete_password_change_flow(self):
        """Test a complete password change validation flow."""
        current_password = "OldPassword123!"
        new_password = "NewSecure456#"
        new_password_confirm = "NewSecure456#"

        # Test all validations in sequence
        validate_passwords_different(current_password, new_password)
        validate_passwords_match(new_password, new_password_confirm)
        result = validate_password_strength(new_password)
        assert result == new_password

    def test_registration_flow(self):
        """Test a complete registration validation flow."""
        password = "RegistrationPass123!"
        password_confirm = "RegistrationPass123!"

        # Test registration validations
        validate_passwords_match(password, password_confirm)
        result = validate_password_strength(password)
        assert result == password

    def test_failed_registration_flow(self):
        """Test failed registration with various invalid scenarios."""
        # Test password mismatch
        with pytest.raises(ValueError, match="Passwords do not match"):
            validate_passwords_match("Password123!", "DifferentPass456#")

        # Test weak password
        with pytest.raises(ValueError, match="at least one uppercase letter"):
            validate_password_strength("weakpassword123!")

    def test_failed_password_change_flow(self):
        """Test failed password change with various scenarios."""
        current = "CurrentPass123!"

        # Test same password
        with pytest.raises(ValueError, match="New password must be different"):
            validate_passwords_different(current, current)

        # Test weak new password
        new_weak = "differentweak"
        validate_passwords_different(current, new_weak)  # This should pass
        with pytest.raises(ValueError, match="at least one uppercase letter"):
            validate_password_strength(new_weak)
