"""
Tests for SessionSecurityService.

Tests cover session management, security event logging, and risk assessment.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from tripsage_core.services.business.session_security_service import (
    SecurityEvent,
    SessionSecurityMetrics,
    SessionSecurityService,
    UserSession,
)


@pytest.fixture
def mock_database_service():
    """Mock database service."""
    db_service = AsyncMock()
    db_service.insert = AsyncMock()
    db_service.select = AsyncMock()
    db_service.update = AsyncMock()
    return db_service


@pytest.fixture
def session_service(mock_database_service):
    """Session security service with mocked dependencies."""
    return SessionSecurityService(
        database_service=mock_database_service,
        session_duration_hours=24,
        max_sessions_per_user=3,
    )


class TestSessionCreation:
    """Test session creation functionality."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, session_service, mock_database_service):
        """Test successful session creation."""
        # Mock database insert
        mock_database_service.insert.return_value = {"id": "session-1"}
        mock_database_service.select.return_value = []  # No existing sessions

        user_id = "user-123"
        ip_address = "192.168.1.100"
        user_agent = "Mozilla/5.0..."
        device_info = {"device": "iPhone", "os": "iOS 15"}

        session = await session_service.create_session(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info,
        )

        # Verify session properties
        assert session.user_id == user_id
        assert session.ip_address == ip_address
        assert session.user_agent == user_agent
        assert session.device_info == device_info
        assert session.is_active is True
        assert session.expires_at > datetime.now(timezone.utc)

        # Verify database calls
        assert mock_database_service.insert.call_count == 2

        # First call should be for user_sessions table
        session_call = mock_database_service.insert.call_args_list[0]
        assert session_call[0][0] == "user_sessions"

    @pytest.mark.asyncio
    async def test_create_session_with_max_sessions_exceeded(
        self, session_service, mock_database_service
    ):
        """Test session creation when max sessions exceeded."""
        # Mock existing sessions (at max limit)
        existing_sessions = [
            {
                "id": f"session-{i}",
                "user_id": "user-123",
                "session_token": f"token-{i}",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "device_info": {},
                "location_info": {},
                "is_active": True,
                "last_activity_at": (
                    datetime.now(timezone.utc) - timedelta(hours=i)
                ).isoformat(),
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(hours=24)
                ).isoformat(),
                "created_at": (
                    datetime.now(timezone.utc) - timedelta(hours=i)
                ).isoformat(),
                "ended_at": None,
            }
            for i in range(3)  # Max sessions = 3
        ]

        mock_database_service.select.return_value = existing_sessions
        mock_database_service.insert.return_value = {"id": "new-session"}
        mock_database_service.update.return_value = True

        user_id = "user-123"
        session = await session_service.create_session(user_id=user_id)

        # Should terminate oldest session and create new one
        assert session.user_id == user_id
        mock_database_service.update.assert_called()  # Terminate oldest session
        mock_database_service.insert.assert_called()  # Create new session

    @pytest.mark.asyncio
    async def test_create_session_logs_security_event(
        self, session_service, mock_database_service
    ):
        """Test that session creation logs security event."""
        mock_database_service.insert.return_value = {"id": "session-1"}
        mock_database_service.select.return_value = []

        await session_service.create_session(user_id="user-123")

        # Should have two insert calls: session and security event
        assert mock_database_service.insert.call_count == 2

        # Second call should be for security_events table
        security_event_call = mock_database_service.insert.call_args_list[1]
        assert security_event_call[0][0] == "security_events"


