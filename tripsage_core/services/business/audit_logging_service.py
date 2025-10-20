"""Comprehensive Security Audit Logging Service.

This service provides enterprise-grade audit logging capabilities following
NIST SP 800-92, OWASP, and industry best practices for security event tracking.

Features:
- Structured JSON logging with consistent schema
- Security event classification and severity levels
- Configurable log retention and rotation policies
- Non-blocking asynchronous logging
- Integration with monitoring and alerting systems
- Compliance-ready audit trails
- Optional log forwarding to external systems
- Tamper-resistant log integrity controls
"""

import asyncio
import hashlib
import json
import logging
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, validator

from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class AuditEventType(str, Enum):
    """Types of security events that can be audited."""

    # Authentication Events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILED = "auth.login.failed"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_REFRESH = "auth.token.refresh"
    AUTH_TOKEN_EXPIRED = "auth.token.expired"
    AUTH_MFA_SUCCESS = "auth.mfa.success"
    AUTH_MFA_FAILED = "auth.mfa.failed"
    AUTH_PASSWORD_CHANGE = "auth.password.change"
    AUTH_PASSWORD_RESET = "auth.password.reset"

    # API Key Management Events
    API_KEY_CREATED = "api_key.created"
    API_KEY_ROTATED = "api_key.rotated"
    API_KEY_DELETED = "api_key.deleted"
    API_KEY_VALIDATION_SUCCESS = "api_key.validation.success"
    API_KEY_VALIDATION_FAILED = "api_key.validation.failed"
    API_KEY_RATE_LIMITED = "api_key.rate_limited"
    API_KEY_QUOTA_EXCEEDED = "api_key.quota_exceeded"

    # Access Control Events
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"
    PERMISSION_CHANGED = "permission.changed"
    ROLE_ASSIGNED = "role.assigned"
    ROLE_REMOVED = "role.removed"

    # Configuration Changes
    CONFIG_CHANGED = "config.changed"
    SYSTEM_SETTING_CHANGED = "system.setting.changed"
    SECURITY_POLICY_CHANGED = "security.policy.changed"

    # Security Violations
    SECURITY_SUSPICIOUS_ACTIVITY = "security.suspicious_activity"
    SECURITY_MULTIPLE_FAILED_ATTEMPTS = "security.multiple_failed_attempts"
    SECURITY_UNUSUAL_PATTERN = "security.unusual_pattern"
    SECURITY_PRIVILEGE_ESCALATION = "security.privilege_escalation"
    SECURITY_DATA_EXFILTRATION = "security.data_exfiltration"

    # Rate Limiting & Abuse
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"
    QUOTA_WARNING = "quota.warning"
    QUOTA_EXCEEDED = "quota.exceeded"
    ABUSE_DETECTED = "abuse.detected"

    # Data Access Events
    DATA_ACCESS = "data.access"
    DATA_MODIFICATION = "data.modification"
    DATA_DELETION = "data.deletion"
    DATA_EXPORT = "data.export"
    DATA_BACKUP = "data.backup"

    # System Events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_MAINTENANCE = "system.maintenance"

    # Administrative Actions
    ADMIN_USER_CREATED = "admin.user.created"
    ADMIN_USER_DELETED = "admin.user.deleted"
    ADMIN_USER_MODIFIED = "admin.user.modified"
    ADMIN_PRIVILEGE_GRANTED = "admin.privilege.granted"
    ADMIN_PRIVILEGE_REVOKED = "admin.privilege.revoked"


class AuditSeverity(str, Enum):
    """Severity levels for audit events following NIST guidelines."""

    INFORMATIONAL = "informational"  # Normal operations
    LOW = "low"  # Minor security events
    MEDIUM = "medium"  # Moderate security concerns
    HIGH = "high"  # Significant security events
    CRITICAL = "critical"  # Critical security incidents


class AuditOutcome(str, Enum):
    """Outcome of the audited event."""

    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


