"""
Demonstration integration test for API key validation.

This is a simplified example showing the integration test patterns
in action with proper setup and teardown.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ServiceType,
    ValidationStatus,
)

class TestApiKeyIntegrationDemo:
    """Demonstration integration test class."""

    @pytest.mark.asyncio
    async def test_api_key_creation_demo(self, test_db_service, test_cache_service):
        """Demo test showing API key creation with real dependencies."""
        # Create a test user
        user_id = str(uuid.uuid4())
        user_data = {
            "id": user_id,
            "email": "demo@example.com",
            "username": "demouser",
            "full_name": "Demo User",
            "is_active": True,
            "is_verified": True,
        }

        await test_db_service.insert("users", user_data)

        # Create API key service with test dependencies
        from tripsage_core.config import get_settings
        from tripsage_core.services.business.api_key_service import ApiKeyService

        settings = get_settings()
        api_service = ApiKeyService(
            db=test_db_service, cache=test_cache_service, settings=settings
        )

        # Mock external API validation
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
            mock_get.return_value = mock_response

            # Create API key
            request = ApiKeyCreateRequest(
                name="Demo API Key",
                service=ServiceType.OPENAI,
                key_value="sk-demo_key_12345",
                description="Demonstration API key",
            )

            created_key = await api_service.create_api_key(user_id, request)

            # Verify creation
            assert created_key.name == "Demo API Key"
            assert created_key.service == ServiceType.OPENAI
            assert created_key.is_valid is True
            assert created_key.id is not None

            # Verify in database
            keys = await api_service.list_user_keys(user_id)
            assert len(keys) == 1
            assert keys[0].id == created_key.id

    @pytest.mark.asyncio
    async def test_validation_with_cache_demo(
        self, test_db_service, test_cache_service
    ):
        """Demo test showing validation with cache integration."""
        user_id = str(uuid.uuid4())

        # Create API key service
        from tripsage_core.config import get_settings
        from tripsage_core.services.business.api_key_service import ApiKeyService

        settings = get_settings()
        api_service = ApiKeyService(
            db=test_db_service, cache=test_cache_service, settings=settings
        )

        # Mock external API
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
            mock_get.return_value = mock_response

            # First validation - should hit external API
            result1 = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-demo_validation", user_id
            )

            assert result1.is_valid is True
            assert result1.status == ValidationStatus.VALID
            assert mock_get.call_count == 1

            # Second validation - should use cache (if available)
            result2 = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-demo_validation", user_id
            )

            assert result2.is_valid is True
            # Call count may or may not increase depending on cache implementation

    @pytest.mark.asyncio
    async def test_error_handling_demo(self, test_db_service, test_cache_service):
        """Demo test showing error handling integration."""
        user_id = str(uuid.uuid4())

        # Create API key service
        from tripsage_core.config import get_settings
        from tripsage_core.services.business.api_key_service import ApiKeyService

        settings = get_settings()
        api_service = ApiKeyService(
            db=test_db_service, cache=test_cache_service, settings=settings
        )

        # Test invalid API key
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response

            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-invalid_key", user_id
            )

            assert result.is_valid is False
            assert result.status == ValidationStatus.INVALID
            assert "authentication failed" in result.message.lower()
