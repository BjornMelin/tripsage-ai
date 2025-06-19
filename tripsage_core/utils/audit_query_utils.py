"""
Audit Log Querying and Analysis Utilities.

This module provides utilities for querying, analyzing, and reporting on
audit logs. It includes functions for common audit queries, log analysis,
and generating compliance reports.

Features:
- Structured audit log queries
- Log aggregation and analysis
- Compliance reporting
- Security event correlation
- Trend analysis
- Export capabilities
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.services.business.audit_logging_service import (
    AuditEvent,
    AuditEventType,
    AuditOutcome,
    AuditSeverity,
    SecurityAuditLogger,
    get_audit_logger,
)
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class AuditQuery(BaseModel):
    """Structured audit log query parameters."""

    # Time range
    start_time: datetime | None = None
    end_time: datetime | None = None

    # Event filters
    event_types: list[AuditEventType] | None = None
    severities: list[AuditSeverity] | None = None
    outcomes: list[AuditOutcome] | None = None

    # Actor filters
    actor_ids: list[str] | None = None
    actor_types: list[str] | None = None

    # Source filters
    ip_addresses: list[str] | None = None
    countries: list[str] | None = None

    # Target filters
    resource_types: list[str] | None = None
    resource_ids: list[str] | None = None

    # Risk and compliance
    min_risk_score: int | None = None
    max_risk_score: int | None = None
    compliance_tags: list[str] | None = None

    # Text search
    message_contains: str | None = None
    description_contains: str | None = None

    # Pagination and sorting
    limit: int = 1000
    offset: int = 0
    sort_by: str = "timestamp"
    sort_order: str = "desc"  # asc or desc

    # Aggregation
    group_by: str | None = None  # event_type, actor_id, ip_address, etc.
    include_stats: bool = False


class AuditAnalysisResult(TripSageModel):
    """Result of audit log analysis."""

    total_events: int
    events: list[AuditEvent]

    # Statistics
    events_by_type: dict[str, int] = Field(default_factory=dict)
    events_by_severity: dict[str, int] = Field(default_factory=dict)
    events_by_outcome: dict[str, int] = Field(default_factory=dict)
    events_by_actor: dict[str, int] = Field(default_factory=dict)
    events_by_ip: dict[str, int] = Field(default_factory=dict)

    # Time-based analysis
    events_by_hour: dict[int, int] = Field(default_factory=dict)
    events_by_day: dict[str, int] = Field(default_factory=dict)

    # Risk analysis
    high_risk_events: int = 0
    security_incidents: int = 0
    failed_authentications: int = 0

    # Trends
    trends: dict[str, Any] = Field(default_factory=dict)

    # Query metadata
    query_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    query_duration_ms: float | None = None


class ComplianceReport(TripSageModel):
    """Compliance audit report."""

    report_id: str = Field(
        default_factory=lambda: f"rpt-{int(datetime.now().timestamp())}"
    )
    report_type: str  # HIPAA, SOX, PCI, GDPR, etc.
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Report period
    start_date: datetime
    end_date: datetime

    # Summary statistics
    total_events: int
    security_events: int
    failed_access_attempts: int
    configuration_changes: int
    data_access_events: int

    # Compliance-specific metrics
    compliance_violations: list[dict[str, Any]] = Field(default_factory=list)
    policy_violations: list[dict[str, Any]] = Field(default_factory=list)
    access_patterns: dict[str, Any] = Field(default_factory=dict)

    # Risk assessment
    overall_risk_score: int = 0
    risk_factors: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # Supporting data
    events_summary: dict[str, Any] = Field(default_factory=dict)
    trends: dict[str, Any] = Field(default_factory=dict)


class AuditQueryEngine:
    """Engine for querying and analyzing audit logs."""

    def __init__(self, audit_logger: SecurityAuditLogger | None = None):
        """Initialize the query engine."""
        self.audit_logger = audit_logger

    async def query(self, query: AuditQuery) -> AuditAnalysisResult:
        """Execute an audit log query and return results with analysis."""
        start_time = datetime.now()

        # Get audit logger if not provided
        if not self.audit_logger:
            self.audit_logger = await get_audit_logger()

        # Execute the query
        events = await self._execute_query(query)

        # Perform analysis
        result = await self._analyze_events(events, query)

        # Calculate query duration
        query_duration = (datetime.now() - start_time).total_seconds() * 1000
        result.query_duration_ms = query_duration

        return result

    async def _execute_query(self, query: AuditQuery) -> list[AuditEvent]:
        """Execute the actual query against audit logs."""
        # Use the audit logger's query method with our parameters
        events = await self.audit_logger.query_events(
            start_time=query.start_time,
            end_time=query.end_time,
            event_types=query.event_types,
            severity=query.severities[0]
            if query.severities and len(query.severities) == 1
            else None,
            actor_id=query.actor_ids[0]
            if query.actor_ids and len(query.actor_ids) == 1
            else None,
            limit=query.limit,
        )

        # Apply additional filtering that the basic query doesn't support
        filtered_events = []
        for event in events:
            if not self._matches_filters(event, query):
                continue
            filtered_events.append(event)

        # Apply sorting
        if query.sort_by == "timestamp":
            filtered_events.sort(
                key=lambda x: x.timestamp, reverse=(query.sort_order == "desc")
            )
        elif query.sort_by == "risk_score":
            filtered_events.sort(
                key=lambda x: x.risk_score or 0, reverse=(query.sort_order == "desc")
            )

        # Apply pagination
        start_idx = query.offset
        end_idx = start_idx + query.limit

        return filtered_events[start_idx:end_idx]

    def _matches_filters(self, event: AuditEvent, query: AuditQuery) -> bool:
        """Check if an event matches all query filters."""
        # Severity filter
        if query.severities and event.severity not in query.severities:
            return False

        # Outcome filter
        if query.outcomes and event.outcome not in query.outcomes:
            return False

        # Actor filters
        if query.actor_ids and event.actor.actor_id not in query.actor_ids:
            return False

        if query.actor_types and event.actor.actor_type not in query.actor_types:
            return False

        # Source filters
        if query.ip_addresses and event.source.ip_address not in query.ip_addresses:
            return False

        if query.countries and event.source.country not in query.countries:
            return False

        # Target filters
        if query.resource_types and event.target:
            if event.target.resource_type not in query.resource_types:
                return False
        elif query.resource_types:  # Required but event has no target
            return False

        if query.resource_ids and event.target:
            if event.target.resource_id not in query.resource_ids:
                return False
        elif query.resource_ids:  # Required but event has no target
            return False

        # Risk score filters
        if query.min_risk_score is not None and (
            not event.risk_score or event.risk_score < query.min_risk_score
        ):
            return False

        if query.max_risk_score is not None:
            if not event.risk_score or event.risk_score > query.max_risk_score:
                return False

        # Compliance tags
        if query.compliance_tags:
            if not any(tag in event.compliance_tags for tag in query.compliance_tags):
                return False

        # Text search
        if query.message_contains:
            if query.message_contains.lower() not in event.message.lower():
                return False

        if query.description_contains and event.description:
            if query.description_contains.lower() not in event.description.lower():
                return False

        return True

    async def _analyze_events(
        self, events: list[AuditEvent], query: AuditQuery
    ) -> AuditAnalysisResult:
        """Analyze a list of events and generate statistics."""
        result = AuditAnalysisResult(total_events=len(events), events=events)

        if not events:
            return result

        # Event type analysis
        for event in events:
            result.events_by_type[event.event_type.value] = (
                result.events_by_type.get(event.event_type.value, 0) + 1
            )
            result.events_by_severity[event.severity.value] = (
                result.events_by_severity.get(event.severity.value, 0) + 1
            )
            result.events_by_outcome[event.outcome.value] = (
                result.events_by_outcome.get(event.outcome.value, 0) + 1
            )
            result.events_by_actor[event.actor.actor_id] = (
                result.events_by_actor.get(event.actor.actor_id, 0) + 1
            )
            result.events_by_ip[event.source.ip_address] = (
                result.events_by_ip.get(event.source.ip_address, 0) + 1
            )

            # Time-based analysis
            hour = event.timestamp.hour
            day = event.timestamp.strftime("%Y-%m-%d")
            result.events_by_hour[hour] = result.events_by_hour.get(hour, 0) + 1
            result.events_by_day[day] = result.events_by_day.get(day, 0) + 1

            # Risk analysis
            if event.risk_score and event.risk_score >= 70:
                result.high_risk_events += 1

            if event.event_type in [
                AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
                AuditEventType.SECURITY_MULTIPLE_FAILED_ATTEMPTS,
                AuditEventType.SECURITY_UNUSUAL_PATTERN,
            ]:
                result.security_incidents += 1

            if event.event_type in [
                AuditEventType.AUTH_LOGIN_FAILED,
                AuditEventType.API_KEY_VALIDATION_FAILED,
                AuditEventType.ACCESS_DENIED,
            ]:
                result.failed_authentications += 1

        # Calculate trends
        result.trends = await self._calculate_trends(events)

        return result

    async def _calculate_trends(self, events: list[AuditEvent]) -> dict[str, Any]:
        """Calculate trends from events."""
        if len(events) < 2:
            return {}

        # Sort events by time
        sorted_events = sorted(events, key=lambda x: x.timestamp)

        # Calculate daily event counts
        daily_counts = defaultdict(int)
        for event in sorted_events:
            day = event.timestamp.strftime("%Y-%m-%d")
            daily_counts[day] += 1

        # Calculate trend direction
        days = sorted(daily_counts.keys())
        if len(days) >= 2:
            recent_avg = sum(daily_counts[day] for day in days[-3:]) / min(3, len(days))
            earlier_avg = sum(daily_counts[day] for day in days[:3]) / min(3, len(days))

            trend_direction = "increasing" if recent_avg > earlier_avg else "decreasing"
            trend_magnitude = abs(recent_avg - earlier_avg) / max(earlier_avg, 1)
        else:
            trend_direction = "stable"
            trend_magnitude = 0.0

        return {
            "daily_counts": dict(daily_counts),
            "trend_direction": trend_direction,
            "trend_magnitude": trend_magnitude,
            "total_days": len(days),
            "avg_events_per_day": sum(daily_counts.values()) / len(days) if days else 0,
        }

    async def generate_compliance_report(
        self,
        report_type: str,
        start_date: datetime,
        end_date: datetime,
        compliance_framework: str | None = None,
    ) -> ComplianceReport:
        """Generate a compliance audit report."""
        # Query all events in the date range
        query = AuditQuery(
            start_time=start_date,
            end_time=end_date,
            limit=10000,  # Get more events for comprehensive report
            include_stats=True,
        )

        analysis = await self.query(query)

        # Create compliance report
        report = ComplianceReport(
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            total_events=analysis.total_events,
            security_events=analysis.security_incidents,
            failed_access_attempts=analysis.failed_authentications,
            configuration_changes=analysis.events_by_type.get("config.changed", 0),
            data_access_events=analysis.events_by_type.get("data.access", 0),
        )

        # Analyze compliance violations
        report.compliance_violations = await self._analyze_compliance_violations(
            analysis.events, report_type
        )

        # Analyze policy violations
        report.policy_violations = await self._analyze_policy_violations(
            analysis.events
        )

        # Calculate overall risk score
        report.overall_risk_score = await self._calculate_overall_risk_score(analysis)

        # Generate recommendations
        report.recommendations = await self._generate_recommendations(
            analysis, report_type
        )

        # Add supporting data
        report.events_summary = {
            "by_type": analysis.events_by_type,
            "by_severity": analysis.events_by_severity,
            "by_outcome": analysis.events_by_outcome,
        }
        report.trends = analysis.trends

        return report

    async def _analyze_compliance_violations(
        self, events: list[AuditEvent], report_type: str
    ) -> list[dict[str, Any]]:
        """Analyze events for compliance violations."""
        violations = []

        # Example compliance checks (customize based on framework)
        if report_type.upper() == "HIPAA":
            # HIPAA-specific checks
            for event in events:
                if (
                    event.event_type == AuditEventType.DATA_ACCESS
                    and not event.metadata.get("hipaa_authorized", False)
                ):
                    violations.append(
                        {
                            "type": "unauthorized_data_access",
                            "event_id": event.event_id,
                            "description": "Data access without HIPAA authorization",
                            "severity": "high",
                            "timestamp": event.timestamp.isoformat(),
                        }
                    )

        elif report_type.upper() == "SOX":
            # SOX-specific checks
            for event in events:
                if (
                    event.event_type == AuditEventType.CONFIG_CHANGED
                    and event.severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]
                    and not event.metadata.get("sox_approved", False)
                ):
                    violations.append(
                        {
                            "type": "unapproved_system_change",
                            "event_id": event.event_id,
                            "description": "System change without SOX approval",
                            "severity": "critical",
                            "timestamp": event.timestamp.isoformat(),
                        }
                    )

        return violations

    async def _analyze_policy_violations(
        self, events: list[AuditEvent]
    ) -> list[dict[str, Any]]:
        """Analyze events for policy violations."""
        violations = []

        # Example policy violation checks
        failed_login_counts = defaultdict(int)
        for event in events:
            if event.event_type == AuditEventType.AUTH_LOGIN_FAILED:
                failed_login_counts[event.actor.actor_id] += 1

        # Check for excessive failed logins
        for actor_id, count in failed_login_counts.items():
            if count >= 5:
                violations.append(
                    {
                        "type": "excessive_failed_logins",
                        "actor_id": actor_id,
                        "description": (
                            f"Actor {actor_id} had {count} failed login attempts"
                        ),
                        "severity": "medium",
                        "count": count,
                    }
                )

        return violations

    async def _calculate_overall_risk_score(self, analysis: AuditAnalysisResult) -> int:
        """Calculate overall risk score based on analysis."""
        if analysis.total_events == 0:
            return 0

        # Base score from high-risk events
        high_risk_ratio = analysis.high_risk_events / analysis.total_events
        base_score = int(high_risk_ratio * 100)

        # Add points for security incidents
        security_ratio = analysis.security_incidents / analysis.total_events
        security_score = int(security_ratio * 50)

        # Add points for failed authentications
        auth_failure_ratio = analysis.failed_authentications / analysis.total_events
        auth_score = int(auth_failure_ratio * 30)

        return min(100, base_score + security_score + auth_score)

    async def _generate_recommendations(
        self, analysis: AuditAnalysisResult, report_type: str
    ) -> list[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        # High-risk events recommendation
        if analysis.high_risk_events > analysis.total_events * 0.1:
            recommendations.append(
                "Consider implementing additional security controls to reduce "
                "high-risk events"
            )

        # Failed authentication recommendation
        if analysis.failed_authentications > analysis.total_events * 0.2:
            recommendations.append(
                "Review authentication policies and consider implementing "
                "account lockout mechanisms"
            )

        # Security incidents recommendation
        if analysis.security_incidents > 0:
            recommendations.append(
                "Investigate security incidents and implement preventive measures"
            )

        # IP-based recommendation
        ip_counts = sorted(
            analysis.events_by_ip.items(), key=lambda x: x[1], reverse=True
        )
        if ip_counts and ip_counts[0][1] > analysis.total_events * 0.5:
            recommendations.append(
                f"Monitor IP {ip_counts[0][0]} which generated {ip_counts[0][1]} events"
            )

        return recommendations


# Convenience functions for common queries


async def query_failed_logins(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 100,
) -> AuditAnalysisResult:
    """Query failed login attempts."""
    if not start_time:
        start_time = datetime.now(timezone.utc) - timedelta(days=7)

    query = AuditQuery(
        start_time=start_time,
        end_time=end_time,
        event_types=[AuditEventType.AUTH_LOGIN_FAILED],
        limit=limit,
        include_stats=True,
    )

    engine = AuditQueryEngine()
    return await engine.query(query)


async def query_high_risk_events(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    min_risk_score: int = 70,
    limit: int = 100,
) -> AuditAnalysisResult:
    """Query high-risk security events."""
    if not start_time:
        start_time = datetime.now(timezone.utc) - timedelta(days=1)

    query = AuditQuery(
        start_time=start_time,
        end_time=end_time,
        min_risk_score=min_risk_score,
        limit=limit,
        sort_by="risk_score",
        include_stats=True,
    )

    engine = AuditQueryEngine()
    return await engine.query(query)


async def query_user_activity(
    user_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 100,
) -> AuditAnalysisResult:
    """Query activity for a specific user."""
    if not start_time:
        start_time = datetime.now(timezone.utc) - timedelta(days=30)

    query = AuditQuery(
        start_time=start_time,
        end_time=end_time,
        actor_ids=[user_id],
        limit=limit,
        include_stats=True,
    )

    engine = AuditQueryEngine()
    return await engine.query(query)


async def query_api_key_events(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 100,
) -> AuditAnalysisResult:
    """Query API key related events."""
    if not start_time:
        start_time = datetime.now(timezone.utc) - timedelta(days=7)

    api_key_events = [
        AuditEventType.API_KEY_CREATED,
        AuditEventType.API_KEY_DELETED,
        AuditEventType.API_KEY_ROTATED,
        AuditEventType.API_KEY_VALIDATION_SUCCESS,
        AuditEventType.API_KEY_VALIDATION_FAILED,
        AuditEventType.API_KEY_RATE_LIMITED,
    ]

    query = AuditQuery(
        start_time=start_time,
        end_time=end_time,
        event_types=api_key_events,
        limit=limit,
        include_stats=True,
    )

    engine = AuditQueryEngine()
    return await engine.query(query)


async def generate_daily_security_report() -> ComplianceReport:
    """Generate a daily security report."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=1)

    engine = AuditQueryEngine()
    return await engine.generate_compliance_report(
        report_type="DAILY_SECURITY", start_date=start_time, end_date=end_time
    )
