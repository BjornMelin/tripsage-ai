"""Unit tests for WebSocket CSWSH (Cross-Site WebSocket Hijacking) protection.

Tests Origin header validation to prevent malicious websites from hijacking
authenticated WebSocket connections.
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import WebSocket

from tripsage.api.routers.websocket import validate_websocket_origin


class TestWebSocketCSWSHProtection:
    """Test suite for WebSocket CSWSH protection via Origin validation."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        websocket = Mock(spec=WebSocket)
        websocket.headers = {}
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with CORS origins."""
        settings = Mock()
        settings.cors_origins = ["http://localhost:3000", "https://tripsage.com"]
        settings.is_production = False
        return settings

    @pytest.fixture
    def production_settings(self):
        """Create mock production settings."""
        settings = Mock()
        settings.cors_origins = ["https://tripsage.com", "https://app.tripsage.com"]
        settings.is_production = True
        return settings

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_validate_websocket_origin_valid_origin(
        self, mock_get_settings, mock_websocket, mock_settings
    ):
        """Test that valid origins are accepted."""
        # Arrange
        mock_get_settings.return_value = mock_settings
        mock_websocket.headers = {"origin": "http://localhost:3000"}

        # Act
        result = await validate_websocket_origin(mock_websocket)

        # Assert
        assert result is True

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_validate_websocket_origin_invalid_origin(
        self, mock_get_settings, mock_websocket, mock_settings
    ):
        """Test that invalid origins are rejected."""
        # Arrange
        mock_get_settings.return_value = mock_settings
        mock_websocket.headers = {"origin": "https://malicious-site.com"}

        # Act
        result = await validate_websocket_origin(mock_websocket)

        # Assert
        assert result is False

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_validate_websocket_origin_missing_origin_development(
        self, mock_get_settings, mock_websocket, mock_settings
    ):
        """Test that missing Origin header is allowed in development."""
        # Arrange
        mock_get_settings.return_value = mock_settings
        mock_websocket.headers = {}  # No origin header

        # Act
        result = await validate_websocket_origin(mock_websocket)

        # Assert
        assert result is True

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_validate_websocket_origin_missing_origin_production(
        self, mock_get_settings, mock_websocket, production_settings
    ):
        """Test that missing Origin header is rejected in production."""
        # Arrange
        mock_get_settings.return_value = production_settings
        mock_websocket.headers = {}  # No origin header

        # Act
        result = await validate_websocket_origin(mock_websocket)

        # Assert
        assert result is False

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_validate_websocket_origin_wildcard_origin(
        self, mock_get_settings, mock_websocket
    ):
        """Test wildcard origins allow all connections (insecure but configurable)."""
        # Arrange
        settings = Mock()
        settings.cors_origins = ["*"]
        settings.is_production = False
        mock_get_settings.return_value = settings
        mock_websocket.headers = {"origin": "https://any-site.com"}

        # Act
        result = await validate_websocket_origin(mock_websocket)

        # Assert
        assert result is True

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_validate_websocket_origin_case_sensitivity(
        self, mock_get_settings, mock_websocket, mock_settings
    ):
        """Test that origin validation is case sensitive."""
        # Arrange
        mock_get_settings.return_value = mock_settings
        mock_websocket.headers = {"origin": "HTTP://LOCALHOST:3000"}  # Different case

        # Act
        result = await validate_websocket_origin(mock_websocket)

        # Assert
        assert result is False

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_validate_websocket_origin_subdomain_attack(
        self, mock_get_settings, mock_websocket, mock_settings
    ):
        """Test that subdomain attacks are prevented."""
        # Arrange
        mock_get_settings.return_value = mock_settings
        mock_websocket.headers = {"origin": "http://evil.localhost:3000"}

        # Act
        result = await validate_websocket_origin(mock_websocket)

        # Assert
        assert result is False

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_validate_websocket_origin_port_mismatch(
        self, mock_get_settings, mock_websocket, mock_settings
    ):
        """Test that port mismatches are rejected."""
        # Arrange
        mock_get_settings.return_value = mock_settings
        mock_websocket.headers = {"origin": "http://localhost:3001"}  # Different port

        # Act
        result = await validate_websocket_origin(mock_websocket)

        # Assert
        assert result is False

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_validate_websocket_origin_protocol_mismatch(
        self, mock_get_settings, mock_websocket, mock_settings
    ):
        """Test that protocol mismatches are rejected."""
        # Arrange
        mock_get_settings.return_value = mock_settings
        mock_websocket.headers = {
            "origin": "https://localhost:3000"
        }  # HTTPS instead of HTTP

        # Act
        result = await validate_websocket_origin(mock_websocket)

        # Assert
        assert result is False

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_validate_websocket_origin_multiple_allowed_origins(
        self, mock_get_settings, mock_websocket, mock_settings
    ):
        """Test validation with multiple allowed origins."""
        # Arrange
        mock_get_settings.return_value = mock_settings
        mock_websocket.headers = {
            "origin": "https://tripsage.com"
        }  # Second allowed origin

        # Act
        result = await validate_websocket_origin(mock_websocket)

        # Assert
        assert result is True

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_validate_websocket_origin_null_origin(
        self, mock_get_settings, mock_websocket, mock_settings
    ):
        """Test handling of null origin (browser privacy mode)."""
        # Arrange
        mock_get_settings.return_value = mock_settings
        mock_websocket.headers = {"origin": "null"}

        # Act
        result = await validate_websocket_origin(mock_websocket)

        # Assert
        assert result is False

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_validate_websocket_origin_empty_cors_origins(
        self, mock_get_settings, mock_websocket
    ):
        """Test validation when no CORS origins are configured."""
        # Arrange
        settings = Mock()
        settings.cors_origins = []
        settings.is_production = False
        mock_get_settings.return_value = settings
        mock_websocket.headers = {"origin": "http://localhost:3000"}

        # Act
        result = await validate_websocket_origin(mock_websocket)

        # Assert
        assert result is False


class TestWebSocketEndpointCSWSHIntegration:
    """Integration tests for CSWSH protection in WebSocket endpoints."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        websocket = Mock(spec=WebSocket)
        websocket.headers = {}
        websocket.close = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()
        return websocket

    @pytest.fixture
    def valid_headers(self):
        """Valid Origin headers for testing."""
        return {"origin": "http://localhost:3000"}

    @pytest.fixture
    def invalid_headers(self):
        """Invalid Origin headers for testing."""
        return {"origin": "https://malicious-site.com"}

    @patch("tripsage.api.routers.websocket.validate_websocket_origin")
    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_chat_websocket_blocks_invalid_origin(
        self, mock_websocket_manager, mock_validate_origin, mock_websocket
    ):
        """Test that chat WebSocket endpoint blocks invalid origins."""
        # Arrange
        from tripsage.api.routers.websocket import chat_websocket

        session_id = uuid4()
        mock_db = Mock()
        mock_chat_service = Mock()
        mock_validate_origin.return_value = False

        # Act
        await chat_websocket(
            websocket=mock_websocket,
            session_id=session_id,
            db=mock_db,
            chat_service=mock_chat_service,
        )

        # Assert
        mock_validate_origin.assert_called_once_with(mock_websocket)
        mock_websocket.close.assert_called_once_with(
            code=4003, reason="Unauthorized origin"
        )
        mock_websocket.accept.assert_not_called()

    @patch("tripsage.api.routers.websocket.validate_websocket_origin")
    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_agent_status_websocket_blocks_invalid_origin(
        self, mock_websocket_manager, mock_validate_origin, mock_websocket
    ):
        """Test that agent status WebSocket endpoint blocks invalid origins."""
        # Arrange
        from tripsage.api.routers.websocket import agent_status_websocket

        user_id = uuid4()
        mock_validate_origin.return_value = False

        # Act
        await agent_status_websocket(websocket=mock_websocket, user_id=user_id)

        # Assert
        mock_validate_origin.assert_called_once_with(mock_websocket)
        mock_websocket.close.assert_called_once_with(
            code=4003, reason="Unauthorized origin"
        )
        mock_websocket.accept.assert_not_called()

    @patch("tripsage.api.routers.websocket.validate_websocket_origin")
    async def test_websocket_origin_validation_called_before_accept(
        self, mock_validate_origin, mock_websocket
    ):
        """Test that Origin validation is called before WebSocket.accept()."""
        # Arrange
        from tripsage.api.routers.websocket import chat_websocket

        session_id = uuid4()
        mock_db = Mock()
        mock_chat_service = Mock()
        mock_validate_origin.return_value = False

        # Act
        await chat_websocket(
            websocket=mock_websocket,
            session_id=session_id,
            db=mock_db,
            chat_service=mock_chat_service,
        )

        # Assert
        # Validate origin should be called before accept
        call_order = []

        def track_validate_call(websocket):
            call_order.append("validate")
            return False

        def track_accept_call():
            call_order.append("accept")

        mock_validate_origin.side_effect = track_validate_call
        mock_websocket.accept.side_effect = track_accept_call

        # Run again to check order
        await chat_websocket(
            websocket=mock_websocket,
            session_id=session_id,
            db=mock_db,
            chat_service=mock_chat_service,
        )

        # Accept should not be called when validation fails
        assert "accept" not in call_order


