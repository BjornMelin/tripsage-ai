"""Session Management and Security Monitoring Service.

This service provides comprehensive session management, security event logging,
and user activity monitoring for TripSage authentication system.
"""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from ipaddress import AddressValueError, ip_address as parse_ip_address
from typing import Any

from pydantic import Field, field_validator

from tripsage_core.exceptions import (
    CoreSecurityError,
)
from tripsage_core.models.base_core_model import TripSageModel


logger = logging.getLogger(__name__)


class UserSession(TripSageModel):
    """User session model with enhanced security validation."""

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
    def validate_session_id(cls, v: str) -> str:
        """Validate session ID format and security."""
        if not v or not isinstance(v, str):
            raise ValueError("Session ID must be a non-empty string")

        if len(v) < 8:
            raise ValueError("Session ID must be at least 8 characters")

        if len(v) > 128:
            raise ValueError("Session ID must not exceed 128 characters")

        # Check for basic security patterns
        if any(char in v for char in ["\x00", "\n", "\r", "\t"]):
            raise ValueError("Session ID contains invalid characters")

        return v

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user ID format and security."""
        if not v or not isinstance(v, str):
            raise ValueError("User ID must be a non-empty string")

        if len(v) > 255:
            raise ValueError("User ID must not exceed 255 characters")

        # Check for control characters that might cause issues
        if any(ord(char) < 32 for char in v if char not in ["\t"]):
            raise ValueError("User ID contains invalid control characters")

        return v

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: str | None) -> str | None:
        """Validate IP address format and security."""
        if v is None or v == "":
            return None

        if not isinstance(v, str):
            raise ValueError("IP address must be a string")

        # Sanitize and validate
        cleaned_ip = v.strip().replace("\x00", "")

        if len(cleaned_ip) > 45:  # IPv6 max is 39 characters
            raise ValueError("IP address is too long")

        # Check for malicious patterns
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

        # Optional: Validate IP format (but allow invalid IPs to be stored for analysis)
        # This is a security vs. usability tradeoff

        return cleaned_ip

    @field_validator("user_agent")
    @classmethod
    def validate_user_agent(cls, v: str | None) -> str | None:
        """Validate user agent string."""
        if v is None:
            return None

        if not isinstance(v, str):
            raise ValueError("User agent must be a string")

        # Limit length to prevent abuse
        if len(v) > 2048:
            raise ValueError("User agent string is too long")

        # Remove null bytes and other problematic characters
        return v.replace("\x00", "").replace("\r", "").replace("\n", " ")

    @field_validator("session_token")
    @classmethod
    def validate_session_token(cls, v: str) -> str:
        """Validate session token hash."""
        if not v or not isinstance(v, str):
            raise ValueError("Session token must be a non-empty string")

        # For SHA256 hashes, expect 64 characters
        if len(v) != 64:
            raise ValueError("Session token must be a valid hash (64 characters)")

        # Validate hex format
        try:
            int(v, 16)
        except ValueError as e:
            raise ValueError("Session token must be a valid hexadecimal hash") from e

        return v


class SecurityEvent(TripSageModel):
    """Security event model."""

    id: str | None = Field(None, description="Event ID")
    user_id: str | None = Field(None, description="User ID")
    event_type: str = Field(..., description="Event type")
    event_category: str = Field(default="authentication", description="Event category")
    severity: str = Field(default="info", description="Event severity")
    ip_address: str | None = Field(None, description="IP address")
    user_agent: str | None = Field(None, description="User agent")
    details: dict[str, Any] = Field(default_factory=dict, description="Event details")
    risk_score: int = Field(default=0, description="Risk score (0-100)")
    is_blocked: bool = Field(default=False, description="Whether action was blocked")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
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
        if v not in allowed_types:
            raise ValueError(f"Invalid event type: {v}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity level."""
        allowed_severities = {"info", "warning", "error", "critical"}
        if v not in allowed_severities:
            raise ValueError(f"Invalid severity: {v}")
        return v

    @field_validator("risk_score")
    @classmethod
    def validate_risk_score(cls, v: int) -> int:
        """Validate risk score."""
        if not 0 <= v <= 100:
            raise ValueError("Risk score must be between 0 and 100")
        return v


