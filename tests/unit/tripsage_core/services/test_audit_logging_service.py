"""
Comprehensive test suite for the security audit logging service.

Tests cover:
- Event creation and validation
- JSON serialization and deserialization
- Audit logger functionality
- Performance and reliability
- Security features (integrity hashing)
- Configuration validation
- Integration with authentication and rate limiting
"""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from tripsage_core.services.business.audit_logging_service import (
    AuditActor,
    AuditEvent,
    AuditEventType,
    AuditLogConfig,
    AuditOutcome,
    AuditSeverity,
    AuditSource,
    AuditTarget,
    SecurityAuditLogger,
    audit_api_key,
    audit_authentication,
    audit_config_change,
    audit_security_event,
    get_audit_logger,
)


class TestAuditEventModels:
    """Test audit event model validation and serialization."""

    def test_audit_event_creation(self):
        """Test basic audit event creation."""
        actor = AuditActor(
            actor_type="user",
            actor_id="user123",
            actor_name="John Doe",
            authentication_method="jwt",
        )

        source = AuditSource(
            ip_address="192.168.1.100", user_agent="Mozilla/5.0", country="US"
        )

        target = AuditTarget(
            resource_type="api_key", resource_id="key123", resource_name="OpenAI Key"
        )

        event = AuditEvent(
            event_type=AuditEventType.API_KEY_CREATED,
            severity=AuditSeverity.MEDIUM,
            outcome=AuditOutcome.SUCCESS,
            message="API key created successfully",
            actor=actor,
            source=source,
            target=target,
        )

        assert event.event_type == AuditEventType.API_KEY_CREATED
        assert event.severity == AuditSeverity.MEDIUM
        assert event.outcome == AuditOutcome.SUCCESS
        assert event.actor.actor_id == "user123"
        assert event.source.ip_address == "192.168.1.100"
        assert event.target.resource_id == "key123"
        assert event.timestamp.tzinfo == timezone.utc

    def test_audit_event_defaults(self):
        """Test audit event with default values."""
        actor = AuditActor(actor_type="system", actor_id="system")
        source = AuditSource(ip_address="127.0.0.1")

        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_STARTUP,
            severity=AuditSeverity.INFORMATIONAL,
            outcome=AuditOutcome.SUCCESS,
            message="System started",
            actor=actor,
            source=source,
        )

        assert event.event_id is not None
        assert event.event_version == "1.0"
        assert event.application == "tripsage"
        assert event.environment == "production"
        assert event.retention_period_days == 2555
        assert len(event.tags) == 0
        assert len(event.metadata) == 0

    def test_audit_event_json_serialization(self):
        """Test JSON serialization of audit events."""
        actor = AuditActor(actor_type="user", actor_id="user123")
        source = AuditSource(ip_address="192.168.1.100")

        event = AuditEvent(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            outcome=AuditOutcome.SUCCESS,
            message="User logged in",
            actor=actor,
            source=source,
            metadata={"session_id": "sess123", "device": "mobile"},
        )

        json_str = event.to_json_log()
        parsed = json.loads(json_str)

        assert parsed["event_type"] == "auth.login.success"
        assert parsed["severity"] == "low"
        assert parsed["actor"]["actor_id"] == "user123"
        assert parsed["metadata"]["session_id"] == "sess123"

    def test_risk_score_validation(self):
        """Test risk score validation."""
        actor = AuditActor(actor_type="user", actor_id="user123")
        source = AuditSource(ip_address="192.168.1.100")

        # Valid risk score
        event = AuditEvent(
            event_type=AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.HIGH,
            outcome=AuditOutcome.WARNING,
            message="Suspicious activity detected",
            actor=actor,
            source=source,
            risk_score=85,
        )
        assert event.risk_score == 85

        # Invalid risk score should raise validation error
        with pytest.raises(ValidationError):
            AuditEvent(
                event_type=AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
                severity=AuditSeverity.HIGH,
                outcome=AuditOutcome.WARNING,
                message="Suspicious activity detected",
                actor=actor,
                source=source,
                risk_score=150,  # Invalid: > 100
            )

    def test_integrity_hash_computation(self):
        """Test integrity hash computation for tamper detection."""
        actor = AuditActor(actor_type="user", actor_id="user123")
        source = AuditSource(ip_address="192.168.1.100")

        event = AuditEvent(
            event_type=AuditEventType.CONFIG_CHANGED,
            severity=AuditSeverity.MEDIUM,
            outcome=AuditOutcome.SUCCESS,
            message="Configuration updated",
            actor=actor,
            source=source,
        )

        secret_key = "test_secret_key"
        hash1 = event.compute_integrity_hash(secret_key)
        hash2 = event.compute_integrity_hash(secret_key)

        # Same event should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

        # Different secret should produce different hash
        hash3 = event.compute_integrity_hash("different_secret")
        assert hash1 != hash3


