"""Comprehensive tests for BYOK (Bring Your Own Key) functionality.

This module provides tests for the complete BYOK implementation including
database models, API endpoints, key service, and MCP integration.
"""

import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tripsage.api.models.api_key import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyValidateRequest,
    ApiKeyValidateResponse,
)
from tripsage.api.services.key import KeyService
from tripsage.api.services.key_mcp_integration import KeyMCPIntegrationService
from tripsage.models.db.api_key import ApiKeyDB


class TestApiKeyModels:
    """Test API key Pydantic models."""

    def test_api_key_create_valid(self):
        """Test creating a valid API key creation request."""
        key_data = ApiKeyCreate(
            name="Test OpenAI Key",
            service="openai",
            key="sk-test123",
            description="Test key for OpenAI",
        )

        assert key_data.name == "Test OpenAI Key"
        assert key_data.service == "openai"
        assert key_data.key == "sk-test123"
        assert key_data.description == "Test key for OpenAI"

    def test_api_key_create_invalid_service(self):
        """Test API key creation with invalid service name."""
        with pytest.raises(ValueError, match="Service name must contain only"):
            ApiKeyCreate(
                name="Test Key",
                service="Invalid Service!",
                key="sk-test123",
            )

    def test_api_key_response_model(self):
        """Test API key response model."""
        now = datetime.now(datetime.UTC)
        response = ApiKeyResponse(
            id="test-id",
            name="Test Key",
            service="openai",
            created_at=now,
            updated_at=now,
            is_valid=True,
        )

        assert response.id == "test-id"
        assert response.name == "Test Key"
        assert response.service == "openai"
        assert response.is_valid is True

    def test_api_key_validate_request(self):
        """Test API key validation request model."""
        request = ApiKeyValidateRequest(
            key="sk-test123",
            service="openai",
        )

        assert request.key == "sk-test123"
        assert request.service == "openai"

    def test_api_key_validate_response(self):
        """Test API key validation response model."""
        response = ApiKeyValidateResponse(
            is_valid=True,
            service="openai",
            message="API key is valid",
        )

        assert response.is_valid is True
        assert response.service == "openai"
        assert response.message == "API key is valid"


class TestApiKeyDBModels:
    """Test database models for API keys."""

    def test_api_key_db_valid(self):
        """Test creating a valid database API key model."""
        key_id = uuid.uuid4()
        now = datetime.now(datetime.UTC)

        key_db = ApiKeyDB(
            id=key_id,
            user_id=1,
            name="Test Key",
            service="openai",
            encrypted_key="encrypted_value",
            created_at=now,
            updated_at=now,
        )

        assert key_db.id == key_id
        assert key_db.user_id == 1
        assert key_db.name == "Test Key"
        assert key_db.service == "openai"
        assert key_db.is_active is True

    def test_api_key_db_service_validation(self):
        """Test service name validation in database model."""
        key_id = uuid.uuid4()
        now = datetime.now(datetime.UTC)

        with pytest.raises(ValueError, match="Service name must contain only"):
            ApiKeyDB(
                id=key_id,
                user_id=1,
                name="Test Key",
                service="Invalid Service!",
                encrypted_key="encrypted_value",
                created_at=now,
                updated_at=now,
            )

    def test_api_key_db_expiration_validation(self):
        """Test expiration date validation."""
        key_id = uuid.uuid4()
        now = datetime.now(datetime.UTC)
        past_date = now - timedelta(days=1)

        with pytest.raises(ValueError, match="Expiration date must be in the future"):
            ApiKeyDB(
                id=key_id,
                user_id=1,
                name="Test Key",
                service="openai",
                encrypted_key="encrypted_value",
                created_at=now,
                updated_at=now,
                expires_at=past_date,
            )

    def test_api_key_db_is_expired(self):
        """Test is_expired method."""
        key_id = uuid.uuid4()
        now = datetime.now(datetime.UTC)

        # Key without expiration
        key_no_exp = ApiKeyDB(
            id=key_id,
            user_id=1,
            name="Test Key",
            service="openai",
            encrypted_key="encrypted_value",
            created_at=now,
            updated_at=now,
        )
        assert not key_no_exp.is_expired()

        # Key with future expiration
        future_exp = now + timedelta(days=30)
        key_future = ApiKeyDB(
            id=key_id,
            user_id=1,
            name="Test Key",
            service="openai",
            encrypted_key="encrypted_value",
            created_at=now,
            updated_at=now,
            expires_at=future_exp,
        )
        assert not key_future.is_expired()

    def test_api_key_db_is_usable(self):
        """Test is_usable method."""
        key_id = uuid.uuid4()
        now = datetime.now(datetime.UTC)

        # Active, non-expired key
        key_usable = ApiKeyDB(
            id=key_id,
            user_id=1,
            name="Test Key",
            service="openai",
            encrypted_key="encrypted_value",
            created_at=now,
            updated_at=now,
            is_active=True,
        )
        assert key_usable.is_usable()

        # Inactive key
        key_inactive = ApiKeyDB(
            id=key_id,
            user_id=1,
            name="Test Key",
            service="openai",
            encrypted_key="encrypted_value",
            created_at=now,
            updated_at=now,
            is_active=False,
        )
        assert not key_inactive.is_usable()


