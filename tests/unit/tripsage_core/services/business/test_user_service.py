"""
Comprehensive tests for UserService.

This module provides full test coverage for user management operations
including user creation, authentication, profile management, and settings.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.user_service import (
    PasswordChangeRequest,
    UserCreateRequest,
    UserResponse,
    UserService,
    UserUpdateRequest,
    get_user_service,
)


class TestUserService:
    """Test suite for UserService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def user_service(self, mock_database_service):
        """Create UserService instance with mocked dependencies."""
        return UserService(database_service=mock_database_service)

    @pytest.fixture
    def sample_user_create_request(self):
        """Sample user creation request."""
        return UserCreateRequest(
            email="test@example.com",
            password="securepassword123",
            full_name="Test User",
            username="testuser",
        )

    @pytest.fixture
    def sample_user_response(self):
        """Sample user response object."""
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        return UserResponse(
            id=user_id,
            email="test@example.com",
            full_name="Test User",
            username="testuser",
            is_active=True,
            is_verified=False,
            created_at=now,
            updated_at=now,
            preferences={},
        )

    @pytest.fixture
    def sample_db_user_data(self):
        """Sample database user data."""
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        return {
            "id": user_id,
            "email": "test@example.com",
            "full_name": "Test User",
            "username": "testuser",
            "hashed_password": "$2b$12$hashed_password",
            "is_active": True,
            "is_verified": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "preferences": {},
        }

    @pytest.mark.asyncio
    async def test_create_user_success(
        self, user_service, mock_database_service, sample_user_create_request
    ):
        """Test successful user creation."""
        # Mock database responses
        mock_database_service.get_user_by_email.return_value = None
        mock_database_service.get_user_by_username.return_value = None
        mock_database_service.create_user.return_value = {
            "id": "test-user-id",
            "email": sample_user_create_request.email,
            "full_name": sample_user_create_request.full_name,
            "username": sample_user_create_request.username,
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "preferences": {},
        }

        # Create user
        result = await user_service.create_user(sample_user_create_request)

        # Assertions
        assert result.email == sample_user_create_request.email
        assert result.full_name == sample_user_create_request.full_name
        assert result.username == sample_user_create_request.username
        assert result.is_active is True
        assert result.is_verified is False

        # Verify database calls
        mock_database_service.get_user_by_email.assert_called_once_with(
            sample_user_create_request.email
        )
        mock_database_service.get_user_by_username.assert_called_once_with(
            sample_user_create_request.username
        )
        mock_database_service.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self,
        user_service,
        mock_database_service,
        sample_user_create_request,
        sample_db_user_data,
    ):
        """Test user creation with duplicate email."""
        # Mock existing user
        mock_database_service.get_user_by_email.return_value = sample_db_user_data

        # Attempt to create user
        with pytest.raises(ValidationError, match="already exists"):
            await user_service.create_user(sample_user_create_request)

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(
        self,
        user_service,
        mock_database_service,
        sample_user_create_request,
        sample_db_user_data,
    ):
        """Test user creation with duplicate username."""
        # Mock existing user by username
        mock_database_service.get_user_by_email.return_value = None
        mock_database_service.get_user_by_username.return_value = sample_db_user_data

        # Attempt to create user
        with pytest.raises(ValidationError, match="already taken"):
            await user_service.create_user(sample_user_create_request)

    @pytest.mark.asyncio
    async def test_create_user_weak_password(self, user_service):
        """Test user creation with weak password."""
        # This should fail during request validation
        with pytest.raises(ValueError, match="at least 8 characters"):
            UserCreateRequest(
                email="test@example.com", password="weak", full_name="Test User"
            )

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(
        self, user_service, mock_database_service, sample_db_user_data
    ):
        """Test successful user retrieval by ID."""
        mock_database_service.get_user_by_id.return_value = sample_db_user_data

        result = await user_service.get_user_by_id(sample_db_user_data["id"])

        assert result.id == sample_db_user_data["id"]
        assert result.email == sample_db_user_data["email"]
        mock_database_service.get_user_by_id.assert_called_once_with(
            sample_db_user_data["id"]
        )

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_service, mock_database_service):
        """Test user retrieval when user doesn't exist."""
        user_id = str(uuid4())
        mock_database_service.get_user_by_id.return_value = None

        result = await user_service.get_user_by_id(user_id)

        assert result is None
        mock_database_service.get_user_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(
        self, user_service, mock_database_service, sample_db_user_data
    ):
        """Test successful user retrieval by email."""
        mock_database_service.get_user_by_email.return_value = sample_db_user_data

        result = await user_service.get_user_by_email(sample_db_user_data["email"])

        assert result.email == sample_db_user_data["email"]
        mock_database_service.get_user_by_email.assert_called_once_with(
            sample_db_user_data["email"]
        )

    @pytest.mark.asyncio
    async def test_get_user_by_username_success(
        self, user_service, mock_database_service, sample_db_user_data
    ):
        """Test successful user retrieval by username."""
        mock_database_service.get_user_by_username.return_value = sample_db_user_data

        result = await user_service.get_user_by_username(
            sample_db_user_data["username"]
        )

        assert result.username == sample_db_user_data["username"]
        mock_database_service.get_user_by_username.assert_called_once_with(
            sample_db_user_data["username"]
        )

    @pytest.mark.asyncio
    async def test_update_user_success(
        self, user_service, mock_database_service, sample_db_user_data
    ):
        """Test successful user update."""
        mock_database_service.get_user_by_id.return_value = sample_db_user_data
        mock_database_service.get_user_by_username.return_value = None

        updated_data = sample_db_user_data.copy()
        updated_data["full_name"] = "Updated Name"
        updated_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        mock_database_service.update_user.return_value = updated_data

        update_request = UserUpdateRequest(full_name="Updated Name")

        result = await user_service.update_user(
            sample_db_user_data["id"], update_request
        )

        assert result.full_name == "Updated Name"
        mock_database_service.update_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_service, mock_database_service):
        """Test user update when user doesn't exist."""
        user_id = str(uuid4())
        mock_database_service.get_user_by_id.return_value = None

        update_request = UserUpdateRequest(full_name="Updated Name")

        with pytest.raises(NotFoundError, match="not found"):
            await user_service.update_user(user_id, update_request)

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, user_service, mock_database_service, sample_db_user_data
    ):
        """Test successful password change."""
        # Add hashed password to db data
        user_with_password = sample_db_user_data.copy()
        user_with_password["hashed_password"] = "$2b$12$hashed_password"

        mock_database_service.get_user_with_password.return_value = user_with_password
        mock_database_service.update_user_password.return_value = True

        password_data = PasswordChangeRequest(
            current_password="currentpass123", new_password="newpassword456"
        )

        # Mock password verification
        with patch.object(user_service, "_verify_password", return_value=True):
            result = await user_service.change_password(
                sample_db_user_data["id"], password_data
            )

        assert result is True
        mock_database_service.update_user_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, user_service, mock_database_service, sample_db_user_data
    ):
        """Test password change with wrong current password."""
        user_with_password = sample_db_user_data.copy()
        user_with_password["hashed_password"] = "$2b$12$hashed_password"

        mock_database_service.get_user_with_password.return_value = user_with_password

        password_data = PasswordChangeRequest(
            current_password="wrongpassword", new_password="newpassword456"
        )

        # Mock password verification to return False
        with patch.object(user_service, "_verify_password", return_value=False):
            with pytest.raises(AuthenticationError, match="incorrect"):
                await user_service.change_password(
                    sample_db_user_data["id"], password_data
                )

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(
        self, user_service, mock_database_service
    ):
        """Test password change when user doesn't exist."""
        user_id = str(uuid4())
        mock_database_service.get_user_with_password.return_value = None

        password_data = PasswordChangeRequest(
            current_password="currentpass123", new_password="newpassword456"
        )

        with pytest.raises(NotFoundError, match="not found"):
            await user_service.change_password(user_id, password_data)

    @pytest.mark.asyncio
    async def test_verify_user_credentials_success(
        self, user_service, mock_database_service, sample_db_user_data
    ):
        """Test successful credential verification."""
        user_with_password = sample_db_user_data.copy()
        user_with_password["hashed_password"] = "$2b$12$hashed_password"

        mock_database_service.get_user_with_password_by_email.return_value = (
            user_with_password
        )

        # Mock password verification
        with patch.object(user_service, "_verify_password", return_value=True):
            result = await user_service.verify_user_credentials(
                "test@example.com", "password123"
            )

        assert result is not None
        assert result.email == sample_db_user_data["email"]

    @pytest.mark.asyncio
    async def test_verify_user_credentials_wrong_password(
        self, user_service, mock_database_service, sample_db_user_data
    ):
        """Test credential verification with wrong password."""
        user_with_password = sample_db_user_data.copy()
        user_with_password["hashed_password"] = "$2b$12$hashed_password"

        mock_database_service.get_user_with_password_by_email.return_value = (
            user_with_password
        )

        # Mock password verification to return False
        with patch.object(user_service, "_verify_password", return_value=False):
            result = await user_service.verify_user_credentials(
                "test@example.com", "wrongpassword"
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_verify_user_credentials_user_not_found(
        self, user_service, mock_database_service
    ):
        """Test credential verification when user doesn't exist."""
        mock_database_service.get_user_with_password_by_email.return_value = None

        result = await user_service.verify_user_credentials(
            "nonexistent@example.com", "password123"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_verify_user_credentials_inactive_user(
        self, user_service, mock_database_service, sample_db_user_data
    ):
        """Test credential verification with inactive user."""
        user_with_password = sample_db_user_data.copy()
        user_with_password["hashed_password"] = "$2b$12$hashed_password"
        user_with_password["is_active"] = False

        mock_database_service.get_user_with_password_by_email.return_value = (
            user_with_password
        )

        # Mock password verification
        with patch.object(user_service, "_verify_password", return_value=True):
            result = await user_service.verify_user_credentials(
                "test@example.com", "password123"
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_deactivate_user_success(
        self, user_service, mock_database_service, sample_db_user_data
    ):
        """Test successful user deactivation."""
        mock_database_service.get_user_by_id.return_value = sample_db_user_data
        mock_database_service.update_user.return_value = sample_db_user_data

        result = await user_service.deactivate_user(sample_db_user_data["id"])

        assert result is True
        mock_database_service.update_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_user_success(
        self, user_service, mock_database_service, sample_db_user_data
    ):
        """Test successful user activation."""
        inactive_user = sample_db_user_data.copy()
        inactive_user["is_active"] = False

        mock_database_service.get_user_by_id.return_value = inactive_user
        mock_database_service.update_user.return_value = sample_db_user_data

        result = await user_service.activate_user(sample_db_user_data["id"])

        assert result is True
        mock_database_service.update_user.assert_called_once()

    def test_hash_password(self, user_service):
        """Test password hashing."""
        password = "testpassword123"
        hashed = user_service._hash_password(password)

        assert hashed.startswith("$2b$")
        assert hashed != password

        # Verify the hash can be used to verify the original password
        assert user_service._verify_password(password, hashed) is True

    def test_verify_password(self, user_service):
        """Test password verification."""
        password = "testpassword123"
        hashed = user_service._hash_password(password)

        # Correct password should verify
        assert user_service._verify_password(password, hashed) is True

        # Wrong password should not verify
        assert user_service._verify_password("wrongpassword", hashed) is False

    @pytest.mark.asyncio
    async def test_get_user_service_dependency(self, mock_database_service):
        """Test the dependency injection function."""
        service = await get_user_service(database_service=mock_database_service)
        assert isinstance(service, UserService)