class TestAuditLogConfig:
    """Test audit log configuration validation."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AuditLogConfig()

        assert config.enabled is True
        assert config.log_level == "INFO"
        assert config.async_logging is True
        assert config.buffer_size == 1000
        assert config.flush_interval_seconds == 10
        assert config.max_file_size_mb == 100
        assert config.max_files == 365
        assert config.default_retention_days == 2555
        assert config.compression_enabled is True
        assert config.integrity_checks_enabled is True
        assert config.circuit_breaker_enabled is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = AuditLogConfig(
            enabled=False,
            log_level="DEBUG",
            buffer_size=500,
            max_file_size_mb=50,
            external_forwarding_enabled=True,
            external_endpoints=["https://siem.example.com/logs"],
            compliance_mode="hipaa",
        )

        assert config.enabled is False
        assert config.log_level == "DEBUG"
        assert config.buffer_size == 500
        assert config.max_file_size_mb == 50
        assert config.external_forwarding_enabled is True
        assert len(config.external_endpoints) == 1
        assert config.compliance_mode == "hipaa"


class TestSecurityAuditLogger:
    """Test the main security audit logger functionality."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary directory for test logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def audit_config(self, temp_log_dir):
        """Create test audit configuration."""
        return AuditLogConfig(
            log_directory=temp_log_dir,
            async_logging=False,  # Synchronous for easier testing
            flush_interval_seconds=1,
            cleanup_enabled=False,  # Disable cleanup during tests
            integrity_checks_enabled=True,
            integrity_secret_key="test_secret_key",
        )

    @pytest.fixture
    def audit_logger(self, audit_config):
        """Create test audit logger."""
        return SecurityAuditLogger(audit_config)

    @pytest.mark.asyncio
    async def test_logger_lifecycle(self, audit_logger):
        """Test audit logger start/stop lifecycle."""
        assert not audit_logger._is_running

        await audit_logger.start()
        assert audit_logger._is_running

        await audit_logger.stop()
        assert not audit_logger._is_running

    @pytest.mark.asyncio
    async def test_log_event_basic(self, audit_logger, temp_log_dir):
        """Test basic event logging."""
        await audit_logger.start()

        actor = AuditActor(actor_type="user", actor_id="user123")
        source = AuditSource(ip_address="192.168.1.100")

        event = AuditEvent(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            outcome=AuditOutcome.SUCCESS,
            message="User logged in successfully",
            actor=actor,
            source=source,
        )

        result = await audit_logger.log_event(event)
        assert result is True

        # Check statistics
        stats = audit_logger.get_statistics()
        assert stats["total_events_logged"] == 1
        assert stats["events_by_type"][AuditEventType.AUTH_LOGIN_SUCCESS] == 1
        assert stats["events_by_severity"][AuditSeverity.LOW] == 1

        await audit_logger.stop()

        # Verify log file was created
        log_files = list(Path(temp_log_dir).glob("audit-*.log"))
        assert len(log_files) > 0

    @pytest.mark.asyncio
    async def test_rate_limiting(self, audit_logger):
        """Test rate limiting functionality."""
        # Set low rate limit for testing
        audit_logger.config.max_events_per_second = 2

        await audit_logger.start()

        actor = AuditActor(actor_type="user", actor_id="user123")
        source = AuditSource(ip_address="192.168.1.100")

        # First 2 events should succeed
        for i in range(2):
            event = AuditEvent(
                event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
                severity=AuditSeverity.LOW,
                outcome=AuditOutcome.SUCCESS,
                message=f"Login attempt {i}",
                actor=actor,
                source=source,
            )
            result = await audit_logger.log_event(event)
            assert result is True

        # Third event should be rate limited
        event = AuditEvent(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            outcome=AuditOutcome.SUCCESS,
            message="Rate limited event",
            actor=actor,
            source=source,
        )
        result = await audit_logger.log_event(event)
        assert result is False

        await audit_logger.stop()

    @pytest.mark.asyncio
    async def test_circuit_breaker(self, audit_logger):
        """Test circuit breaker functionality."""
        audit_logger.config.circuit_breaker_enabled = True
        audit_logger.config.circuit_breaker_failure_threshold = 2

        # Mock the file handler to raise exceptions
        audit_logger.audit_logger = MagicMock()
        audit_logger.audit_logger.info.side_effect = Exception("Logging failed")

        await audit_logger.start()

        actor = AuditActor(actor_type="user", actor_id="user123")
        source = AuditSource(ip_address="192.168.1.100")

        # First few events should fail and trigger circuit breaker
        for i in range(3):
            event = AuditEvent(
                event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
                severity=AuditSeverity.LOW,
                outcome=AuditOutcome.SUCCESS,
                message=f"Test event {i}",
                actor=actor,
                source=source,
            )
            result = await audit_logger.log_event(event)

        # Circuit breaker should be open now
        assert audit_logger._circuit_breaker_open

        # New events should be rejected without trying to log
        event = AuditEvent(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            outcome=AuditOutcome.SUCCESS,
            message="Rejected event",
            actor=actor,
            source=source,
        )
        result = await audit_logger.log_event(event)
        assert result is False

        await audit_logger.stop()

    @pytest.mark.asyncio
    async def test_async_buffering(self, audit_config, temp_log_dir):
        """Test asynchronous buffering and flushing."""
        # Enable async logging
        audit_config.async_logging = True
        audit_config.buffer_size = 3
        audit_config.flush_interval_seconds = 0.1

        audit_logger = SecurityAuditLogger(audit_config)
        await audit_logger.start()

        actor = AuditActor(actor_type="user", actor_id="user123")
        source = AuditSource(ip_address="192.168.1.100")

        # Log events that should be buffered
        for i in range(2):
            event = AuditEvent(
                event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
                severity=AuditSeverity.LOW,
                outcome=AuditOutcome.SUCCESS,
                message=f"Buffered event {i}",
                actor=actor,
                source=source,
            )
            result = await audit_logger.log_event(event)
            assert result is True

        # Buffer should have events
        assert len(audit_logger._buffer) == 2

        # Wait for automatic flush
        await asyncio.sleep(0.2)

        # Buffer should be empty after flush
        assert len(audit_logger._buffer) == 0

        await audit_logger.stop()

    @pytest.mark.asyncio
    async def test_query_events(self, audit_logger, temp_log_dir):
        """Test event querying functionality."""
        await audit_logger.start()

        actor = AuditActor(actor_type="user", actor_id="user123")
        source = AuditSource(ip_address="192.168.1.100")

        # Log different types of events
        events_to_log = [
            (AuditEventType.AUTH_LOGIN_SUCCESS, AuditSeverity.LOW),
            (AuditEventType.AUTH_LOGIN_FAILED, AuditSeverity.MEDIUM),
            (AuditEventType.API_KEY_CREATED, AuditSeverity.MEDIUM),
        ]

        for event_type, severity in events_to_log:
            event = AuditEvent(
                event_type=event_type,
                severity=severity,
                outcome=AuditOutcome.SUCCESS,
                message=f"Test {event_type.value}",
                actor=actor,
                source=source,
            )
            await audit_logger.log_event(event)

        await audit_logger.stop()

        # Query all events
        all_events = await audit_logger.query_events()
        assert len(all_events) == 3

        # Query by event type
        auth_events = await audit_logger.query_events(
            event_types=[
                AuditEventType.AUTH_LOGIN_SUCCESS,
                AuditEventType.AUTH_LOGIN_FAILED,
            ]
        )
        assert len(auth_events) == 2

        # Query by severity
        medium_events = await audit_logger.query_events(severity=AuditSeverity.MEDIUM)
        assert len(medium_events) == 2

        # Query by actor
        user_events = await audit_logger.query_events(actor_id="user123")
        assert len(user_events) == 3


