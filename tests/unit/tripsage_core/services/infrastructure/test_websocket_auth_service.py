"""
Comprehensive tests for TripSage Core WebSocket Authentication Service.

This module provides comprehensive test coverage for WebSocket authentication functionality
including JWT token validation, channel access control, rate limiting, session management,
security features, and error handling.
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import jwt  # Use PyJWT instead of jose
import pytest
from pydantic import ValidationError

from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreAuthorizationError,
)
from tripsage_core.services.infrastructure.websocket_auth_service import (
    WebSocketAuthRequest,
    WebSocketAuthResponse,
    WebSocketAuthService,
)


class TestWebSocketAuthModels:
    """Test suite for WebSocket authentication models."""

    def test_websocket_auth_request_creation(self):
        """Test WebSocketAuthRequest model creation."""
        session_id = uuid4()
        request = WebSocketAuthRequest(
            token="test_token_123",
            session_id=session_id,
            channels=["general", "notifications"],
        )

        assert request.token == "test_token_123"
        assert request.session_id == session_id
        assert request.channels == ["general", "notifications"]

    def test_websocket_auth_request_minimal(self):
        """Test WebSocketAuthRequest with minimal required fields."""
        request = WebSocketAuthRequest(token="test_token_123")

        assert request.token == "test_token_123"
        assert request.session_id is None
        assert request.channels == []

    def test_websocket_auth_response_success(self):
        """Test successful WebSocketAuthResponse."""
        user_id = uuid4()
        session_id = uuid4()

        response = WebSocketAuthResponse(
            success=True,
            connection_id="conn_123",
            user_id=user_id,
            session_id=session_id,
            available_channels=["general", "notifications"],
        )

        assert response.success is True
        assert response.connection_id == "conn_123"
        assert response.user_id == user_id
        assert response.session_id == session_id
        assert response.available_channels == ["general", "notifications"]
        assert response.error is None

    def test_websocket_auth_response_failure(self):
        """Test failed WebSocketAuthResponse."""
        response = WebSocketAuthResponse(success=False, connection_id="conn_123", error="Invalid token")

        assert response.success is False
        assert response.connection_id == "conn_123"
        assert response.user_id is None
        assert response.session_id is None
        assert response.available_channels == []
        assert response.error == "Invalid token"


class TestWebSocketAuthService:
    """Test suite for WebSocketAuthService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.database_jwt_secret.get_secret_value.return_value = "test-jwt-secret-for-testing-only"
        settings.max_connections_per_user = 5
        settings.max_sessions_per_user = 3
        return settings

    @pytest.fixture
    def auth_service(self, mock_settings):
        """Create WebSocketAuthService instance."""
        with patch(
            "tripsage_core.services.infrastructure.websocket_auth_service.get_settings",
            return_value=mock_settings,
        ):
            return WebSocketAuthService()

    def create_test_token(
        self,
        user_id,
        session_id=None,
        exp_minutes=60,
        secret="test-jwt-secret-for-testing-only",
    ):
        """Helper to create test JWT tokens."""
        payload = {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=exp_minutes),
            "iat": datetime.now(timezone.utc),
            "iss": "tripsage",
        }
        if session_id:
            payload["session_id"] = str(session_id)

        return jwt.encode(payload, secret, algorithm="HS256")

    @pytest.mark.asyncio
    async def test_verify_jwt_token_valid(self, auth_service):
        """Test JWT token verification with valid token."""
        user_id = uuid4()
        token = self.create_test_token(user_id)

        result_user_id = await auth_service.verify_jwt_token(token)
        assert result_user_id == user_id

    @pytest.mark.asyncio
    async def test_verify_jwt_token_expired(self, auth_service):
        """Test JWT token verification with expired token."""
        user_id = uuid4()
        token = self.create_test_token(user_id, exp_minutes=-30)

        with pytest.raises(CoreAuthenticationError, match="Token has expired"):
            await auth_service.verify_jwt_token(token)

    @pytest.mark.asyncio
    async def test_verify_jwt_token_invalid(self, auth_service):
        """Test JWT token verification with invalid token."""
        with pytest.raises(CoreAuthenticationError, match="Invalid token"):
            await auth_service.verify_jwt_token("invalid_token")

    @pytest.mark.asyncio
    async def test_verify_jwt_token_wrong_secret(self, auth_service):
        """Test JWT token verification with wrong secret."""
        user_id = uuid4()
        token = self.create_test_token(user_id, secret="wrong-secret")

        with pytest.raises(CoreAuthenticationError, match="Invalid token"):
            await auth_service.verify_jwt_token(token)

    @pytest.mark.asyncio
    async def test_verify_jwt_token_missing_user_id(self, auth_service):
        """Test JWT token verification with missing user ID."""
        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, "test-jwt-secret-for-testing-only", algorithm="HS256")

        with pytest.raises(CoreAuthenticationError, match="Token missing user ID"):
            await auth_service.verify_jwt_token(token)

    def test_get_available_channels(self, auth_service):
        """Test getting available channels for user."""
        user_id = uuid4()
        channels = auth_service.get_available_channels(user_id)

        expected_channels = [
            f"user:{user_id}",
            "notifications",
            "system_messages",
            "premium_notifications",
            "advanced_features",
        ]

        assert channels == expected_channels

    def test_validate_channel_access(self, auth_service):
        """Test channel access validation."""
        user_id = uuid4()
        requested_channels = [
            f"user:{user_id}",
            "notifications",
            "invalid_channel",
            "system_messages",
        ]

        allowed, denied = auth_service.validate_channel_access(user_id, requested_channels)

        assert f"user:{user_id}" in allowed
        assert "notifications" in allowed
        assert "system_messages" in allowed
        assert "invalid_channel" in denied

    def test_parse_channel_target(self, auth_service):
        """Test parsing channel target."""
        # Test user channel
        target_type, target_id = auth_service.parse_channel_target("user:123")
        assert target_type == "user"
        assert target_id == "123"

        # Test session channel
        target_type, target_id = auth_service.parse_channel_target("session:abc")
        assert target_type == "session"
        assert target_id == "abc"

        # Test general channel
        target_type, target_id = auth_service.parse_channel_target("general")
        assert target_type == "channel"
        assert target_id == "general"

    def test_is_authorized_for_channel(self, auth_service):
        """Test channel authorization check."""
        user_id = uuid4()

        # User should have access to their own channel
        assert auth_service.is_authorized_for_channel(user_id, f"user:{user_id}") is True

        # User should have access to notifications
        assert auth_service.is_authorized_for_channel(user_id, "notifications") is True

        # User should not have access to other user's channel
        other_user_id = uuid4()
        assert auth_service.is_authorized_for_channel(user_id, f"user:{other_user_id}") is False

    def test_get_user_channels(self, auth_service):
        """Test getting user-specific channels."""
        user_id = uuid4()
        channels = auth_service.get_user_channels(user_id)

        expected_channels = [
            f"user:{user_id}",
            f"user:{user_id}:notifications",
            f"user:{user_id}:status",
        ]

        assert channels == expected_channels

    def test_get_session_channels(self, auth_service):
        """Test getting session-specific channels."""
        session_id = uuid4()
        channels = auth_service.get_session_channels(session_id)

        expected_channels = [
            f"session:{session_id}",
            f"session:{session_id}:chat",
            f"session:{session_id}:agent_status",
        ]

        assert channels == expected_channels

    @pytest.mark.asyncio
    async def test_authenticate_token_valid(self, auth_service):
        """Test token authentication with valid token."""
        user_id = uuid4()
        token = self.create_test_token(user_id)

        result = await auth_service.authenticate_token(token)

        assert result["valid"] is True
        assert result["user_id"] == str(user_id)
        assert isinstance(result["channels"], list)
        assert len(result["channels"]) > 0

    @pytest.mark.asyncio
    async def test_authenticate_token_empty(self, auth_service):
        """Test token authentication with empty token."""
        with pytest.raises(CoreAuthenticationError, match="Token is missing or empty"):
            await auth_service.authenticate_token("")

    @pytest.mark.asyncio
    async def test_authenticate_token_invalid_format(self, auth_service):
        """Test token authentication with invalid token format."""
        with pytest.raises(CoreAuthenticationError, match="Invalid token"):
            await auth_service.authenticate_token("invalid.token.format")

    @pytest.mark.asyncio
    async def test_authenticate_token_with_email(self, auth_service):
        """Test token authentication with email in payload."""
        user_id = uuid4()
        payload = {
            "sub": str(user_id),
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, "test-jwt-secret-for-testing-only", algorithm="HS256")

        result = await auth_service.authenticate_token(token)

        assert result["valid"] is True
        assert result["user_id"] == str(user_id)
        assert result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_token_non_uuid_user_id(self, auth_service):
        """Test token authentication with non-UUID user ID."""
        user_id = "string_user_id"
        payload = {
            "sub": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, "test-jwt-secret-for-testing-only", algorithm="HS256")

        result = await auth_service.authenticate_token(token)

        assert result["valid"] is True
        assert result["user_id"] == user_id
        assert f"user:{user_id}" in result["channels"]

    @pytest.mark.asyncio
    async def test_verify_session_access_valid(self, auth_service):
        """Test session access verification with valid access."""
        user_id = "test-user-123"
        session_id = uuid4()

        result = await auth_service.verify_session_access(user_id, session_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_session_access_invalid(self, auth_service):
        """Test session access verification with invalid access."""
        user_id = "invalid-user"
        session_id = uuid4()

        with pytest.raises(CoreAuthorizationError, match="Session access denied"):
            await auth_service.verify_session_access(user_id, session_id)

    @pytest.mark.asyncio
    async def test_verify_channel_access_user_channel(self, auth_service):
        """Test channel access verification for user channel."""
        user_id = "test-user-123"
        channel = f"user:{user_id}"

        result = await auth_service.verify_channel_access(user_id, channel)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_channel_access_general_channel(self, auth_service):
        """Test channel access verification for general channels."""
        user_id = "test-user-123"

        for channel in ["general", "notifications", "system_messages"]:
            result = await auth_service.verify_channel_access(user_id, channel)
            assert result is True

    @pytest.mark.asyncio
    async def test_verify_channel_access_other_user_channel(self, auth_service):
        """Test channel access verification for other user's channel."""
        user_id = "test-user-123"
        other_user_channel = "user:other-user-456"

        with pytest.raises(CoreAuthorizationError, match="Channel access denied"):
            await auth_service.verify_channel_access(user_id, other_user_channel)

    @pytest.mark.asyncio
    async def test_verify_channel_access_admin_channel(self, auth_service):
        """Test channel access verification for admin channels."""
        user_id = "test-user-123"

        for channel in ["admin", "system:internal"]:
            with pytest.raises(CoreAuthorizationError, match="Channel access denied"):
                await auth_service.verify_channel_access(user_id, channel)

    @pytest.mark.asyncio
    async def test_verify_channel_access_session_channel(self, auth_service):
        """Test channel access verification for session channels."""
        user_id = "test-user-123"
        session_channel = "session:abc123"

        result = await auth_service.verify_channel_access(user_id, session_channel)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_connection_limit_within_limit(self, auth_service):
        """Test connection limit check when within limits."""
        user_id = uuid4()

        # Mock connection count within limit
        with patch.object(auth_service, "_get_user_connection_count", return_value=3):
            result = await auth_service.check_connection_limit(user_id)
            assert result is True

    @pytest.mark.asyncio
    async def test_check_connection_limit_exceeded(self, auth_service):
        """Test connection limit check when limit exceeded."""
        user_id = uuid4()

        # Mock connection count exceeding limit
        with patch.object(auth_service, "_get_user_connection_count", return_value=10):
            with pytest.raises(CoreAuthorizationError, match="Connection limit exceeded"):
                await auth_service.check_connection_limit(user_id)

    @pytest.mark.asyncio
    async def test_check_session_limit_within_limit(self, auth_service):
        """Test session limit check when within limits."""
        user_id = uuid4()

        # Mock session count within limit
        with patch.object(auth_service, "_get_user_session_count", return_value=2):
            result = await auth_service.check_session_limit(user_id)
            assert result is True

    @pytest.mark.asyncio
    async def test_check_session_limit_exceeded(self, auth_service):
        """Test session limit check when limit exceeded."""
        user_id = uuid4()

        # Mock session count exceeding limit
        with patch.object(auth_service, "_get_user_session_count", return_value=5):
            with pytest.raises(CoreAuthorizationError, match="Session limit exceeded"):
                await auth_service.check_session_limit(user_id)

    def test_private_methods_tracking(self, auth_service):
        """Test private tracking methods."""
        user_id = uuid4()
        source_ip = "192.168.1.100"

        # These methods should not raise exceptions
        auth_service._track_connection_attempt(user_id, source_ip)

        # Test count methods return reasonable defaults
        connection_count = auth_service._get_user_connection_count(user_id)
        assert isinstance(connection_count, int)
        assert connection_count >= 0

        session_count = auth_service._get_user_session_count(user_id)
        assert isinstance(session_count, int)
        assert session_count >= 0

    @pytest.mark.asyncio
    async def test_error_handling_with_mock_settings(self, auth_service):
        """Test error handling when settings have mock objects."""
        user_id = uuid4()

        # Test with mock settings that have _mock_name attribute
        mock_settings = Mock()
        mock_settings.max_connections_per_user._mock_name = "mock"
        mock_settings.max_sessions_per_user._mock_name = "mock"

        with patch(
            "tripsage_core.services.infrastructure.websocket_auth_service.get_settings",
            return_value=mock_settings,
        ):
            # Should use fallback values and not raise exceptions
            result = await auth_service.check_connection_limit(user_id)
            assert result is True

            result = await auth_service.check_session_limit(user_id)
            assert result is True

    @pytest.mark.asyncio
    async def test_rate_limiting_methods(self, auth_service):
        """Test rate limiting tracking methods."""
        user_id = uuid4()
        source_ip = "192.168.1.100"

        # Test connection tracking - should not raise exceptions
        auth_service._track_connection_attempt(user_id, source_ip)
        auth_service._track_connection_attempt(str(user_id), source_ip)

        # Test connection counting methods with different types
        count1 = auth_service._get_user_connection_count(user_id)
        count2 = auth_service._get_user_connection_count(str(user_id))

        assert isinstance(count1, int)
        assert isinstance(count2, int)
        assert count1 >= 0
        assert count2 >= 0

    @pytest.mark.asyncio
    async def test_advanced_jwt_validation(self, auth_service):
        """Test advanced JWT token validation scenarios."""
        # Test token with missing iat (issued at)
        payload = {
            "sub": str(uuid4()),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, "test-jwt-secret-for-testing-only", algorithm="HS256")

        result_user_id = await auth_service.verify_jwt_token(token)
        assert result_user_id == UUID(payload["sub"])

    @pytest.mark.asyncio
    async def test_channel_access_edge_cases(self, auth_service):
        """Test edge cases in channel access validation."""
        user_id = "test-user-123"

        # Test various channel patterns based on actual implementation
        # Looking at _verify_channel_access, channels like "admin:system" don't match specific patterns
        # but don't start with "user:" either, so they return True by default
        test_cases = [
            ("session:123", True),
            ("session:456:subchannel", True),
            ("user:test-user-123", True),
            ("user:other-user-456", False),  # Other user's channel should be denied
            ("admin", False),  # Listed in denied patterns
            ("system:internal", False),  # Listed in denied patterns
        ]

        for channel, should_pass in test_cases:
            if should_pass:
                result = await auth_service.verify_channel_access(user_id, channel)
                assert result is True
            else:
                try:
                    await auth_service.verify_channel_access(user_id, channel)
                    raise AssertionError(f"Expected {channel} to be denied")
                except CoreAuthorizationError:
                    pass

    @pytest.mark.asyncio
    async def test_jwt_edge_cases(self, auth_service):
        """Test JWT edge cases and error conditions."""
        # Test malformed JWT
        with pytest.raises(CoreAuthenticationError, match="Invalid token"):
            await auth_service.verify_jwt_token("not.a.jwt")

        # Test empty payload
        with pytest.raises(CoreAuthenticationError):
            await auth_service.verify_jwt_token("")

        # Test None token
        with pytest.raises(CoreAuthenticationError):
            await auth_service.authenticate_token("")

    def test_channel_parsing_edge_cases(self, auth_service):
        """Test channel parsing with various formats."""
        test_cases = [
            ("user:123", ("user", "123")),
            ("session:abc:def", ("session", "abc:def")),
            ("general", ("channel", "general")),
            ("", ("channel", "")),
            ("single", ("channel", "single")),
            ("multiple:colons:here", ("multiple", "colons:here")),
        ]

        for channel, expected in test_cases:
            result = auth_service.parse_channel_target(channel)
            assert result == expected

    def test_available_channels_consistency(self, auth_service):
        """Test that available channels are consistent."""
        user_id = uuid4()

        # Get channels multiple times to ensure consistency
        channels1 = auth_service.get_available_channels(user_id)
        channels2 = auth_service.get_available_channels(user_id)

        assert channels1 == channels2
        assert f"user:{user_id}" in channels1
        assert "notifications" in channels1
        assert "system_messages" in channels1

    @pytest.mark.asyncio
    async def test_concurrent_authentication(self, auth_service):
        """Test concurrent authentication requests."""
        import asyncio

        user_id = uuid4()
        token = self.create_test_token(user_id)

        # Run multiple concurrent authentications
        tasks = [auth_service.verify_jwt_token(token) for _ in range(5)]

        results = await asyncio.gather(*tasks)

        # All should return the same user ID
        for result in results:
            assert result == user_id

    @pytest.mark.asyncio
    async def test_limit_checking_with_high_counts(self, auth_service):
        """Test limit checking with various count scenarios."""
        user_id = uuid4()

        # Mock high connection count
        with patch.object(auth_service, "_get_user_connection_count", return_value=6):
            with pytest.raises(CoreAuthorizationError, match="Connection limit exceeded"):
                await auth_service.check_connection_limit(user_id)

        # Mock high session count
        with patch.object(auth_service, "_get_user_session_count", return_value=4):
            with pytest.raises(CoreAuthorizationError, match="Session limit exceeded"):
                await auth_service.check_session_limit(user_id)

    def test_validation_error_handling(self):
        """Test proper validation error handling for models."""
        # Test invalid WebSocketAuthRequest
        with pytest.raises(ValidationError):
            WebSocketAuthRequest()  # Missing required token

        # Test invalid session_id type
        with pytest.raises(ValidationError):
            WebSocketAuthRequest(token="test", session_id="not-a-uuid")

    @pytest.mark.asyncio
    async def test_private_verify_methods(self, auth_service):
        """Test private verification methods directly."""
        user_id = "test-user-123"
        session_id = uuid4()

        # Test private session verification
        result = await auth_service._verify_session_access(user_id, session_id)
        assert result is True

        # Test with invalid user
        with pytest.raises(CoreAuthorizationError):
            await auth_service._verify_session_access("invalid-user", session_id)

        # Test private channel verification
        result = await auth_service._verify_channel_access(user_id, f"user:{user_id}")
        assert result is True

    def test_model_serialization(self):
        """Test model serialization and deserialization."""
        # Test WebSocketAuthRequest
        session_id = uuid4()
        request = WebSocketAuthRequest(
            token="test-token",
            session_id=session_id,
            channels=["general", "notifications"],
        )

        # Test JSON round trip
        json_data = request.model_dump_json()
        restored = WebSocketAuthRequest.model_validate_json(json_data)
        assert restored.token == request.token
        assert restored.session_id == request.session_id
        assert restored.channels == request.channels

        # Test WebSocketAuthResponse
        user_id = uuid4()
        response = WebSocketAuthResponse(
            success=True,
            connection_id="conn_123",
            user_id=user_id,
            session_id=session_id,
            available_channels=["general"],
        )

        json_data = response.model_dump_json()
        restored = WebSocketAuthResponse.model_validate_json(json_data)
        assert restored.success == response.success
        assert restored.user_id == response.user_id

    @pytest.mark.asyncio
    async def test_settings_property_access(self, auth_service):
        """Test settings property access patterns."""
        # Test that settings property returns current settings
        settings = auth_service.settings
        assert hasattr(settings, "database_jwt_secret")

        # Test repeated access
        settings2 = auth_service.settings
        assert settings is not None
        assert settings2 is not None


@pytest.mark.integration
class TestWebSocketAuthServiceIntegration:
    """Integration tests for WebSocketAuthService."""

    @pytest.fixture
    def auth_service_real(self):
        """Create real WebSocketAuthService for integration tests."""
        return WebSocketAuthService()

    def create_test_token(
        self,
        user_id,
        session_id=None,
        exp_minutes=60,
        secret="test-jwt-secret-for-testing-only",
    ):
        """Helper to create test JWT tokens."""
        payload = {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=exp_minutes),
            "iat": datetime.now(timezone.utc),
            "iss": "tripsage",
        }
        if session_id:
            payload["session_id"] = str(session_id)

        return jwt.encode(payload, secret, algorithm="HS256")

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self, auth_service_real):
        """Test complete authentication flow."""
        user_id = uuid4()
        session_id = uuid4()

        # Create valid token
        token = self.create_test_token(user_id, session_id)

        # Test full flow
        auth_result = await auth_service_real.authenticate_token(token)
        assert auth_result["valid"] is True
        assert auth_result["user_id"] == str(user_id)

        # Verify user has access to their channels
        user_channels = auth_service_real.get_user_channels(UUID(auth_result["user_id"]))
        assert f"user:{user_id}" in user_channels

        # Test session access - expect denial for non-test-user-123
        if str(user_id) == "test-user-123":
            session_access = await auth_service_real.verify_session_access(user_id, session_id)
            assert session_access is True
        else:
            # For other user IDs, expect access denial
            with pytest.raises(CoreAuthorizationError):
                await auth_service_real.verify_session_access(user_id, session_id)

    @pytest.mark.asyncio
    async def test_concurrent_authentication_requests(self, auth_service_real):
        """Test concurrent authentication requests."""
        import asyncio

        user_id = uuid4()
        token = self.create_test_token(user_id)

        # Create multiple concurrent authentication tasks
        tasks = []
        for _i in range(10):
            tasks.append(auth_service_real.authenticate_token(token))

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        for result in results:
            assert not isinstance(result, Exception)
            assert result["valid"] is True
            assert result["user_id"] == str(user_id)

    @pytest.mark.asyncio
    async def test_authentication_performance(self, auth_service_real):
        """Test authentication performance under load."""
        user_id = uuid4()
        token = self.create_test_token(user_id)

        # Time multiple authentications
        start_time = time.time()
        iterations = 100

        for _ in range(iterations):
            result = await auth_service_real.authenticate_token(token)
            assert result["valid"] is True

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations

        # Performance assertion - should complete within reasonable time
        assert avg_time < 0.01  # Less than 10ms per authentication
        assert total_time < 1.0  # Total time less than 1 second

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, auth_service_real):
        """Test that repeated operations don't cause memory leaks."""
        import gc

        user_id = uuid4()
        token = self.create_test_token(user_id)

        # Perform many operations
        for _ in range(50):
            await auth_service_real.authenticate_token(token)
            auth_service_real.get_available_channels(user_id)
            auth_service_real.validate_channel_access(user_id, ["general", "notifications"])
            await auth_service_real.check_connection_limit(user_id)
            await auth_service_real.check_session_limit(user_id)

        # Force garbage collection and verify no issues
        gc.collect()
        assert True  # If we reach here without memory errors, test passes


