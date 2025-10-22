"""Unit tests for the final-only session security service."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import ANY, AsyncMock

import pytest

from tripsage_core.exceptions import CoreSecurityError
from tripsage_core.services.business.session_security_service import (
    SecurityEvent,
    SessionSecurityMetrics,
    SessionSecurityService,
    UserSession,
)


@pytest.fixture()
def mock_database_service() -> AsyncMock:
    """Provide an async database mock that matches the protocol."""
    db = AsyncMock()
    db.select = AsyncMock(return_value=[])
    db.insert = AsyncMock(return_value=[{"id": "row-1"}])
    db.update = AsyncMock(return_value=[{"id": "row-1"}])
    return db


@pytest.fixture()
def session_service(mock_database_service: AsyncMock) -> SessionSecurityService:
    """Create a service instance backed by the database mock."""
    return SessionSecurityService(database_service=mock_database_service)


def _build_session_row(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    base = {
        "id": "session-1",
        "user_id": "user-123",
        "session_token": hashlib.sha256(b"token").hexdigest(),
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0",
        "device_info": {},
        "location_info": {},
        "is_active": True,
        "created_at": (now - timedelta(minutes=5)).isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "last_activity_at": (now - timedelta(minutes=1)).isoformat(),
        "ended_at": None,
    }
    base.update(overrides)
    return base


def test_service_requires_database_service() -> None:
    """Initialisation without a database service is not allowed."""
    with pytest.raises(ValueError):
        SessionSecurityService(database_service=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_session_inserts_session_and_logs_event(
    session_service: SessionSecurityService, mock_database_service: AsyncMock
) -> None:
    """Creating a session stores it and logs a login event."""
    mock_database_service.select.side_effect = [[], []]
    session = await session_service.create_session(
        user_id="user-123",
        ip_address="203.0.113.5",
        user_agent="Mozilla/5.0",
        device_info={"platform": "web"},
        location_info={"country": "US"},
    )

    assert session.user_id == "user-123"
    assert len(session.session_token) == 64

    session_insert = mock_database_service.insert.await_args_list[0]
    assert session_insert.args[0] == "user_sessions"
    payload = session_insert.args[1]
    assert payload["user_id"] == "user-123"
    assert payload["ip_address"] == "203.0.113.5"

    event_insert = mock_database_service.insert.await_args_list[1]
    assert event_insert.args[0] == "security_events"
    event_payload = event_insert.args[1]
    assert event_payload["event_type"] == "login_success"
    assert event_payload["user_id"] == "user-123"


@pytest.mark.asyncio
async def test_create_session_terminates_oldest_when_limit_exceeded(
    session_service: SessionSecurityService, mock_database_service: AsyncMock
) -> None:
    """The service terminates the oldest session when the max limit is hit."""
    now = datetime.now(UTC)
    older = _build_session_row(
        id="session-old",
        created_at=(now - timedelta(hours=2)).isoformat(),
    )
    newer = _build_session_row(
        id="session-new",
        created_at=(now - timedelta(minutes=10)).isoformat(),
    )
    mock_database_service.select.side_effect = [
        [older, newer, newer, newer, newer, newer],
        [],
    ]

    await session_service.create_session(user_id="user-123")

    mock_database_service.update.assert_awaited()
    terminate_call = mock_database_service.update.await_args_list[0]
    assert terminate_call.args[0] == "user_sessions"
    assert terminate_call.args[1] == {"is_active": False, "ended_at": ANY}
    assert terminate_call.args[2]["id"] == "session-old"


@pytest.mark.asyncio
async def test_create_session_when_database_fails(
    session_service: SessionSecurityService, mock_database_service: AsyncMock
) -> None:
    """Failures while inserting a session raise a CoreSecurityError."""
    mock_database_service.select.side_effect = [[], []]
    mock_database_service.insert.side_effect = [Exception("db error")]

    with pytest.raises(CoreSecurityError):
        await session_service.create_session(user_id="user-123")


@pytest.mark.asyncio
async def test_validate_session_updates_activity(
    session_service: SessionSecurityService, mock_database_service: AsyncMock
) -> None:
    """Valid sessions refresh metadata and may log suspicious activity."""
    session_row = _build_session_row()
    mock_database_service.select.side_effect = [[session_row]]

    result = await session_service.validate_session(session_token="token")

    assert result is not None
    mock_database_service.update.assert_awaited()
    update_call = mock_database_service.update.await_args_list[0]
    assert update_call.args[0] == "user_sessions"
    assert update_call.args[1]["ip_address"] is None
    assert update_call.args[2] == {"id": session_row["id"]}


@pytest.mark.asyncio
async def test_validate_session_expires_and_terminates(
    session_service: SessionSecurityService, mock_database_service: AsyncMock
) -> None:
    """Expired sessions are terminated and return None."""
    expired_row = _build_session_row(
        expires_at=(datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    )
    mock_database_service.select.side_effect = [[expired_row]]
    mock_database_service.update.return_value = [{"id": expired_row["id"]}]

    result = await session_service.validate_session(session_token="token")

    assert result is None
    mock_database_service.update.assert_awaited()


@pytest.mark.asyncio
async def test_log_security_event_handles_insert_failure(
    session_service: SessionSecurityService, mock_database_service: AsyncMock
) -> None:
    """Logging failures are caught and do not raise."""
    mock_database_service.insert.side_effect = [Exception("insert failure")]

    event = await session_service.log_security_event(event_type="login_failure")

    assert isinstance(event, SecurityEvent)


@pytest.mark.asyncio
async def test_get_security_metrics_aggregates_counts(
    session_service: SessionSecurityService, mock_database_service: AsyncMock
) -> None:
    """Security metrics are derived from the database results."""
    active_session = _build_session_row()
    now = datetime.now(UTC)
    mock_database_service.select.side_effect = [
        [active_session],  # active sessions
        [{"id": "fail-1"}, {"id": "fail-2"}],  # failed logins
        [{"id": "success-1"}],  # successful logins
        [{"id": "event-1"}, {"id": "event-2"}, {"id": "event-3"}],  # events
        [{"created_at": (now - timedelta(hours=1)).isoformat()}],  # last login
    ]

    metrics = await session_service.get_security_metrics(user_id="user-123")

    assert isinstance(metrics, SessionSecurityMetrics)
    assert metrics.active_sessions == 1
    assert metrics.failed_login_attempts_24h == 2
    assert metrics.successful_logins_24h == 1
    assert metrics.security_events_7d == 3
    assert metrics.risk_score > 0


@pytest.mark.asyncio
async def test_cleanup_expired_sessions_marks_sessions(
    session_service: SessionSecurityService, mock_database_service: AsyncMock
) -> None:
    """Expired sessions are terminated and counted."""
    expired_row = _build_session_row(
        id="expired-1",
        expires_at=(datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
    )
    mock_database_service.select.side_effect = [[expired_row]]
    mock_database_service.update.return_value = [{"id": "expired-1"}]
    mock_database_service.insert.return_value = []

    count = await session_service.cleanup_expired_sessions()

    assert count == 1
    mock_database_service.update.assert_awaited()


def test_user_session_validation_rejects_bad_data() -> None:
    """The UserSession model enforces strict validation rules."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=1)
    with pytest.raises(ValueError):
        UserSession(
            id="bad",
            user_id="user",
            session_token="abcd",
            ip_address=None,
            user_agent=None,
            device_info={},
            location_info={},
            is_active=True,
            last_activity_at=now,
            expires_at=expires_at,
            created_at=now,
            ended_at=None,
        )


def test_security_event_validation_rejects_unknown_type() -> None:
    """Security events validate type and severity fields."""
    with pytest.raises(ValueError):
        SecurityEvent(
            id=None,
            user_id=None,
            event_type="unknown",
            severity="info",
            ip_address=None,
            user_agent=None,
            details={},
        )
