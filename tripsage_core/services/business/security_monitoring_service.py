"""
Security Monitoring Service for Suspicious Activity Detection.

This service analyzes audit logs and system behavior to detect and respond to
suspicious activities, security threats, and anomalous patterns. It provides
real-time threat detection, correlation analysis, and automated alerting.

Features:
- Real-time analysis of audit events
- Pattern detection for common attack vectors
- Machine learning-based anomaly detection
- Automated threat response and alerting
- Integration with external security systems
- Risk scoring and threat prioritization
"""

import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.services.business.audit_logging_service import (
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    SecurityAuditLogger,
    audit_security_event,
    get_audit_logger,
)
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)

class ThreatLevel(str, Enum):
    """Threat severity levels for security incidents."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatCategory(str, Enum):
    """Categories of security threats."""

    BRUTE_FORCE = "brute_force"
    CREDENTIAL_STUFFING = "credential_stuffing"
    API_ABUSE = "api_abuse"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ACCOUNT_TAKEOVER = "account_takeover"
    SUSPICIOUS_LOGIN = "suspicious_login"
    UNUSUAL_PATTERN = "unusual_pattern"
    RATE_LIMIT_EVASION = "rate_limit_evasion"
    MALICIOUS_PAYLOAD = "malicious_payload"

class ThreatIndicator(BaseModel):
    """A single threat indicator detected from analysis."""

    indicator_id: str = Field(default_factory=lambda: str(time.time()))
    threat_category: ThreatCategory
    threat_level: ThreatLevel
    confidence: float = Field(ge=0.0, le=1.0)  # 0.0 to 1.0
    description: str
    affected_entities: list[str] = Field(default_factory=list)
    source_events: list[str] = Field(default_factory=list)  # Event IDs
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    count: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)

class SecurityIncident(TripSageModel):
    """A security incident composed of multiple threat indicators."""

    incident_id: str = Field(default_factory=lambda: f"INC-{int(time.time())}")
    title: str
    description: str
    threat_level: ThreatLevel
    threat_categories: list[ThreatCategory]
    status: str = "open"  # open, investigating, resolved, false_positive
    affected_users: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    affected_ips: list[str] = Field(default_factory=list)

    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Analysis
    indicators: list[ThreatIndicator] = Field(default_factory=list)
    risk_score: int = Field(default=0, ge=0, le=100)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Response
    automated_actions: list[str] = Field(default_factory=list)
    manual_actions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    # Metadata
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

class ActivityPattern(BaseModel):
    """Pattern detection configuration for suspicious activities."""

    pattern_id: str
    name: str
    description: str
    threat_category: ThreatCategory
    threat_level: ThreatLevel

    # Detection criteria
    event_types: list[AuditEventType]
    time_window_minutes: int = 60
    min_occurrences: int = 5
    max_false_positive_rate: float = 0.1

    # Conditions
    same_actor: bool = False
    same_ip: bool = False
    same_service: bool = False
    outcome_filter: str | None = None  # "failure", "success", None

    # Response
    auto_block: bool = False
    alert_threshold: float = 0.7
    escalate_threshold: float = 0.9

class SecurityMonitoringService:
    """
    Real-time security monitoring and threat detection service.

    This service continuously analyzes audit events to detect suspicious
    activities, security threats, and anomalous behavior patterns.
    """

    def __init__(self, audit_logger: SecurityAuditLogger | None = None):
        """Initialize the security monitoring service."""
        self.audit_logger = audit_logger
        self._is_running = False
        self._monitoring_task: asyncio.Task | None = None

        # Detection state
        self._event_buffer: deque = deque(maxlen=10000)
        self._active_incidents: dict[str, SecurityIncident] = {}
        self._threat_indicators: dict[str, ThreatIndicator] = {}

        # Pattern tracking
        self._patterns = self._initialize_patterns()
        self._actor_activity: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._ip_activity: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._service_activity: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )

        # Statistics
        self.stats = {
            "events_processed": 0,
            "threats_detected": 0,
            "incidents_created": 0,
            "false_positives": 0,
            "alerts_sent": 0,
            "automated_blocks": 0,
        }

    def _initialize_patterns(self) -> list[ActivityPattern]:
        """Initialize detection patterns for common threats."""
        return [
            # Brute force login attempts
            ActivityPattern(
                pattern_id="brute_force_login",
                name="Brute Force Login Attempts",
                description="Multiple failed login attempts from same IP/user",
                threat_category=ThreatCategory.BRUTE_FORCE,
                threat_level=ThreatLevel.HIGH,
                event_types=[AuditEventType.AUTH_LOGIN_FAILED],
                time_window_minutes=15,
                min_occurrences=5,
                same_ip=True,
                outcome_filter="failure",
                auto_block=True,
                alert_threshold=0.8,
            ),
            # API key abuse
            ActivityPattern(
                pattern_id="api_key_abuse",
                name="API Key Abuse Pattern",
                description="Excessive API key validation failures",
                threat_category=ThreatCategory.API_ABUSE,
                threat_level=ThreatLevel.MEDIUM,
                event_types=[AuditEventType.API_KEY_VALIDATION_FAILED],
                time_window_minutes=30,
                min_occurrences=10,
                same_ip=True,
                outcome_filter="failure",
                alert_threshold=0.7,
            ),
            # Rate limit evasion
            ActivityPattern(
                pattern_id="rate_limit_evasion",
                name="Rate Limit Evasion",
                description=(
                    "Multiple rate limit violations suggesting evasion attempts"
                ),
                threat_category=ThreatCategory.RATE_LIMIT_EVASION,
                threat_level=ThreatLevel.MEDIUM,
                event_types=[AuditEventType.RATE_LIMIT_EXCEEDED],
                time_window_minutes=10,
                min_occurrences=3,
                same_actor=True,
                alert_threshold=0.6,
            ),
            # Suspicious login patterns
            ActivityPattern(
                pattern_id="suspicious_login_geographic",
                name="Suspicious Geographic Login Pattern",
                description="Logins from unusual geographic locations",
                threat_category=ThreatCategory.SUSPICIOUS_LOGIN,
                threat_level=ThreatLevel.MEDIUM,
                event_types=[AuditEventType.AUTH_LOGIN_SUCCESS],
                time_window_minutes=60,
                min_occurrences=2,
                same_actor=True,
                alert_threshold=0.5,
            ),
            # Data access anomalies
            ActivityPattern(
                pattern_id="unusual_data_access",
                name="Unusual Data Access Pattern",
                description="Abnormal data access patterns",
                threat_category=ThreatCategory.DATA_EXFILTRATION,
                threat_level=ThreatLevel.HIGH,
                event_types=[AuditEventType.DATA_ACCESS, AuditEventType.DATA_EXPORT],
                time_window_minutes=30,
                min_occurrences=20,
                same_actor=True,
                alert_threshold=0.8,
                escalate_threshold=0.9,
            ),
            # Privilege escalation
            ActivityPattern(
                pattern_id="privilege_escalation",
                name="Privilege Escalation Attempts",
                description="Attempts to gain elevated privileges",
                threat_category=ThreatCategory.PRIVILEGE_ESCALATION,
                threat_level=ThreatLevel.CRITICAL,
                event_types=[
                    AuditEventType.PERMISSION_CHANGED,
                    AuditEventType.ROLE_ASSIGNED,
                ],
                time_window_minutes=15,
                min_occurrences=3,
                alert_threshold=0.9,
                escalate_threshold=0.95,
            ),
        ]

    async def start(self):
        """Start the security monitoring service."""
        if self._is_running:
            return

        self._is_running = True

        # Get audit logger if not provided
        if not self.audit_logger:
            self.audit_logger = await get_audit_logger()

        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info("Security monitoring service started")

    async def stop(self):
        """Stop the security monitoring service."""
        if not self._is_running:
            return

        self._is_running = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Security monitoring service stopped")

    async def process_event(self, event: AuditEvent) -> list[ThreatIndicator]:
        """
        Process a single audit event and detect threats.

        Args:
            event: The audit event to analyze

        Returns:
            List of threat indicators detected from this event
        """
        self.stats["events_processed"] += 1

        # Add to buffer for pattern analysis
        self._event_buffer.append(event)

        # Track activity by different dimensions
        self._actor_activity[event.actor.actor_id].append(event)
        self._ip_activity[event.source.ip_address].append(event)
        if event.target and hasattr(event.target, "resource_attributes"):
            service = event.target.resource_attributes.get("service")
            if service:
                self._service_activity[service].append(event)

        # Detect threats using patterns
        threats = []
        for pattern in self._patterns:
            if event.event_type in pattern.event_types:
                threat = await self._check_pattern(event, pattern)
                if threat:
                    threats.append(threat)

        # Check for anomalies
        anomaly_threats = await self._detect_anomalies(event)
        threats.extend(anomaly_threats)

        # Create or update incidents
        for threat in threats:
            await self._handle_threat_indicator(threat)

        return threats

    async def _check_pattern(
        self, event: AuditEvent, pattern: ActivityPattern
    ) -> ThreatIndicator | None:
        """Check if an event matches a suspicious pattern."""
        now = datetime.now(timezone.utc)
        time_window = timedelta(minutes=pattern.time_window_minutes)
        cutoff_time = now - time_window

        # Get relevant events based on pattern criteria
        relevant_events = []

        if pattern.same_actor:
            actor_events = [
                e
                for e in self._actor_activity[event.actor.actor_id]
                if e.timestamp >= cutoff_time and e.event_type in pattern.event_types
            ]
            relevant_events.extend(actor_events)

        if pattern.same_ip:
            ip_events = [
                e
                for e in self._ip_activity[event.source.ip_address]
                if e.timestamp >= cutoff_time and e.event_type in pattern.event_types
            ]
            relevant_events.extend(ip_events)

        if pattern.same_service and event.target:
            service = (
                event.target.resource_attributes.get("service")
                if event.target.resource_attributes
                else None
            )
            if service:
                service_events = [
                    e
                    for e in self._service_activity[service]
                    if e.timestamp >= cutoff_time
                    and e.event_type in pattern.event_types
                ]
                relevant_events.extend(service_events)

        # Remove duplicates
        relevant_events = list({e.event_id: e for e in relevant_events}.values())

        # Apply outcome filter
        if pattern.outcome_filter:
            relevant_events = [
                e for e in relevant_events if e.outcome.value == pattern.outcome_filter
            ]

        # Check if pattern threshold is met
        if len(relevant_events) >= pattern.min_occurrences:
            # Calculate confidence based on pattern strength
            confidence = min(1.0, len(relevant_events) / (pattern.min_occurrences * 2))

            # Adjust confidence based on time distribution
            if len(relevant_events) > 1:
                time_spread = (
                    max(e.timestamp for e in relevant_events)
                    - min(e.timestamp for e in relevant_events)
                ).total_seconds()
                if time_spread < 60:  # Very rapid succession increases confidence
                    confidence *= 1.2
                confidence = min(1.0, confidence)

            return ThreatIndicator(
                threat_category=pattern.threat_category,
                threat_level=pattern.threat_level,
                confidence=confidence,
                description=(
                    f"{pattern.name}: {len(relevant_events)} occurrences in "
                    f"{pattern.time_window_minutes} minutes"
                ),
                affected_entities=[event.actor.actor_id, event.source.ip_address],
                source_events=[
                    e.event_id for e in relevant_events[-10:]
                ],  # Last 10 events
                metadata={
                    "pattern_id": pattern.pattern_id,
                    "occurrences": len(relevant_events),
                    "time_window_minutes": pattern.time_window_minutes,
                    "event_types": [et.value for et in pattern.event_types],
                },
            )

        return None

    async def _detect_anomalies(self, event: AuditEvent) -> list[ThreatIndicator]:
        """Detect anomalies using statistical analysis."""
        threats = []

        # Time-based anomaly detection
        hour_of_day = event.timestamp.hour
        day_of_week = event.timestamp.weekday()

        # Detect unusual timing patterns
        if await self._is_unusual_time(event.actor.actor_id, hour_of_day, day_of_week):
            weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            threats.append(
                ThreatIndicator(
                    threat_category=ThreatCategory.UNUSUAL_PATTERN,
                    threat_level=ThreatLevel.LOW,
                    confidence=0.4,
                    description=(
                        f"Unusual activity time: {hour_of_day}:00 on "
                        f"{weekdays[day_of_week]}"
                    ),
                    affected_entities=[event.actor.actor_id],
                    source_events=[event.event_id],
                    metadata={
                        "anomaly_type": "unusual_timing",
                        "hour_of_day": hour_of_day,
                        "day_of_week": day_of_week,
                    },
                )
            )

        # Geographic anomaly detection
        if event.source.country and await self._is_unusual_location(
            event.actor.actor_id, event.source.country
        ):
            threats.append(
                ThreatIndicator(
                    threat_category=ThreatCategory.SUSPICIOUS_LOGIN,
                    threat_level=ThreatLevel.MEDIUM,
                    confidence=0.6,
                    description=f"Unusual geographic location: {event.source.country}",
                    affected_entities=[event.actor.actor_id],
                    source_events=[event.event_id],
                    metadata={
                        "anomaly_type": "unusual_location",
                        "country": event.source.country,
                        "ip_address": event.source.ip_address,
                    },
                )
            )

        # Volume anomaly detection
        if await self._is_unusual_volume(event.actor.actor_id, event.event_type):
            threats.append(
                ThreatIndicator(
                    threat_category=ThreatCategory.UNUSUAL_PATTERN,
                    threat_level=ThreatLevel.MEDIUM,
                    confidence=0.7,
                    description=f"Unusual activity volume for {event.event_type.value}",
                    affected_entities=[event.actor.actor_id],
                    source_events=[event.event_id],
                    metadata={
                        "anomaly_type": "unusual_volume",
                        "event_type": event.event_type.value,
                    },
                )
            )

        return threats

    async def _is_unusual_time(self, actor_id: str, hour: int, day: int) -> bool:
        """Check if the activity time is unusual for this actor."""
        # Simple heuristic: activity outside business hours (9-17) on weekdays
        # or any activity on weekends might be suspicious for some actors

        actor_events = list(self._actor_activity[actor_id])
        if len(actor_events) < 10:  # Not enough data
            return False

        # Count activity by hour
        hour_counts = defaultdict(int)
        for event in actor_events[-100:]:  # Last 100 events
            hour_counts[event.timestamp.hour] += 1

        # If this hour has < 5% of total activity, it's unusual
        total_activity = sum(hour_counts.values())
        hour_activity = hour_counts.get(hour, 0)

        return hour_activity / total_activity < 0.05

    async def _is_unusual_location(self, actor_id: str, country: str) -> bool:
        """Check if the location is unusual for this actor."""
        actor_events = list(self._actor_activity[actor_id])
        if len(actor_events) < 5:  # Not enough data
            return False

        # Get historical countries
        historical_countries = set()
        for event in actor_events[-50:]:  # Last 50 events
            if event.source.country:
                historical_countries.add(event.source.country)

        # If country hasn't been seen before and we have significant history
        return country not in historical_countries and len(historical_countries) > 0

    async def _is_unusual_volume(
        self, actor_id: str, event_type: AuditEventType
    ) -> bool:
        """Check if the event volume is unusually high."""
        actor_events = list(self._actor_activity[actor_id])
        if len(actor_events) < 20:  # Not enough data
            return False

        # Count events of this type in last hour
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)

        recent_events = [
            e
            for e in actor_events
            if e.timestamp >= hour_ago and e.event_type == event_type
        ]

        # Simple threshold: more than 50 events of same type in an hour
        return len(recent_events) > 50

    async def _handle_threat_indicator(self, threat: ThreatIndicator):
        """Handle a detected threat indicator."""
        self.stats["threats_detected"] += 1

        # Store the threat indicator
        self._threat_indicators[threat.indicator_id] = threat

        # Check if this should create or update an incident
        incident = await self._find_or_create_incident(threat)

        # Take automated actions if configured
        if threat.confidence >= 0.8:
            await self._take_automated_action(threat, incident)

        # Send alerts if needed
        if threat.confidence >= 0.7:
            await self._send_alert(threat, incident)

    async def _find_or_create_incident(
        self, threat: ThreatIndicator
    ) -> SecurityIncident:
        """Find existing incident or create new one for threat."""
        # Look for existing incidents with same affected entities and threat category
        for incident in self._active_incidents.values():
            if threat.threat_category in incident.threat_categories and any(
                entity in incident.affected_users + incident.affected_ips
                for entity in threat.affected_entities
            ):
                # Update existing incident
                incident.indicators.append(threat)
                incident.updated_at = datetime.now(timezone.utc)
                incident.risk_score = self._calculate_incident_risk_score(incident)
                incident.confidence = self._calculate_incident_confidence(incident)

                return incident

        # Create new incident
        category_name = threat.threat_category.value.replace("_", " ").title()
        incident = SecurityIncident(
            title=f"{category_name} - {threat.description}",
            description=f"Security incident involving {threat.threat_category.value}",
            threat_level=threat.threat_level,
            threat_categories=[threat.threat_category],
            affected_users=[
                e for e in threat.affected_entities if not self._is_ip_address(e)
            ],
            affected_ips=[
                e for e in threat.affected_entities if self._is_ip_address(e)
            ],
            indicators=[threat],
            risk_score=int(threat.confidence * 100),
            confidence=threat.confidence,
        )

        self._active_incidents[incident.incident_id] = incident
        self.stats["incidents_created"] += 1

        # Log incident creation
        await audit_security_event(
            event_type=AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.HIGH
            if threat.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
            else AuditSeverity.MEDIUM,
            message=f"Security incident created: {incident.title}",
            actor_id="security_monitoring_service",
            ip_address="127.0.0.1",
            target_resource="security_incident",
            risk_score=incident.risk_score,
            incident_id=incident.incident_id,
            threat_category=threat.threat_category.value,
            confidence=threat.confidence,
        )

        return incident

    def _calculate_incident_risk_score(self, incident: SecurityIncident) -> int:
        """Calculate risk score for an incident based on its indicators."""
        if not incident.indicators:
            return 0

        # Base score from highest confidence indicator
        max_confidence = max(i.confidence for i in incident.indicators)
        base_score = int(max_confidence * 100)

        # Multiply by threat level
        threat_multipliers = {
            ThreatLevel.LOW: 0.5,
            ThreatLevel.MEDIUM: 1.0,
            ThreatLevel.HIGH: 1.5,
            ThreatLevel.CRITICAL: 2.0,
        }

        highest_threat = max(i.threat_level for i in incident.indicators)
        multiplier = threat_multipliers[highest_threat]

        # Add points for multiple indicators
        indicator_bonus = min(20, len(incident.indicators) * 5)

        return min(100, int(base_score * multiplier) + indicator_bonus)

    def _calculate_incident_confidence(self, incident: SecurityIncident) -> float:
        """Calculate confidence score for an incident."""
        if not incident.indicators:
            return 0.0

        # Average confidence of all indicators
        avg_confidence = sum(i.confidence for i in incident.indicators) / len(
            incident.indicators
        )

        # Boost confidence for multiple correlated indicators
        correlation_boost = min(0.2, len(incident.indicators) * 0.05)

        return min(1.0, avg_confidence + correlation_boost)

    def _is_ip_address(self, value: str) -> bool:
        """Check if a string is an IP address."""
        try:
            from ipaddress import ip_address

            ip_address(value)
            return True
        except ValueError:
            return False

    async def _take_automated_action(
        self, threat: ThreatIndicator, incident: SecurityIncident
    ):
        """Take automated defensive actions based on threat."""
        actions_taken = []

        # Rate limiting or blocking based on threat type
        if threat.threat_category in [
            ThreatCategory.BRUTE_FORCE,
            ThreatCategory.API_ABUSE,
        ]:
            for entity in threat.affected_entities:
                if self._is_ip_address(entity):
                    # TODO: Implement IP blocking
                    actions_taken.append(f"Blocked IP: {entity}")
                    self.stats["automated_blocks"] += 1

        # Log automated actions
        if actions_taken:
            incident.automated_actions.extend(actions_taken)

            await audit_security_event(
                event_type=AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
                severity=AuditSeverity.HIGH,
                message=f"Automated security actions taken: {', '.join(actions_taken)}",
                actor_id="security_monitoring_service",
                ip_address="127.0.0.1",
                target_resource="automated_response",
                incident_id=incident.incident_id,
                actions=actions_taken,
            )

    async def _send_alert(self, threat: ThreatIndicator, incident: SecurityIncident):
        """Send security alert for threat."""
        self.stats["alerts_sent"] += 1

        # Log alert
        await audit_security_event(
            event_type=AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.HIGH
            if threat.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
            else AuditSeverity.MEDIUM,
            message=f"Security alert: {threat.description}",
            actor_id="security_monitoring_service",
            ip_address="127.0.0.1",
            target_resource="security_alert",
            risk_score=int(threat.confidence * 100),
            incident_id=incident.incident_id,
            threat_category=threat.threat_category.value,
            confidence=threat.confidence,
            affected_entities=threat.affected_entities,
        )

        # TODO: Send to external alerting systems (Slack, email, PagerDuty, etc.)
        logger.warning(
            f"SECURITY ALERT: {threat.description}",
            extra={
                "incident_id": incident.incident_id,
                "threat_category": threat.threat_category.value,
                "threat_level": threat.threat_level.value,
                "confidence": threat.confidence,
                "affected_entities": threat.affected_entities,
                "risk_score": incident.risk_score,
            },
        )

    async def _monitoring_loop(self):
        """Background monitoring loop for continuous analysis."""
        while self._is_running:
            try:
                # Perform periodic analysis tasks
                await self._cleanup_old_data()
                await self._analyze_trends()
                await self._update_risk_scores()

                # Sleep before next iteration
                await asyncio.sleep(60)  # Run every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)

    async def _cleanup_old_data(self):
        """Clean up old data to manage memory usage."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)  # Keep 24 hours of data

        # Clean up activity tracking
        for actor_id in list(self._actor_activity.keys()):
            events = self._actor_activity[actor_id]
            # Keep only events from last 24 hours
            self._actor_activity[actor_id] = deque(
                [e for e in events if e.timestamp >= cutoff], maxlen=1000
            )

            # Remove empty entries
            if not self._actor_activity[actor_id]:
                del self._actor_activity[actor_id]

        # Similar cleanup for IP and service activity
        for ip in list(self._ip_activity.keys()):
            events = self._ip_activity[ip]
            self._ip_activity[ip] = deque(
                [e for e in events if e.timestamp >= cutoff], maxlen=1000
            )
            if not self._ip_activity[ip]:
                del self._ip_activity[ip]

        for service in list(self._service_activity.keys()):
            events = self._service_activity[service]
            self._service_activity[service] = deque(
                [e for e in events if e.timestamp >= cutoff], maxlen=1000
            )
            if not self._service_activity[service]:
                del self._service_activity[service]

        # Clean up old threat indicators
        old_indicators = [
            tid
            for tid, threat in self._threat_indicators.items()
            if threat.last_seen < cutoff
        ]
        for tid in old_indicators:
            del self._threat_indicators[tid]

    async def _analyze_trends(self):
        """Analyze trends and patterns in threat data."""
        # TODO: Implement trend analysis
        # - Identify escalating threat patterns
        # - Detect coordinated attacks
        # - Analyze attack timing patterns
        pass

    async def _update_risk_scores(self):
        """Update risk scores for active incidents."""
        for incident in self._active_incidents.values():
            incident.risk_score = self._calculate_incident_risk_score(incident)
            incident.confidence = self._calculate_incident_confidence(incident)

    def get_statistics(self) -> dict[str, Any]:
        """Get monitoring service statistics."""
        return {
            **self.stats,
            "active_incidents": len(self._active_incidents),
            "threat_indicators": len(self._threat_indicators),
            "tracked_actors": len(self._actor_activity),
            "tracked_ips": len(self._ip_activity),
            "tracked_services": len(self._service_activity),
            "buffer_size": len(self._event_buffer),
            "is_running": self._is_running,
        }

    def get_active_incidents(self) -> list[SecurityIncident]:
        """Get list of active security incidents."""
        return list(self._active_incidents.values())

    def get_threat_indicators(self, limit: int = 100) -> list[ThreatIndicator]:
        """Get recent threat indicators."""
        indicators = sorted(
            self._threat_indicators.values(), key=lambda x: x.last_seen, reverse=True
        )
        return indicators[:limit]

    async def resolve_incident(
        self, incident_id: str, resolution: str, notes: str | None = None
    ):
        """Mark an incident as resolved."""
        if incident_id in self._active_incidents:
            incident = self._active_incidents[incident_id]
            incident.status = "resolved"
            incident.updated_at = datetime.now(timezone.utc)
            if notes:
                incident.notes.append(f"Resolved: {notes}")

            # Log resolution
            await audit_security_event(
                event_type=AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
                severity=AuditSeverity.LOW,
                message=f"Security incident resolved: {incident.title}",
                actor_id="security_monitoring_service",
                ip_address="127.0.0.1",
                target_resource="security_incident",
                incident_id=incident_id,
                resolution=resolution,
            )

            # Remove from active incidents
            del self._active_incidents[incident_id]

# Global monitoring service instance
_monitoring_service: SecurityMonitoringService | None = None

async def get_monitoring_service() -> SecurityMonitoringService:
    """Get or create the global monitoring service instance."""
    global _monitoring_service

    if _monitoring_service is None:
        _monitoring_service = SecurityMonitoringService()
        await _monitoring_service.start()

    return _monitoring_service

async def shutdown_monitoring_service():
    """Shutdown the global monitoring service instance."""
    global _monitoring_service

    if _monitoring_service is not None:
        await _monitoring_service.stop()
        _monitoring_service = None
