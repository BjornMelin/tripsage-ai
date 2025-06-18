"""
Unit tests for user-related endpoints including preferences.

Tests user preferences endpoints that require authentication.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from tripsage.api.routers.users import (
    get_user_preferences,
    update_user_preferences,
)
from tripsage.api.schemas.users import (
    UserPreferencesRequest,
    UserPreferencesResponse,
)
from tripsage_core.services.business.user_service import UserService

class TestUsersRouter:
    """Test users router functionality."""

    @pytest.fixture
    def mock_user_service(self):
        """Mock user service."""
        service = MagicMock(spec=UserService)
        service.get_user_by_id = AsyncMock()
        service.update_user_preferences = AsyncMock()
        return service

    @pytest.fixture
    def sample_preferences(self):
        """Sample user preferences."""
        return {
            "theme": "dark",
            "currency": "USD",
            "language": "en",
            "notifications": {
                "email": True,
                "push": False,
                "marketing": False,
            },
            "travel_preferences": {
                "budget_level": "moderate",
                "accommodation_type": ["hotel", "resort"],
                "travel_style": ["adventure", "cultural"],
                "dietary_restrictions": ["vegetarian"],
            },
        }

    async def test_get_user_preferences_success(
        self, mock_user_service, sample_preferences
    ):
        """Test successful retrieval of user preferences."""
        from tripsage.api.middlewares.authentication import Principal

        # Setup mock principal
        mock_principal = Principal(
            id="user123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
            scopes=["read", "write"],
            metadata={},
        )

        # Setup mock user with preferences
        mock_user = MagicMock()
        mock_user.id = "user123"
        mock_user.preferences_json = sample_preferences
        mock_user_service.get_user_by_id.return_value = mock_user

        # Call endpoint
        result = await get_user_preferences(
            principal=mock_principal,
            user_service=mock_user_service,
        )

        # Verify
        assert result == UserPreferencesResponse(preferences=sample_preferences)
        mock_user_service.get_user_by_id.assert_called_once_with("user123")

    async def test_get_user_preferences_no_preferences(self, mock_user_service):
        """Test retrieval when user has no preferences set."""
        from tripsage.api.middlewares.authentication import Principal

        # Setup mock principal
        mock_principal = Principal(
            id="user123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
            scopes=["read", "write"],
            metadata={},
        )

        # Setup mock user with no preferences
        mock_user = MagicMock()
        mock_user.id = "user123"
        mock_user.preferences_json = None
        mock_user_service.get_user_by_id.return_value = mock_user

        # Call endpoint
        result = await get_user_preferences(
            principal=mock_principal,
            user_service=mock_user_service,
        )

        # Verify - should return empty preferences dict
        assert result == UserPreferencesResponse(preferences={})
        mock_user_service.get_user_by_id.assert_called_once_with("user123")

    async def test_get_user_preferences_user_not_found(self, mock_user_service):
        """Test retrieval when user is not found."""
        from tripsage.api.middlewares.authentication import Principal

        # Setup mock principal
        mock_principal = Principal(
            id="user123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
            scopes=["read", "write"],
            metadata={},
        )

        # Setup mock to return None
        mock_user_service.get_user_by_id.return_value = None

        # Call endpoint and expect 404
        with pytest.raises(HTTPException) as exc_info:
            await get_user_preferences(
                principal=mock_principal,
                user_service=mock_user_service,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"

    async def test_update_user_preferences_success(
        self, mock_user_service, sample_preferences
    ):
        """Test successful update of user preferences."""
        from tripsage.api.middlewares.authentication import Principal

        # Setup mock principal
        mock_principal = Principal(
            id="user123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
            scopes=["read", "write"],
            metadata={},
        )

        # Setup request
        preferences_request = UserPreferencesRequest(preferences=sample_preferences)

        # Setup mock user response
        from tripsage_core.services.business.user_service import UserResponse

        mock_user_response = UserResponse(
            id="user123",
            email="test@example.com",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            preferences=sample_preferences,
        )
        mock_user_service.update_user_preferences.return_value = mock_user_response

        # Call endpoint
        result = await update_user_preferences(
            preferences_request=preferences_request,
            principal=mock_principal,
            user_service=mock_user_service,
        )

        # Verify
        assert result == UserPreferencesResponse(preferences=sample_preferences)
        mock_user_service.update_user_preferences.assert_called_once_with(
            "user123", sample_preferences
        )

    async def test_update_user_preferences_partial_update(self, mock_user_service):
        """Test partial update of user preferences."""
        from tripsage.api.middlewares.authentication import Principal

        # Setup mock principal
        mock_principal = Principal(
            id="user123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
            scopes=["read", "write"],
            metadata={},
        )

        # Setup request with partial preferences
        partial_preferences = {
            "theme": "light",
            "notifications": {
                "email": False,
            },
        }
        preferences_request = UserPreferencesRequest(preferences=partial_preferences)

        # Setup mock user with merged preferences
        from tripsage_core.services.business.user_service import UserResponse

        merged_preferences = {
            "theme": "light",
            "currency": "USD",
            "language": "en",
            "notifications": {
                "email": False,
                "push": False,
                "marketing": False,
            },
        }
        mock_user_response = UserResponse(
            id="user123",
            email="test@example.com",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            preferences=merged_preferences,
        )
        mock_user_service.update_user_preferences.return_value = mock_user_response

        # Call endpoint
        result = await update_user_preferences(
            preferences_request=preferences_request,
            principal=mock_principal,
            user_service=mock_user_service,
        )

        # Verify
        assert result == UserPreferencesResponse(preferences=merged_preferences)
        mock_user_service.update_user_preferences.assert_called_once_with(
            "user123", partial_preferences
        )

    async def test_update_user_preferences_empty_update(
        self, mock_user_service, sample_preferences
    ):
        """Test update with empty preferences object."""
        # Setup request with empty preferences
        preferences_request = UserPreferencesRequest(preferences={})

        # Setup mock user response
        from tripsage_core.services.business.user_service import UserResponse

        mock_user_response = UserResponse(
            id="user123",
            email="test@example.com",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            preferences=sample_preferences,
        )
        mock_user_service.update_user_preferences.return_value = mock_user_response

        # Call endpoint
        from tripsage.api.middlewares.authentication import Principal

        mock_principal = Principal(
            id="user123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
            scopes=["read", "write"],
            metadata={},
        )

        result = await update_user_preferences(
            preferences_request=preferences_request,
            principal=mock_principal,
            user_service=mock_user_service,
        )

        # Verify - preferences should remain unchanged
        assert result == UserPreferencesResponse(preferences=sample_preferences)
        mock_user_service.update_user_preferences.assert_called_once_with("user123", {})

    async def test_update_user_preferences_service_error(self, mock_user_service):
        """Test update when service raises an error."""
        # Setup request
        preferences_request = UserPreferencesRequest(preferences={"theme": "dark"})

        # Setup mock to raise error
        mock_user_service.update_user_preferences.side_effect = Exception(
            "Database error"
        )

        # Call endpoint and expect 500
        from tripsage.api.middlewares.authentication import Principal

        mock_principal = Principal(
            id="user123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
            scopes=["read", "write"],
            metadata={},
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_user_preferences(
                preferences_request=preferences_request,
                principal=mock_principal,
                user_service=mock_user_service,
            )

        assert exc_info.value.status_code == 500
        assert "Failed to update preferences" in exc_info.value.detail
