"""
Database Security Hardening Module for TripSage.

This module implements comprehensive security hardening for database connections
including connection validation, IP-based rate limiting, threat detection,
audit trails, and compliance checks following 2024 security best practices.
"""

import hashlib
import ipaddress
import logging
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import ValidationError

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security threat levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(Enum):
    """Types of security threats."""

    SQL_INJECTION = "sql_injection"
    BRUTE_FORCE = "brute_force"
    DDoS = "ddos"
    SUSPICIOUS_QUERY = "suspicious_query"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CONNECTION_ABUSE = "connection_abuse"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class AuditEventType(Enum):
    """Types of audit events."""

    CONNECTION_ATTEMPT = "connection_attempt"
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILURE = "authentication_failure"
    QUERY_EXECUTION = "query_execution"
    SECURITY_VIOLATION = "security_violation"
    CONFIGURATION_CHANGE = "configuration_change"
    ADMIN_ACTION = "admin_action"
    DATA_ACCESS = "data_access"
    RATE_LIMIT_HIT = "rate_limit_hit"
    THREAT_DETECTED = "threat_detected"


@dataclass
class SecurityMetrics:
    """Security metrics for monitoring."""

    total_connections: int = 0
    blocked_connections: int = 0
    threats_detected: int = 0
    rate_limit_violations: int = 0
    suspicious_queries: int = 0
    failed_authentications: int = 0
    last_threat_time: datetime | None = None
    threat_score: float = 0.0


@dataclass
class ThreatAlert:
    """Security threat alert."""

    threat_type: ThreatType
    severity: SecurityLevel
    source_ip: str
    timestamp: datetime
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)
    blocked: bool = False
    acknowledged: bool = False


@dataclass
class AuditEvent:
    """Security audit event."""

    event_type: AuditEventType
    timestamp: datetime
    user_id: str | None
    source_ip: str
    query_hash: str | None
    table_accessed: str | None
    success: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class ConnectionSecurityValidator(BaseModel):
    """Enhanced connection security validation with Pydantic."""

    model_config = {"str_strip_whitespace": True, "validate_assignment": True}

    database_url: str = Field(..., description="Database URL to validate")
    api_key: str = Field(..., min_length=20, description="API key for authentication")
    source_ip: str = Field(..., description="Source IP address")
    user_agent: str | None = Field(None, description="User agent string")
    connection_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format and security."""
        if not v or not v.startswith("https://"):
            raise ValueError("Database URL must be a valid HTTPS URL")

        parsed = urlparse(v)
        if not parsed.hostname:
            raise ValueError("Database URL must have a valid hostname")

        # Check for known malicious patterns
        suspicious_patterns = [
            r"localhost",
            r"127\.0\.0\.1",
            r"0\.0\.0\.0",
            r"file://",
            r"javascript:",
            r"data:",
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Database URL contains suspicious pattern: {pattern}")

        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format and strength."""
        if not v or len(v) < 20:
            raise ValueError("API key must be at least 20 characters long")

        # Check for common weak patterns
        weak_patterns = [
            r"^test",
            r"^demo",
            r"^sample",
            r"^default",
            r"12345",
            r"abcde",
        ]

        for pattern in weak_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"API key contains weak pattern: {pattern}")

        return v

    @field_validator("source_ip")
    @classmethod
    def validate_source_ip(cls, v: str) -> str:
        """Validate and normalize IP address."""
        try:
            ip = ipaddress.ip_address(v)

            # Block known malicious ranges
            if ip.is_private and str(ip) not in ["127.0.0.1", "::1"]:
                logger.warning(f"Connection from private IP: {v}")

            if ip.is_multicast or ip.is_unspecified:
                raise ValueError(f"Invalid IP address type: {v}")

            return str(ip)
        except ValueError as e:
            raise ValueError(f"Invalid IP address format: {v}") from e

    @model_validator(mode="after")
    def validate_connection_security(self) -> "ConnectionSecurityValidator":
        """Perform comprehensive connection security validation."""
        # Check for correlation between IP and API key
        if self.source_ip and self.api_key:
            ip_hash = hashlib.sha256(self.source_ip.encode()).hexdigest()[:8]
            if ip_hash in self.api_key.lower():
                raise ValueError("API key appears to be correlated with IP address")

        return self