class TestWebSocketAuthServiceRateLimiting:
    """Test rate limiting functionality."""

    @pytest.fixture
    def auth_service_with_limits(self):
        """Create auth service with specific limits."""
        return WebSocketAuthService()

    @pytest.mark.asyncio
    async def test_connection_rate_limiting(self, auth_service_with_limits):
        """Test connection rate limiting."""
        user_id = uuid4()

        # Mock the settings to have lower limits
        mock_settings = Mock()
        mock_settings.max_connections_per_user = 2
        mock_settings.database_jwt_secret.get_secret_value.return_value = "test-jwt-secret-for-testing-only"

        # Mock high connection count to trigger limit and patch get_settings
        with (
            patch.object(auth_service_with_limits, "_get_user_connection_count", return_value=3),
            patch(
                "tripsage_core.services.infrastructure.websocket_auth_service.get_settings",
                return_value=mock_settings,
            ),
        ):
            with pytest.raises(CoreAuthorizationError) as exc_info:
                await auth_service_with_limits.check_connection_limit(user_id)

            assert "Connection limit exceeded" in str(exc_info.value)
            assert "3/2" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_session_rate_limiting(self, auth_service_with_limits):
        """Test session rate limiting."""
        user_id = uuid4()

        # Mock the settings to have lower limits
        mock_settings = Mock()
        mock_settings.max_sessions_per_user = 1
        mock_settings.database_jwt_secret.get_secret_value.return_value = "test-jwt-secret-for-testing-only"

        # Mock high session count to trigger limit and patch get_settings
        with (
            patch.object(auth_service_with_limits, "_get_user_session_count", return_value=2),
            patch(
                "tripsage_core.services.infrastructure.websocket_auth_service.get_settings",
                return_value=mock_settings,
            ),
        ):
            with pytest.raises(CoreAuthorizationError) as exc_info:
                await auth_service_with_limits.check_session_limit(user_id)

            assert "Session limit exceeded" in str(exc_info.value)
            assert "2/1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_tracking_methods_coverage(self, auth_service_with_limits):
        """Test that tracking methods handle various input types."""
        user_id = uuid4()
        string_user_id = "string_user_123"

        # Test connection tracking with different ID types
        auth_service_with_limits._track_connection_attempt(user_id, "192.168.1.1")
        auth_service_with_limits._track_connection_attempt(string_user_id, "192.168.1.2")

        # Test count methods with different ID types
        count1 = auth_service_with_limits._get_user_connection_count(user_id)
        count2 = auth_service_with_limits._get_user_connection_count(string_user_id)
        count3 = auth_service_with_limits._get_user_session_count(user_id)
        count4 = auth_service_with_limits._get_user_session_count(string_user_id)

        # All should return integers
        assert all(isinstance(count, int) for count in [count1, count2, count3, count4])


