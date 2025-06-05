"""Comprehensive unit tests for auth router."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.factories import UserFactory
from tripsage.api.main import app


class TestAuthRouter:
    """Test suite for auth router endpoints."""

    def setup_method(self):
        """Set up test client and mocks."""
        self.client = TestClient(app)
        self.mock_user_service = Mock()

        # Sample test data
        self.sample_user = UserFactory.create()
        self.sample_register_request = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "full_name": "Test User",
        }

        self.sample_login_request = {
            "username": "testuser",
            "password": "StrongPassword123!",
            "remember_me": False,
        }

        self.sample_token_response = {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": "test-user-id",
                "username": "testuser",
                "email": "test@example.com",
                "full_name": "Test User",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "is_active": True,
                "is_verified": False,
                "preferences": {},
            },
        }

    @patch("tripsage.api.routers.auth.get_user_service")
    def test_register_user_success(self, mock_get_service):
        """Test successful user registration."""
        # Arrange
        mock_get_service.return_value = self.mock_user_service
        self.mock_user_service.register_user = AsyncMock(return_value=self.sample_user)

        # Act
        response = self.client.post(
            "/api/auth/register", json=self.sample_register_request
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["email"] == self.sample_register_request["email"]
        assert data["username"] == self.sample_register_request["username"]
        self.mock_user_service.register_user.assert_called_once()

    @patch("tripsage.api.routers.auth.get_user_service")
    def test_register_user_email_already_exists(self, mock_get_service):
        """Test user registration with existing email."""
        # Arrange
        mock_get_service.return_value = self.mock_user_service
        from fastapi import HTTPException

        self.mock_user_service.register_user = AsyncMock(
            side_effect=HTTPException(
                status_code=409, detail="Email already registered"
            )
        )

        # Act
        response = self.client.post(
            "/api/auth/register", json=self.sample_register_request
        )

        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Email already registered" in response.json()["detail"]

    def test_register_user_password_mismatch(self):
        """Test user registration with password mismatch."""
        # Arrange
        register_request = {
            **self.sample_register_request,
            "password_confirm": "DifferentPassword123!",
        }

        # Act
        response = self.client.post("/api/auth/register", json=register_request)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_user_weak_password(self):
        """Test user registration with weak password."""
        # Arrange
        register_request = {
            **self.sample_register_request,
            "password": "weak",
            "password_confirm": "weak",
        }

        # Act
        response = self.client.post("/api/auth/register", json=register_request)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_user_invalid_email(self):
        """Test user registration with invalid email."""
        # Arrange
        register_request = {**self.sample_register_request, "email": "invalid-email"}

        # Act
        response = self.client.post("/api/auth/register", json=register_request)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_user_invalid_username(self):
        """Test user registration with invalid username."""
        # Arrange
        register_request = {
            **self.sample_register_request,
            "username": "a",  # Too short
        }

        # Act
        response = self.client.post("/api/auth/register", json=register_request)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.auth.get_auth_service")
    def test_login_success(self, mock_get_auth_service):
        """Test successful user login."""
        # Arrange
        mock_auth_service = Mock()
        mock_get_auth_service.return_value = mock_auth_service
        mock_auth_service.authenticate_user = AsyncMock(
            return_value=self.sample_token_response
        )

        # Act
        response = self.client.post("/api/auth/login", json=self.sample_login_request)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["token_type"] == "bearer"

    @patch("tripsage.api.routers.auth.get_auth_service")
    def test_login_invalid_credentials(self, mock_get_auth_service):
        """Test login with invalid credentials."""
        # Arrange
        mock_auth_service = Mock()
        mock_get_auth_service.return_value = mock_auth_service
        from fastapi import HTTPException

        mock_auth_service.authenticate_user = AsyncMock(
            side_effect=HTTPException(status_code=401, detail="Invalid credentials")
        )

        # Act
        response = self.client.post("/api/auth/login", json=self.sample_login_request)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid credentials" in response.json()["detail"]

    @patch("tripsage.api.routers.auth.get_auth_service")
    def test_login_user_not_found(self, mock_get_auth_service):
        """Test login with non-existent user."""
        # Arrange
        mock_auth_service = Mock()
        mock_get_auth_service.return_value = mock_auth_service
        from fastapi import HTTPException

        mock_auth_service.authenticate_user = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="User not found")
        )

        # Act
        response = self.client.post("/api/auth/login", json=self.sample_login_request)

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("tripsage.api.routers.auth.get_auth_service")
    def test_refresh_token_success(self, mock_get_auth_service):
        """Test successful token refresh."""
        # Arrange
        mock_auth_service = Mock()
        mock_get_auth_service.return_value = mock_auth_service
        new_token_response = {
            **self.sample_token_response,
            "access_token": "new_access_token",
        }
        mock_auth_service.refresh_token = AsyncMock(return_value=new_token_response)

        refresh_request = {"refresh_token": "valid_refresh_token"}

        # Act
        response = self.client.post("/api/auth/refresh", json=refresh_request)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "new_access_token"

    @patch("tripsage.api.routers.auth.get_auth_service")
    def test_refresh_token_invalid(self, mock_get_auth_service):
        """Test token refresh with invalid token."""
        # Arrange
        mock_auth_service = Mock()
        mock_get_auth_service.return_value = mock_auth_service
        from fastapi import HTTPException

        mock_auth_service.refresh_token = AsyncMock(
            side_effect=HTTPException(status_code=401, detail="Invalid refresh token")
        )

        refresh_request = {"refresh_token": "invalid_refresh_token"}

        # Act
        response = self.client.post("/api/auth/refresh", json=refresh_request)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("tripsage.api.routers.auth.get_auth_service")
    @patch("tripsage.api.routers.auth.require_principal_dep")
    def test_logout_success(self, mock_require_principal, mock_get_auth_service):
        """Test successful logout."""
        # Arrange
        mock_require_principal.return_value = Mock(id="test-user-id")
        mock_auth_service = Mock()
        mock_get_auth_service.return_value = mock_auth_service
        mock_auth_service.logout_user = AsyncMock(
            return_value={"message": "Logged out successfully"}
        )

        # Act
        response = self.client.post(
            "/api/auth/logout", headers={"Authorization": "Bearer valid_token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data

    @patch("tripsage.api.routers.auth.get_user_service")
    def test_forgot_password_success(self, mock_get_service):
        """Test successful forgot password request."""
        # Arrange
        mock_get_service.return_value = self.mock_user_service
        reset_response = {
            "message": "Password reset instructions sent to email",
            "email": "test@example.com",
            "reset_token_expires_at": "2024-01-01T01:00:00Z",
        }
        self.mock_user_service.request_password_reset = AsyncMock(
            return_value=reset_response
        )

        forgot_request = {"email": "test@example.com"}

        # Act
        response = self.client.post("/api/auth/forgot-password", json=forgot_request)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert data["email"] == "test@example.com"

    @patch("tripsage.api.routers.auth.get_user_service")
    def test_reset_password_success(self, mock_get_service):
        """Test successful password reset."""
        # Arrange
        mock_get_service.return_value = self.mock_user_service
        self.mock_user_service.reset_password = AsyncMock(
            return_value={"message": "Password reset successfully", "success": True}
        )

        reset_request = {
            "token": "valid_reset_token",
            "new_password": "NewStrongPassword123!",
            "new_password_confirm": "NewStrongPassword123!",
        }

        # Act
        response = self.client.post("/api/auth/reset-password", json=reset_request)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "message" in data

    @patch("tripsage.api.routers.auth.get_user_service")
    def test_reset_password_invalid_token(self, mock_get_service):
        """Test password reset with invalid token."""
        # Arrange
        mock_get_service.return_value = self.mock_user_service
        from fastapi import HTTPException

        self.mock_user_service.reset_password = AsyncMock(
            side_effect=HTTPException(
                status_code=400, detail="Invalid or expired reset token"
            )
        )

        reset_request = {
            "token": "invalid_reset_token",
            "new_password": "NewStrongPassword123!",
            "new_password_confirm": "NewStrongPassword123!",
        }

        # Act
        response = self.client.post("/api/auth/reset-password", json=reset_request)

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("tripsage.api.routers.auth.get_user_service")
    @patch("tripsage.api.routers.auth.require_principal_dep")
    def test_change_password_success(self, mock_require_principal, mock_get_service):
        """Test successful password change."""
        # Arrange
        mock_require_principal.return_value = Mock(id="test-user-id")
        mock_get_service.return_value = self.mock_user_service
        self.mock_user_service.change_password = AsyncMock(
            return_value={"message": "Password changed successfully", "success": True}
        )

        change_request = {
            "current_password": "CurrentPassword123!",
            "new_password": "NewStrongPassword123!",
            "new_password_confirm": "NewStrongPassword123!",
        }

        # Act
        response = self.client.put(
            "/api/auth/change-password",
            json=change_request,
            headers={"Authorization": "Bearer valid_token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    @patch("tripsage.api.routers.auth.require_principal_dep")
    def test_get_me_success(self, mock_require_principal):
        """Test successful get current user info."""
        # Arrange
        mock_principal = Mock(id="test-user-id")
        mock_require_principal.return_value = mock_principal

        # Act
        response = self.client.get(
            "/api/auth/me", headers={"Authorization": "Bearer valid_token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        # Note: Actual implementation would fetch user data from service

    def test_get_me_unauthorized(self):
        """Test get current user without authentication."""
        # Act
        response = self.client.get("/api/auth/me")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("tripsage.api.routers.auth.get_user_service")
    @patch("tripsage.api.routers.auth.require_principal_dep")
    def test_update_profile_success(self, mock_require_principal, mock_get_service):
        """Test successful profile update."""
        # Arrange
        mock_require_principal.return_value = Mock(id="test-user-id")
        mock_get_service.return_value = self.mock_user_service
        updated_user = {**self.sample_user, "full_name": "Updated Name"}
        self.mock_user_service.update_user_profile = AsyncMock(
            return_value=updated_user
        )

        update_request = {"full_name": "Updated Name", "preferences": {"theme": "dark"}}

        # Act
        response = self.client.put(
            "/api/auth/profile",
            json=update_request,
            headers={"Authorization": "Bearer valid_token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Updated Name"

    def test_login_missing_fields(self):
        """Test login with missing required fields."""
        # Arrange
        incomplete_request = {"username": "testuser"}  # Missing password

        # Act
        response = self.client.post("/api/auth/login", json=incomplete_request)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_missing_fields(self):
        """Test registration with missing required fields."""
        # Arrange
        incomplete_request = {
            "username": "testuser",
            "email": "test@example.com",
            # Missing password fields and full_name
        }

        # Act
        response = self.client.post("/api/auth/register", json=incomplete_request)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize(
        "username", ["", "ab", "a" * 51, "user@invalid", "user space"]
    )
    def test_register_invalid_usernames(self, username):
        """Test registration with various invalid usernames."""
        # Arrange
        register_request = {**self.sample_register_request, "username": username}

        # Act
        response = self.client.post("/api/auth/register", json=register_request)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize(
        "password", ["", "1234567", "password", "PASSWORD", "Password", "12345678"]
    )
    def test_register_weak_passwords(self, password):
        """Test registration with various weak passwords."""
        # Arrange
        register_request = {
            **self.sample_register_request,
            "password": password,
            "password_confirm": password,
        }

        # Act
        response = self.client.post("/api/auth/register", json=register_request)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_reset_password_password_mismatch(self):
        """Test password reset with password confirmation mismatch."""
        # Arrange
        reset_request = {
            "token": "valid_token",
            "new_password": "NewPassword123!",
            "new_password_confirm": "DifferentPassword123!",
        }

        # Act
        response = self.client.post("/api/auth/reset-password", json=reset_request)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_change_password_password_mismatch(self):
        """Test password change with confirmation mismatch."""
        # Arrange
        change_request = {
            "current_password": "CurrentPassword123!",
            "new_password": "NewPassword123!",
            "new_password_confirm": "DifferentPassword123!",
        }

        # Act
        response = self.client.put(
            "/api/auth/change-password",
            json=change_request,
            headers={"Authorization": "Bearer valid_token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.auth.get_user_service")
    @patch("tripsage.api.routers.auth.require_principal_dep")
    def test_verify_email_success(self, mock_require_principal, mock_get_service):
        """Test successful email verification."""
        # Arrange
        mock_require_principal.return_value = Mock(id="test-user-id")
        mock_get_service.return_value = self.mock_user_service
        self.mock_user_service.verify_email = AsyncMock(
            return_value={"message": "Email verified successfully", "success": True}
        )

        # Act
        response = self.client.post(
            "/api/auth/verify-email?token=valid_verification_token",
            headers={"Authorization": "Bearer valid_token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    @patch("tripsage.api.routers.auth.get_user_service")
    @patch("tripsage.api.routers.auth.require_principal_dep")
    def test_resend_verification_email(self, mock_require_principal, mock_get_service):
        """Test resending verification email."""
        # Arrange
        mock_require_principal.return_value = Mock(id="test-user-id")
        mock_get_service.return_value = self.mock_user_service
        self.mock_user_service.resend_verification_email = AsyncMock(
            return_value={"message": "Verification email sent", "success": True}
        )

        # Act
        response = self.client.post(
            "/api/auth/resend-verification",
            headers={"Authorization": "Bearer valid_token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