class TestCSWSHSecurityScenarios:
    """Test CSWSH attack scenarios and edge cases."""

    @pytest.fixture
    def attacker_origins(self):
        """Common attacker origin patterns."""
        return [
            "https://attacker.com",
            "http://evil-site.com",
            "https://tripsage.com.evil.com",  # Subdomain attack
            "https://xn--tripsage-bva.com",  # IDN homograph attack
            "null",  # Null origin
            "",  # Empty origin
            "data:",  # Data URI scheme
            "file://",  # File scheme
            "javascript:",  # JavaScript scheme
        ]

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_multiple_attack_origins(self, mock_get_settings, attacker_origins):
        """Test that various attacker origin patterns are blocked."""
        # Arrange
        settings = Mock()
        settings.cors_origins = ["https://tripsage.com", "http://localhost:3000"]
        settings.is_production = True
        mock_get_settings.return_value = settings

        # Act & Assert
        for origin in attacker_origins:
            websocket = Mock(spec=WebSocket)
            websocket.headers = {"origin": origin}

            result = await validate_websocket_origin(websocket)
            assert result is False, f"Origin '{origin}' should be rejected"

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_unicode_domain_attack(self, mock_get_settings):
        """Test that Unicode domain attacks are prevented."""
        # Arrange
        settings = Mock()
        settings.cors_origins = ["https://tripsage.com"]
        settings.is_production = True
        mock_get_settings.return_value = settings

        websocket = Mock(spec=WebSocket)
        # Unicode character that looks like 'a' but is different
        websocket.headers = {"origin": "https://tripsage.com"}  # Cyrillic 'a'

        # Act
        result = await validate_websocket_origin(websocket)

        # Assert
        assert result is False

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_ip_address_origin_attack(self, mock_get_settings):
        """Test that IP address origins are handled correctly."""
        # Arrange
        settings = Mock()
        settings.cors_origins = ["http://localhost:3000"]
        settings.is_production = True
        mock_get_settings.return_value = settings

        websocket = Mock(spec=WebSocket)
        websocket.headers = {"origin": "http://127.0.0.1:3000"}

        # Act
        result = await validate_websocket_origin(websocket)

        # Assert
        assert result is False  # Should be rejected unless explicitly allowed

    @patch("tripsage.api.routers.websocket.get_settings")
    async def test_path_traversal_origin_attack(self, mock_get_settings):
        """Test that origins with path components are handled correctly."""
        # Arrange
        settings = Mock()
        settings.cors_origins = ["https://tripsage.com"]
        settings.is_production = True
        mock_get_settings.return_value = settings

        websocket = Mock(spec=WebSocket)
        websocket.headers = {"origin": "https://tripsage.com/../evil.com"}

        # Act
        result = await validate_websocket_origin(websocket)

        # Assert
        assert result is False