class TestSessionValidation:
    """Test session validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_session_success(
        self, session_service, mock_database_service
    ):
        """Test successful session validation."""
        session_token = "test-token"
        session_token_hash = hashlib.sha256(session_token.encode()).hexdigest()

        # Mock database response
        session_data = {
            "id": "session-1",
            "user_id": "user-123",
            "session_token": session_token_hash,
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0...",
            "device_info": {},
            "location_info": {},
            "is_active": True,
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
        }

        mock_database_service.select.return_value = [session_data]
        mock_database_service.update.return_value = True

        session = await session_service.validate_session(session_token)

        # Verify session is returned
        assert session is not None
        assert session.id == "session-1"
        assert session.user_id == "user-123"

        # Verify last activity was updated
        mock_database_service.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_session_expired(
        self, session_service, mock_database_service
    ):
        """Test validation of expired session."""
        session_token = "test-token"
        session_token_hash = hashlib.sha256(session_token.encode()).hexdigest()

        # Mock expired session
        session_data = {
            "id": "session-1",
            "user_id": "user-123",
            "session_token": session_token_hash,
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0...",
            "device_info": {},
            "location_info": {},
            "is_active": True,
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (
                datetime.now(timezone.utc) - timedelta(hours=1)
            ).isoformat(),  # Expired
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
        }

        mock_database_service.select.return_value = [session_data]
        mock_database_service.update.return_value = True

        session = await session_service.validate_session(session_token)

        # Should return None for expired session
        assert session is None

        # Should terminate expired session
        mock_database_service.update.assert_called()

    @pytest.mark.asyncio
    async def test_validate_session_not_found(
        self, session_service, mock_database_service
    ):
        """Test validation of non-existent session."""
        mock_database_service.select.return_value = []

        session = await session_service.validate_session("invalid-token")

        assert session is None

    @pytest.mark.asyncio
    async def test_validate_session_suspicious_activity(
        self, session_service, mock_database_service
    ):
        """Test detection of suspicious activity during validation."""
        session_token = "test-token"
        session_token_hash = hashlib.sha256(session_token.encode()).hexdigest()

        session_data = {
            "id": "session-1",
            "user_id": "user-123",
            "session_token": session_token_hash,
            "ip_address": "192.168.1.100",  # Original IP
            "user_agent": "Mozilla/5.0...",  # Original user agent
            "device_info": {},
            "location_info": {},
            "is_active": True,
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
        }

        mock_database_service.select.return_value = [session_data]
        mock_database_service.update.return_value = True
        mock_database_service.insert.return_value = {"id": "event-1"}

        # Validate with different IP and user agent
        session = await session_service.validate_session(
            session_token,
            ip_address="203.0.113.1",  # Different IP
            user_agent="Different/Browser",  # Different user agent
        )

        # Should still return session
        assert session is not None

        # With IP change (30) + user agent change (20) = 50 risk score,
        # which is below the 70 threshold, so no suspicious activity event should be logged
        insert_calls = mock_database_service.insert.call_args_list
        security_event_calls = [
            call for call in insert_calls if call[0][0] == "security_events"
        ]
        # Should not have any security events logged for this risk level
        assert len(security_event_calls) == 0


class TestSessionTermination:
    """Test session termination functionality."""

    @pytest.mark.asyncio
    async def test_terminate_session_success(
        self, session_service, mock_database_service
    ):
        """Test successful session termination."""
        mock_database_service.update.return_value = True
        mock_database_service.insert.return_value = {"id": "event-1"}

        success = await session_service.terminate_session(
            session_id="session-1",
            user_id="user-123",
            reason="user_logout",
        )

        assert success is True

        # Verify session was deactivated
        mock_database_service.update.assert_called_once()
        update_call = mock_database_service.update.call_args
        assert update_call[0][0] == "user_sessions"
        assert update_call[0][1] == {"id": "session-1", "user_id": "user-123"}
        assert update_call[0][2]["is_active"] is False

    @pytest.mark.asyncio
    async def test_terminate_session_not_found(
        self, session_service, mock_database_service
    ):
        """Test termination of non-existent session."""
        mock_database_service.update.return_value = False

        success = await session_service.terminate_session("invalid-session")

        assert success is False

    @pytest.mark.asyncio
    async def test_terminate_session_logs_event(
        self, session_service, mock_database_service
    ):
        """Test that session termination logs security event."""
        mock_database_service.update.return_value = True
        mock_database_service.insert.return_value = {"id": "event-1"}

        await session_service.terminate_session(
            session_id="session-1",
            user_id="user-123",
        )

        # Should log logout event
        mock_database_service.insert.assert_called_once()
        event_call = mock_database_service.insert.call_args
        assert event_call[0][0] == "security_events"
        assert event_call[0][1]["event_type"] == "logout"


class TestSecurityEventLogging:
    """Test security event logging functionality."""

    @pytest.mark.asyncio
    async def test_log_security_event_success(
        self, session_service, mock_database_service
    ):
        """Test successful security event logging."""
        mock_database_service.insert.return_value = {"id": "event-1"}

        event = await session_service.log_security_event(
            event_type="login_success",
            user_id="user-123",
            ip_address="192.168.1.100",
            details={"test": "data"},
            risk_score=25,
            severity="info",
        )

        assert event.event_type == "login_success"
        assert event.user_id == "user-123"
        assert event.ip_address == "192.168.1.100"
        assert event.risk_score == 25
        assert event.severity == "info"
        assert event.id == "event-1"

        # Verify database insert
        mock_database_service.insert.assert_called_once()
        call_args = mock_database_service.insert.call_args
        assert call_args[0][0] == "security_events"

    @pytest.mark.asyncio
    async def test_log_security_event_with_invalid_type(self):
        """Test security event logging with invalid event type."""
        SessionSecurityService()

        with pytest.raises(ValueError, match="Invalid event type"):
            SecurityEvent(
                event_type="invalid_event_type",
                user_id="user-123",
            )

    @pytest.mark.asyncio
    async def test_log_security_event_handles_failure(
        self, session_service, mock_database_service
    ):
        """Test that event logging failures don't raise exceptions."""
        mock_database_service.insert.side_effect = Exception("Database error")

        # Should not raise exception
        event = await session_service.log_security_event(
            event_type="login_success",
            user_id="user-123",
        )

        # Should return event even if logging failed
        assert event.event_type == "login_success"
        assert event.id is None  # No ID since insert failed