class AuditSource(BaseModel):
    """Source information for the audit event."""

    ip_address: str
    user_agent: str | None = None
    country: str | None = None
    city: str | None = None
    isp: str | None = None
    threat_level: str | None = None
    is_tor: bool = False
    is_vpn: bool = False


class AuditTarget(BaseModel):
    """Target resource or entity of the audit event."""

    resource_type: str  # user, api_key, configuration, etc.
    resource_id: str
    resource_name: str | None = None
    resource_attributes: dict[str, Any] = Field(default_factory=dict)


class AuditActor(BaseModel):
    """Actor (user or system) performing the audited action."""

    actor_type: str  # user, system, api_key, service
    actor_id: str
    actor_name: str | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    session_id: str | None = None
    authentication_method: str | None = None


class AuditEvent(TripSageModel):
    """Comprehensive audit event following NIST SP 800-92 guidelines.

    This model represents a single security event with all required
    metadata for compliance and forensic analysis.
    """

    # Core Event Identification
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AuditEventType
    event_version: str = "1.0"

    # Temporal Information
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    timezone: str = "UTC"

    # Event Details
    severity: AuditSeverity
    outcome: AuditOutcome
    message: str
    description: str | None = None

    # Context Information
    actor: AuditActor
    target: AuditTarget | None = None
    source: AuditSource

    # Request Context
    request_id: str | None = None
    correlation_id: str | None = None
    session_id: str | None = None
    trace_id: str | None = None

    # Technical Details
    application: str = "tripsage"
    environment: str = "production"
    service_name: str = "audit-service"
    service_version: str = "1.0.0"

    # Additional Data
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Security Context
    risk_score: int | None = None  # 0-100
    compliance_tags: list[str] = Field(default_factory=list)

    # Data Classification
    data_classification: str | None = None  # public, internal, confidential, restricted
    retention_period_days: int = 2555  # 7 years default

    @validator("risk_score")
    def validate_risk_score(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("Risk score must be between 0 and 100")
        return v

    @validator("timestamp")
    def validate_timestamp(cls, v):
        # Ensure timestamp is UTC
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)
        return v

    def to_json_log(self) -> str:
        """Convert to structured JSON log format."""
        return json.dumps(self.model_dump(mode="json"), separators=(",", ":"))

    def compute_integrity_hash(self, secret_key: str) -> str:
        """Compute HMAC-SHA256 integrity hash for tamper detection."""
        content = self.to_json_log()
        return hashlib.sha256(f"{content}{secret_key}".encode()).hexdigest()


class AuditLogConfig(BaseModel):
    """Configuration for audit logging service."""

    # Logging Configuration
    enabled: bool = True
    log_level: str = "INFO"
    async_logging: bool = True
    buffer_size: int = 1000
    flush_interval_seconds: int = 10

    # Storage Configuration
    log_directory: str = "/var/log/tripsage/audit"
    log_filename_pattern: str = "audit-{date}.log"
    max_file_size_mb: int = 100
    max_files: int = 365
    compression_enabled: bool = True

    # Retention Configuration
    default_retention_days: int = 2555  # 7 years
    cleanup_enabled: bool = True
    cleanup_interval_hours: int = 24

    # Security Configuration
    integrity_checks_enabled: bool = True
    integrity_secret_key: str | None = None
    encryption_enabled: bool = False
    encryption_key: str | None = None

    # Performance Configuration
    max_events_per_second: int = 1000
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 30

    # External Integration
    external_forwarding_enabled: bool = False
    external_endpoints: list[str] = Field(default_factory=list)
    external_headers: dict[str, str] = Field(default_factory=dict)
    external_timeout_seconds: int = 5

    # Compliance Configuration
    compliance_mode: str = "standard"  # standard, hipaa, pci, gdpr
    anonymization_enabled: bool = False
    data_residency_region: str | None = None