class TestKeyService:
    """Test the KeyService class."""

    @pytest.fixture
    def key_service(self):
        """Create a KeyService instance for testing."""
        with patch.dict(os.environ, {"API_KEY_MASTER_SECRET": "test_secret"}):
            service = KeyService()
            # Mock the MCP manager
            service.mcp_manager = AsyncMock()
            return service

    @pytest.fixture
    def mock_supabase_mcp(self):
        """Create a mock Supabase MCP."""
        mock = AsyncMock()
        return mock

    def test_encryption_initialization(self, key_service):
        """Test that encryption is properly initialized."""
        assert hasattr(key_service, "master_key")
        assert hasattr(key_service, "cipher")
        assert key_service.master_key is not None

    def test_encrypt_decrypt_api_key(self, key_service):
        """Test API key encryption and decryption."""
        original_key = "sk-test123456789"

        # Encrypt the key
        encrypted = key_service._encrypt_api_key(original_key)
        assert encrypted != original_key
        assert len(encrypted) > len(original_key)

        # Decrypt the key
        decrypted = key_service._decrypt_api_key(encrypted)
        assert decrypted == original_key

    @pytest.mark.asyncio
    async def test_create_key(self, key_service, mock_supabase_mcp):
        """Test creating a new API key."""
        # Setup mocks
        key_service.mcp_manager.initialize_mcp.return_value = mock_supabase_mcp
        mock_supabase_mcp.invoke_method.return_value = {
            "data": [
                {
                    "id": "test-id",
                    "name": "Test Key",
                    "service": "openai",
                    "description": "Test description",
                    "created_at": "2025-01-22T10:00:00Z",
                    "updated_at": "2025-01-22T10:00:00Z",
                    "expires_at": None,
                }
            ]
        }

        # Create key data
        key_data = ApiKeyCreate(
            name="Test Key",
            service="openai",
            key="sk-test123",
            description="Test description",
        )

        # Call the method
        result = await key_service.create_key("user123", key_data)

        # Verify the result
        assert isinstance(result, ApiKeyResponse)
        assert result.name == "Test Key"
        assert result.service == "openai"
        assert result.description == "Test description"

        # Verify MCP calls
        mock_supabase_mcp.invoke_method.assert_called_once()
        call_args = mock_supabase_mcp.invoke_method.call_args
        assert call_args[0][0] == "insert"
        assert call_args[1]["params"]["table"] == "api_keys"

    @pytest.mark.asyncio
    async def test_list_keys(self, key_service, mock_supabase_mcp):
        """Test listing API keys for a user."""
        # Setup mocks
        key_service.mcp_manager.initialize_mcp.return_value = mock_supabase_mcp
        mock_supabase_mcp.invoke_method.return_value = {
            "data": [
                {
                    "id": "key1",
                    "name": "OpenAI Key",
                    "service": "openai",
                    "description": "Test key",
                    "created_at": "2025-01-22T10:00:00Z",
                    "updated_at": "2025-01-22T10:00:00Z",
                    "expires_at": None,
                    "last_used": None,
                },
                {
                    "id": "key2",
                    "name": "Google Maps Key",
                    "service": "google_maps",
                    "description": "Maps API key",
                    "created_at": "2025-01-22T09:00:00Z",
                    "updated_at": "2025-01-22T09:00:00Z",
                    "expires_at": None,
                    "last_used": "2025-01-22T10:30:00Z",
                },
            ]
        }

        # Call the method
        result = await key_service.list_keys("user123")

        # Verify the result
        assert len(result) == 2
        assert all(isinstance(key, ApiKeyResponse) for key in result)
        assert result[0].name == "OpenAI Key"
        assert result[1].name == "Google Maps Key"

    @pytest.mark.asyncio
    async def test_delete_key(self, key_service, mock_supabase_mcp):
        """Test deleting an API key."""
        # Setup mocks
        key_service.mcp_manager.initialize_mcp.return_value = mock_supabase_mcp
        mock_supabase_mcp.invoke_method.return_value = {"count": 1}

        # Call the method
        result = await key_service.delete_key("key123")

        # Verify the result
        assert result is True

        # Verify MCP calls
        mock_supabase_mcp.invoke_method.assert_called_once()
        call_args = mock_supabase_mcp.invoke_method.call_args
        assert call_args[0][0] == "delete"
        assert call_args[1]["params"]["query"]["id"] == "key123"

    @pytest.mark.asyncio
    async def test_validate_key_success(self, key_service):
        """Test successful API key validation."""
        # Setup mocks
        mock_mcp = AsyncMock()
        mock_mcp.invoke_method.return_value = {"valid": True}
        key_service.mcp_manager.initialize_mcp.return_value = mock_mcp

        # Call the method
        result = await key_service.validate_key("sk-test123", "openai")

        # Verify the result
        assert isinstance(result, ApiKeyValidateResponse)
        assert result.is_valid is True
        assert result.service == "openai"
        assert "valid" in result.message

    @pytest.mark.asyncio
    async def test_validate_key_failure(self, key_service):
        """Test API key validation failure."""
        # Setup mocks
        mock_mcp = AsyncMock()
        mock_mcp.invoke_method.return_value = {"valid": False, "message": "Invalid key"}
        key_service.mcp_manager.initialize_mcp.return_value = mock_mcp

        # Call the method
        result = await key_service.validate_key("invalid-key", "openai")

        # Verify the result
        assert isinstance(result, ApiKeyValidateResponse)
        assert result.is_valid is False
        assert result.service == "openai"
        assert "Invalid key" in result.message


