"""
API Key Usage Monitoring Service.

This service provides comprehensive monitoring for API key usage including:
- Request tracking and analytics
- Rate limit monitoring
- Anomaly detection
- Usage aggregation and reporting
- Real-time alerts
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageModel

logger = logging.getLogger(__name__)


class UsageMetricType(str, Enum):
    """Types of usage metrics tracked."""

    REQUEST_COUNT = "request_count"
    ERROR_COUNT = "error_count"
    LATENCY = "latency"
    RATE_LIMIT_HIT = "rate_limit_hit"
    QUOTA_USAGE = "quota_usage"


class AnomalyType(str, Enum):
    """Types of anomalies detected."""

    SPIKE = "spike"  # Sudden increase in usage
    DROP = "drop"  # Sudden decrease in usage
    ERROR_RATE = "error_rate"  # High error rate
    LATENCY = "latency"  # High latency
    PATTERN = "pattern"  # Unusual usage pattern


class UsageRecord(TripSageModel):
    """Single usage record for an API key."""

    key_id: str
    user_id: str
    service: str
    endpoint: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool
    latency_ms: float
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    request_size: Optional[int] = None
    response_size: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UsageStatistics(TripSageModel):
    """Aggregated usage statistics."""

    key_id: str
    service: str
    period_start: datetime
    period_end: datetime
    request_count: int = 0
    error_count: int = 0
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    total_request_bytes: int = 0
    total_response_bytes: int = 0
    unique_endpoints: int = 0
    rate_limit_hits: int = 0


class UsageAlert(TripSageModel):
    """Alert for unusual API key usage."""

    alert_id: str
    key_id: str
    user_id: str
    service: str
    anomaly_type: AnomalyType
    severity: str  # low, medium, high, critical
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False


class UsageDashboard(TripSageModel):
    """Dashboard data for API key usage monitoring."""

    total_requests: int
    total_errors: int
    overall_success_rate: float
    active_keys: int
    services_status: Dict[str, str]  # service -> status
    top_users: List[Dict[str, Any]]
    recent_alerts: List[UsageAlert]
    usage_by_service: Dict[str, int]
    usage_trend: List[Dict[str, Any]]  # Time series data


class ApiKeyMonitoringService:
    """
    Comprehensive API key usage monitoring service.

    Features:
    - Real-time usage tracking
    - Sliding window rate limiting
    - Usage aggregation and analytics
    - Anomaly detection
    - Alert generation
    - Dashboard data generation
    """

    def __init__(
        self,
        cache_service=None,
        database_service=None,
        alert_threshold_error_rate: float = 0.1,  # 10% error rate
        alert_threshold_spike_multiplier: float = 3.0,  # 3x normal usage
        anomaly_window_minutes: int = 15,
        aggregation_interval_minutes: int = 5,
    ):
        """
        Initialize the monitoring service.

        Args:
            cache_service: DragonflyDB cache service
            database_service: Database service for persistence
            alert_threshold_error_rate: Error rate threshold for alerts
            alert_threshold_spike_multiplier: Spike detection multiplier
            anomaly_window_minutes: Window for anomaly detection
            aggregation_interval_minutes: Interval for aggregating stats
        """
        self.cache = cache_service
        self.db = database_service
        self.alert_threshold_error_rate = alert_threshold_error_rate
        self.alert_threshold_spike_multiplier = alert_threshold_spike_multiplier
        self.anomaly_window_minutes = anomaly_window_minutes
        self.aggregation_interval_minutes = aggregation_interval_minutes

        # In-memory buffers for recent data
        self.recent_usage: Dict[str, List[UsageRecord]] = defaultdict(list)
        self.active_alerts: Dict[str, UsageAlert] = {}

        # Background tasks
        self._aggregation_task = None
        self._anomaly_detection_task = None

    async def start_background_tasks(self):
        """Start background monitoring tasks."""
        if not self._aggregation_task:
            self._aggregation_task = asyncio.create_task(self._aggregation_loop())

        if not self._anomaly_detection_task:
            self._anomaly_detection_task = asyncio.create_task(
                self._anomaly_detection_loop()
            )

    async def stop_background_tasks(self):
        """Stop background monitoring tasks."""
        if self._aggregation_task:
            self._aggregation_task.cancel()
            try:
                await self._aggregation_task
            except asyncio.CancelledError:
                pass

        if self._anomaly_detection_task:
            self._anomaly_detection_task.cancel()
            try:
                await self._anomaly_detection_task
            except asyncio.CancelledError:
                pass

    async def track_usage(
        self,
        key_id: str,
        user_id: str,
        service: str,
        endpoint: str,
        success: bool,
        latency_ms: float,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Track API key usage.

        Args:
            key_id: API key ID
            user_id: User ID
            service: Service name
            endpoint: API endpoint
            success: Whether request was successful
            latency_ms: Request latency in milliseconds
            error_code: Error code if failed
            error_message: Error message if failed
            request_size: Request size in bytes
            response_size: Response size in bytes
            metadata: Additional metadata
        """
        usage_record = UsageRecord(
            key_id=key_id,
            user_id=user_id,
            service=service,
            endpoint=endpoint,
            success=success,
            latency_ms=latency_ms,
            error_code=error_code,
            error_message=error_message,
            request_size=request_size,
            response_size=response_size,
            metadata=metadata or {},
        )

        # Add to in-memory buffer
        self.recent_usage[key_id].append(usage_record)

        # Store in cache for real-time access
        if self.cache:
            await self._store_usage_in_cache(usage_record)

        # Check for immediate alerts (high latency, errors)
        await self._check_immediate_alerts(usage_record)

    async def get_usage_statistics(
        self,
        key_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        service: Optional[str] = None,
    ) -> UsageStatistics:
        """
        Get usage statistics for an API key.

        Args:
            key_id: API key ID
            start_time: Start of period (default: last hour)
            end_time: End of period (default: now)
            service: Filter by service

        Returns:
            Aggregated usage statistics
        """
        if not start_time:
            start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        if not end_time:
            end_time = datetime.now(timezone.utc)

        # Get data from cache
        if self.cache:
            stats = await self._get_cached_statistics(
                key_id, start_time, end_time, service
            )
            if stats:
                return stats

        # Fallback to calculating from recent usage
        return self._calculate_statistics_from_buffer(
            key_id, start_time, end_time, service
        )

    async def get_rate_limit_status(
        self, key_id: str, window_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Get current rate limit status for an API key.

        Args:
            key_id: API key ID
            window_minutes: Rate limit window in minutes

        Returns:
            Rate limit status including current usage and limits
        """
        if not self.cache:
            return {
                "error": "Cache service not available",
                "requests_in_window": 0,
                "window_minutes": window_minutes,
            }

        try:
            # Get request count from sliding window
            window_key = f"rate_limit:sliding:{key_id}:{window_minutes}"
            current_time = datetime.now(timezone.utc).timestamp()
            window_start = current_time - (window_minutes * 60)

            # Remove old entries and count current
            request_count = await self.cache.zcount(
                window_key, window_start, current_time
            )

            # Get configured limits
            limit_key = f"rate_limit:config:{key_id}"
            limit_data = await self.cache.get(limit_key)

            if limit_data:
                limits = json.loads(limit_data)
            else:
                # Default limits
                limits = {
                    "requests_per_minute": 60,
                    "requests_per_hour": 1000,
                }

            # Calculate appropriate limit for window
            if window_minutes <= 1:
                limit = limits.get("requests_per_minute", 60)
            elif window_minutes <= 60:
                limit = limits.get("requests_per_hour", 1000) * (window_minutes / 60)
            else:
                limit = limits.get("requests_per_hour", 1000) * (window_minutes / 60)

            return {
                "requests_in_window": int(request_count),
                "window_minutes": window_minutes,
                "limit": int(limit),
                "remaining": max(0, int(limit - request_count)),
                "reset_at": datetime.fromtimestamp(
                    current_time + (window_minutes * 60), tz=timezone.utc
                ).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}")
            return {
                "error": str(e),
                "requests_in_window": 0,
                "window_minutes": window_minutes,
            }

    async def get_dashboard_data(
        self,
        time_range_hours: int = 24,
        top_users_limit: int = 10,
    ) -> UsageDashboard:
        """
        Get dashboard data for monitoring UI.

        Args:
            time_range_hours: Time range for statistics
            top_users_limit: Number of top users to include

        Returns:
            Dashboard data including statistics and trends
        """
        start_time = datetime.now(timezone.utc) - timedelta(hours=time_range_hours)
        end_time = datetime.now(timezone.utc)

        # Aggregate data from cache
        total_requests = 0
        total_errors = 0
        usage_by_service = defaultdict(int)
        user_usage = defaultdict(int)
        service_errors = defaultdict(int)

        # Get all recent usage data
        if self.cache:
            # Get aggregated stats from cache
            stats_pattern = "usage:stats:*"
            stats_keys = await self.cache.keys(stats_pattern)

            for key in stats_keys:
                try:
                    data = await self.cache.get(key)
                    if data:
                        stats = json.loads(data)
                        total_requests += stats.get("request_count", 0)
                        total_errors += stats.get("error_count", 0)

                        service = stats.get("service", "unknown")
                        usage_by_service[service] += stats.get("request_count", 0)

                        if stats.get("error_count", 0) > 0:
                            service_errors[service] += stats.get("error_count", 0)

                except Exception as e:
                    logger.warning(f"Failed to process stats key {key}: {e}")

        # Calculate overall success rate
        overall_success_rate = (
            (total_requests - total_errors) / total_requests
            if total_requests > 0
            else 1.0
        )

        # Determine service status
        services_status = {}
        for service in usage_by_service:
            error_rate = (
                service_errors[service] / usage_by_service[service]
                if usage_by_service[service] > 0
                else 0
            )

            if error_rate > 0.1:  # >10% errors
                services_status[service] = "unhealthy"
            elif error_rate > 0.05:  # >5% errors
                services_status[service] = "degraded"
            else:
                services_status[service] = "healthy"

        # Get top users (simplified for now)
        top_users = [
            {"user_id": user_id, "request_count": count}
            for user_id, count in sorted(
                user_usage.items(), key=lambda x: x[1], reverse=True
            )[:top_users_limit]
        ]

        # Get recent alerts
        recent_alerts = list(self.active_alerts.values())[:10]

        # Generate usage trend (simplified)
        usage_trend = await self._generate_usage_trend(start_time, end_time)

        return UsageDashboard(
            total_requests=total_requests,
            total_errors=total_errors,
            overall_success_rate=overall_success_rate,
            active_keys=len(set(key for key in self.recent_usage.keys())),
            services_status=services_status,
            top_users=top_users,
            recent_alerts=recent_alerts,
            usage_by_service=dict(usage_by_service),
            usage_trend=usage_trend,
        )

    async def detect_anomalies(self, key_id: str) -> List[UsageAlert]:
        """
        Detect anomalies in API key usage.

        Args:
            key_id: API key ID

        Returns:
            List of detected anomalies
        """
        alerts = []

        # Get recent usage
        recent_records = self.recent_usage.get(key_id, [])
        if len(recent_records) < 10:  # Not enough data
            return alerts

        # Time windows for comparison
        now = datetime.now(timezone.utc)
        current_window_start = now - timedelta(minutes=self.anomaly_window_minutes)
        previous_window_start = current_window_start - timedelta(
            minutes=self.anomaly_window_minutes
        )

        # Split records by window
        current_window = [
            r for r in recent_records if r.timestamp >= current_window_start
        ]
        previous_window = [
            r
            for r in recent_records
            if previous_window_start <= r.timestamp < current_window_start
        ]

        if not previous_window:
            return alerts

        # 1. Check for usage spike/drop
        current_count = len(current_window)
        previous_count = len(previous_window)

        if previous_count > 0:
            ratio = current_count / previous_count

            if ratio >= self.alert_threshold_spike_multiplier:
                alerts.append(
                    self._create_alert(
                        key_id,
                        AnomalyType.SPIKE,
                        "high",
                        f"Usage spike detected: {ratio:.1f}x normal",
                        {
                            "current_requests": current_count,
                            "previous_requests": previous_count,
                            "ratio": ratio,
                        },
                    )
                )
            elif ratio <= 0.2:  # 80% drop
                alerts.append(
                    self._create_alert(
                        key_id,
                        AnomalyType.DROP,
                        "medium",
                        f"Usage drop detected: {ratio:.1%} of normal",
                        {
                            "current_requests": current_count,
                            "previous_requests": previous_count,
                            "ratio": ratio,
                        },
                    )
                )

        # 2. Check error rate
        current_errors = sum(1 for r in current_window if not r.success)
        if current_count > 0:
            error_rate = current_errors / current_count

            if error_rate >= self.alert_threshold_error_rate:
                alerts.append(
                    self._create_alert(
                        key_id,
                        AnomalyType.ERROR_RATE,
                        "high" if error_rate >= 0.5 else "medium",
                        f"High error rate: {error_rate:.1%}",
                        {
                            "error_count": current_errors,
                            "total_requests": current_count,
                            "error_rate": error_rate,
                        },
                    )
                )

        # 3. Check latency
        if current_window:
            latencies = [r.latency_ms for r in current_window]
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

            # Compare with historical average
            if previous_window:
                prev_latencies = [r.latency_ms for r in previous_window]
                prev_avg = sum(prev_latencies) / len(prev_latencies)

                if avg_latency > prev_avg * 2 and avg_latency > 1000:  # 2x and >1s
                    alerts.append(
                        self._create_alert(
                            key_id,
                            AnomalyType.LATENCY,
                            "medium",
                            f"High latency detected: {avg_latency:.0f}ms average",
                            {
                                "avg_latency_ms": avg_latency,
                                "p95_latency_ms": p95_latency,
                                "previous_avg_ms": prev_avg,
                            },
                        )
                    )

        return alerts

    async def _store_usage_in_cache(self, record: UsageRecord) -> None:
        """Store usage record in cache for real-time access."""
        if not self.cache:
            return

        try:
            # Store in sliding window for rate limiting
            window_key = f"rate_limit:sliding:{record.key_id}:60"
            timestamp = record.timestamp.timestamp()

            # Add to sorted set with timestamp as score
            await self.cache.zadd(window_key, {str(timestamp): timestamp})

            # Set expiration to clean up old data
            await self.cache.expire(window_key, 7200)  # 2 hours

            # Store detailed record for analytics
            record_key = f"usage:record:{record.key_id}:{timestamp}"
            await self.cache.set(
                record_key,
                json.dumps(record.model_dump(mode="json")),
                ex=86400,  # 24 hours
            )

            # Update real-time counters
            counter_key = f"usage:counter:{record.service}:{record.key_id}"
            await self.cache.hincrby(counter_key, "total", 1)
            if not record.success:
                await self.cache.hincrby(counter_key, "errors", 1)

        except Exception as e:
            logger.error(f"Failed to store usage in cache: {e}")

    async def _check_immediate_alerts(self, record: UsageRecord) -> None:
        """Check for immediate alerts based on single usage record."""
        # High latency alert
        if record.latency_ms > 5000:  # >5 seconds
            alert = self._create_alert(
                record.key_id,
                AnomalyType.LATENCY,
                "high" if record.latency_ms > 10000 else "medium",
                f"Very high latency: {record.latency_ms:.0f}ms",
                {
                    "endpoint": record.endpoint,
                    "latency_ms": record.latency_ms,
                    "service": record.service,
                },
            )
            self.active_alerts[alert.alert_id] = alert

    def _create_alert(
        self,
        key_id: str,
        anomaly_type: AnomalyType,
        severity: str,
        message: str,
        details: Dict[str, Any],
    ) -> UsageAlert:
        """Create a new usage alert."""
        import uuid

        # Get user_id and service from recent usage
        recent = self.recent_usage.get(key_id, [])
        user_id = recent[0].user_id if recent else "unknown"
        service = recent[0].service if recent else "unknown"

        return UsageAlert(
            alert_id=str(uuid.uuid4()),
            key_id=key_id,
            user_id=user_id,
            service=service,
            anomaly_type=anomaly_type,
            severity=severity,
            message=message,
            details=details,
        )

    def _calculate_statistics_from_buffer(
        self,
        key_id: str,
        start_time: datetime,
        end_time: datetime,
        service: Optional[str] = None,
    ) -> UsageStatistics:
        """Calculate statistics from in-memory buffer."""
        records = self.recent_usage.get(key_id, [])

        # Filter by time and service
        filtered = [
            r
            for r in records
            if start_time <= r.timestamp <= end_time
            and (service is None or r.service == service)
        ]

        if not filtered:
            return UsageStatistics(
                key_id=key_id,
                service=service or "all",
                period_start=start_time,
                period_end=end_time,
            )

        # Calculate statistics
        request_count = len(filtered)
        error_count = sum(1 for r in filtered if not r.success)
        success_rate = (
            (request_count - error_count) / request_count if request_count > 0 else 1.0
        )

        latencies = [r.latency_ms for r in filtered]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        sorted_latencies = sorted(latencies)
        p95_latency = sorted_latencies[int(len(latencies) * 0.95)] if latencies else 0
        p99_latency = sorted_latencies[int(len(latencies) * 0.99)] if latencies else 0

        total_request_bytes = sum(r.request_size or 0 for r in filtered)
        total_response_bytes = sum(r.response_size or 0 for r in filtered)

        unique_endpoints = len(set(r.endpoint for r in filtered))

        return UsageStatistics(
            key_id=key_id,
            service=service or "all",
            period_start=start_time,
            period_end=end_time,
            request_count=request_count,
            error_count=error_count,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            total_request_bytes=total_request_bytes,
            total_response_bytes=total_response_bytes,
            unique_endpoints=unique_endpoints,
            rate_limit_hits=0,  # Would need to track separately
        )

    async def _get_cached_statistics(
        self,
        key_id: str,
        start_time: datetime,
        end_time: datetime,
        service: Optional[str] = None,
    ) -> Optional[UsageStatistics]:
        """Get statistics from cache if available."""
        if not self.cache:
            return None

        try:
            # Try to get pre-aggregated stats
            stats_key = f"usage:stats:{key_id}:{service or 'all'}"
            data = await self.cache.get(stats_key)

            if data:
                stats_dict = json.loads(data)
                # Convert timestamps
                stats_dict["period_start"] = datetime.fromisoformat(
                    stats_dict["period_start"]
                )
                stats_dict["period_end"] = datetime.fromisoformat(
                    stats_dict["period_end"]
                )

                stats = UsageStatistics(**stats_dict)

                # Check if cached stats match requested period
                if stats.period_start <= start_time and stats.period_end >= end_time:
                    return stats

        except Exception as e:
            logger.warning(f"Failed to get cached statistics: {e}")

        return None

    async def _generate_usage_trend(
        self, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Generate usage trend data for dashboard."""
        # Simplified trend generation - would be more sophisticated in production
        trend = []

        # Generate hourly buckets
        current = start_time
        while current < end_time:
            next_hour = current + timedelta(hours=1)

            # Count requests in this hour (simplified)
            request_count = 0
            error_count = 0

            for records in self.recent_usage.values():
                for record in records:
                    if current <= record.timestamp < next_hour:
                        request_count += 1
                        if not record.success:
                            error_count += 1

            trend.append(
                {
                    "timestamp": current.isoformat(),
                    "requests": request_count,
                    "errors": error_count,
                    "success_rate": (
                        (request_count - error_count) / request_count
                        if request_count > 0
                        else 1.0
                    ),
                }
            )

            current = next_hour

        return trend

    async def _aggregation_loop(self):
        """Background task for aggregating statistics."""
        while True:
            try:
                await asyncio.sleep(self.aggregation_interval_minutes * 60)

                # Aggregate statistics for each key
                for key_id in list(self.recent_usage.keys()):
                    await self._aggregate_key_statistics(key_id)

                # Clean up old records from buffer
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=2)
                for key_id in list(self.recent_usage.keys()):
                    self.recent_usage[key_id] = [
                        r
                        for r in self.recent_usage[key_id]
                        if r.timestamp > cutoff_time
                    ]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Aggregation loop error: {e}")

    async def _aggregate_key_statistics(self, key_id: str) -> None:
        """Aggregate statistics for a single key."""
        if not self.cache:
            return

        try:
            # Get recent records
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(minutes=self.aggregation_interval_minutes)

            stats = self._calculate_statistics_from_buffer(
                key_id, window_start, now, None
            )

            # Store in cache
            stats_key = f"usage:stats:{key_id}:all"
            await self.cache.set(
                stats_key,
                json.dumps(stats.model_dump(mode="json")),
                ex=86400,  # 24 hours
            )

            # Also store per-service stats
            services = set(r.service for r in self.recent_usage.get(key_id, []))
            for service in services:
                service_stats = self._calculate_statistics_from_buffer(
                    key_id, window_start, now, service
                )

                service_key = f"usage:stats:{key_id}:{service}"
                await self.cache.set(
                    service_key,
                    json.dumps(service_stats.model_dump(mode="json")),
                    ex=86400,
                )

        except Exception as e:
            logger.error(f"Failed to aggregate statistics for {key_id}: {e}")

    async def _anomaly_detection_loop(self):
        """Background task for anomaly detection."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Check each active key for anomalies
                for key_id in list(self.recent_usage.keys()):
                    alerts = await self.detect_anomalies(key_id)

                    # Store new alerts
                    for alert in alerts:
                        self.active_alerts[alert.alert_id] = alert

                        # Log critical alerts
                        if alert.severity in ["high", "critical"]:
                            logger.warning(
                                f"Anomaly detected: {alert.message}",
                                extra={
                                    "key_id": alert.key_id,
                                    "anomaly_type": alert.anomaly_type,
                                    "severity": alert.severity,
                                    "details": alert.details,
                                },
                            )

                # Clean up old alerts
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                self.active_alerts = {
                    aid: alert
                    for aid, alert in self.active_alerts.items()
                    if alert.created_at > cutoff_time
                }

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Anomaly detection loop error: {e}")