class IPBasedRateLimiter:
    """Advanced IP-based rate limiting with geographic and behavioral analysis."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_limit: int = 100,
        geographic_variance_threshold: float = 0.8,
        behavioral_window_minutes: int = 15,
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.geographic_variance_threshold = geographic_variance_threshold
        self.behavioral_window_minutes = behavioral_window_minutes

        # Rate limiting data structures
        self.ip_requests: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.ip_locations: dict[str, set[str]] = defaultdict(set)
        self.ip_patterns: dict[str, list[datetime]] = defaultdict(list)
        self.blocked_ips: dict[str, datetime] = {}

        # Behavioral analysis
        self.request_patterns: dict[str, dict[str, Any]] = defaultdict(dict)

    async def check_rate_limit(
        self,
        ip_address: str,
        user_region: str | None = None,
        request_metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, ThreatAlert | None]:
        """Check if request should be rate limited."""
        now = datetime.now(timezone.utc)

        # Check if IP is currently blocked
        if ip_address in self.blocked_ips:
            block_time = self.blocked_ips[ip_address]
            if (now - block_time).total_seconds() < 3600:  # 1 hour block
                return False, ThreatAlert(
                    threat_type=ThreatType.RATE_LIMIT_EXCEEDED,
                    severity=SecurityLevel.HIGH,
                    source_ip=ip_address,
                    timestamp=now,
                    message=f"IP {ip_address} is currently blocked",
                    blocked=True,
                )
            else:
                # Unblock after timeout
                del self.blocked_ips[ip_address]

        # Get recent requests for this IP
        recent_requests = self.ip_requests[ip_address]

        # Clean old requests (older than 1 minute)
        cutoff_time = now.timestamp() - 60
        while recent_requests and recent_requests[0] < cutoff_time:
            recent_requests.popleft()

        # Check rate limits
        current_requests = len(recent_requests)

        # Burst limit check
        if current_requests >= self.burst_limit:
            self.blocked_ips[ip_address] = now
            return False, ThreatAlert(
                threat_type=ThreatType.DDoS,
                severity=SecurityLevel.CRITICAL,
                source_ip=ip_address,
                timestamp=now,
                message=f"Burst limit exceeded: {current_requests}/{self.burst_limit}",
                blocked=True,
            )

        # Rate limit check
        if current_requests >= self.requests_per_minute:
            return False, ThreatAlert(
                threat_type=ThreatType.RATE_LIMIT_EXCEEDED,
                severity=SecurityLevel.MEDIUM,
                source_ip=ip_address,
                timestamp=now,
                message=(
                    f"Rate limit exceeded: "
                    f"{current_requests}/{self.requests_per_minute}"
                ),
                metadata={"requests_per_minute": current_requests},
            )

        # Geographic anomaly detection
        if user_region:
            self.ip_locations[ip_address].add(user_region)
            location_variance = len(self.ip_locations[ip_address])

            if location_variance > 3:  # Suspicious if from more than 3 regions
                return False, ThreatAlert(
                    threat_type=ThreatType.GEOGRAPHIC_ANOMALY,
                    severity=SecurityLevel.HIGH,
                    source_ip=ip_address,
                    timestamp=now,
                    message=f"Geographic anomaly: {location_variance} regions",
                    metadata={"regions": list(self.ip_locations[ip_address])},
                )

        # Behavioral pattern analysis
        alert = await self._analyze_behavioral_patterns(
            ip_address, now, request_metadata
        )
        if alert:
            return False, alert

        # Record the request
        recent_requests.append(now.timestamp())
        self.ip_patterns[ip_address].append(now)

        return True, None

    async def _analyze_behavioral_patterns(
        self,
        ip_address: str,
        now: datetime,
        request_metadata: dict[str, Any] | None,
    ) -> ThreatAlert | None:
        """Analyze behavioral patterns for anomalies."""
        pattern_data = self.request_patterns[ip_address]

        # Initialize pattern tracking
        if "first_seen" not in pattern_data:
            pattern_data["first_seen"] = now
            pattern_data["request_intervals"] = []
            pattern_data["user_agents"] = set()
            pattern_data["query_types"] = defaultdict(int)
            return None

        # Track request intervals
        if pattern_data.get("last_request"):
            interval = (now - pattern_data["last_request"]).total_seconds()
            pattern_data["request_intervals"].append(interval)

            # Keep only recent intervals
            if len(pattern_data["request_intervals"]) > 100:
                pattern_data["request_intervals"] = pattern_data["request_intervals"][
                    -50:
                ]

            # Check for bot-like behavior (very regular intervals)
            if len(pattern_data["request_intervals"]) >= 10:
                intervals = pattern_data["request_intervals"][-10:]
                avg_interval = sum(intervals) / len(intervals)
                variance = sum((x - avg_interval) ** 2 for x in intervals) / len(
                    intervals
                )

                if variance < 0.1 and avg_interval < 2.0:  # Very regular, fast requests
                    return ThreatAlert(
                        threat_type=ThreatType.ANOMALOUS_BEHAVIOR,
                        severity=SecurityLevel.HIGH,
                        source_ip=ip_address,
                        timestamp=now,
                        message="Bot-like behavior detected: regular intervals",
                        metadata={
                            "avg_interval": avg_interval,
                            "variance": variance,
                        },
                    )

        pattern_data["last_request"] = now

        # Track user agents
        if request_metadata and "user_agent" in request_metadata:
            user_agent = request_metadata["user_agent"]
            pattern_data["user_agents"].add(user_agent)

            # Suspicious if too many different user agents
            if len(pattern_data["user_agents"]) > 5:
                return ThreatAlert(
                    threat_type=ThreatType.ANOMALOUS_BEHAVIOR,
                    severity=SecurityLevel.MEDIUM,
                    source_ip=ip_address,
                    timestamp=now,
                    message=f"Multiple user agents: {len(pattern_data['user_agents'])}",
                    metadata={"user_agents": list(pattern_data["user_agents"])},
                )

        return None

    def get_ip_statistics(self, ip_address: str) -> dict[str, Any]:
        """Get statistics for an IP address."""
        pattern_data = self.request_patterns.get(ip_address, {})
        recent_requests = len(self.ip_requests.get(ip_address, []))

        return {
            "recent_requests": recent_requests,
            "first_seen": pattern_data.get("first_seen"),
            "last_request": pattern_data.get("last_request"),
            "regions": list(self.ip_locations.get(ip_address, set())),
            "user_agents_count": len(pattern_data.get("user_agents", set())),
            "blocked": ip_address in self.blocked_ips,
        }


class SQLInjectionDetector:
    """Advanced SQL injection pattern detection."""

    def __init__(self):
        # Common SQL injection patterns
        self.sql_patterns = [
            # Union-based injection
            r"union\s+select",
            r"union\s+all\s+select",
            # Boolean-based injection
            r"'\s*or\s*'1'\s*=\s*'1",
            r"'\s*or\s*1\s*=\s*1",
            r"'\s*and\s*'1'\s*=\s*'1",
            # Time-based injection
            r"waitfor\s+delay",
            r"pg_sleep\s*\(",
            r"sleep\s*\(",
            # Error-based injection
            r"extractvalue\s*\(",
            r"updatexml\s*\(",
            r"convert\s*\(",
            # Stacked queries
            r";\s*drop\s+table",
            r";\s*delete\s+from",
            r";\s*insert\s+into",
            r";\s*update\s+",
            # Comment injection
            r"--\s*",
            r"/\*.*\*/",
            r"#.*",
            # Special functions
            r"load_file\s*\(",
            r"into\s+outfile",
            r"into\s+dumpfile",
            # PostgreSQL specific
            r"pg_read_file\s*\(",
            r"copy\s+.*\s+from\s+program",
        ]

        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.sql_patterns
        ]

    def detect_sql_injection(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> ThreatAlert | None:
        """Detect SQL injection attempts in queries."""
        if not query:
            return None

        # Normalize query for analysis
        normalized_query = query.lower().strip()

        # Check for SQL injection patterns
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(normalized_query):
                return ThreatAlert(
                    threat_type=ThreatType.SQL_INJECTION,
                    severity=SecurityLevel.CRITICAL,
                    source_ip="unknown",  # Will be set by caller
                    timestamp=datetime.now(timezone.utc),
                    message=f"SQL injection pattern detected: {self.sql_patterns[i]}",
                    metadata={
                        "query_hash": hashlib.sha256(query.encode()).hexdigest()[:16],
                        "pattern_matched": self.sql_patterns[i],
                        "query_length": len(query),
                    },
                    blocked=True,
                )

        # Check parameters for injection
        if parameters:
            for key, value in parameters.items():
                if isinstance(value, str):
                    for i, pattern in enumerate(self.compiled_patterns):
                        if pattern.search(value.lower()):
                            return ThreatAlert(
                                threat_type=ThreatType.SQL_INJECTION,
                                severity=SecurityLevel.CRITICAL,
                                source_ip="unknown",
                                timestamp=datetime.now(timezone.utc),
                                message=(
                                    f"SQL injection in parameter '{key}': "
                                    f"{self.sql_patterns[i]}"
                                ),
                                metadata={
                                    "parameter": key,
                                    "pattern_matched": self.sql_patterns[i],
                                    "value_hash": hashlib.sha256(
                                        str(value).encode()
                                    ).hexdigest()[:16],
                                },
                                blocked=True,
                            )

        return None


class DatabaseAuditLogger:
    """Comprehensive database audit logging."""

    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.audit_events: deque = deque(maxlen=max_events)
        self.event_index: dict[str, list[AuditEvent]] = defaultdict(list)

    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: str | None,
        source_ip: str,
        success: bool,
        query: str | None = None,
        table_accessed: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a security audit event."""
        event = AuditEvent(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            source_ip=source_ip,
            query_hash=hashlib.sha256(query.encode()).hexdigest()[:16]
            if query
            else None,
            table_accessed=table_accessed,
            success=success,
            metadata=metadata or {},
        )

        self.audit_events.append(event)
        self.event_index[source_ip].append(event)

        # Keep index size manageable
        if len(self.event_index[source_ip]) > 1000:
            self.event_index[source_ip] = self.event_index[source_ip][-500:]

        # Log critical events immediately
        if event_type in [
            AuditEventType.SECURITY_VIOLATION,
            AuditEventType.THREAT_DETECTED,
        ]:
            logger.warning(
                f"SECURITY AUDIT: {event_type.value} from {source_ip} "
                f"(user: {user_id}, success: {success})"
            )

    def get_events_by_ip(self, source_ip: str, limit: int = 100) -> list[AuditEvent]:
        """Get audit events for a specific IP address."""
        events = self.event_index.get(source_ip, [])
        return events[-limit:] if events else []

    def get_recent_events(self, limit: int = 100) -> list[AuditEvent]:
        """Get recent audit events."""
        return list(self.audit_events)[-limit:]

    def get_security_summary(self, hours: int = 24) -> dict[str, Any]:
        """Get security summary for the specified time period."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        recent_events = [
            event
            for event in self.audit_events
            if event.timestamp.timestamp() > cutoff_time
        ]

        summary = {
            "total_events": len(recent_events),
            "failed_attempts": sum(1 for e in recent_events if not e.success),
            "unique_ips": len(set(e.source_ip for e in recent_events)),
            "event_types": defaultdict(int),
            "top_ips": defaultdict(int),
        }

        for event in recent_events:
            summary["event_types"][event.event_type.value] += 1
            summary["top_ips"][event.source_ip] += 1

        # Convert to sorted lists
        summary["top_ips"] = dict(
            sorted(summary["top_ips"].items(), key=lambda x: x[1], reverse=True)[:10]
        )

        return summary


class SecurityConfigurationValidator:
    """Validate security configuration and compliance."""

    def __init__(self):
        self.compliance_checks = [
            self._check_ssl_configuration,
            self._check_authentication_strength,
            self._check_connection_limits,
            self._check_logging_configuration,
            self._check_encryption_settings,
        ]

    async def validate_configuration(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate security configuration against best practices."""
        results = {
            "compliant": True,
            "score": 0,
            "max_score": len(self.compliance_checks) * 10,
            "checks": [],
            "recommendations": [],
        }

        for check in self.compliance_checks:
            try:
                check_result = await check(config)
                results["checks"].append(check_result)
                results["score"] += check_result["score"]

                if not check_result["passed"]:
                    results["compliant"] = False
                    results["recommendations"].extend(
                        check_result.get("recommendations", [])
                    )

            except Exception as e:
                logger.error(f"Configuration check failed: {e}")
                results["checks"].append(
                    {
                        "name": check.__name__,
                        "passed": False,
                        "score": 0,
                        "error": str(e),
                    }
                )

        results["compliance_percentage"] = (
            results["score"] / results["max_score"]
        ) * 100

        return results

    async def _check_ssl_configuration(self, config: dict[str, Any]) -> dict[str, Any]:
        """Check SSL/TLS configuration."""
        score = 0
        recommendations = []

        database_url = config.get("database_url", "")
        if database_url.startswith("https://"):
            score += 5
        else:
            recommendations.append("Use HTTPS for database connections")

        # Check for SSL enforcement
        if config.get("ssl_required", False):
            score += 3
        else:
            recommendations.append("Enable SSL requirement for all connections")

        # Check SSL version
        ssl_version = config.get("ssl_version", "")
        if ssl_version in ["TLSv1.2", "TLSv1.3"]:
            score += 2
        else:
            recommendations.append("Use TLS 1.2 or higher")

        return {
            "name": "SSL Configuration",
            "passed": score >= 8,
            "score": score,
            "recommendations": recommendations,
        }

    async def _check_authentication_strength(
        self, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Check authentication configuration."""
        score = 0
        recommendations = []

        # Check API key strength
        api_key = config.get("database_public_key", "")
        if len(api_key) >= 32:
            score += 3
        else:
            recommendations.append("Use API keys with at least 32 characters")

        # Check for key rotation
        if config.get("key_rotation_enabled", False):
            score += 2
        else:
            recommendations.append("Enable automatic key rotation")

        # Check for multi-factor authentication
        if config.get("mfa_enabled", False):
            score += 3
        else:
            recommendations.append("Enable multi-factor authentication")

        # Check session timeout
        session_timeout = config.get("session_timeout", 0)
        if 300 <= session_timeout <= 3600:  # 5 minutes to 1 hour
            score += 2
        else:
            recommendations.append("Set session timeout between 5 minutes and 1 hour")

        return {
            "name": "Authentication Strength",
            "passed": score >= 7,
            "score": score,
            "recommendations": recommendations,
        }

    async def _check_connection_limits(self, config: dict[str, Any]) -> dict[str, Any]:
        """Check connection limit configuration."""
        score = 0
        recommendations = []

        max_connections = config.get("max_connections", 0)
        if 10 <= max_connections <= 100:
            score += 3
        else:
            recommendations.append("Set max_connections between 10 and 100")

        rate_limit = config.get("rate_limit_requests", 0)
        if 10 <= rate_limit <= 1000:
            score += 3
        else:
            recommendations.append("Set rate_limit_requests between 10 and 1000")

        connection_timeout = config.get("connection_timeout", 0)
        if 5 <= connection_timeout <= 60:
            score += 2
        else:
            recommendations.append("Set connection_timeout between 5 and 60 seconds")

        idle_timeout = config.get("idle_timeout", 0)
        if 60 <= idle_timeout <= 300:
            score += 2
        else:
            recommendations.append("Set idle_timeout between 60 and 300 seconds")

        return {
            "name": "Connection Limits",
            "passed": score >= 8,
            "score": score,
            "recommendations": recommendations,
        }

    async def _check_logging_configuration(
        self, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Check logging configuration."""
        score = 0
        recommendations = []

        if config.get("enable_security_monitoring", False):
            score += 3
        else:
            recommendations.append("Enable security monitoring")

        if config.get("log_failed_connections", False):
            score += 2
        else:
            recommendations.append("Enable logging of failed connections")

        if config.get("log_query_details", False):
            score += 2
        else:
            recommendations.append("Enable query logging")

        log_retention = config.get("log_retention_days", 0)
        if 30 <= log_retention <= 365:
            score += 2
        else:
            recommendations.append("Set log retention between 30 and 365 days")

        if config.get("audit_trail_enabled", False):
            score += 1
        else:
            recommendations.append("Enable audit trail")

        return {
            "name": "Logging Configuration",
            "passed": score >= 8,
            "score": score,
            "recommendations": recommendations,
        }

    async def _check_encryption_settings(
        self, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Check encryption configuration."""
        score = 0
        recommendations = []

        if config.get("encrypt_data_at_rest", False):
            score += 3
        else:
            recommendations.append("Enable data-at-rest encryption")

        if config.get("encrypt_data_in_transit", False):
            score += 3
        else:
            recommendations.append("Enable data-in-transit encryption")

        encryption_algo = config.get("encryption_algorithm", "")
        if encryption_algo in ["AES-256", "ChaCha20-Poly1305"]:
            score += 2
        else:
            recommendations.append("Use AES-256 or ChaCha20-Poly1305 encryption")

        if config.get("key_management_hsm", False):
            score += 2
        else:
            recommendations.append("Use HSM for key management")

        return {
            "name": "Encryption Settings",
            "passed": score >= 8,
            "score": score,
            "recommendations": recommendations,
        }


class DatabaseSecurityManager:
    """Main security hardening manager coordinating all security components."""

    def __init__(
        self,
        enable_rate_limiting: bool = True,
        enable_sql_injection_detection: bool = True,
        enable_audit_logging: bool = True,
        enable_threat_detection: bool = True,
        rate_limit_requests: int = 60,
        rate_limit_burst: int = 100,
    ):
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_sql_injection_detection = enable_sql_injection_detection
        self.enable_audit_logging = enable_audit_logging
        self.enable_threat_detection = enable_threat_detection

        # Initialize security components
        if enable_rate_limiting:
            self.rate_limiter = IPBasedRateLimiter(
                requests_per_minute=rate_limit_requests,
                burst_limit=rate_limit_burst,
            )

        if enable_sql_injection_detection:
            self.sql_detector = SQLInjectionDetector()

        if enable_audit_logging:
            self.audit_logger = DatabaseAuditLogger()

        self.config_validator = SecurityConfigurationValidator()

        # Security metrics
        self.security_metrics = SecurityMetrics()
        self.threat_alerts: deque = deque(maxlen=1000)

    async def validate_connection(
        self,
        database_url: str,
        api_key: str,
        source_ip: str,
        user_agent: str | None = None,
        user_region: str | None = None,
        connection_metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, ThreatAlert | None]:
        """Comprehensive connection validation with security checks."""
        try:
            # Validate connection parameters
            ConnectionSecurityValidator(
                database_url=database_url,
                api_key=api_key,
                source_ip=source_ip,
                user_agent=user_agent,
                connection_metadata=connection_metadata or {},
            )

            self.security_metrics.total_connections += 1

            # Check rate limiting
            if self.enable_rate_limiting:
                allowed, alert = await self.rate_limiter.check_rate_limit(
                    source_ip, user_region, {"user_agent": user_agent}
                )
                if not allowed:
                    self.security_metrics.blocked_connections += 1
                    if alert:
                        alert.source_ip = source_ip
                        await self._handle_threat_alert(alert)
                    return False, alert

            # Log successful connection attempt
            if self.enable_audit_logging:
                await self.audit_logger.log_event(
                    AuditEventType.CONNECTION_ATTEMPT,
                    None,  # user_id not available at connection time
                    source_ip,
                    True,
                    metadata={
                        "user_agent": user_agent,
                        "user_region": user_region,
                    },
                )

            return True, None

        except ValidationError as e:
            # Log validation failure
            if self.enable_audit_logging:
                await self.audit_logger.log_event(
                    AuditEventType.SECURITY_VIOLATION,
                    None,
                    source_ip,
                    False,
                    metadata={"validation_errors": str(e)},
                )

            alert = ThreatAlert(
                threat_type=ThreatType.SUSPICIOUS_QUERY,
                severity=SecurityLevel.MEDIUM,
                source_ip=source_ip,
                timestamp=datetime.now(timezone.utc),
                message=f"Connection validation failed: {str(e)}",
                metadata={"validation_errors": str(e)},
            )

            await self._handle_threat_alert(alert)
            return False, alert

    async def validate_query(
        self,
        query: str,
        parameters: dict[str, Any] | None,
        user_id: str | None,
        source_ip: str,
        table_accessed: str | None = None,
    ) -> tuple[bool, ThreatAlert | None]:
        """Validate database query for security threats."""
        try:
            # SQL injection detection
            if self.enable_sql_injection_detection:
                threat = self.sql_detector.detect_sql_injection(query, parameters)
                if threat:
                    threat.source_ip = source_ip
                    self.security_metrics.suspicious_queries += 1

                    # Log security violation
                    if self.enable_audit_logging:
                        await self.audit_logger.log_event(
                            AuditEventType.SECURITY_VIOLATION,
                            user_id,
                            source_ip,
                            False,
                            query,
                            table_accessed,
                            metadata={"threat_type": threat.threat_type.value},
                        )

                    await self._handle_threat_alert(threat)
                    return False, threat

            # Log successful query execution
            if self.enable_audit_logging:
                await self.audit_logger.log_event(
                    AuditEventType.QUERY_EXECUTION,
                    user_id,
                    source_ip,
                    True,
                    query,
                    table_accessed,
                )

            return True, None

        except Exception as e:
            logger.error(f"Query validation error: {e}")
            return True, None  # Don't block on validation errors

    async def _handle_threat_alert(self, alert: ThreatAlert) -> None:
        """Handle security threat alerts."""
        self.threat_alerts.append(alert)
        self.security_metrics.threats_detected += 1
        self.security_metrics.last_threat_time = alert.timestamp

        # Update threat score based on severity
        severity_scores = {
            SecurityLevel.LOW: 1,
            SecurityLevel.MEDIUM: 3,
            SecurityLevel.HIGH: 7,
            SecurityLevel.CRITICAL: 10,
        }
        self.security_metrics.threat_score += severity_scores.get(alert.severity, 1)

        # Log threat detection
        if self.enable_audit_logging:
            await self.audit_logger.log_event(
                AuditEventType.THREAT_DETECTED,
                None,
                alert.source_ip,
                False,
                metadata={
                    "threat_type": alert.threat_type.value,
                    "severity": alert.severity.value,
                    "message": alert.message,
                },
            )

        # Log critical threats immediately
        if alert.severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            logger.warning(
                f"SECURITY THREAT: {alert.threat_type.value} from {alert.source_ip} "
                f"(severity: {alert.severity.value}) - {alert.message}"
            )

    async def get_security_status(self) -> dict[str, Any]:
        """Get comprehensive security status."""
        status = {
            "metrics": {
                "total_connections": self.security_metrics.total_connections,
                "blocked_connections": self.security_metrics.blocked_connections,
                "threats_detected": self.security_metrics.threats_detected,
                "suspicious_queries": self.security_metrics.suspicious_queries,
                "threat_score": self.security_metrics.threat_score,
                "last_threat_time": self.security_metrics.last_threat_time.isoformat()
                if self.security_metrics.last_threat_time
                else None,
            },
            "components": {
                "rate_limiting": self.enable_rate_limiting,
                "sql_injection_detection": self.enable_sql_injection_detection,
                "audit_logging": self.enable_audit_logging,
                "threat_detection": self.enable_threat_detection,
            },
            "recent_threats": [
                {
                    "type": alert.threat_type.value,
                    "severity": alert.severity.value,
                    "source_ip": alert.source_ip,
                    "timestamp": alert.timestamp.isoformat(),
                    "message": alert.message,
                    "blocked": alert.blocked,
                }
                for alert in list(self.threat_alerts)[-10:]
            ],
        }

        # Add audit summary if enabled
        if self.enable_audit_logging:
            status["audit_summary"] = self.audit_logger.get_security_summary()

        return status

    async def validate_security_configuration(
        self, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate security configuration compliance."""
        return await self.config_validator.validate_configuration(config)

    def get_threat_alerts(self, limit: int = 50) -> list[ThreatAlert]:
        """Get recent threat alerts."""
        return list(self.threat_alerts)[-limit:]

    def acknowledge_threat(self, alert_timestamp: datetime) -> bool:
        """Acknowledge a threat alert."""
        for alert in self.threat_alerts:
            if alert.timestamp == alert_timestamp:
                alert.acknowledged = True
                return True
        return False