class TestKeyMCPIntegrationService:
    """Test the KeyMCPIntegrationService class."""

    @pytest.fixture
    def mock_key_service(self):
        """Create a mock KeyService."""
        service = AsyncMock(spec=KeyService)
        return service

    @pytest.fixture
    def integration_service(self, mock_key_service):
        """Create a KeyMCPIntegrationService for testing."""
        service = KeyMCPIntegrationService(mock_key_service)
        service.mcp_manager = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_invoke_with_user_key_success(
        self, integration_service, mock_key_service
    ):
        """Test successful MCP invocation with user key."""
        # Setup mocks
        mock_key_service.get_key_for_service.return_value = "user-api-key"
        integration_service.mcp_manager.invoke.return_value = {"result": "success"}

        # Call the method
        result = await integration_service.invoke_with_user_key(
            "openai", "list_models", "user123", {"max_results": 10}
        )

        # Verify the result
        assert result == {"result": "success"}

        # Verify key lookup
        mock_key_service.get_key_for_service.assert_called_once_with(
            "user123", "openai"
        )

        # Verify MCP call with injected key
        integration_service.mcp_manager.invoke.assert_called_once()
        call_args = integration_service.mcp_manager.invoke.call_args[0]
        assert call_args[0] == "openai"
        assert call_args[1] == "list_models"

        # Verify key injection
        call_params = integration_service.mcp_manager.invoke.call_args[0][2]
        assert "api_key" in call_params
        assert call_params["api_key"] == "user-api-key"

    @pytest.mark.asyncio
    async def test_invoke_with_user_key_fallback(
        self, integration_service, mock_key_service
    ):
        """Test MCP invocation fallback when no user key."""
        # Setup mocks
        mock_key_service.get_key_for_service.return_value = None
        integration_service.mcp_manager.invoke.return_value = {"result": "success"}

        # Call the method
        result = await integration_service.invoke_with_user_key(
            "openai", "list_models", "user123", {"max_results": 10}
        )

        # Verify the result
        assert result == {"result": "success"}

        # Verify MCP call without user key injection
        integration_service.mcp_manager.invoke.assert_called_once()
        call_params = integration_service.mcp_manager.invoke.call_args[0][2]
        assert "api_key" not in call_params
        assert call_params["max_results"] == 10

    @pytest.mark.asyncio
    async def test_invoke_with_user_key_auth_failure_fallback(
        self, integration_service, mock_key_service
    ):
        """Test fallback when user key authentication fails."""
        from tripsage.mcp_abstraction.exceptions import MCPAuthenticationError

        # Setup mocks
        mock_key_service.get_key_for_service.return_value = "invalid-user-key"

        # First call fails with auth error, second succeeds
        integration_service.mcp_manager.invoke.side_effect = [
            MCPAuthenticationError("Authentication failed", mcp_name="openai"),
            {"result": "success"},
        ]

        # Call the method
        result = await integration_service.invoke_with_user_key(
            "openai", "list_models", "user123", {"max_results": 10}
        )

        # Verify the result
        assert result == {"result": "success"}

        # Verify two MCP calls (first with user key, second with default)
        assert integration_service.mcp_manager.invoke.call_count == 2

    def test_inject_api_key_openai(self, integration_service):
        """Test API key injection for OpenAI service."""
        params = {"max_results": 10}
        result = integration_service._inject_api_key(params, "openai", "sk-test123")

        assert result["api_key"] == "sk-test123"
        assert result["max_results"] == 10

    def test_inject_api_key_duffel(self, integration_service):
        """Test API key injection for Duffel service."""
        params = {"limit": 5}
        result = integration_service._inject_api_key(params, "duffel", "duffel-token")

        assert result["api_token"] == "duffel-token"
        assert result["limit"] == 5

    def test_remove_api_key_injection(self, integration_service):
        """Test removing API key injection."""
        params = {"api_key": "sk-test123", "max_results": 10}
        result = integration_service._remove_api_key_injection(params, "openai")

        assert "api_key" not in result
        assert result["max_results"] == 10

    def test_cache_operations(self, integration_service):
        """Test key caching operations."""
        # Test caching
        integration_service._cache_user_key("user123", "openai", "sk-test123")

        # Test cache retrieval
        assert "user123" in integration_service._cache
        assert integration_service._cache["user123"]["openai"] == "sk-test123"

        # Test cache removal
        integration_service._remove_from_cache("user123", "openai")
        assert "user123" not in integration_service._cache

    def test_get_cache_stats(self, integration_service):
        """Test cache statistics."""
        # Add some test data to cache
        integration_service._cache_user_key("user1", "openai", "key1")
        integration_service._cache_user_key("user1", "google_maps", "key2")
        integration_service._cache_user_key("user2", "openai", "key3")

        # Get stats
        stats = integration_service.get_cache_stats()

        assert stats["total_users"] == 2
        assert stats["total_cached_keys"] == 3
        assert set(stats["cached_services"]) == {"openai", "google_maps"}
        assert stats["cache_size"] == 2


class TestBYOKEndpoints:
    """Test BYOK API endpoints."""

    @pytest.fixture
    def mock_key_service(self):
        """Create a mock KeyService."""
        return AsyncMock(spec=KeyService)

    @pytest.fixture
    def client(self, mock_key_service):
        """Create a test client with mocked dependencies."""
        from fastapi import FastAPI

        from tripsage.api.routers.keys import router

        app = FastAPI()
        app.include_router(router, prefix="/api/keys")

        # Override dependencies
        app.dependency_overrides = {}

        return TestClient(app)

    def test_health_check(self, client):
        """Test that the test client is working."""
        # This is a basic test to ensure our test setup works
        # Since we're testing the router in isolation, we expect 422 for missing auth
        response = client.get("/api/keys")
        assert response.status_code in [
            401,
            422,
        ]  # Either unauthorized or validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
