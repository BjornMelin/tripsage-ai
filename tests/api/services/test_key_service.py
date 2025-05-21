"""Tests for the key service.

This module provides tests for the key service used for API key
operations in TripSage.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.api.services.key import KeyService
from tripsage.api.services.key_monitoring import KeyOperation


@pytest.fixture
def mock_supabase_mcp():
    """Create a mock Supabase MCP client."""
    supabase_mcp = AsyncMock()
    supabase_mcp.invoke_method = AsyncMock()
    return supabase_mcp


@pytest.fixture
def mock_monitoring_service():
    """Create a mock monitoring service."""
    monitoring_service = AsyncMock()
    monitoring_service.log_operation = AsyncMock()
    monitoring_service.initialize = AsyncMock()
    monitoring_service.is_rate_limited = AsyncMock(return_value=False)
    monitoring_service._check_suspicious_patterns = AsyncMock(return_value=False)
    monitoring_service._send_alert = AsyncMock()
    return monitoring_service


@pytest.fixture
def key_service(mock_supabase_mcp, mock_monitoring_service):
    """Create a key service with mock dependencies."""
    service = KeyService()
    service.supabase_mcp = mock_supabase_mcp
    service.monitoring_service = mock_monitoring_service
    return service


@pytest.mark.asyncio
async def test_initialize(key_service, mock_monitoring_service):
    """Test initializing the key service."""
    # Reset dependencies to test initialization
    key_service.supabase_mcp = None
    key_service.monitoring_service = None

    # Mock MCP manager
    with (
        patch("tripsage.api.services.key.mcp_manager") as mock_manager,
        patch("tripsage.api.services.key.KeyMonitoringService") as mock_monitoring_cls,
    ):
        mock_manager.initialize_mcp = AsyncMock(return_value=AsyncMock())
        mock_monitoring_cls.return_value = mock_monitoring_service

        # Call initialize
        await key_service.initialize()

        # Verify mocks
        mock_manager.initialize_mcp.assert_called_once_with("supabase")
        assert key_service.supabase_mcp is not None
        assert key_service.monitoring_service == mock_monitoring_service
        mock_monitoring_service.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_list_keys(key_service, mock_supabase_mcp, mock_monitoring_service):
    """Test listing API keys."""
    # Configure mocks
    mock_supabase_mcp.invoke_method.return_value = {
        "data": [
            {
                "id": "key-1",
                "name": "Test Key 1",
                "service": "openai",
                "description": "Test key 1",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "expires_at": "2024-01-01T00:00:00Z",
                "is_valid": True,
                "last_used": "2023-01-01T00:00:00Z",
            },
            {
                "id": "key-2",
                "name": "Test Key 2",
                "service": "googlemaps",
                "description": "Test key 2",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "expires_at": None,
                "is_valid": True,
                "last_used": None,
            },
        ]
    }

    # Call list_keys
    result = await key_service.list_keys("test-user")

    # Verify result
    assert len(result) == 2
    assert result[0]["id"] == "key-1"
    assert result[0]["name"] == "Test Key 1"
    assert result[0]["service"] == "openai"
    assert result[1]["id"] == "key-2"
    assert result[1]["name"] == "Test Key 2"
    assert result[1]["service"] == "googlemaps"

    # Verify Supabase call
    mock_supabase_mcp.invoke_method.assert_called_once_with(
        "from",
        params={
            "table": "api_keys",
            "query": {"user_id": "test-user"},
        },
    )

    # Verify monitoring call
    mock_monitoring_service.log_operation.assert_called_once()
    call_args = mock_monitoring_service.log_operation.call_args[1]
    assert call_args["operation"] == KeyOperation.LIST
    assert call_args["user_id"] == "test-user"
    assert call_args["success"] is True


@pytest.mark.asyncio
async def test_get_key(key_service, mock_supabase_mcp, mock_monitoring_service):
    """Test getting an API key."""
    # Configure mocks
    mock_supabase_mcp.invoke_method.return_value = {
        "data": [
            {
                "id": "test-key",
                "user_id": "test-user",
                "name": "Test Key",
                "service": "openai",
                "description": "Test key",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "expires_at": "2024-01-01T00:00:00Z",
                "is_valid": True,
                "last_used": "2023-01-01T00:00:00Z",
            }
        ]
    }

    # Call get_key
    result = await key_service.get_key("test-key")

    # Verify result
    assert result["id"] == "test-key"
    assert result["user_id"] == "test-user"
    assert result["name"] == "Test Key"
    assert result["service"] == "openai"

    # Verify Supabase call
    mock_supabase_mcp.invoke_method.assert_called_once_with(
        "from",
        params={
            "table": "api_keys",
            "query": {"id": "test-key"},
            "limit": 1,
        },
    )

    # Verify monitoring call
    mock_monitoring_service.log_operation.assert_called_once()
    call_args = mock_monitoring_service.log_operation.call_args[1]
    assert call_args["operation"] == KeyOperation.GET
    assert call_args["key_id"] == "test-key"
    assert call_args["success"] is True


@pytest.mark.asyncio
async def test_get_key_not_found(
    key_service, mock_supabase_mcp, mock_monitoring_service
):
    """Test getting a non-existent API key."""
    # Configure mocks
    mock_supabase_mcp.invoke_method.return_value = {"data": []}

    # Call get_key
    result = await key_service.get_key("nonexistent-key")

    # Verify result
    assert result is None

    # Verify Supabase call
    mock_supabase_mcp.invoke_method.assert_called_once_with(
        "from",
        params={
            "table": "api_keys",
            "query": {"id": "nonexistent-key"},
            "limit": 1,
        },
    )

    # Verify monitoring call
    mock_monitoring_service.log_operation.assert_called_once()
    call_args = mock_monitoring_service.log_operation.call_args[1]
    assert call_args["operation"] == KeyOperation.GET
    assert call_args["key_id"] == "nonexistent-key"
    assert call_args["success"] is False


@pytest.mark.asyncio
async def test_create_key(key_service, mock_supabase_mcp, mock_monitoring_service):
    """Test creating an API key."""
    # Configure mocks
    mock_supabase_mcp.invoke_method.return_value = {
        "data": [
            {
                "id": "new-key",
                "user_id": "test-user",
                "name": "New Key",
                "service": "openai",
                "description": "New key",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "expires_at": None,
                "is_valid": True,
                "last_used": None,
            }
        ]
    }

    # Check if rate limited
    mock_monitoring_service.is_rate_limited.return_value = False

    # Call create_key
    result = await key_service.create_key(
        user_id="test-user",
        name="New Key",
        service="openai",
        api_key="sk-test-key",
        description="New key",
    )

    # Verify result
    assert result["id"] == "new-key"
    assert result["user_id"] == "test-user"
    assert result["name"] == "New Key"
    assert result["service"] == "openai"

    # Verify rate limit check
    mock_monitoring_service.is_rate_limited.assert_called_once_with(
        "test-user", KeyOperation.CREATE
    )

    # Verify Supabase calls (insert and encryption)
    assert mock_supabase_mcp.invoke_method.call_count == 2
    mock_supabase_mcp.invoke_method.assert_any_call(
        "encrypt_sensitive_data",
        params={"data": "sk-test-key"},
    )

    # Verify monitoring call
    mock_monitoring_service.log_operation.assert_called_once()
    call_args = mock_monitoring_service.log_operation.call_args[1]
    assert call_args["operation"] == KeyOperation.CREATE
    assert call_args["user_id"] == "test-user"
    assert call_args["key_id"] == "new-key"
    assert call_args["service"] == "openai"
    assert call_args["success"] is True


@pytest.mark.asyncio
async def test_create_key_rate_limited(
    key_service, mock_supabase_mcp, mock_monitoring_service
):
    """Test creating an API key when rate limited."""
    # Configure rate limiting
    mock_monitoring_service.is_rate_limited.return_value = True

    # Call create_key and expect an exception
    with pytest.raises(Exception, match="Rate limit exceeded"):
        await key_service.create_key(
            user_id="test-user",
            name="New Key",
            service="openai",
            api_key="sk-test-key",
            description="New key",
        )

    # Verify rate limit check
    mock_monitoring_service.is_rate_limited.assert_called_once_with(
        "test-user", KeyOperation.CREATE
    )

    # Verify no Supabase calls were made
    mock_supabase_mcp.invoke_method.assert_not_called()


@pytest.mark.asyncio
async def test_delete_key(key_service, mock_supabase_mcp, mock_monitoring_service):
    """Test deleting an API key."""
    # Configure mocks
    mock_supabase_mcp.invoke_method.return_value = {"count": 1}

    # Call delete_key
    result = await key_service.delete_key("test-key")

    # Verify result
    assert result is True

    # Verify Supabase call
    mock_supabase_mcp.invoke_method.assert_called_once_with(
        "delete",
        params={
            "table": "api_keys",
            "query": {"id": "test-key"},
        },
    )

    # Verify monitoring call
    mock_monitoring_service.log_operation.assert_called_once()
    call_args = mock_monitoring_service.log_operation.call_args[1]
    assert call_args["operation"] == KeyOperation.DELETE
    assert call_args["key_id"] == "test-key"
    assert call_args["success"] is True


@pytest.mark.asyncio
async def test_delete_key_not_found(
    key_service, mock_supabase_mcp, mock_monitoring_service
):
    """Test deleting a non-existent API key."""
    # Configure mocks
    mock_supabase_mcp.invoke_method.return_value = {"count": 0}

    # Call delete_key
    result = await key_service.delete_key("nonexistent-key")

    # Verify result
    assert result is False

    # Verify Supabase call
    mock_supabase_mcp.invoke_method.assert_called_once_with(
        "delete",
        params={
            "table": "api_keys",
            "query": {"id": "nonexistent-key"},
        },
    )

    # Verify monitoring call
    mock_monitoring_service.log_operation.assert_called_once()
    call_args = mock_monitoring_service.log_operation.call_args[1]
    assert call_args["operation"] == KeyOperation.DELETE
    assert call_args["key_id"] == "nonexistent-key"
    assert call_args["success"] is False


@pytest.mark.asyncio
async def test_validate_key(key_service, mock_supabase_mcp, mock_monitoring_service):
    """Test validating an API key."""
    # Mock key validation for different services
    with (
        patch(
            "tripsage.api.services.key._validate_openai_key",
            AsyncMock(return_value=True),
        ),
        patch(
            "tripsage.api.services.key._validate_googlemaps_key",
            AsyncMock(return_value=True),
        ),
    ):
        # Call validate_key for OpenAI
        openai_result = await key_service.validate_key("sk-test-key", "openai")

        # Verify OpenAI result
        assert openai_result["is_valid"] is True
        assert openai_result["service"] == "openai"
        assert "message" in openai_result

        # Call validate_key for Google Maps
        maps_result = await key_service.validate_key("maps-test-key", "googlemaps")

        # Verify Google Maps result
        assert maps_result["is_valid"] is True
        assert maps_result["service"] == "googlemaps"
        assert "message" in maps_result

        # Verify monitoring calls
        assert mock_monitoring_service.log_operation.call_count == 2
        # First call for OpenAI
        call_args = mock_monitoring_service.log_operation.call_args_list[0][1]
        assert call_args["operation"] == KeyOperation.VALIDATE
        assert call_args["service"] == "openai"
        assert call_args["success"] is True
        # Second call for Google Maps
        call_args = mock_monitoring_service.log_operation.call_args_list[1][1]
        assert call_args["operation"] == KeyOperation.VALIDATE
        assert call_args["service"] == "googlemaps"
        assert call_args["success"] is True


@pytest.mark.asyncio
async def test_validate_key_invalid(key_service, mock_monitoring_service):
    """Test validating an invalid API key."""
    # Mock key validation to return False
    with patch(
        "tripsage.api.services.key._validate_openai_key", AsyncMock(return_value=False)
    ):
        # Call validate_key
        result = await key_service.validate_key("invalid-key", "openai")

        # Verify result
        assert result["is_valid"] is False
        assert result["service"] == "openai"
        assert "Invalid" in result["message"]

        # Verify monitoring call
        mock_monitoring_service.log_operation.assert_called_once()
        call_args = mock_monitoring_service.log_operation.call_args[1]
        assert call_args["operation"] == KeyOperation.VALIDATE
        assert call_args["service"] == "openai"
        assert call_args["success"] is False


@pytest.mark.asyncio
async def test_validate_key_unsupported_service(key_service, mock_monitoring_service):
    """Test validating an API key for an unsupported service."""
    # Call validate_key for an unsupported service
    result = await key_service.validate_key("some-key", "unsupported")

    # Verify result
    assert result["is_valid"] is False
    assert result["service"] == "unsupported"
    assert "Unsupported" in result["message"]

    # Verify monitoring call
    mock_monitoring_service.log_operation.assert_called_once()
    call_args = mock_monitoring_service.log_operation.call_args[1]
    assert call_args["operation"] == KeyOperation.VALIDATE
    assert call_args["service"] == "unsupported"
    assert call_args["success"] is False


@pytest.mark.asyncio
async def test_rotate_key(key_service, mock_supabase_mcp, mock_monitoring_service):
    """Test rotating an API key."""
    # Configure mocks
    mock_supabase_mcp.invoke_method.side_effect = [
        # First call: get key for encryption
        {
            "data": [
                {
                    "id": "test-key",
                    "user_id": "test-user",
                    "name": "Test Key",
                    "service": "openai",
                }
            ]
        },
        # Second call: encrypt new key
        {"data": "encrypted-key"},
        # Third call: update key
        {
            "data": [
                {
                    "id": "test-key",
                    "user_id": "test-user",
                    "name": "Test Key",
                    "service": "openai",
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ]
        },
    ]

    # Call rotate_key
    result = await key_service.rotate_key("test-key", "sk-new-key")

    # Verify result
    assert result["id"] == "test-key"
    assert result["user_id"] == "test-user"
    assert result["name"] == "Test Key"
    assert result["service"] == "openai"

    # Verify Supabase calls
    assert mock_supabase_mcp.invoke_method.call_count == 3
    # First call: get key
    mock_supabase_mcp.invoke_method.assert_any_call(
        "from",
        params={
            "table": "api_keys",
            "query": {"id": "test-key"},
            "limit": 1,
        },
    )
    # Second call: encrypt new key
    mock_supabase_mcp.invoke_method.assert_any_call(
        "encrypt_sensitive_data",
        params={"data": "sk-new-key"},
    )
    # Third call: update key
    mock_supabase_mcp.invoke_method.assert_any_call(
        "update",
        params={
            "table": "api_keys",
            "query": {"id": "test-key"},
            "data": {
                "encrypted_key": "encrypted-key",
                "updated_at": pytest.approx(
                    datetime.utcnow().isoformat(), abs=timedelta(seconds=5)
                ),
                "is_valid": True,
            },
        },
    )

    # Verify monitoring call
    mock_monitoring_service.log_operation.assert_called_once()
    call_args = mock_monitoring_service.log_operation.call_args[1]
    assert call_args["operation"] == KeyOperation.ROTATE
    assert call_args["key_id"] == "test-key"
    assert call_args["service"] == "openai"
    assert call_args["success"] is True


def test_decrypt_api_key(key_service, mock_supabase_mcp):
    """Test decrypting an API key."""
    # Configure key_service and mock cipher
    key_service.cipher = MagicMock()
    key_service.cipher.decrypt.return_value = b"data-key"

    # Create a mock Fernet instance
    mock_fernet = MagicMock()
    mock_fernet.decrypt.return_value = b"decrypted-key"

    # Patch the Fernet class
    with patch("tripsage.api.services.key.Fernet", return_value=mock_fernet):
        # Mock base64 decoding function
        with patch("tripsage.api.services.key.base64") as mock_base64:
            mock_base64.urlsafe_b64decode.return_value = (
                b"encrypted_data_key.encrypted_key"
            )
            mock_base64.urlsafe_b64encode.return_value = b"encoded"

            # Create test data with encrypted key
            key_data = {
                "id": "test-key",
                "name": "Test Key",
                "encrypted_key": "encrypted-key-base64",
            }

            # Call _decrypt_api_key directly for testing
            result = key_service._decrypt_api_key(key_data["encrypted_key"])

            # Verify result
            assert result == "decrypted-key"

            # Verify split operation on the decoded data
            mock_base64.urlsafe_b64decode.assert_called_once_with(
                b"encrypted-key-base64"
            )


def test_encrypt_api_key(key_service, mock_supabase_mcp):
    """Test encrypting an API key."""
    # Configure key_service and mock cipher
    key_service.cipher = MagicMock()
    key_service.cipher.encrypt.return_value = b"encrypted_data_key"

    # Create a mock Fernet instance
    mock_fernet = MagicMock()
    mock_fernet.encrypt.return_value = b"encrypted_key"
    mock_fernet.generate_key.return_value = b"data_key"

    # Patch the Fernet class
    with patch("tripsage.api.services.key.Fernet") as mock_fernet_cls:
        mock_fernet_cls.return_value = mock_fernet
        mock_fernet_cls.generate_key.return_value = b"data_key"

        # Mock base64 encoding function
        with patch("tripsage.api.services.key.base64") as mock_base64:
            mock_base64.urlsafe_b64encode.return_value = b"combined_encrypted_key"

            # Call _encrypt_api_key directly for testing
            result = key_service._encrypt_api_key("test-key")

            # Verify result
            assert result == "combined_encrypted_key"

            # Verify the encryptions and base64 encoding
            mock_fernet.encrypt.assert_called_once()
            mock_base64.urlsafe_b64encode.assert_called_once()
