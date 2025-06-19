"""Unit tests for WebSocket security features."""

from unittest.mock import MagicMock, Mock

import pytest
from fastapi import WebSocket

from tripsage.api.routers.websocket import (
    get_allowed_origins,
    validate_websocket_origin,
)


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket with configurable headers."""
    websocket = Mock(spec=WebSocket)
    websocket.headers = {}
    return websocket


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.websocket_allowed_origins = [
        "https://app.tripsage.com",
        "http://localhost:3000",
        "http://test.example.com",
    ]
    return settings


class TestWebSocketOriginValidation:
    """Test WebSocket Origin validation for CSWSH protection."""

    @pytest.mark.asyncio
    async def test_validate_origin_with_valid_origin(self, mock_websocket):
        """Test that valid origins are accepted."""
        # Test exact match
        mock_websocket.headers = {"origin": "https://app.tripsage.com"}
        assert await validate_websocket_origin(mock_websocket) is True

        # Test localhost
        mock_websocket.headers = {"origin": "http://localhost:3000"}
        assert await validate_websocket_origin(mock_websocket) is True

    @pytest.mark.asyncio
    async def test_validate_origin_with_invalid_origin(self, mock_websocket):
        """Test that invalid origins are rejected."""
        # Test malicious origin
        mock_websocket.headers = {"origin": "https://evil.com"}
        assert await validate_websocket_origin(mock_websocket) is False

        # Test different port
        mock_websocket.headers = {"origin": "http://localhost:8080"}
        assert await validate_websocket_origin(mock_websocket) is False

    @pytest.mark.asyncio
    async def test_validate_origin_with_no_origin_header(self, mock_websocket):
        """Test that connections without Origin header are rejected."""
        # No origin header
        mock_websocket.headers = {}
        assert await validate_websocket_origin(mock_websocket) is False

        # Empty origin header
        mock_websocket.headers = {"origin": ""}
        assert await validate_websocket_origin(mock_websocket) is False

    @pytest.mark.asyncio
    async def test_validate_origin_case_insensitive(self, mock_websocket):
        """Test that origin validation is case-insensitive."""
        # Test uppercase origin
        mock_websocket.headers = {"origin": "HTTPS://APP.TRIPSAGE.COM"}
        assert await validate_websocket_origin(mock_websocket) is True

        # Test mixed case
        mock_websocket.headers = {"origin": "Http://LocalHost:3000"}
        assert await validate_websocket_origin(mock_websocket) is True

    @pytest.mark.asyncio
    async def test_validate_origin_with_subdomain(self, mock_websocket):
        """Test origin validation with subdomains."""
        # This should pass if the allowed origin starts with the provided origin
        mock_websocket.headers = {"origin": "https://app.tripsage.com"}
        assert await validate_websocket_origin(mock_websocket) is True

        # But arbitrary subdomains should not pass
        mock_websocket.headers = {"origin": "https://evil.app.tripsage.com"}
        assert await validate_websocket_origin(mock_websocket) is False

    def test_get_allowed_origins_from_settings(self, monkeypatch, mock_settings):
        """Test that allowed origins are loaded from settings."""

        # Mock get_settings to return our mock settings
        def mock_get_settings():
            return mock_settings

        monkeypatch.setattr(
            "tripsage.api.routers.websocket.get_settings", mock_get_settings
        )

        origins = get_allowed_origins()
        assert "https://app.tripsage.com" in origins
        assert "http://localhost:3000" in origins
        assert "http://test.example.com" in origins

    def test_get_allowed_origins_with_defaults(self, monkeypatch):
        """Test that default origins are used when settings don't have them."""
        # Mock settings without websocket_allowed_origins
        settings = MagicMock()
        delattr(settings, "websocket_allowed_origins")

        def mock_get_settings():
            return settings

        monkeypatch.setattr(
            "tripsage.api.routers.websocket.get_settings", mock_get_settings
        )

        origins = get_allowed_origins()
        # Should return default origins
        assert "https://app.tripsage.com" in origins
        assert "http://localhost:3000" in origins
        assert "http://localhost:3001" in origins
        assert "http://127.0.0.1:3000" in origins

    @pytest.mark.asyncio
    async def test_validate_origin_with_path(self, mock_websocket):
        """Test that origins with paths are handled correctly."""
        # Origin with path should still match the base origin
        mock_websocket.headers = {"origin": "http://localhost:3000/some/path"}
        # Origins shouldn't have paths, but if they do, they should fail
        assert await validate_websocket_origin(mock_websocket) is False

    @pytest.mark.asyncio
    async def test_validate_origin_prevents_cswsh(self, mock_websocket):
        """Test that CSWSH attack vectors are prevented."""
        # Common CSWSH attack patterns
        attack_origins = [
            "null",  # Some browsers send 'null' for local files
            "file://",  # Local file origin
            "https://attacker.com",  # Different domain
            "http://app.tripsage.com",  # Wrong protocol
            "https://app.tripsage.com.attacker.com",  # Subdomain attack
            "https://app.tripsage.com@attacker.com",  # URL confusion
            "https://127.0.0.1:3000",  # IP instead of localhost (not in default list)
        ]

        for origin in attack_origins:
            mock_websocket.headers = {"origin": origin}
            assert await validate_websocket_origin(mock_websocket) is False, (
                f"Origin '{origin}' should have been rejected"
            )