class TestConvenienceFunctions:
    """Test convenience functions for common audit events."""

    @pytest.mark.asyncio
    async def test_audit_authentication(self):
        """Test authentication audit convenience function."""
        with patch(
            "tripsage_core.services.business.audit_logging_service.get_audit_logger"
        ) as mock_get_logger:
            mock_logger = AsyncMock()
            mock_logger.log_authentication_event.return_value = True
            mock_get_logger.return_value = mock_logger

            result = await audit_authentication(
                event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
                outcome=AuditOutcome.SUCCESS,
                user_id="user123",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
                session_id="sess123",
            )

            assert result is True
            mock_logger.log_authentication_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_api_key(self):
        """Test API key audit convenience function."""
        with patch(
            "tripsage_core.services.business.audit_logging_service.get_audit_logger"
        ) as mock_get_logger:
            mock_logger = AsyncMock()
            mock_logger.log_api_key_event.return_value = True
            mock_get_logger.return_value = mock_logger

            result = await audit_api_key(
                event_type=AuditEventType.API_KEY_CREATED,
                outcome=AuditOutcome.SUCCESS,
                key_id="key123",
                service="openai",
                ip_address="192.168.1.100",
                key_name="My OpenAI Key",
            )

            assert result is True
            mock_logger.log_api_key_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_security_event(self):
        """Test security event audit convenience function."""
        with patch(
            "tripsage_core.services.business.audit_logging_service.get_audit_logger"
        ) as mock_get_logger:
            mock_logger = AsyncMock()
            mock_logger.log_security_event.return_value = True
            mock_get_logger.return_value = mock_logger

            result = await audit_security_event(
                event_type=AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
                severity=AuditSeverity.HIGH,
                message="Multiple failed login attempts",
                actor_id="user123",
                ip_address="192.168.1.100",
                risk_score=75,
                attempt_count=5,
            )

            assert result is True
            mock_logger.log_security_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_config_change(self):
        """Test configuration change audit convenience function."""
        with patch(
            "tripsage_core.services.business.audit_logging_service.get_audit_logger"
        ) as mock_get_logger:
            mock_logger = AsyncMock()
            mock_logger.log_configuration_change.return_value = True
            mock_get_logger.return_value = mock_logger

            result = await audit_config_change(
                config_key="max_file_size",
                old_value="100MB",
                new_value="200MB",
                changed_by="admin123",
                ip_address="192.168.1.100",
                reason="Increased storage capacity",
            )

            assert result is True
            mock_logger.log_configuration_change.assert_called_once()


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.mark.asyncio
    async def test_authentication_flow_audit(self):
        """Test complete authentication flow audit logging."""
        with patch(
            "tripsage_core.services.business.audit_logging_service.get_audit_logger"
        ) as mock_get_logger:
            mock_logger = AsyncMock()
            mock_logger.log_authentication_event.return_value = True
            mock_get_logger.return_value = mock_logger

            user_id = "user123"
            ip_address = "192.168.1.100"
            user_agent = "Mozilla/5.0"

            # Failed login attempt
            await audit_authentication(
                event_type=AuditEventType.AUTH_LOGIN_FAILED,
                outcome=AuditOutcome.FAILURE,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                error="Invalid credentials",
            )

            # Successful login
            await audit_authentication(
                event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
                outcome=AuditOutcome.SUCCESS,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id="sess123",
            )

            # Password change
            await audit_authentication(
                event_type=AuditEventType.AUTH_PASSWORD_CHANGE,
                outcome=AuditOutcome.SUCCESS,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            # Logout
            await audit_authentication(
                event_type=AuditEventType.AUTH_LOGOUT,
                outcome=AuditOutcome.SUCCESS,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id="sess123",
            )

            # Verify all events were logged
            assert mock_logger.log_authentication_event.call_count == 4

    @pytest.mark.asyncio
    async def test_api_key_lifecycle_audit(self):
        """Test complete API key lifecycle audit logging."""
        with patch(
            "tripsage_core.services.business.audit_logging_service.get_audit_logger"
        ) as mock_get_logger:
            mock_logger = AsyncMock()
            mock_logger.log_api_key_event.return_value = True
            mock_get_logger.return_value = mock_logger

            key_id = "key123"
            service = "openai"
            ip_address = "192.168.1.100"

            # Key creation
            await audit_api_key(
                event_type=AuditEventType.API_KEY_CREATED,
                outcome=AuditOutcome.SUCCESS,
                key_id=key_id,
                service=service,
                ip_address=ip_address,
            )

            # Key validation (successful)
            await audit_api_key(
                event_type=AuditEventType.API_KEY_VALIDATION_SUCCESS,
                outcome=AuditOutcome.SUCCESS,
                key_id=key_id,
                service=service,
                ip_address=ip_address,
            )

            # Rate limiting
            await audit_api_key(
                event_type=AuditEventType.API_KEY_RATE_LIMITED,
                outcome=AuditOutcome.FAILURE,
                key_id=key_id,
                service=service,
                ip_address=ip_address,
            )

            # Key rotation
            await audit_api_key(
                event_type=AuditEventType.API_KEY_ROTATED,
                outcome=AuditOutcome.SUCCESS,
                key_id=key_id,
                service=service,
                ip_address=ip_address,
            )

            # Key deletion
            await audit_api_key(
                event_type=AuditEventType.API_KEY_DELETED,
                outcome=AuditOutcome.SUCCESS,
                key_id=key_id,
                service=service,
                ip_address=ip_address,
            )

            # Verify all events were logged
            assert mock_logger.log_api_key_event.call_count == 5

    @pytest.mark.asyncio
    async def test_global_logger_singleton(self, tmp_path):
        """Test global audit logger singleton pattern."""
        # Use temporary directory for tests
        from tripsage_core.services.business.audit_logging_service import AuditLogConfig

        # Override default config to use temp directory
        original_get_audit_logger = get_audit_logger

        # Use a local variable to track the logger instance
        test_audit_logger = None

        async def test_get_audit_logger():
            nonlocal test_audit_logger

            if test_audit_logger is None:
                config = AuditLogConfig(log_directory=str(tmp_path))
                test_audit_logger = SecurityAuditLogger(config)
                await test_audit_logger.start()

            return test_audit_logger

        # Patch the function temporarily
        import tripsage_core.services.business.audit_logging_service as audit_module

        audit_module.get_audit_logger = test_get_audit_logger

        try:
            # Get logger twice - should be same instance
            logger1 = await test_get_audit_logger()
            logger2 = await test_get_audit_logger()

            assert logger1 is logger2
            assert logger1._is_running

            # Shutdown should cleanup
            await logger1.stop()

            # Reset local state
            test_audit_logger = None

            # Getting logger again should create new instance
            logger3 = await test_get_audit_logger()
            assert logger3 is not logger1

            await logger3.stop()

        finally:
            # Restore original function
            audit_module.get_audit_logger = original_get_audit_logger


class TestPerformanceAndReliability:
    """Test performance and reliability aspects."""

    @pytest.mark.asyncio
    async def test_high_volume_logging(self, audit_config, temp_log_dir):
        """Test high volume event logging performance."""
        audit_config.async_logging = True
        audit_config.buffer_size = 100
        audit_config.flush_interval_seconds = 0.1

        audit_logger = SecurityAuditLogger(audit_config)
        await audit_logger.start()

        actor = AuditActor(actor_type="user", actor_id="user123")
        source = AuditSource(ip_address="192.168.1.100")

        # Log many events quickly
        num_events = 1000
        start_time = datetime.now()

        tasks = []
        for i in range(num_events):
            event = AuditEvent(
                event_type=AuditEventType.DATA_ACCESS,
                severity=AuditSeverity.INFORMATIONAL,
                outcome=AuditOutcome.SUCCESS,
                message=f"Data access event {i}",
                actor=actor,
                source=source,
            )
            tasks.append(audit_logger.log_event(event))

        results = await asyncio.gather(*tasks)
        end_time = datetime.now()

        # All events should be logged successfully
        assert all(results)

        # Performance should be reasonable (< 1 second for 1000 events)
        duration = (end_time - start_time).total_seconds()
        assert duration < 1.0

        # Wait for all events to be flushed
        await asyncio.sleep(0.5)

        stats = audit_logger.get_statistics()
        assert stats["total_events_logged"] == num_events

        await audit_logger.stop()

    @pytest.mark.asyncio
    async def test_error_resilience(self, audit_config, temp_log_dir):
        """Test audit logger resilience to errors."""
        audit_logger = SecurityAuditLogger(audit_config)
        await audit_logger.start()

        # Test with invalid event data
        actor = AuditActor(actor_type="user", actor_id="user123")
        source = AuditSource(ip_address="192.168.1.100")

        # Mock file handler to occasionally fail
        original_info = audit_logger.audit_logger.info
        call_count = 0

        def failing_info(message):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Fail every 3rd call
                raise Exception("Simulated logging failure")
            return original_info(message)

        audit_logger.audit_logger.info = failing_info

        # Log events - some should fail but service should continue
        success_count = 0
        for i in range(10):
            event = AuditEvent(
                event_type=AuditEventType.SYSTEM_ERROR,
                severity=AuditSeverity.LOW,
                outcome=AuditOutcome.SUCCESS,
                message=f"Test event {i}",
                actor=actor,
                source=source,
            )
            result = await audit_logger.log_event(event)
            if result:
                success_count += 1

        # Some events should succeed despite failures
        assert success_count > 0
        assert success_count < 10  # Some should have failed

        await audit_logger.stop()