class SessionSecurityMetrics(TripSageModel):
    """Security metrics for a user."""

    user_id: str = Field(..., description="User ID")
    active_sessions: int = Field(default=0, description="Number of active sessions")
    failed_login_attempts_24h: int = Field(
        default=0, description="Failed logins in 24h"
    )
    successful_logins_24h: int = Field(
        default=0, description="Successful logins in 24h"
    )
    security_events_7d: int = Field(default=0, description="Security events in 7 days")
    risk_score: int = Field(default=0, description="Overall risk score")
    last_login_at: datetime | None = Field(None, description="Last login time")
    password_changed_at: datetime | None = Field(
        None, description="Last password change"
    )


class SessionSecurityService:
    """Comprehensive session management and security monitoring service.

    This service provides:
    - Session lifecycle management
    - Security event logging and analysis
    - Risk assessment and anomaly detection
    - User activity monitoring
    - Device and location tracking
    """

    def __init__(
        self,
        database_service=None,
        session_duration_hours: int = 24,
        max_sessions_per_user: int = 5,
        rate_limit_window_minutes: int = 15,
        max_failed_attempts: int = 5,
    ):
        """Initialize the session security service.

        Args:
            database_service: Database service for persistence
            session_duration_hours: Default session duration
            max_sessions_per_user: Maximum concurrent sessions per user
            rate_limit_window_minutes: Rate limiting window
            max_failed_attempts: Max failed attempts before blocking
        """
        # Import here to avoid circular imports
        if database_service is None:
            from tripsage_core.services.infrastructure import get_database_service

            database_service = get_database_service()

        self.db = database_service
        self.session_duration = timedelta(hours=session_duration_hours)
        self.max_sessions_per_user = max_sessions_per_user
        self.rate_limit_window = timedelta(minutes=rate_limit_window_minutes)
        self.max_failed_attempts = max_failed_attempts

        # In-memory cache for rate limiting (use Redis in production)
        self._rate_limit_cache: dict[str, list[float]] = {}
        self._risk_scores: dict[str, int] = {}

    async def create_session(
        self,
        user_id: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_info: dict[str, Any] | None = None,
        location_info: dict[str, Any] | None = None,
    ) -> UserSession:
        """Create a new user session.

        Args:
            user_id: User identifier
            ip_address: Client IP address
            user_agent: User agent string
            device_info: Device information
            location_info: Location information

        Returns:
            Created session object

        Raises:
            CoreSecurityError: If session creation fails security checks
        """
        try:
            # Check for too many active sessions
            active_sessions = await self.get_active_sessions(user_id)
            if len(active_sessions) >= self.max_sessions_per_user:
                # Terminate oldest session
                oldest_session = min(active_sessions, key=lambda s: s.created_at)
                await self.terminate_session(
                    oldest_session.id, reason="max_sessions_exceeded"
                )

            # Generate secure session token
            session_token = secrets.token_urlsafe(32)
            session_token_hash = hashlib.sha256(session_token.encode()).hexdigest()

            # Create session
            now = datetime.now(UTC)
            session = UserSession(
                id=secrets.token_urlsafe(16),
                user_id=user_id,
                session_token=session_token_hash,
                ip_address=ip_address,
                user_agent=user_agent,
                device_info=device_info or {},
                location_info=location_info or {},
                expires_at=now + self.session_duration,
            )

            # Store in database
            session_data = session.model_dump()
            session_data["created_at"] = session.created_at.isoformat()
            session_data["expires_at"] = session.expires_at.isoformat()
            session_data["last_activity_at"] = session.last_activity_at.isoformat()

            await self.db.insert("user_sessions", session_data)

            # Log security event
            await self.log_security_event(
                user_id=user_id,
                event_type="login_success",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"session_id": session.id},
                risk_score=self._calculate_login_risk_score(user_id, ip_address),
            )

            logger.info(
                "Session created",
                extra={
                    "user_id": user_id,
                    "session_id": session.id,
                    "ip_address": ip_address,
                },
            )

            return session

        except Exception as e:
            logger.exception(
                "Failed to create session",
                extra={"user_id": user_id, "error": str(e)},
            )
            raise CoreSecurityError(
                message="Failed to create session",
                code="SESSION_CREATION_FAILED",
            ) from e

    async def validate_session(
        self,
        session_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserSession | None:
        """Validate and refresh a session.

        Args:
            session_token: Session token to validate
            ip_address: Current IP address
            user_agent: Current user agent

        Returns:
            Valid session or None if invalid
        """
        try:
            session_token_hash = hashlib.sha256(session_token.encode()).hexdigest()

            # Get session from database
            result = await self.db.select(
                "user_sessions",
                "*",
                {
                    "session_token": session_token_hash,
                    "is_active": True,
                },
            )

            if not result:
                return None

            session_data = result[0]
            session = UserSession(**session_data)

            # Check if session is expired
            now = datetime.now(UTC)
            if session.expires_at <= now:
                await self.terminate_session(session.id, reason="expired")
                return None

            # Update last activity
            await self.db.update(
                "user_sessions",
                {"id": session.id},
                {
                    "last_activity_at": now.isoformat(),
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
            )

            # Check for suspicious activity
            risk_score = self._calculate_activity_risk_score(
                session, ip_address, user_agent
            )
            if risk_score > 70:  # High risk threshold
                await self.log_security_event(
                    user_id=session.user_id,
                    event_type="suspicious_activity",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "session_id": session.id,
                        "risk_factors": "IP or user agent change",
                    },
                    risk_score=risk_score,
                    severity="warning",
                )

            return session

        except Exception as e:
            logger.exception(
                "Session validation failed",
                extra={"error": str(e)},
            )
            return None

    async def terminate_session(
        self,
        session_id: str,
        reason: str = "user_logout",
        user_id: str | None = None,
    ) -> bool:
        """Terminate a user session.

        Args:
            session_id: Session ID to terminate
            reason: Termination reason
            user_id: User ID for authorization

        Returns:
            True if session was terminated
        """
        try:
            # Build query conditions
            conditions = {"id": session_id}
            if user_id:
                conditions["user_id"] = user_id

            # Update session
            now = datetime.now(UTC)
            result = await self.db.update(
                "user_sessions",
                conditions,
                {
                    "is_active": False,
                    "ended_at": now.isoformat(),
                },
            )

            if result:
                # Log security event
                if user_id:
                    await self.log_security_event(
                        user_id=user_id,
                        event_type="logout",
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

            return bool(result)

        except Exception as e:
            logger.exception(
                "Failed to terminate session",
                extra={"session_id": session_id, "error": str(e)},
            )
            return False

    async def get_active_sessions(self, user_id: str) -> list[UserSession]:
        """Get all active sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of active sessions
        """
        try:
            results = await self.db.select(
                "user_sessions",
                "*",
                {"user_id": user_id, "is_active": True},
            )

            sessions = []
            now = datetime.now(UTC)

            for result in results:
                session = UserSession(**result)

                # Check if session is expired
                if session.expires_at <= now:
                    await self.terminate_session(session.id, reason="expired")
                    continue

                sessions.append(session)

            return sessions

        except Exception as e:
            logger.exception(
                "Failed to get active sessions",
                extra={"user_id": user_id, "error": str(e)},
            )
            return []

    async def log_security_event(
        self,
        event_type: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
        risk_score: int = 0,
        severity: str = "info",
        event_category: str = "authentication",
    ) -> SecurityEvent:
        """Log a security event.

        Args:
            event_type: Type of security event
            user_id: User ID (if applicable)
            ip_address: IP address
            user_agent: User agent
            details: Additional event details
            risk_score: Risk score (0-100)
            severity: Event severity
            event_category: Event category

        Returns:
            Created security event
        """
        try:
            event = SecurityEvent(
                user_id=user_id,
                event_type=event_type,
                event_category=event_category,
                severity=severity,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or {},
                risk_score=risk_score,
            )

            # Store in database
            event_data = event.model_dump()
            event_data["created_at"] = event.created_at.isoformat()

            result = await self.db.insert("security_events", event_data)
            event.id = str(result["id"])

            logger.info(
                "Security event logged",
                extra={
                    "event_type": event_type,
                    "user_id": user_id,
                    "risk_score": risk_score,
                    "severity": severity,
                },
            )

            return event

        except Exception as e:
            logger.exception(
                "Failed to log security event",
                extra={"event_type": event_type, "error": str(e)},
            )
            # Don't raise exception for logging failures
            return event

    async def get_security_metrics(self, user_id: str) -> SessionSecurityMetrics:
        """Get security metrics for a user.

        Args:
            user_id: User identifier

        Returns:
            Security metrics
        """
        try:
            # Get active sessions count
            active_sessions = await self.get_active_sessions(user_id)

            # Get recent events
            now = datetime.now(UTC)
            day_ago = now - timedelta(days=1)
            week_ago = now - timedelta(days=7)

            # Failed logins in 24h
            failed_logins = await self.db.select(
                "security_events",
                "COUNT(*) as count",
                {
                    "user_id": user_id,
                    "event_type": "login_failure",
                    "created_at__gte": day_ago.isoformat(),
                },
            )

            # Successful logins in 24h
            successful_logins = await self.db.select(
                "security_events",
                "COUNT(*) as count",
                {
                    "user_id": user_id,
                    "event_type": "login_success",
                    "created_at__gte": day_ago.isoformat(),
                },
            )

            # Security events in 7 days
            security_events = await self.db.select(
                "security_events",
                "COUNT(*) as count",
                {
                    "user_id": user_id,
                    "created_at__gte": week_ago.isoformat(),
                },
            )

            # Get last login
            last_login = await self.db.select(
                "security_events",
                "created_at",
                {"user_id": user_id, "event_type": "login_success"},
                order_by="created_at DESC",
                limit=1,
            )

            # Calculate overall risk score
            risk_score = self._calculate_user_risk_score(
                user_id,
                {
                    "failed_logins": failed_logins[0]["count"] if failed_logins else 0,
                    "active_sessions": len(active_sessions),
                    "security_events": security_events[0]["count"]
                    if security_events
                    else 0,
                },
            )

            return SessionSecurityMetrics(
                user_id=user_id,
                active_sessions=len(active_sessions),
                failed_login_attempts_24h=failed_logins[0]["count"]
                if failed_logins
                else 0,
                successful_logins_24h=successful_logins[0]["count"]
                if successful_logins
                else 0,
                security_events_7d=security_events[0]["count"]
                if security_events
                else 0,
                risk_score=risk_score,
                last_login_at=datetime.fromisoformat(last_login[0]["created_at"])
                if last_login
                else None,
            )

        except Exception as e:
            logger.exception(
                "Failed to get security metrics",
                extra={"user_id": user_id, "error": str(e)},
            )
            return SessionSecurityMetrics(user_id=user_id)

    def _calculate_login_risk_score(self, user_id: str, ip_address: str | None) -> int:
        """Calculate risk score for login attempt."""
        risk_score = 0

        # Check recent failed attempts
        recent_failures = self._get_recent_failures(user_id)
        if recent_failures > 2:
            risk_score += min(recent_failures * 10, 40)

        # Check IP reputation with enhanced validation
        if ip_address:
            ip_risk = self._validate_and_score_ip(ip_address, user_id)
            risk_score += ip_risk

        return min(risk_score, 100)

    def _validate_and_score_ip(self, ip_address: str, user_id: str) -> int:
        """Validate IP address and calculate risk score with enhanced security.

        Args:
            ip_address: IP address to validate
            user_id: User ID for logging context

        Returns:
            Risk score based on IP validation (0-50)
        """
        try:
            # Sanitize input - remove leading/trailing whitespace and null bytes
            cleaned_ip = ip_address.strip().replace("\x00", "")

            # Check for obvious malicious patterns
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
                        extra={
                            "ip_address": cleaned_ip[:100],  # Limit log size
                            "user_id": user_id,
                            "pattern": pattern,
                        },
                    )
                    return 50  # Maximum IP risk score

            # Validate IP length to prevent buffer overflow attempts
            if len(cleaned_ip) > 45:  # IPv6 max length is 39, add buffer for edge cases
                logger.warning(
                    "Excessively long IP address provided",
                    extra={
                        "ip_length": len(cleaned_ip),
                        "ip_address": cleaned_ip[:50] + "...",
                        "user_id": user_id,
                    },
                )
                return 40

            # Validate empty or None IP
            if not cleaned_ip:
                logger.info("Empty IP address provided", extra={"user_id": user_id})
                return 10  # Low risk for missing IP

            # Parse and validate IP address
            try:
                ip_obj = parse_ip_address(cleaned_ip)

                # Calculate risk based on IP type
                if ip_obj.is_private:
                    return 5  # Private IPs are slightly more risky
                elif ip_obj.is_loopback:
                    return 15  # Loopback IPs are suspicious for remote auth
                elif ip_obj.is_reserved or ip_obj.is_multicast:
                    return 25  # Reserved/multicast IPs are highly suspicious
                elif ip_obj.is_link_local:
                    return 20  # Link-local IPs are suspicious
                elif not ip_obj.is_global:
                    return 15  # Non-global IPs are moderately risky
                else:
                    return 0  # Global IPs are lowest risk

            except AddressValueError as e:
                # Handle invalid IP format with detailed logging
                logger.warning(
                    "Invalid IP address format detected",
                    extra={
                        "ip_address": cleaned_ip[:100],  # Limit log size
                        "user_id": user_id,
                        "error": str(e),
                        "error_type": "AddressValueError",
                    },
                )
                return 30  # Moderate risk for invalid IP format

            except ValueError as e:
                # Handle other parsing errors
                logger.warning(
                    "IP address parsing error",
                    extra={
                        "ip_address": cleaned_ip[:100],  # Limit log size
                        "user_id": user_id,
                        "error": str(e),
                        "error_type": "ValueError",
                    },
                )
                return 25  # Moderate risk for parsing errors

        except Exception as e:
            # Handle any unexpected errors gracefully
            logger.exception(
                "Unexpected error during IP validation",
                extra={
                    "ip_address": str(ip_address)[:100] if ip_address else "None",
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return 35  # Higher risk for unexpected errors

        return 0  # Default to no additional risk

    def _calculate_activity_risk_score(
        self,
        session: UserSession,
        current_ip: str | None,
        current_user_agent: str | None,
    ) -> int:
        """Calculate risk score for activity."""
        risk_score = 0

        # IP address change
        if session.ip_address and current_ip and session.ip_address != current_ip:
            risk_score += 30

        # User agent change
        if (
            session.user_agent
            and current_user_agent
            and session.user_agent != current_user_agent
        ):
            risk_score += 20

        return min(risk_score, 100)

    def _calculate_user_risk_score(self, user_id: str, metrics: dict[str, Any]) -> int:
        """Calculate overall user risk score."""
        risk_score = 0

        # Failed login attempts
        failed_logins = metrics.get("failed_logins", 0)
        if failed_logins > 0:
            risk_score += min(failed_logins * 5, 25)

        # Too many active sessions
        active_sessions = metrics.get("active_sessions", 0)
        if active_sessions > 3:
            risk_score += (active_sessions - 3) * 5

        # High security event count
        security_events = metrics.get("security_events", 0)
        if security_events > 10:
            risk_score += min((security_events - 10) * 2, 20)

        return min(risk_score, 100)

    def _get_recent_failures(self, user_id: str) -> int:
        """Get recent failed login attempts (simplified)."""
        # In a real implementation, this would query the database
        # For now, return the count of failures from cache
        failures_list = self._rate_limit_cache.get(f"failures_{user_id}", [])
        return len(failures_list) if isinstance(failures_list, list) else 0

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        try:
            now = datetime.now(UTC)

            # Find expired sessions
            expired_sessions = await self.db.select(
                "user_sessions",
                "*",
                {
                    "is_active": True,
                    "expires_at__lt": now.isoformat(),
                },
            )

            # Terminate expired sessions
            cleanup_count = 0
            for session_data in expired_sessions:
                success = await self.terminate_session(
                    session_data["id"],
                    reason="expired",
                    user_id=session_data["user_id"],
                )
                if success:
                    cleanup_count += 1

            if cleanup_count > 0:
                logger.info("Cleaned up %s expired sessions", cleanup_count)

            return cleanup_count

        except Exception:
            logger.exception("Failed to cleanup expired sessions")
            return 0


# Dependency function for FastAPI
async def get_session_security_service() -> SessionSecurityService:
    """Get session security service instance for dependency injection.

    Returns:
        SessionSecurityService instance
    """
    return SessionSecurityService()
