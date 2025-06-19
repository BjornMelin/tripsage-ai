"""
Comprehensive tests for TripSage Core Key Monitoring Service.

This module provides comprehensive test coverage for key monitoring service
functionality including operation logging, suspicious pattern detection, rate
limiting, security features, health metrics, and error handling.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from tripsage_core.config import Settings
from tripsage_core.services.infrastructure.key_monitoring_service import (
    KeyMonitoringService,
    KeyOperation,
    KeyOperationRateLimitMiddleware,
    check_key_expiration,
    clear_sensitive_data,
    constant_time_compare,
    get_key_health_metrics,
    monitor_key_operation,
    secure_random_token,
)


class TestKeyOperation:
    """Test suite for KeyOperation enum."""

    def test_key_operation_values(self):
        """Test KeyOperation enum values."""
        assert KeyOperation.CREATE == "create"
        assert KeyOperation.LIST == "list"
        assert KeyOperation.DELETE == "delete"
        assert KeyOperation.VALIDATE == "validate"
        assert KeyOperation.ROTATE == "rotate"
        assert KeyOperation.ACCESS == "access"

    def test_key_operation_string_conversion(self):
        """Test KeyOperation string conversion."""
        assert str(KeyOperation.CREATE) == "create"
        assert KeyOperation.CREATE.value == "create"


class TestKeyMonitoringService:
    """Test suite for KeyMonitoringService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        return settings

    @pytest.fixture
    def mock_cache_service(self):
        """Create a mock cache service."""
        cache = AsyncMock()
        cache.get_json = AsyncMock(return_value=None)
        cache.set_json = AsyncMock(return_value=True)
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.incr = AsyncMock(return_value=1)
        return cache

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock database service."""
        db = AsyncMock()
        db.select = AsyncMock(return_value=[])
        db.count = AsyncMock(return_value=0)
        return db

    @pytest.fixture
    def key_monitoring_service(
        self, mock_settings, mock_cache_service, mock_database_service
    ):
        """Create a KeyMonitoringService instance with mocked dependencies."""
        service = KeyMonitoringService(settings=mock_settings)
        service.cache_service = mock_cache_service
        service.database_service = mock_database_service
        return service

    @pytest.mark.asyncio
    async def test_initialize_services(self, mock_settings):
        """Test service initialization."""
        with (
            patch(
                "tripsage_core.services.infrastructure.key_monitoring_service.get_cache_service"
            ) as mock_get_cache,
            patch(
                "tripsage_core.services.infrastructure.key_monitoring_service.get_database_service"
            ) as mock_get_db,
        ):
            mock_cache = AsyncMock()
            mock_db = AsyncMock()
            mock_get_cache.return_value = mock_cache
            mock_get_db.return_value = mock_db

            service = KeyMonitoringService(settings=mock_settings)
            await service.initialize()

            assert service.cache_service is mock_cache
            assert service.database_service is mock_db

    @pytest.mark.asyncio
    async def test_log_operation_success(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test successful operation logging."""
        user_id = str(uuid4())
        key_id = str(uuid4())
        service_name = "openai"
        metadata = {"api_version": "v1"}

        mock_cache_service.get_json.return_value = []  # No existing logs

        await key_monitoring_service.log_operation(
            operation=KeyOperation.CREATE,
            user_id=user_id,
            key_id=key_id,
            service=service_name,
            success=True,
            metadata=metadata,
        )

        # Verify cache operations were called
        assert mock_cache_service.get_json.call_count >= 1
        assert mock_cache_service.set_json.call_count >= 1

        # Verify log data was stored
        set_json_calls = mock_cache_service.set_json.call_args_list
        log_data_call = None
        for call in set_json_calls:
            if call[0][0].startswith("key_logs:"):
                log_data_call = call
                break

        assert log_data_call is not None
        stored_logs = log_data_call[0][1]
        assert len(stored_logs) == 1

        log_entry = stored_logs[0]
        assert log_entry["operation"] == "create"
        assert log_entry["user_id"] == user_id
        assert log_entry["key_id"] == key_id
        assert log_entry["service"] == service_name
        assert log_entry["success"] is True
        assert log_entry["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_log_operation_failure(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test operation logging for failures."""
        user_id = str(uuid4())

        mock_cache_service.get_json.return_value = []

        await key_monitoring_service.log_operation(
            operation=KeyOperation.DELETE,
            user_id=user_id,
            success=False,
            metadata={"error": "Key not found"},
        )

        # Verify log was stored with failure status
        set_json_calls = mock_cache_service.set_json.call_args_list
        log_data_call = None
        for call in set_json_calls:
            if call[0][0].startswith("key_logs:"):
                log_data_call = call
                break

        assert log_data_call is not None
        stored_logs = log_data_call[0][1]
        log_entry = stored_logs[0]
        assert log_entry["success"] is False
        assert log_entry["metadata"]["error"] == "Key not found"

    @pytest.mark.asyncio
    async def test_log_operation_suspicious_pattern(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test logging operation that triggers suspicious pattern detection."""
        user_id = str(uuid4())

        # Mock pattern detection to return True
        with patch.object(
            key_monitoring_service, "_check_suspicious_patterns", return_value=True
        ):
            mock_cache_service.get_json.return_value = []

            await key_monitoring_service.log_operation(
                operation=KeyOperation.CREATE, user_id=user_id, success=True
            )

            # Verify suspicious pattern was flagged
            assert f"{user_id}:create" in key_monitoring_service.suspicious_patterns

            # Verify alert was sent (should store alert in cache)
            alert_calls = [
                call
                for call in mock_cache_service.set_json.call_args_list
                if call[0][0] == "key_alerts"
            ]
            assert len(alert_calls) > 0

    @pytest.mark.asyncio
    async def test_log_operation_with_existing_logs(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test logging operation with existing logs."""
        user_id = str(uuid4())

        # Mock existing logs
        existing_logs = [
            {
                "operation": "list",
                "user_id": user_id,
                "timestamp": "2024-01-01T00:00:00",
            }
        ]
        mock_cache_service.get_json.return_value = existing_logs

        await key_monitoring_service.log_operation(
            operation=KeyOperation.VALIDATE, user_id=user_id, success=True
        )

        # Verify new log was appended to existing logs
        set_json_calls = mock_cache_service.set_json.call_args_list
        log_data_call = None
        for call in set_json_calls:
            if call[0][0].startswith("key_logs:"):
                log_data_call = call
                break

        assert log_data_call is not None
        stored_logs = log_data_call[0][1]
        assert len(stored_logs) == 2  # Existing + new log

    @pytest.mark.asyncio
    async def test_log_operation_max_logs_limit(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test log storage respects maximum log limit."""
        user_id = str(uuid4())

        # Mock 1000 existing logs (at the limit)
        existing_logs = [
            {
                "operation": "list",
                "user_id": user_id,
                "timestamp": f"2024-01-{i:02d}T00:00:00",
            }
            for i in range(1, 1001)
        ]
        mock_cache_service.get_json.return_value = existing_logs

        await key_monitoring_service.log_operation(
            operation=KeyOperation.CREATE, user_id=user_id, success=True
        )

        # Verify logs were trimmed to 1000
        set_json_calls = mock_cache_service.set_json.call_args_list
        log_data_call = None
        for call in set_json_calls:
            if call[0][0].startswith("key_logs:"):
                log_data_call = call
                break

        assert log_data_call is not None
        stored_logs = log_data_call[0][1]
        assert len(stored_logs) == 1000

    @pytest.mark.asyncio
    async def test_store_operation_for_pattern_detection(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test storing operation for pattern detection."""
        user_id = str(uuid4())
        operation = KeyOperation.CREATE

        mock_cache_service.get_json.return_value = []

        await key_monitoring_service._store_operation_for_pattern_detection(
            operation, user_id
        )

        # Verify operation was stored with correct key
        expected_key = f"key_ops:{user_id}:{operation.value}"
        mock_cache_service.get_json.assert_called_with(expected_key)
        mock_cache_service.set_json.assert_called()

        # Verify TTL was set
        set_call = mock_cache_service.set_json.call_args
        assert set_call[1]["ttl"] == key_monitoring_service.pattern_timeframe

    @pytest.mark.asyncio
    async def test_store_operation_filters_old_operations(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test that old operations are filtered out during storage."""
        user_id = str(uuid4())
        operation = KeyOperation.CREATE

        # Mock existing operations - some old, some recent
        now = datetime.now(timezone.utc)
        old_timestamp = (
            now - timedelta(seconds=700)
        ).isoformat()  # Older than timeframe
        recent_timestamp = (
            now - timedelta(seconds=300)
        ).isoformat()  # Within timeframe

        existing_ops = [old_timestamp, recent_timestamp]
        mock_cache_service.get_json.return_value = existing_ops

        await key_monitoring_service._store_operation_for_pattern_detection(
            operation, user_id
        )

        # Verify only recent operations were kept
        set_call = mock_cache_service.set_json.call_args
        stored_ops = set_call[0][1]
        assert len(stored_ops) == 2  # Recent + new operation
        assert old_timestamp not in stored_ops
        assert recent_timestamp in stored_ops

    @pytest.mark.asyncio
    async def test_check_suspicious_patterns_below_threshold(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test suspicious pattern detection below threshold."""
        user_id = str(uuid4())
        operation = KeyOperation.CREATE

        # Mock 3 operations (below threshold of 5)
        mock_cache_service.get_json.return_value = ["op1", "op2", "op3"]

        result = await key_monitoring_service._check_suspicious_patterns(
            operation, user_id
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_suspicious_patterns_above_threshold(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test suspicious pattern detection above threshold."""
        user_id = str(uuid4())
        operation = KeyOperation.CREATE

        # Mock 6 operations (above threshold of 5)
        mock_cache_service.get_json.return_value = [
            "op1",
            "op2",
            "op3",
            "op4",
            "op5",
            "op6",
        ]

        result = await key_monitoring_service._check_suspicious_patterns(
            operation, user_id
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_suspicious_patterns_list_operation_exempt(
        self, key_monitoring_service
    ):
        """Test that LIST operations are exempt from suspicious pattern detection."""
        user_id = str(uuid4())

        result = await key_monitoring_service._check_suspicious_patterns(
            KeyOperation.LIST, user_id
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_alert(self, key_monitoring_service, mock_cache_service):
        """Test alert sending functionality."""
        user_id = str(uuid4())
        operation = KeyOperation.CREATE
        log_data = {"count": 6, "timestamp": datetime.now(timezone.utc).isoformat()}

        mock_cache_service.get_json.return_value = []  # No existing alerts

        await key_monitoring_service._send_alert(operation, user_id, log_data)

        # Verify alert was stored
        expected_key = "key_alerts"
        mock_cache_service.get_json.assert_called_with(expected_key)
        mock_cache_service.set_json.assert_called()

        # Verify alert content
        set_call = mock_cache_service.set_json.call_args
        stored_alerts = set_call[0][1]
        assert len(stored_alerts) == 1

        alert = stored_alerts[0]
        assert alert["operation"] == operation.value
        assert alert["user_id"] == user_id
        assert "ALERT: Suspicious API key" in alert["message"]

    @pytest.mark.asyncio
    async def test_send_alert_max_alerts_limit(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test alert storage respects maximum alert limit."""
        user_id = str(uuid4())
        operation = KeyOperation.DELETE
        log_data = {}

        # Mock 1000 existing alerts (at the limit)
        existing_alerts = [
            {"message": f"Alert {i}", "timestamp": f"2024-01-{i:02d}T00:00:00"}
            for i in range(1, 1001)
        ]
        mock_cache_service.get_json.return_value = existing_alerts

        await key_monitoring_service._send_alert(operation, user_id, log_data)

        # Verify alerts were trimmed to 1000
        set_call = mock_cache_service.set_json.call_args
        stored_alerts = set_call[0][1]
        assert len(stored_alerts) == 1000

    @pytest.mark.asyncio
    async def test_get_user_operations(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test retrieving user operations."""
        user_id = str(uuid4())

        # Mock stored operations
        stored_ops = [
            {"operation": "create", "timestamp": "2024-01-01T00:00:00"},
            {"operation": "list", "timestamp": "2024-01-02T00:00:00"},
            {"operation": "delete", "timestamp": "2024-01-03T00:00:00"},
        ]
        mock_cache_service.get_json.return_value = stored_ops

        result = await key_monitoring_service.get_user_operations(user_id, limit=10)

        assert result == stored_ops
        expected_key = f"key_logs:{user_id}"
        mock_cache_service.get_json.assert_called_with(expected_key)

    @pytest.mark.asyncio
    async def test_get_user_operations_with_limit(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test retrieving user operations with limit."""
        user_id = str(uuid4())

        # Mock more operations than limit
        stored_ops = [
            {"operation": f"op{i}", "timestamp": f"2024-01-{i:02d}T00:00:00"}
            for i in range(1, 11)
        ]
        mock_cache_service.get_json.return_value = stored_ops

        result = await key_monitoring_service.get_user_operations(user_id, limit=5)

        assert len(result) == 5
        # Should return the last 5 operations
        assert result == stored_ops[-5:]

    @pytest.mark.asyncio
    async def test_get_user_operations_no_logs(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test retrieving user operations when no logs exist."""
        user_id = str(uuid4())

        mock_cache_service.get_json.return_value = None

        result = await key_monitoring_service.get_user_operations(user_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_alerts(self, key_monitoring_service, mock_cache_service):
        """Test retrieving alerts."""
        stored_alerts = [
            {"message": "Alert 1", "timestamp": "2024-01-01T00:00:00"},
            {"message": "Alert 2", "timestamp": "2024-01-02T00:00:00"},
        ]
        mock_cache_service.get_json.return_value = stored_alerts

        result = await key_monitoring_service.get_alerts(limit=10)

        assert result == stored_alerts
        mock_cache_service.get_json.assert_called_with("key_alerts")

    @pytest.mark.asyncio
    async def test_get_alerts_with_limit(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test retrieving alerts with limit."""
        stored_alerts = [
            {"message": f"Alert {i}", "timestamp": f"2024-01-{i:02d}T00:00:00"}
            for i in range(1, 11)
        ]
        mock_cache_service.get_json.return_value = stored_alerts

        result = await key_monitoring_service.get_alerts(limit=3)

        assert len(result) == 3
        assert result == stored_alerts[-3:]

    @pytest.mark.asyncio
    async def test_get_alerts_no_alerts(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test retrieving alerts when none exist."""
        mock_cache_service.get_json.return_value = None

        result = await key_monitoring_service.get_alerts()

        assert result == []

    @pytest.mark.asyncio
    async def test_is_rate_limited_first_operation(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test rate limiting for first operation."""
        user_id = str(uuid4())
        operation = KeyOperation.CREATE

        mock_cache_service.get.return_value = None  # No existing count

        result = await key_monitoring_service.is_rate_limited(user_id, operation)

        assert result is False
        # Verify initial count was set
        expected_key = f"rate_limit:key_ops:{user_id}:{operation.value}"
        mock_cache_service.set.assert_called_with(expected_key, "1", ttl=60)

    @pytest.mark.asyncio
    async def test_is_rate_limited_below_limit(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test rate limiting below limit."""
        user_id = str(uuid4())
        operation = KeyOperation.VALIDATE

        mock_cache_service.get.return_value = "5"  # Below limit of 10

        result = await key_monitoring_service.is_rate_limited(user_id, operation)

        assert result is False
        # Verify counter was incremented
        expected_key = f"rate_limit:key_ops:{user_id}:{operation.value}"
        mock_cache_service.incr.assert_called_with(expected_key)

    @pytest.mark.asyncio
    async def test_is_rate_limited_at_limit(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test rate limiting at limit."""
        user_id = str(uuid4())
        operation = KeyOperation.DELETE

        mock_cache_service.get.return_value = "10"  # At limit

        result = await key_monitoring_service.is_rate_limited(user_id, operation)

        assert result is True
        # Should not increment counter when at limit
        mock_cache_service.incr.assert_not_called()

    @pytest.mark.asyncio
    async def test_is_rate_limited_above_limit(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test rate limiting above limit."""
        user_id = str(uuid4())
        operation = KeyOperation.ROTATE

        mock_cache_service.get.return_value = "15"  # Above limit

        result = await key_monitoring_service.is_rate_limited(user_id, operation)

        assert result is True

    def test_alert_thresholds(self, key_monitoring_service):
        """Test default alert thresholds."""
        assert key_monitoring_service.alert_threshold[KeyOperation.CREATE] == 5
        assert key_monitoring_service.alert_threshold[KeyOperation.DELETE] == 5
        assert key_monitoring_service.alert_threshold[KeyOperation.VALIDATE] == 10
        assert key_monitoring_service.alert_threshold[KeyOperation.ROTATE] == 3

    def test_pattern_timeframe(self, key_monitoring_service):
        """Test pattern detection timeframe."""
        assert key_monitoring_service.pattern_timeframe == 600  # 10 minutes


class TestKeyOperationRateLimitMiddleware:
    """Test suite for KeyOperationRateLimitMiddleware."""

    @pytest.fixture
    def mock_monitoring_service(self):
        """Create a mock monitoring service."""
        service = AsyncMock(spec=KeyMonitoringService)
        service.is_rate_limited = AsyncMock(return_value=False)
        service.log_operation = AsyncMock()
        return service

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        return Mock(spec=Settings)

    @pytest.fixture
    def middleware(self, mock_monitoring_service, mock_settings):
        """Create middleware instance."""
        app = Mock()
        return KeyOperationRateLimitMiddleware(
            app, mock_monitoring_service, mock_settings
        )

    @pytest.mark.asyncio
    async def test_dispatch_non_key_operation(self, middleware):
        """Test middleware dispatch for non-key operations."""
        request = Mock()
        request.url.path = "/api/other/endpoint"
        request.method = "GET"

        response = Mock()
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert result is response
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_key_operation_no_user(self, middleware):
        """Test middleware dispatch for key operation without user ID."""
        request = Mock()
        request.url.path = "/api/user/keys"
        request.method = "GET"
        request.state = Mock()
        # No user_id attribute

        response = Mock()
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert result is response
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_key_operation_not_rate_limited(
        self, middleware, mock_monitoring_service
    ):
        """Test middleware dispatch for key operation not rate limited."""
        request = Mock()
        request.url.path = "/api/user/keys"
        request.method = "POST"
        request.state = Mock()
        request.state.user_id = str(uuid4())

        mock_monitoring_service.is_rate_limited.return_value = False

        response = Mock()
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert result is response
        call_next.assert_called_once_with(request)
        mock_monitoring_service.is_rate_limited.assert_called_once_with(
            request.state.user_id, KeyOperation.CREATE
        )

    @pytest.mark.asyncio
    async def test_dispatch_key_operation_rate_limited(
        self, middleware, mock_monitoring_service
    ):
        """Test middleware dispatch for rate limited key operation."""
        request = Mock()
        request.url.path = "/api/user/keys"
        request.method = "POST"
        request.state = Mock()
        user_id = str(uuid4())
        request.state.user_id = user_id

        mock_monitoring_service.is_rate_limited.return_value = True

        call_next = AsyncMock()

        result = await middleware.dispatch(request, call_next)

        assert result.status_code == 429
        assert "Rate limit exceeded" in result.content
        assert result.headers["Retry-After"] == "60"

        # Should not call next middleware
        call_next.assert_not_called()

        # Should log the rate limit
        mock_monitoring_service.log_operation.assert_called_once_with(
            operation=KeyOperation.CREATE,
            user_id=user_id,
            success=False,
            metadata={"rate_limited": True},
        )

    def test_get_key_operation_list(self, middleware):
        """Test key operation detection for LIST."""
        request = Mock()
        request.url.path = "/api/user/keys"
        request.method = "GET"

        result = middleware._get_key_operation(request)

        assert result == KeyOperation.LIST

    def test_get_key_operation_create(self, middleware):
        """Test key operation detection for CREATE."""
        request = Mock()
        request.url.path = "/api/user/keys/"
        request.method = "POST"

        result = middleware._get_key_operation(request)

        assert result == KeyOperation.CREATE

    def test_get_key_operation_validate(self, middleware):
        """Test key operation detection for VALIDATE."""
        request = Mock()
        request.url.path = "/api/user/keys/validate"
        request.method = "POST"

        result = middleware._get_key_operation(request)

        assert result == KeyOperation.VALIDATE

    def test_get_key_operation_rotate(self, middleware):
        """Test key operation detection for ROTATE."""
        request = Mock()
        request.url.path = "/api/user/keys/key-123/rotate"
        request.method = "POST"

        result = middleware._get_key_operation(request)

        assert result == KeyOperation.ROTATE

    def test_get_key_operation_delete(self, middleware):
        """Test key operation detection for DELETE."""
        request = Mock()
        request.url.path = "/api/user/keys/key-123"
        request.method = "DELETE"

        result = middleware._get_key_operation(request)

        assert result == KeyOperation.DELETE

    def test_get_key_operation_non_key_path(self, middleware):
        """Test key operation detection for non-key paths."""
        request = Mock()
        request.url.path = "/api/other/endpoint"
        request.method = "GET"

        result = middleware._get_key_operation(request)

        assert result is None

    def test_get_key_operation_unknown_method(self, middleware):
        """Test key operation detection for unknown method."""
        request = Mock()
        request.url.path = "/api/user/keys"
        request.method = "PATCH"

        result = middleware._get_key_operation(request)

        assert result is None


class TestMonitorKeyOperationDecorator:
    """Test suite for monitor_key_operation decorator."""

    @pytest.mark.asyncio
    async def test_decorator_with_monitoring_service_in_args(self):
        """Test decorator with monitoring service in arguments."""
        mock_service = AsyncMock(spec=KeyMonitoringService)
        mock_service.log_operation = AsyncMock()

        @monitor_key_operation(KeyOperation.CREATE)
        async def test_function(monitoring_service, user_id, key_id=None):
            return "success"

        result = await test_function(mock_service, "user-123", key_id="key-456")

        assert result == "success"
        mock_service.log_operation.assert_called_once()

        # Verify log call parameters
        call_args = mock_service.log_operation.call_args
        assert call_args[1]["operation"] == KeyOperation.CREATE
        assert call_args[1]["user_id"] == "user-123"
        assert call_args[1]["key_id"] == "key-456"
        assert call_args[1]["success"] is True

    @pytest.mark.asyncio
    async def test_decorator_with_monitoring_service_in_kwargs(self):
        """Test decorator with monitoring service in keyword arguments."""
        mock_service = AsyncMock(spec=KeyMonitoringService)
        mock_service.log_operation = AsyncMock()

        @monitor_key_operation(KeyOperation.DELETE)
        async def test_function(user_id, monitoring_service=None):
            return "deleted"

        result = await test_function("user-123", monitoring_service=mock_service)

        assert result == "deleted"
        mock_service.log_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_creates_new_service_if_not_found(self):
        """Test decorator creates new monitoring service if not found."""
        with patch(
            "tripsage_core.services.infrastructure.key_monitoring_service.KeyMonitoringService"
        ) as mock_class:
            mock_service = AsyncMock()
            mock_service.log_operation = AsyncMock()
            mock_class.return_value = mock_service

            @monitor_key_operation(KeyOperation.VALIDATE)
            async def test_function(user_id):
                return "validated"

            result = await test_function("user-123")

            assert result == "validated"
            mock_class.assert_called_once()
            mock_service.log_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_handles_function_exception(self):
        """Test decorator handles function exceptions."""
        mock_service = AsyncMock(spec=KeyMonitoringService)
        mock_service.log_operation = AsyncMock()

        @monitor_key_operation(KeyOperation.ROTATE)
        async def test_function(monitoring_service, user_id):
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await test_function(mock_service, "user-123")

        # Should log the error
        assert mock_service.log_operation.call_count == 1
        call_args = mock_service.log_operation.call_args
        assert call_args[1]["success"] is False
        assert call_args[1]["metadata"]["error"] == "Test error"

    @pytest.mark.asyncio
    async def test_decorator_extracts_service_from_key_data(self):
        """Test decorator extracts service from key_data."""
        mock_service = AsyncMock(spec=KeyMonitoringService)
        mock_service.log_operation = AsyncMock()

        key_data = Mock()
        key_data.service = "openai"

        @monitor_key_operation(KeyOperation.CREATE)
        async def test_function(monitoring_service, user_id, key_data=None):
            return "created"

        result = await test_function(mock_service, "user-123", key_data=key_data)

        assert result == "created"
        call_args = mock_service.log_operation.call_args
        assert call_args[1]["service"] == "openai"

    @pytest.mark.asyncio
    async def test_decorator_measures_execution_time(self):
        """Test decorator measures execution time."""
        mock_service = AsyncMock(spec=KeyMonitoringService)
        mock_service.log_operation = AsyncMock()

        @monitor_key_operation(KeyOperation.LIST)
        async def test_function(monitoring_service, user_id):
            await asyncio.sleep(0.001)  # Small delay
            return "listed"

        result = await test_function(mock_service, "user-123")

        assert result == "listed"
        call_args = mock_service.log_operation.call_args
        assert "execution_time" in call_args[1]["metadata"]
        assert call_args[1]["metadata"]["execution_time"] > 0


class TestSecurityFunctions:
    """Test suite for security utility functions."""

    def test_secure_random_token_default_length(self):
        """Test secure random token generation with default length."""
        token = secure_random_token()

        assert isinstance(token, str)
        assert len(token) == 64  # Default length

        # Generate another token to ensure they're different
        token2 = secure_random_token()
        assert token != token2

    def test_secure_random_token_custom_length(self):
        """Test secure random token generation with custom length."""
        token = secure_random_token(32)

        assert isinstance(token, str)
        assert len(token) == 32

    def test_secure_random_token_entropy(self):
        """Test that generated tokens have good entropy."""
        tokens = {secure_random_token(16) for _ in range(100)}

        # All tokens should be unique
        assert len(tokens) == 100

    def test_constant_time_compare_equal_strings(self):
        """Test constant time comparison with equal strings."""
        a = "secret123"
        b = "secret123"

        result = constant_time_compare(a, b)

        assert result is True

    def test_constant_time_compare_different_strings(self):
        """Test constant time comparison with different strings."""
        a = "secret123"
        b = "different"

        result = constant_time_compare(a, b)

        assert result is False

    def test_constant_time_compare_different_lengths(self):
        """Test constant time comparison with different length strings."""
        a = "short"
        b = "much longer string"

        result = constant_time_compare(a, b)

        assert result is False

    def test_constant_time_compare_empty_strings(self):
        """Test constant time comparison with empty strings."""
        result = constant_time_compare("", "")

        assert result is True

    def test_clear_sensitive_data_single_key(self):
        """Test clearing single sensitive key."""
        data = {
            "username": "testuser",
            "password": "secret123",
            "email": "test@example.com",
        }

        result = clear_sensitive_data(data, ["password"])

        assert result["username"] == "testuser"
        assert result["password"] == "[REDACTED]"
        assert result["email"] == "test@example.com"

        # Original data should be unchanged
        assert data["password"] == "secret123"

    def test_clear_sensitive_data_multiple_keys(self):
        """Test clearing multiple sensitive keys."""
        data = {
            "username": "testuser",
            "password": "secret123",
            "api_key": "key123",
            "email": "test@example.com",
        }

        result = clear_sensitive_data(data, ["password", "api_key"])

        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"

    def test_clear_sensitive_data_nonexistent_key(self):
        """Test clearing non-existent sensitive key."""
        data = {"username": "testuser", "email": "test@example.com"}

        result = clear_sensitive_data(data, ["password"])

        assert result == data  # Should be unchanged

    def test_clear_sensitive_data_empty_data(self):
        """Test clearing sensitive data from empty dictionary."""
        result = clear_sensitive_data({}, ["password"])

        assert result == {}

    def test_clear_sensitive_data_empty_keys(self):
        """Test clearing with empty keys list."""
        data = {"username": "testuser", "password": "secret123"}

        result = clear_sensitive_data(data, [])

        assert result == data


class TestHealthAndExpirationFunctions:
    """Test suite for health and expiration utility functions."""

    @pytest.mark.asyncio
    async def test_check_key_expiration_with_expiring_keys(self):
        """Test checking for expiring keys."""
        mock_service = AsyncMock(spec=KeyMonitoringService)
        mock_db = AsyncMock()
        mock_service.database_service = mock_db
        mock_service.initialize = AsyncMock()

        # Mock expiring keys
        expiring_keys = [
            {"id": "key1", "expires_at": "2024-12-31T23:59:59"},
            {"id": "key2", "expires_at": "2024-12-30T12:00:00"},
        ]
        mock_db.select.return_value = expiring_keys

        result = await check_key_expiration(mock_service, days_before=7)

        assert result == expiring_keys
        mock_service.initialize.assert_called_once()
        mock_db.select.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_key_expiration_no_expiring_keys(self):
        """Test checking for expiring keys when none are expiring."""
        mock_service = AsyncMock(spec=KeyMonitoringService)
        mock_db = AsyncMock()
        mock_service.database_service = mock_db
        mock_service.initialize = AsyncMock()

        mock_db.select.return_value = []

        result = await check_key_expiration(mock_service, days_before=30)

        assert result == []

    @pytest.mark.asyncio
    async def test_check_key_expiration_database_error(self):
        """Test checking for expiring keys with database error."""
        mock_service = AsyncMock(spec=KeyMonitoringService)
        mock_db = AsyncMock()
        mock_service.database_service = mock_db
        mock_service.initialize = AsyncMock()

        mock_db.select.side_effect = Exception("Database error")

        result = await check_key_expiration(mock_service)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_key_health_metrics_success(self):
        """Test getting key health metrics successfully."""
        mock_db = AsyncMock()

        # Mock database responses
        mock_db.count.side_effect = [10, 2]  # total_count, expired_count
        mock_db.select.side_effect = [
            [
                {"service": "openai"},
                {"service": "openai"},
                {"service": "google"},
            ],  # services
            [{"id": "key1"}, {"id": "key2"}],  # expiring keys
            [{"user_id": "user1"}, {"user_id": "user1"}, {"user_id": "user2"}],  # users
        ]

        with patch(
            "tripsage_core.services.infrastructure.key_monitoring_service.get_database_service",
            return_value=mock_db,
        ):
            result = await get_key_health_metrics()

        assert result["total_count"] == 10
        assert result["expired_count"] == 2
        assert result["expiring_count"] == 2
        assert len(result["service_count"]) == 2
        assert len(result["user_count"]) == 2

        # Check service counts
        service_counts = {
            item["service"]: item["count"] for item in result["service_count"]
        }
        assert service_counts["openai"] == 2
        assert service_counts["google"] == 1

        # Check user counts
        user_counts = {item["user_id"]: item["count"] for item in result["user_count"]}
        assert user_counts["user1"] == 2
        assert user_counts["user2"] == 1

    @pytest.mark.asyncio
    async def test_get_key_health_metrics_database_error(self):
        """Test getting key health metrics with database error."""
        mock_db = AsyncMock()
        mock_db.count.side_effect = Exception("Database connection failed")

        with patch(
            "tripsage_core.services.infrastructure.key_monitoring_service.get_database_service",
            return_value=mock_db,
        ):
            result = await get_key_health_metrics()

        assert "error" in result
        assert result["total_count"] == 0
        assert result["expired_count"] == 0
        assert result["expiring_count"] == 0
        assert result["service_count"] == []
        assert result["user_count"] == []

    @pytest.mark.asyncio
    async def test_get_key_health_metrics_empty_database(self):
        """Test getting key health metrics with empty database."""
        mock_db = AsyncMock()
        mock_db.count.return_value = 0
        mock_db.select.return_value = []

        with patch(
            "tripsage_core.services.infrastructure.key_monitoring_service.get_database_service",
            return_value=mock_db,
        ):
            result = await get_key_health_metrics()

        assert result["total_count"] == 0
        assert result["expired_count"] == 0
        assert result["expiring_count"] == 0
        assert result["service_count"] == []
        assert result["user_count"] == []


class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_log_operation_cache_error(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test operation logging with cache errors."""
        user_id = str(uuid4())

        # Mock cache service to raise exception
        mock_cache_service.get_json.side_effect = Exception("Cache error")

        # Should not raise exception, just handle gracefully
        await key_monitoring_service.log_operation(
            operation=KeyOperation.LIST, user_id=user_id, success=True
        )

    @pytest.mark.asyncio
    async def test_rate_limiting_cache_error(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test rate limiting with cache errors."""
        user_id = str(uuid4())

        mock_cache_service.get.side_effect = Exception("Cache connection lost")

        # Should handle error gracefully
        result = await key_monitoring_service.is_rate_limited(
            user_id, KeyOperation.CREATE
        )

        # Should default to not rate limited on error
        assert result is False

    @pytest.mark.asyncio
    async def test_concurrent_operations_logging(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test concurrent operation logging."""
        user_id = str(uuid4())
        mock_cache_service.get_json.return_value = []

        # Log multiple operations concurrently
        tasks = [
            key_monitoring_service.log_operation(
                KeyOperation.CREATE, user_id, success=True
            ),
            key_monitoring_service.log_operation(
                KeyOperation.LIST, user_id, success=True
            ),
            key_monitoring_service.log_operation(
                KeyOperation.VALIDATE, user_id, success=True
            ),
        ]

        await asyncio.gather(*tasks)

        # All operations should complete successfully
        assert mock_cache_service.set_json.call_count >= 3

    @pytest.mark.asyncio
    async def test_suspicious_pattern_with_custom_threshold(
        self, key_monitoring_service, mock_cache_service
    ):
        """Test suspicious pattern detection with custom thresholds."""
        user_id = str(uuid4())
        operation = KeyOperation.ACCESS  # Not in default thresholds

        # Mock operations above default threshold
        mock_cache_service.get_json.return_value = [
            "op1",
            "op2",
            "op3",
            "op4",
            "op5",
            "op6",
        ]

        result = await key_monitoring_service._check_suspicious_patterns(
            operation, user_id
        )

        # Should use default threshold of 5
        assert result is True

    def test_initialization_with_custom_settings(self):
        """Test service initialization with custom settings."""
        custom_settings = Mock(spec=Settings)
        service = KeyMonitoringService(settings=custom_settings)

        assert service.settings is custom_settings

    def test_initialization_without_settings(self):
        """Test service initialization without settings."""
        with patch(
            "tripsage_core.services.infrastructure.key_monitoring_service.get_settings"
        ) as mock_get_settings:
            mock_settings = Mock()
            mock_get_settings.return_value = mock_settings

            service = KeyMonitoringService()

            assert service.settings is mock_settings
            mock_get_settings.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_initialization_without_settings(
        self, mock_monitoring_service
    ):
        """Test middleware initialization without settings."""
        app = Mock()

        with patch(
            "tripsage_core.services.infrastructure.key_monitoring_service.get_settings"
        ) as mock_get_settings:
            mock_settings = Mock()
            mock_get_settings.return_value = mock_settings

            middleware = KeyOperationRateLimitMiddleware(app, mock_monitoring_service)

            assert middleware.settings is mock_settings
            mock_get_settings.assert_called_once()
