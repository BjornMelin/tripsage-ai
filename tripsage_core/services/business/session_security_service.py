"""
Session Management and Security Monitoring Service.

This service provides comprehensive session management, security event logging,
and user activity monitoring for TripSage authentication system.
"""

import hashlib
import json
import logging
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from ipaddress import AddressValueError, ip_address

from pydantic import Field, field_validator
from tripsage_core.exceptions import (
    CoreSecurityError,
    CoreServiceError,
    CoreValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel

logger = logging.getLogger(__name__)


class UserSession(TripSageModel):
    """User session model."""

    id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    session_token: str = Field(..., description="Session token hash")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    device_info: Dict[str, Any] = Field(default_factory=dict, description="Device information")
    location_info: Dict[str, Any] = Field(default_factory=dict, description="Location information")
    is_active: bool = Field(True, description="Session active status")
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(..., description="Session expiration time")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = Field(None, description="Session end time")


class SecurityEvent(TripSageModel):
    """Security event model."""

    id: Optional[str] = Field(None, description="Event ID")
    user_id: Optional[str] = Field(None, description="User ID")
    event_type: str = Field(..., description="Event type")
    event_category: str = Field(default="authentication", description="Event category")
    severity: str = Field(default="info", description="Event severity")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details")
    risk_score: int = Field(default=0, description="Risk score (0-100)")
    is_blocked: bool = Field(default=False, description="Whether action was blocked")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate event type."""
        allowed_types = {
            "login_success", "login_failure", "logout", "password_reset_request",
            "password_reset_success", "password_change", "api_key_created",
            "api_key_deleted", "suspicious_activity", "rate_limit_exceeded",
            "oauth_login", "session_expired", "invalid_token"
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
    failed_login_attempts_24h: int = Field(default=0, description="Failed logins in 24h")
    successful_logins_24h: int = Field(default=0, description="Successful logins in 24h")
    security_events_7d: int = Field(default=0, description="Security events in 7 days")
    risk_score: int = Field(default=0, description="Overall risk score")
    last_login_at: Optional[datetime] = Field(None, description="Last login time")
    password_changed_at: Optional[datetime] = Field(None, description="Last password change")


class SessionSecurityService:
    """
    Comprehensive session management and security monitoring service.

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
        """
        Initialize the session security service.

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
        self._rate_limit_cache: Dict[str, List[float]] = {}
        self._risk_scores: Dict[str, int] = {}

    async def create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None,
        location_info: Optional[Dict[str, Any]] = None,
    ) -> UserSession:
        """
        Create a new user session.

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
                await self.terminate_session(oldest_session.id, reason="max_sessions_exceeded")

            # Generate secure session token
            session_token = secrets.token_urlsafe(32)
            session_token_hash = hashlib.sha256(session_token.encode()).hexdigest()

            # Create session
            now = datetime.now(timezone.utc)
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
            logger.error(
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
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[UserSession]:
        """
        Validate and refresh a session.

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
            now = datetime.now(timezone.utc)
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
            risk_score = self._calculate_activity_risk_score(session, ip_address, user_agent)
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
            logger.error(
                "Session validation failed",
                extra={"error": str(e)},
            )
            return None

    async def terminate_session(
        self,
        session_id: str,
        reason: str = "user_logout",
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Terminate a user session.

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
            now = datetime.now(timezone.utc)
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
            logger.error(
                "Failed to terminate session",
                extra={"session_id": session_id, "error": str(e)},
            )
            return False

    async def get_active_sessions(self, user_id: str) -> List[UserSession]:
        """
        Get all active sessions for a user.

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
            now = datetime.now(timezone.utc)

            for result in results:
                session = UserSession(**result)
                
                # Check if session is expired
                if session.expires_at <= now:
                    await self.terminate_session(session.id, reason="expired")
                    continue

                sessions.append(session)

            return sessions

        except Exception as e:
            logger.error(
                "Failed to get active sessions",
                extra={"user_id": user_id, "error": str(e)},
            )
            return []

    async def log_security_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        risk_score: int = 0,
        severity: str = "info",
        event_category: str = "authentication",
    ) -> SecurityEvent:
        """
        Log a security event.

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
            logger.error(
                "Failed to log security event",
                extra={"event_type": event_type, "error": str(e)},
            )
            # Don't raise exception for logging failures
            return event

    async def get_security_metrics(self, user_id: str) -> SessionSecurityMetrics:
        """
        Get security metrics for a user.

        Args:
            user_id: User identifier

        Returns:
            Security metrics
        """
        try:
            # Get active sessions count
            active_sessions = await self.get_active_sessions(user_id)

            # Get recent events
            now = datetime.now(timezone.utc)
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
            risk_score = self._calculate_user_risk_score(user_id, {
                "failed_logins": failed_logins[0]["count"] if failed_logins else 0,
                "active_sessions": len(active_sessions),
                "security_events": security_events[0]["count"] if security_events else 0,
            })

            return SessionSecurityMetrics(
                user_id=user_id,
                active_sessions=len(active_sessions),
                failed_login_attempts_24h=failed_logins[0]["count"] if failed_logins else 0,
                successful_logins_24h=successful_logins[0]["count"] if successful_logins else 0,
                security_events_7d=security_events[0]["count"] if security_events else 0,
                risk_score=risk_score,
                last_login_at=datetime.fromisoformat(last_login[0]["created_at"]) if last_login else None,
            )

        except Exception as e:
            logger.error(
                "Failed to get security metrics",
                extra={"user_id": user_id, "error": str(e)},
            )
            return SessionSecurityMetrics(user_id=user_id)

    def _calculate_login_risk_score(self, user_id: str, ip_address: Optional[str]) -> int:
        """Calculate risk score for login attempt."""
        risk_score = 0

        # Check recent failed attempts
        recent_failures = self._get_recent_failures(user_id)
        if recent_failures > 2:
            risk_score += min(recent_failures * 10, 40)

        # Check IP reputation (simplified)
        if ip_address:
            try:
                ip_obj = ip_address(ip_address)
                if ip_obj.is_private:
                    risk_score += 5  # Private IPs are slightly more risky
                elif not ip_obj.is_global:
                    risk_score += 15  # Local/reserved IPs are more risky
            except AddressValueError:
                risk_score += 20  # Invalid IP format

        return min(risk_score, 100)

    def _calculate_activity_risk_score(
        self,
        session: UserSession,
        current_ip: Optional[str],
        current_user_agent: Optional[str],
    ) -> int:
        """Calculate risk score for activity."""
        risk_score = 0

        # IP address change
        if session.ip_address and current_ip and session.ip_address != current_ip:
            risk_score += 30

        # User agent change
        if session.user_agent and current_user_agent and session.user_agent != current_user_agent:
            risk_score += 20

        return min(risk_score, 100)

    def _calculate_user_risk_score(self, user_id: str, metrics: Dict[str, Any]) -> int:
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
        # For now, return a mock value
        return self._rate_limit_cache.get(f"failures_{user_id}", [])

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        try:
            now = datetime.now(timezone.utc)
            
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
                logger.info(f"Cleaned up {cleanup_count} expired sessions")

            return cleanup_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0


# Dependency function for FastAPI
async def get_session_security_service() -> SessionSecurityService:
    """
    Get session security service instance for dependency injection.

    Returns:
        SessionSecurityService instance
    """
    return SessionSecurityService()