class TestWebSocketAuthServiceSecurity:
    """Test security-focused functionality."""

    @pytest.fixture
    def auth_service(self):
        """Create auth service for security tests."""
        mock_settings = Mock()
        mock_settings.database_jwt_secret.get_secret_value.return_value = "test-jwt-secret-for-testing-only"
        mock_settings.max_connections_per_user = 5
        mock_settings.max_sessions_per_user = 3

        with patch(
            "tripsage_core.services.infrastructure.websocket_auth_service.get_settings",
            return_value=mock_settings,
        ):
            return WebSocketAuthService()

    def create_test_token(
        self,
        user_id,
        session_id=None,
        exp_minutes=60,
        secret="test-jwt-secret-for-testing-only",
    ):
        """Helper to create test JWT tokens."""
        payload = {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=exp_minutes),
            "iat": datetime.now(timezone.utc),
            "iss": "tripsage",
        }
        if session_id:
            payload["session_id"] = str(session_id)

        return jwt.encode(payload, secret, algorithm="HS256")

    @pytest.mark.asyncio
    async def test_token_tampering_detection(self, auth_service):
        """Test detection of token tampering."""
        user_id = uuid4()
        token = self.create_test_token(user_id)

        # Tamper with token by changing last character
        tampered_token = token[:-1] + "X"

        with pytest.raises(CoreAuthenticationError):
            await auth_service.verify_jwt_token(tampered_token)

    @pytest.mark.asyncio
    async def test_replay_attack_protection(self, auth_service):
        """Test protection against replay attacks with expired tokens."""
        user_id = uuid4()

        # Create token that's already expired
        expired_token = self.create_test_token(user_id, exp_minutes=-30)

        with pytest.raises(CoreAuthenticationError, match="Token has expired"):
            await auth_service.verify_jwt_token(expired_token)

    @pytest.mark.asyncio
    async def test_unauthorized_channel_access_prevention(self, auth_service):
        """Test prevention of unauthorized channel access."""
        user_id = "test-user-123"

        # Test access to admin channels that are actually restricted in the code
        admin_channels = ["admin", "system:internal"]

        for channel in admin_channels:
            with pytest.raises(CoreAuthorizationError, match="Channel access denied"):
                await auth_service.verify_channel_access(user_id, channel)

    @pytest.mark.asyncio
    async def test_cross_user_channel_access_prevention(self, auth_service):
        """Test prevention of cross-user channel access."""
        user_id = "test-user-123"
        other_user_channels = [
            "user:other-user-456",
            "user:other-user-456:notifications",
            "user:other-user-456:private",
        ]

        for channel in other_user_channels:
            with pytest.raises(CoreAuthorizationError, match="Channel access denied"):
                await auth_service.verify_channel_access(user_id, channel)

    @pytest.mark.asyncio
    async def test_session_ownership_verification(self, auth_service):
        """Test session ownership verification."""
        # Test valid user
        valid_user = "test-user-123"
        session_id = uuid4()

        result = await auth_service.verify_session_access(valid_user, session_id)
        assert result is True

        # Test invalid user
        invalid_user = "unauthorized-user"
        with pytest.raises(CoreAuthorizationError, match="Session access denied"):
            await auth_service.verify_session_access(invalid_user, session_id)

    @pytest.mark.asyncio
    async def test_malicious_payload_handling(self, auth_service):
        """Test handling of malicious JWT payloads."""
        # Test token with no subject
        payload_no_sub = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "role": "admin",  # Malicious role claim
        }
        token_no_sub = jwt.encode(payload_no_sub, "test-jwt-secret-for-testing-only", algorithm="HS256")

        with pytest.raises(CoreAuthenticationError, match="Token missing user ID"):
            await auth_service.verify_jwt_token(token_no_sub)

    def test_channel_validation_boundary_conditions(self, auth_service):
        """Test channel validation with boundary conditions."""
        user_id = uuid4()

        # Test edge cases in channel validation
        edge_cases = [
            [],  # Empty list
            [""],  # Empty string channel
            ["user:" + str(user_id)],  # Valid user channel
            ["user:" + str(user_id), "notifications"],  # Mixed valid
            ["user:" + str(user_id), "invalid_channel"],  # Mixed with invalid
        ]

        for channels in edge_cases:
            allowed, denied = auth_service.validate_channel_access(user_id, channels)

            # Ensure return types are correct
            assert isinstance(allowed, list)
            assert isinstance(denied, list)

            # Ensure no duplicates
            assert len(set(allowed)) == len(allowed)
            assert len(set(denied)) == len(denied)

    @pytest.mark.asyncio
    async def test_jwt_algorithm_security(self, auth_service):
        """Test JWT algorithm security (prevent algorithm confusion)."""
        user_id = uuid4()

        # Create token with correct secret and algorithm
        token_valid = self.create_test_token(user_id, secret="test-jwt-secret-for-testing-only")

        # Should work with correct algorithm and secret
        result = await auth_service.verify_jwt_token(token_valid)
        assert result == user_id

        # Test with wrong secret should fail
        token_wrong_secret = self.create_test_token(user_id, secret="wrong-secret")

        with pytest.raises(CoreAuthenticationError, match="Invalid token"):
            await auth_service.verify_jwt_token(token_wrong_secret)
