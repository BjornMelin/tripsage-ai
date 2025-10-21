"""Session management and security monitoring primitives.

Works with the Supabase-backed `DatabaseService`.
The service focuses on session lifecycle management, security event logging,
and lightweight risk scoring needed by the rest of the TripSage stack.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from ipaddress import AddressValueError, ip_address as parse_ip_address
from typing import Any, Protocol

from pydantic import Field, field_validator

from tripsage_core.exceptions import CoreSecurityError
from tripsage_core.models.base_core_model import TripSageModel


logger = logging.getLogger(__name__)


class DatabaseServiceProtocol(Protocol):
    """Minimal async database contract needed by this service."""

    async def select(
        self,
        table: str,
        columns: str = "*",
        *,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Select rows from a table."""
        ...

    async def insert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Insert one or more rows."""
        ...

    async def update(
        self,
        table: str,
        data: dict[str, Any],
        filters: dict[str, Any],
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Update rows matching *filters*."""
        ...


class UserSession(TripSageModel):
    """User session model with strict validation."""

    id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    session_token: str = Field(..., description="Session token hash")
    ip_address: str | None = Field(None, description="IP address")
    user_agent: str | None = Field(None, description="User agent string")
    device_info: dict[str, Any] = Field(
        default_factory=dict, description="Device information"
    )
    location_info: dict[str, Any] = Field(
        default_factory=dict, description="Location information"
    )
    is_active: bool = Field(True, description="Session active status")
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = Field(..., description="Session expiration time")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = Field(None, description="Session end time")

    @field_validator("id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        """Validate session ID format and security."""
        if not value or not isinstance(value, str):
            raise ValueError("Session ID must be a non-empty string")
        if len(value) < 8:
            raise ValueError("Session ID must be at least 8 characters")
        if len(value) > 128:
            raise ValueError("Session ID must not exceed 128 characters")
        if any(char in value for char in ["\x00", "\n", "\r", "\t"]):
            raise ValueError("Session ID contains invalid characters")
        return value

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        """Validate user ID format and security."""
        if not value or not isinstance(value, str):
            raise ValueError("User ID must be a non-empty string")
        if len(value) > 255:
            raise ValueError("User ID must not exceed 255 characters")
        if any(ord(char) < 32 for char in value if char != "\t"):
            raise ValueError("User ID contains invalid control characters")
        return value

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str | None) -> str | None:
        """Validate IP address format and security."""
        if value is None or value == "":
            return None
        if not isinstance(value, str):
            raise TypeError("IP address must be a string")
        cleaned_ip = value.strip().replace("\x00", "")
        if len(cleaned_ip) > 45:
            raise ValueError("IP address is too long")
        malicious_patterns = [
            "../",
            "..\\",
            "<script",
            "javascript:",
            "data:",
            "DROP TABLE",
            "UNION SELECT",
            "eval(",
            "exec(",
        ]
        for pattern in malicious_patterns:
            if pattern.lower() in cleaned_ip.lower():
                raise ValueError(f"IP address contains suspicious pattern: {pattern}")
        return cleaned_ip

    @field_validator("user_agent")
    @classmethod
    def validate_user_agent(cls, value: str | None) -> str | None:
        """Validate user agent string."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("User agent must be a string")
        if len(value) > 2048:
            raise ValueError("User agent string is too long")
        return value.replace("\x00", "").replace("\r", "").replace("\n", " ")

    @field_validator("session_token")
    @classmethod
    def validate_session_token(cls, value: str) -> str:
        """Validate session token hash."""
        if not value or not isinstance(value, str):
            raise ValueError("Session token must be a non-empty string")
        if len(value) != 64:
            raise ValueError("Session token must be a valid hash (64 characters)")
        try:
            int(value, 16)
        except ValueError as exc:
            raise ValueError("Session token must be a valid hexadecimal hash") from exc
        return value


class SecurityEvent(TripSageModel):
    """Security event model."""

    id: str | None = Field(None, description="Event ID")
    user_id: str | None = Field(None, description="User ID")
    event_type: str = Field(..., description="Event type")
    event_category: str = Field(default="authentication", description="Category")
    severity: str = Field(default="info", description="Event severity")
    ip_address: str | None = Field(None, description="IP address")
    user_agent: str | None = Field(None, description="User agent")
    details: dict[str, Any] = Field(default_factory=dict, description="Details")
    risk_score: int = Field(default=0, description="Risk score (0-100)")
    is_blocked: bool = Field(default=False, description="Whether action was blocked")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        """Validate event type."""
        allowed_types = {
            "login_success",
            "login_failure",
            "logout",
            "password_reset_request",
            "password_reset_success",
            "password_change",
            "api_key_created",
            "api_key_deleted",
            "suspicious_activity",
            "rate_limit_exceeded",
            "oauth_login",
            "session_expired",
            "invalid_token",
        }
        if value not in allowed_types:
            raise ValueError(f"Invalid event type: {value}")
        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        """Validate severity level."""
        allowed_severities = {"info", "warning", "error", "critical"}
        if value not in allowed_severities:
            raise ValueError(f"Invalid severity: {value}")
        return value

    @field_validator("risk_score")
    @classmethod
    def validate_risk_score(cls, value: int) -> int:
        """Validate risk score."""
        if not 0 <= value <= 100:
            raise ValueError("Risk score must be between 0 and 100")
        return value


class SessionSecurityMetrics(TripSageModel):
    """Aggregated security metrics for a user."""

    user_id: str = Field(..., description="User ID")
    active_sessions: int = Field(default=0, description="Active sessions")
    failed_login_attempts_24h: int = Field(
        default=0, description="Failed logins in 24 hours"
    )
    successful_logins_24h: int = Field(
        default=0, description="Successful logins in 24 hours"
    )
    security_events_7d: int = Field(default=0, description="Events in 7 days")
    risk_score: int = Field(default=0, description="Overall risk score")
    last_login_at: datetime | None = Field(None, description="Last login time")
    password_changed_at: datetime | None = Field(
        None, description="Last password change"
    )


class SessionSecurityService:
    """Session lifecycle, auditing, and lightweight risk assessment."""

    def __init__(
        self,
        database_service: DatabaseServiceProtocol,
        *,
        session_duration_hours: int = 24,
        max_sessions_per_user: int = 5,
        rate_limit_window_minutes: int = 15,
    ):
        """Configure the service with the injected database backend."""
        if database_service is None:
            raise ValueError("database_service is required")
        if session_duration_hours <= 0:
            raise ValueError("session_duration_hours must be positive")
        if max_sessions_per_user <= 0:
            raise ValueError("max_sessions_per_user must be positive")
        if rate_limit_window_minutes <= 0:
            raise ValueError("rate_limit_window_minutes must be positive")

        self.db = database_service
        self.session_duration = timedelta(hours=session_duration_hours)
        self.max_sessions_per_user = max_sessions_per_user
        self.rate_limit_window = timedelta(minutes=rate_limit_window_minutes)

    async def create_session(
        self,
        user_id: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_info: dict[str, Any] | None = None,
        location_info: dict[str, Any] | None = None,
    ) -> UserSession:
        """Create a new user session and log the security event."""
        try:
            active_sessions = await self.get_active_sessions(user_id)
            if len(active_sessions) >= self.max_sessions_per_user:
                oldest_session = min(active_sessions, key=lambda item: item.created_at)
                await self.terminate_session(
                    oldest_session.id,
                    reason="max_sessions_exceeded",
                    user_id=user_id,
                )

            session_token = secrets.token_urlsafe(32)
            session_token_hash = hashlib.sha256(session_token.encode()).hexdigest()
            now = datetime.now(UTC)
            session = UserSession(
                id=secrets.token_urlsafe(16),
                user_id=user_id,
                session_token=session_token_hash,
                ip_address=ip_address,
                user_agent=user_agent,
                device_info=device_info or {},
                location_info=location_info or {},
                is_active=True,
                expires_at=now + self.session_duration,
                ended_at=None,
            )

            await self.db.insert("user_sessions", self._serialize_session(session))

            recent_failures = await self._count_recent_failed_logins(user_id)
            risk_score = self._calculate_login_risk_score(
                recent_failures, ip_address, user_id
            )
            await self.log_security_event(
                event_type="login_success",
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"session_id": session.id},
                risk_score=risk_score,
            )

            logger.info(
                "Session created for user %s", user_id, extra={"session_id": session.id}
            )
            return session
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to create session",
                extra={"user_id": user_id, "error": str(exc)},
            )
            raise CoreSecurityError(
                message="Failed to create session",
                code="SESSION_CREATION_FAILED",
            ) from exc

    async def validate_session(
        self,
        session_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession | None:
        """Validate an existing session and refresh activity metadata."""
        try:
            session_token_hash = hashlib.sha256(session_token.encode()).hexdigest()
            result = await self.db.select(
                "user_sessions",
                "*",
                filters={"session_token": session_token_hash, "is_active": True},
                limit=1,
            )
            if not result:
                return None

            session = UserSession(**result[0])
            now = datetime.now(UTC)
            if session.expires_at <= now:
                await self.terminate_session(session.id, reason="expired")
                return None

            await self.db.update(
                "user_sessions",
                {
                    "last_activity_at": now.isoformat(),
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
                {"id": session.id},
            )

            session.last_activity_at = now
            session.ip_address = ip_address
            session.user_agent = user_agent

            risk_score = self._calculate_activity_risk_score(
                session, ip_address, user_agent
            )
            if risk_score > 70:
                await self.log_security_event(
                    event_type="suspicious_activity",
                    user_id=session.user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"session_id": session.id},
                    risk_score=risk_score,
                    severity="warning",
                )

            return session
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Session validation failed", extra={"error": str(exc)})
            return None

    async def terminate_session(
        self,
        session_id: str,
        *,
        reason: str = "user_logout",
        user_id: str | None = None,
    ) -> bool:
        """Terminate a user session and optionally log the event."""
        try:
            filters: dict[str, Any] = {"id": session_id}
            if user_id:
                filters["user_id"] = user_id

            now = datetime.now(UTC)
            updated_rows = await self.db.update(
                "user_sessions",
                {"is_active": False, "ended_at": now.isoformat()},
                filters,
            )

            if updated_rows and user_id:
                await self.log_security_event(
                    event_type="logout",
                    user_id=user_id,
                    details={"session_id": session_id, "reason": reason},
                )

            logger.info(
                "Session terminated",
                extra={
                    "session_id": session_id,
                    "reason": reason,
                    "user_id": user_id,
                },
            )
            return bool(updated_rows)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to terminate session",
                extra={"session_id": session_id, "error": str(exc)},
            )
            return False

    async def get_active_sessions(self, user_id: str) -> list[UserSession]:
        """Return all non-expired active sessions for *user_id*."""
        try:
            results = await self.db.select(
                "user_sessions",
                "*",
                filters={"user_id": user_id, "is_active": True},
            )
            now = datetime.now(UTC)
            active_sessions: list[UserSession] = []
            for row in results:
                session = UserSession(**row)
                if session.expires_at <= now:
                    await self.terminate_session(
                        session.id, reason="expired", user_id=session.user_id
                    )
                    continue
                active_sessions.append(session)
            return active_sessions
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to get active sessions",
                extra={"user_id": user_id, "error": str(exc)},
            )
            return []

    async def log_security_event(
        self,
        *,
        event_type: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
        risk_score: int = 0,
        severity: str = "info",
        event_category: str = "authentication",
    ) -> SecurityEvent:
        """Persist a security event. Errors during persistence are logged only."""
        event = SecurityEvent(
            id=None,
            user_id=user_id,
            event_type=event_type,
            event_category=event_category,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            risk_score=risk_score,
        )
        try:
            rows = await self.db.insert(
                "security_events", self._serialize_security_event(event)
            )
            if rows:
                event.id = str(rows[0].get("id", event.id))

            logger.info(
                "Security event logged",
                extra={
                    "event_type": event_type,
                    "user_id": user_id,
                    "risk_score": risk_score,
                    "severity": severity,
                },
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to log security event",
                extra={"event_type": event_type, "error": str(exc)},
            )
        return event

    async def get_security_metrics(self, user_id: str) -> SessionSecurityMetrics:
        """Load aggregate metrics for *user_id*."""
        try:
            active_sessions = await self.get_active_sessions(user_id)
            now = datetime.now(UTC)
            day_ago = now - timedelta(days=1)
            week_ago = now - timedelta(days=7)

            failed_logins = await self.db.select(
                "security_events",
                "id",
                filters={
                    "user_id": user_id,
                    "event_type": "login_failure",
                    "created_at": {"gte": day_ago.isoformat()},
                },
            )
            successful_logins = await self.db.select(
                "security_events",
                "id",
                filters={
                    "user_id": user_id,
                    "event_type": "login_success",
                    "created_at": {"gte": day_ago.isoformat()},
                },
            )
            security_events = await self.db.select(
                "security_events",
                "id",
                filters={
                    "user_id": user_id,
                    "created_at": {"gte": week_ago.isoformat()},
                },
            )
            last_login_rows = await self.db.select(
                "security_events",
                "created_at",
                filters={"user_id": user_id, "event_type": "login_success"},
                order_by="-created_at",
                limit=1,
            )
            last_login = (
                self._parse_datetime(last_login_rows[0].get("created_at"))
                if last_login_rows
                else None
            )

            risk_score = self._calculate_user_risk_score(
                {
                    "failed_logins": len(failed_logins),
                    "active_sessions": len(active_sessions),
                    "security_events": len(security_events),
                }
            )

            return SessionSecurityMetrics(
                user_id=user_id,
                active_sessions=len(active_sessions),
                failed_login_attempts_24h=len(failed_logins),
                successful_logins_24h=len(successful_logins),
                security_events_7d=len(security_events),
                risk_score=risk_score,
                last_login_at=last_login,
                password_changed_at=None,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to get security metrics",
                extra={"user_id": user_id, "error": str(exc)},
            )
            return SessionSecurityMetrics(
                user_id=user_id,
                last_login_at=None,
                password_changed_at=None,
            )

    async def cleanup_expired_sessions(self) -> int:
        """Terminate expired active sessions."""
        try:
            now = datetime.now(UTC)
            expired_sessions = await self.db.select(
                "user_sessions",
                "*",
                filters={
                    "is_active": True,
                    "expires_at": {"lt": now.isoformat()},
                },
            )
            cleanup_count = 0
            for session_data in expired_sessions:
                success = await self.terminate_session(
                    session_data["id"],
                    reason="expired",
                    user_id=session_data.get("user_id"),
                )
                if success:
                    cleanup_count += 1
            if cleanup_count > 0:
                logger.info("Cleaned up %s expired sessions", cleanup_count)
            return cleanup_count
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to cleanup expired sessions", exc_info=exc)
            return 0

    async def _count_recent_failed_logins(self, user_id: str) -> int:
        """Count failed login events within the rate limit window."""
        window_start = datetime.now(UTC) - self.rate_limit_window
        failures = await self.db.select(
            "security_events",
            "id",
            filters={
                "user_id": user_id,
                "event_type": "login_failure",
                "created_at": {"gte": window_start.isoformat()},
            },
        )
        return len(failures)

    def _calculate_login_risk_score(
        self, recent_failures: int, ip_address: str | None, user_id: str
    ) -> int:
        """Calculate login risk score based on recent failures and IP quality."""
        risk_score = 0
        if recent_failures > 2:
            risk_score += min(recent_failures * 10, 40)
        if ip_address:
            risk_score += self._validate_and_score_ip(ip_address, user_id)
        return min(risk_score, 100)

    def _validate_and_score_ip(self, ip_address: str, user_id: str) -> int:
        """Validate IP address and calculate a risk score (0-50)."""
        risk_score = 0
        try:
            cleaned_ip = ip_address.strip().replace("\x00", "")
            malicious_patterns = [
                "../",
                "..\\",
                "<script",
                "javascript:",
                "data:",
                "vbscript:",
                "DROP TABLE",
                "UNION SELECT",
                "eval(",
                "exec(",
            ]
            for pattern in malicious_patterns:
                if pattern.lower() in cleaned_ip.lower():
                    logger.warning(
                        "Malicious pattern detected in IP address",
                        extra={"ip_address": cleaned_ip[:100], "user_id": user_id},
                    )
                    risk_score = 50
                    break

            if not risk_score:
                if len(cleaned_ip) > 45:
                    logger.warning(
                        "Excessively long IP address provided",
                        extra={"ip_length": len(cleaned_ip), "user_id": user_id},
                    )
                    risk_score = 40
                elif not cleaned_ip:
                    logger.info("Empty IP address provided", extra={"user_id": user_id})
                    risk_score = 10
                else:
                    try:
                        ip_obj = parse_ip_address(cleaned_ip)
                        if ip_obj.is_private:
                            risk_score = 5
                        elif ip_obj.is_loopback:
                            risk_score = 15
                        elif ip_obj.is_reserved or ip_obj.is_multicast:
                            risk_score = 25
                        elif ip_obj.is_link_local:
                            risk_score = 20
                        elif not ip_obj.is_global:
                            risk_score = 15
                        else:
                            risk_score = 0
                    except AddressValueError as exc:
                        logger.warning(
                            "Invalid IP address format detected",
                            extra={"ip_address": cleaned_ip[:100], "user_id": user_id},
                        )
                        logger.debug(
                            "AddressValueError during IP parsing", exc_info=exc
                        )
                        risk_score = 30
                    except ValueError as exc:
                        logger.warning(
                            "IP address parsing error",
                            extra={"ip_address": cleaned_ip[:100], "user_id": user_id},
                        )
                        logger.debug("ValueError during IP parsing", exc_info=exc)
                        risk_score = 25
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Unexpected error during IP validation",
                extra={"ip_address": str(ip_address)[:100], "user_id": user_id},
            )
            logger.debug("Unexpected error details", exc_info=exc)
            risk_score = 35
        return risk_score

    def _calculate_activity_risk_score(
        self,
        session: UserSession,
        current_ip: str | None,
        current_user_agent: str | None,
    ) -> int:
        """Calculate risk score for session activity changes."""
        risk_score = 0
        if session.ip_address and current_ip and session.ip_address != current_ip:
            risk_score += 30
        if (
            session.user_agent
            and current_user_agent
            and session.user_agent != current_user_agent
        ):
            risk_score += 20
        return min(risk_score, 100)

    def _calculate_user_risk_score(self, metrics: dict[str, Any]) -> int:
        """Calculate overall user risk score from aggregate metrics."""
        risk_score = 0
        failed_logins = metrics.get("failed_logins", 0)
        if failed_logins > 0:
            risk_score += min(failed_logins * 5, 25)
        active_sessions = metrics.get("active_sessions", 0)
        if active_sessions > 3:
            risk_score += (active_sessions - 3) * 5
        security_events = metrics.get("security_events", 0)
        if security_events > 10:
            risk_score += min((security_events - 10) * 2, 20)
        return min(risk_score, 100)

    @staticmethod
    def _serialize_session(session: UserSession) -> dict[str, Any]:
        """Convert a session model into database-friendly payload."""
        payload = session.model_dump()
        payload["created_at"] = session.created_at.isoformat()
        payload["expires_at"] = session.expires_at.isoformat()
        payload["last_activity_at"] = session.last_activity_at.isoformat()
        payload["ended_at"] = session.ended_at.isoformat() if session.ended_at else None
        return payload

    @staticmethod
    def _serialize_security_event(event: SecurityEvent) -> dict[str, Any]:
        """Convert a security event model into database-friendly payload."""
        payload = event.model_dump()
        payload["created_at"] = event.created_at.isoformat()
        return payload

    @staticmethod
    def _parse_datetime(value: datetime | str | None) -> datetime | None:
        """Parse ISO datetime strings safely."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.astimezone(UTC)
        normalized = value.replace("Z", "+00:00") if isinstance(value, str) else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            logger.debug("Failed to parse datetime: %s", value)
            return None
        return parsed.astimezone(UTC)


async def get_session_security_service() -> SessionSecurityService:
    """FastAPI dependency factory for the session security service."""
    from tripsage_core.services.infrastructure import get_database_service

    database_service = await get_database_service()
    return SessionSecurityService(database_service=database_service)