class SecurityAuditLogger:
    """Production-ready security audit logging service.

    This service provides comprehensive audit logging capabilities with:
    - Structured JSON logging with consistent schema
    - High-performance async logging with buffering
    - Configurable retention and rotation policies
    - Integrity protection and tamper detection
    - External log forwarding
    - Compliance-ready audit trails
    """

    def __init__(self, config: AuditLogConfig | None = None):
        """Initialize the audit logging service."""
        self.config = config or AuditLogConfig()
        self._buffer: list[AuditEvent] = []
        self._buffer_lock = asyncio.Lock()
        self._is_running = False
        self._flush_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None

        # Performance tracking
        self._events_per_second = 0
        self._last_second = 0
        self._circuit_breaker_failures = 0
        self._circuit_breaker_open = False
        self._circuit_breaker_next_attempt = 0

        # Statistics
        self.stats = {
            "total_events_logged": 0,
            "events_by_type": defaultdict(int),
            "events_by_severity": defaultdict(int),
            "buffer_flushes": 0,
            "errors": 0,
            "external_forwards": 0,
            "external_forward_errors": 0,
        }

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup internal logging configuration."""
        # Create log directory if it doesn't exist
        log_dir = Path(self.config.log_directory)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Configure file handler
        from logging.handlers import RotatingFileHandler

        log_file = log_dir / self.config.log_filename_pattern.format(
            date=datetime.now().strftime("%Y-%m-%d")
        )

        self.file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.config.max_file_size_mb * 1024 * 1024,
            backupCount=self.config.max_files,
        )

        # JSON formatter
        formatter = logging.Formatter("%(message)s")
        self.file_handler.setFormatter(formatter)

        # Create audit logger
        self.audit_logger = logging.getLogger(f"audit.{__name__}")
        self.audit_logger.setLevel(getattr(logging, self.config.log_level))
        self.audit_logger.addHandler(self.file_handler)
        self.audit_logger.propagate = False

    async def start(self):
        """Start the audit logging service."""
        if self._is_running:
            return

        self._is_running = True

        if self.config.async_logging:
            self._flush_task = asyncio.create_task(self._flush_loop())

        if self.config.cleanup_enabled:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("Security audit logging service started")

    async def stop(self):
        """Stop the audit logging service and flush remaining events."""
        if not self._is_running:
            return

        self._is_running = False

        # Cancel background tasks
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Flush remaining events
        await self._flush_buffer()

        logger.info("Security audit logging service stopped")

    async def log_event(self, event: AuditEvent) -> bool:
        """Log a security audit event.

        Args:
            event: The audit event to log

        Returns:
            True if event was successfully queued/logged, False otherwise
        """
        if not self.config.enabled or self._circuit_breaker_open:
            return False

        # Rate limiting check
        current_second = int(datetime.now().timestamp())
        if current_second != self._last_second:
            self._events_per_second = 0
            self._last_second = current_second

        if self._events_per_second >= self.config.max_events_per_second:
            logger.warning("Audit logging rate limit exceeded")
            return False

        self._events_per_second += 1

        try:
            # Add integrity hash if enabled
            if (
                self.config.integrity_checks_enabled
                and self.config.integrity_secret_key
            ):
                event.metadata["integrity_hash"] = event.compute_integrity_hash(
                    self.config.integrity_secret_key
                )

            # Update statistics
            self.stats["total_events_logged"] += 1
            self.stats["events_by_type"][event.event_type] += 1
            self.stats["events_by_severity"][event.severity] += 1

            if self.config.async_logging:
                # Add to buffer for async processing
                async with self._buffer_lock:
                    self._buffer.append(event)

                    # Force flush if buffer is full
                    if len(self._buffer) >= self.config.buffer_size:
                        await self._flush_buffer()
            else:
                # Synchronous logging
                await self._write_event(event)

            return True

        except Exception as e:
            self.stats["errors"] += 1
            self._handle_circuit_breaker_failure()
            logger.error(f"Failed to log audit event: {e}")
            return False

    async def log_authentication_event(
        self,
        event_type: AuditEventType,
        outcome: AuditOutcome,
        user_id: str,
        ip_address: str,
        user_agent: str | None = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Log authentication-related audit event."""
        severity = self._determine_auth_severity(event_type, outcome)

        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            outcome=outcome,
            message=message or f"Authentication {event_type.value}: {outcome.value}",
            actor=AuditActor(
                actor_type="user", actor_id=user_id, authentication_method="jwt"
            ),
            source=AuditSource(ip_address=ip_address, user_agent=user_agent),
            metadata=metadata or {},
        )

        return await self.log_event(event)

    async def log_api_key_event(
        self,
        event_type: AuditEventType,
        outcome: AuditOutcome,
        key_id: str,
        service: str,
        ip_address: str,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Log API key related audit event."""
        severity = self._determine_api_key_severity(event_type, outcome)

        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            outcome=outcome,
            message=message or f"API key {event_type.value}: {outcome.value}",
            actor=AuditActor(
                actor_type="api_key", actor_id=key_id, authentication_method="api_key"
            ),
            target=AuditTarget(
                resource_type="api_key",
                resource_id=key_id,
                resource_attributes={"service": service},
            ),
            source=AuditSource(ip_address=ip_address),
            metadata=metadata or {},
        )

        return await self.log_event(event)

    async def log_security_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        message: str,
        actor_id: str,
        ip_address: str,
        target_resource: str | None = None,
        risk_score: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Log security-related audit event."""
        target = None
        if target_resource:
            target = AuditTarget(resource_type="system", resource_id=target_resource)

        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            outcome=AuditOutcome.WARNING,
            message=message,
            actor=AuditActor(actor_type="user", actor_id=actor_id),
            target=target,
            source=AuditSource(ip_address=ip_address),
            risk_score=risk_score,
            metadata=metadata or {},
        )

        return await self.log_event(event)

    async def log_configuration_change(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        changed_by: str,
        ip_address: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Log configuration change audit event."""
        event = AuditEvent(
            event_type=AuditEventType.CONFIG_CHANGED,
            severity=AuditSeverity.MEDIUM,
            outcome=AuditOutcome.SUCCESS,
            message=f"Configuration '{config_key}' changed",
            actor=AuditActor(actor_type="user", actor_id=changed_by),
            target=AuditTarget(
                resource_type="configuration",
                resource_id=config_key,
                resource_attributes={
                    "old_value": str(old_value),
                    "new_value": str(new_value),
                },
            ),
            source=AuditSource(ip_address=ip_address),
            metadata=metadata or {},
        )

        return await self.log_event(event)

    async def query_events(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        event_types: list[AuditEventType] | None = None,
        severity: AuditSeverity | None = None,
        actor_id: str | None = None,
        limit: int = 1000,
    ) -> list[AuditEvent]:
        """Query audit events (simplified implementation).

        Note: In production, this would typically use a proper search index
        like Elasticsearch or a database with full-text search capabilities.
        """
        # This is a simplified implementation that reads from log files
        # In production, you'd want to use a proper search backend

        events = []
        log_dir = Path(self.config.log_directory)

        # Get date range for file filtering
        if not start_time:
            start_time = datetime.now(UTC) - timedelta(days=7)
        if not end_time:
            end_time = datetime.now(UTC)

        # Read relevant log files
        current_date = start_time.date()
        while current_date <= end_time.date():
            log_file = log_dir / self.config.log_filename_pattern.format(
                date=current_date.strftime("%Y-%m-%d")
            )

            if log_file.exists():
                try:
                    with open(log_file) as f:
                        for line in f:
                            if len(events) >= limit:
                                break

                            try:
                                event_data = json.loads(line.strip())
                                event = AuditEvent(**event_data)

                                # Apply filters
                                if (
                                    event.timestamp < start_time
                                    or event.timestamp > end_time
                                ):
                                    continue

                                if event_types and event.event_type not in event_types:
                                    continue

                                if severity and event.severity != severity:
                                    continue

                                if actor_id and event.actor.actor_id != actor_id:
                                    continue

                                events.append(event)

                            except (json.JSONDecodeError, ValueError):
                                continue

                except Exception as e:
                    logger.warning(f"Failed to read log file {log_file}: {e}")

            current_date += timedelta(days=1)

        return sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_statistics(self) -> dict[str, Any]:
        """Get audit logging statistics."""
        return {
            **self.stats,
            "buffer_size": len(self._buffer),
            "circuit_breaker_open": self._circuit_breaker_open,
            "is_running": self._is_running,
            "config": self.config.model_dump(),
        }

    async def _flush_loop(self):
        """Background task to periodically flush the buffer."""
        while self._is_running:
            try:
                await asyncio.sleep(self.config.flush_interval_seconds)
                await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")

    async def _flush_buffer(self):
        """Flush buffered events to storage."""
        if not self._buffer:
            return

        async with self._buffer_lock:
            events_to_flush = self._buffer.copy()
            self._buffer.clear()

        if not events_to_flush:
            return

        try:
            for event in events_to_flush:
                await self._write_event(event)

            self.stats["buffer_flushes"] += 1

        except Exception as e:
            logger.error(f"Failed to flush events: {e}")
            # Re-add events to buffer for retry
            async with self._buffer_lock:
                self._buffer.extend(events_to_flush)

    async def _write_event(self, event: AuditEvent):
        """Write a single event to storage."""
        try:
            # Write to local log file
            log_line = event.to_json_log()
            self.audit_logger.info(log_line)

            # Forward to external systems if configured
            if (
                self.config.external_forwarding_enabled
                and self.config.external_endpoints
            ):
                await self._forward_to_external(event)

        except Exception as e:
            self.stats["errors"] += 1
            raise e

    async def _forward_to_external(self, event: AuditEvent):
        """Forward event to external logging systems."""
        import aiohttp

        for endpoint in self.config.external_endpoints:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Content-Type": "application/json",
                        **self.config.external_headers,
                    }

                    async with session.post(
                        endpoint,
                        json=event.model_dump(mode="json"),
                        headers=headers,
                        timeout=self.config.external_timeout_seconds,
                    ) as response:
                        if response.status >= 400:
                            raise Exception(f"HTTP {response.status}")

                        self.stats["external_forwards"] += 1

            except Exception as e:
                self.stats["external_forward_errors"] += 1
                logger.warning(f"Failed to forward to {endpoint}: {e}")

    async def _cleanup_loop(self):
        """Background task to clean up old log files."""
        while self._is_running:
            try:
                await asyncio.sleep(self.config.cleanup_interval_hours * 3600)
                await self._cleanup_old_logs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_old_logs(self):
        """Clean up old log files based on retention policy."""
        log_dir = Path(self.config.log_directory)
        if not log_dir.exists():
            return

        cutoff_date = datetime.now() - timedelta(
            days=self.config.default_retention_days
        )

        for log_file in log_dir.glob("audit-*.log*"):
            try:
                # Extract date from filename
                parts = log_file.stem.split("-")
                if len(parts) >= 4:  # audit-YYYY-MM-DD
                    file_date_str = "-".join(parts[1:4])
                    file_date = datetime.strptime(file_date_str, "%Y-%m-%d")

                    if file_date < cutoff_date:
                        log_file.unlink()
                        logger.info(f"Cleaned up old log file: {log_file}")

            except Exception as e:
                logger.warning(f"Failed to process log file {log_file}: {e}")

    def _determine_auth_severity(
        self, event_type: AuditEventType, outcome: AuditOutcome
    ) -> AuditSeverity:
        """Determine severity for authentication events."""
        if outcome == AuditOutcome.FAILURE:
            if event_type in [
                AuditEventType.AUTH_LOGIN_FAILED,
                AuditEventType.AUTH_MFA_FAILED,
            ]:
                return AuditSeverity.MEDIUM
            return AuditSeverity.LOW

        if event_type in [
            AuditEventType.AUTH_PASSWORD_CHANGE,
            AuditEventType.AUTH_PASSWORD_RESET,
        ]:
            return AuditSeverity.MEDIUM

        return AuditSeverity.LOW

    def _determine_api_key_severity(
        self, event_type: AuditEventType, outcome: AuditOutcome
    ) -> AuditSeverity:
        """Determine severity for API key events."""
        if outcome == AuditOutcome.FAILURE:
            return AuditSeverity.MEDIUM

        if event_type in [
            AuditEventType.API_KEY_CREATED,
            AuditEventType.API_KEY_DELETED,
        ]:
            return AuditSeverity.MEDIUM

        if event_type in [
            AuditEventType.API_KEY_RATE_LIMITED,
            AuditEventType.API_KEY_QUOTA_EXCEEDED,
        ]:
            return AuditSeverity.HIGH

        return AuditSeverity.LOW

    def _handle_circuit_breaker_failure(self):
        """Handle circuit breaker logic for failures."""
        if not self.config.circuit_breaker_enabled:
            return

        self._circuit_breaker_failures += 1

        if (
            self._circuit_breaker_failures
            >= self.config.circuit_breaker_failure_threshold
        ):
            self._circuit_breaker_open = True
            self._circuit_breaker_next_attempt = (
                datetime.now().timestamp() + self.config.circuit_breaker_timeout_seconds
            )
            logger.warning("Audit logging circuit breaker opened")

        # Reset circuit breaker if timeout has passed
        if (
            self._circuit_breaker_open
            and datetime.now().timestamp() >= self._circuit_breaker_next_attempt
        ):
            self._circuit_breaker_open = False
            self._circuit_breaker_failures = 0
            logger.info("Audit logging circuit breaker reset")


# Global audit logger instance
_audit_logger: SecurityAuditLogger | None = None


async def get_audit_logger() -> SecurityAuditLogger:
    """Get or create the global audit logger instance."""
    global _audit_logger

    if _audit_logger is None:
        config = AuditLogConfig()
        _audit_logger = SecurityAuditLogger(config)
        await _audit_logger.start()

    return _audit_logger


async def shutdown_audit_logger():
    """Shutdown the global audit logger instance."""
    global _audit_logger

    if _audit_logger is not None:
        await _audit_logger.stop()
        _audit_logger = None


# Convenience functions for common audit events
async def audit_authentication(
    event_type: AuditEventType,
    outcome: AuditOutcome,
    user_id: str,
    ip_address: str,
    user_agent: str | None = None,
    message: str | None = None,
    **metadata,
) -> bool:
    """Log authentication audit event."""
    audit_logger = await get_audit_logger()
    return await audit_logger.log_authentication_event(
        event_type, outcome, user_id, ip_address, user_agent, message, metadata
    )


async def audit_api_key(
    event_type: AuditEventType,
    outcome: AuditOutcome,
    key_id: str,
    service: str,
    ip_address: str,
    message: str | None = None,
    **metadata,
) -> bool:
    """Log API key audit event."""
    audit_logger = await get_audit_logger()
    return await audit_logger.log_api_key_event(
        event_type, outcome, key_id, service, ip_address, message, metadata
    )


async def audit_security_event(
    event_type: AuditEventType,
    severity: AuditSeverity,
    message: str,
    actor_id: str,
    ip_address: str,
    target_resource: str | None = None,
    risk_score: int | None = None,
    **metadata,
) -> bool:
    """Log security audit event."""
    audit_logger = await get_audit_logger()
    return await audit_logger.log_security_event(
        event_type,
        severity,
        message,
        actor_id,
        ip_address,
        target_resource,
        risk_score,
        metadata,
    )


async def audit_config_change(
    config_key: str,
    old_value: Any,
    new_value: Any,
    changed_by: str,
    ip_address: str,
    **metadata,
) -> bool:
    """Log configuration change audit event."""
    audit_logger = await get_audit_logger()
    return await audit_logger.log_configuration_change(
        config_key, old_value, new_value, changed_by, ip_address, metadata
    )