class TestSecurityMetrics:
    """Test security metrics functionality."""

    @pytest.mark.asyncio
    async def test_get_security_metrics_success(
        self, session_service, mock_database_service
    ):
        """Test successful security metrics retrieval."""
        # Mock active sessions
        session_data = [
            {
                "id": "session-1",
                "user_id": "user-123",
                "session_token": "token-hash",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "device_info": {},
                "location_info": {},
                "is_active": True,
                "last_activity_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": None,
            }
        ]

        # Mock security event counts
        mock_database_service.select.side_effect = [
            session_data,  # Active sessions
            [{"count": 2}],  # Failed logins
            [{"count": 5}],  # Successful logins
            [{"count": 10}],  # Security events
            [{"created_at": datetime.now(timezone.utc).isoformat()}],  # Last login
        ]

        metrics = await session_service.get_security_metrics("user-123")

        assert metrics.user_id == "user-123"
        assert metrics.active_sessions == 1
        assert metrics.failed_login_attempts_24h == 2
        assert metrics.successful_logins_24h == 5
        assert metrics.security_events_7d == 10
        assert metrics.last_login_at is not None
        assert 0 <= metrics.risk_score <= 100

    @pytest.mark.asyncio
    async def test_get_security_metrics_handles_errors(
        self, session_service, mock_database_service
    ):
        """Test that metrics retrieval handles database errors gracefully."""
        mock_database_service.select.side_effect = Exception("Database error")

        metrics = await session_service.get_security_metrics("user-123")

        # Should return default metrics
        assert metrics.user_id == "user-123"
        assert metrics.active_sessions == 0
        assert metrics.failed_login_attempts_24h == 0


class TestRiskCalculation:
    """Test risk calculation functionality."""

    def test_calculate_login_risk_score_low_risk(self, session_service):
        """Test low risk login scenario."""
        # Private IP, no recent failures
        risk_score = session_service._calculate_login_risk_score(
            user_id="user-123",
            ip_address="192.168.1.100",
        )

        assert 0 <= risk_score <= 20  # Should be low risk

    def test_calculate_login_risk_score_high_risk(self, session_service):
        """Test high risk login scenario."""
        # Mock recent failures
        session_service._rate_limit_cache["failures_user-123"] = [1, 2, 3, 4, 5]

        risk_score = session_service._calculate_login_risk_score(
            user_id="user-123",
            ip_address="203.0.113.1",  # Public IP
        )

        assert risk_score > 30  # Should be higher risk

    def test_calculate_activity_risk_score_ip_change(self, session_service):
        """Test risk calculation for IP address change."""
        session = UserSession(
            id="session-1",
            user_id="user-123",
            session_token="token-hash",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0...",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        risk_score = session_service._calculate_activity_risk_score(
            session=session,
            current_ip="203.0.113.1",  # Different IP
            current_user_agent="Mozilla/5.0...",  # Same user agent
        )

        assert risk_score >= 30  # IP change should add risk

    def test_calculate_activity_risk_score_user_agent_change(self, session_service):
        """Test risk calculation for user agent change."""
        session = UserSession(
            id="session-1",
            user_id="user-123",
            session_token="token-hash",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0...",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        risk_score = session_service._calculate_activity_risk_score(
            session=session,
            current_ip="192.168.1.100",  # Same IP
            current_user_agent="Different/Browser",  # Different user agent
        )

        assert risk_score >= 20  # User agent change should add risk


class TestSessionCleanup:
    """Test session cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(
        self, session_service, mock_database_service
    ):
        """Test cleanup of expired sessions."""
        # Mock expired sessions
        expired_sessions = [
            {
                "id": "session-1",
                "user_id": "user-123",
                "expires_at": (
                    datetime.now(timezone.utc) - timedelta(hours=1)
                ).isoformat(),
            },
            {
                "id": "session-2",
                "user_id": "user-456",
                "expires_at": (
                    datetime.now(timezone.utc) - timedelta(hours=2)
                ).isoformat(),
            },
        ]

        mock_database_service.select.return_value = expired_sessions
        mock_database_service.update.return_value = True
        mock_database_service.insert.return_value = {"id": "event-1"}

        cleanup_count = await session_service.cleanup_expired_sessions()

        assert cleanup_count == 2

        # Should have updated both sessions
        assert mock_database_service.update.call_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_handles_errors(
        self, session_service, mock_database_service
    ):
        """Test that cleanup handles errors gracefully."""
        mock_database_service.select.side_effect = Exception("Database error")

        cleanup_count = await session_service.cleanup_expired_sessions()

        assert cleanup_count == 0


class TestModelValidation:
    """Test model validation."""

    def test_security_event_validation(self):
        """Test SecurityEvent model validation."""
        # Valid event
        event = SecurityEvent(
            event_type="login_success",
            severity="info",
            risk_score=50,
        )
        assert event.event_type == "login_success"
        assert event.severity == "info"
        assert event.risk_score == 50

        # Invalid event type
        with pytest.raises(ValueError, match="Invalid event type"):
            SecurityEvent(event_type="invalid_type")

        # Invalid severity
        with pytest.raises(ValueError, match="Invalid severity"):
            SecurityEvent(event_type="login_success", severity="invalid")

        # Invalid risk score
        with pytest.raises(ValueError, match="Risk score must be between 0 and 100"):
            SecurityEvent(event_type="login_success", risk_score=150)

    def test_user_session_validation(self):
        """Test UserSession model validation."""
        # Valid session
        session = UserSession(
            id="session-1",
            user_id="user-123",
            session_token="token-hash",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert session.id == "session-1"
        assert session.user_id == "user-123"
        assert session.is_active is True

    def test_session_security_metrics_validation(self):
        """Test SessionSecurityMetrics model validation."""
        metrics = SessionSecurityMetrics(
            user_id="user-123",
            active_sessions=2,
            failed_login_attempts_24h=1,
            risk_score=25,
        )
        assert metrics.user_id == "user-123"
        assert metrics.active_sessions == 2
        assert metrics.risk_score == 25
