"""API key monitoring and security service for TripSage Core.

This module provides monitoring, structured logging, and security features for
API key operations in TripSage.
"""

import inspect
import secrets
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from enum import Enum
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field

from tripsage_core.config import Settings, get_settings
from tripsage_core.services.infrastructure.cache_service import (
    CacheService,
    get_cache_service,
)
from tripsage_core.services.infrastructure.database_service import (
    DatabaseService,
    get_database_service,
)
from tripsage_core.types import JSONObject
from tripsage_core.utils.logging_utils import get_logger


# Type hints
P = ParamSpec("P")
ReturnT = TypeVar("ReturnT")

# Create logger
logger = get_logger("key_operations")


class KeyOperation(str, Enum):
    """API key operations for monitoring."""

    CREATE = "create"
    LIST = "list"
    DELETE = "delete"
    VALIDATE = "validate"
    ROTATE = "rotate"
    ACCESS = "access"


class KeyOperationLogEntry(BaseModel):
    """Structured log entry persisted for API key operations."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Event timestamp"
    )
    operation: KeyOperation = Field(description="API key operation type")
    user_id: str = Field(description="User performing the operation")
    key_id: str | None = Field(default=None, description="API key identifier")
    service: str | None = Field(default=None, description="Associated service name")
    success: bool = Field(default=True, description="Whether the operation succeeded")
    metadata: JSONObject = Field(
        default_factory=dict, description="Supplemental operation metadata"
    )
    suspicious: bool = Field(
        default=False, description="Flag indicating suspicious activity"
    )


class KeyOperationAlert(BaseModel):
    """Structured alert entry stored when suspicious activity is detected."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Alert timestamp"
    )
    message: str = Field(description="Human-readable alert message")
    operation: KeyOperation = Field(description="Operation that triggered the alert")
    user_id: str = Field(description="User associated with the alert")
    data: JSONObject = Field(
        default_factory=dict, description="Structured alert payload"
    )


class KeyHealthServiceCount(BaseModel):
    """Service-level API key aggregate."""

    service: str
    count: int


class KeyHealthUserCount(BaseModel):
    """User-level API key aggregate."""

    user_id: str
    count: int


class KeyHealthMetrics(BaseModel):
    """Aggregate metrics for API keys."""

    total_count: int
    service_count: list[KeyHealthServiceCount]
    expired_count: int
    expiring_count: int
    user_count: list[KeyHealthUserCount]
    error: str | None = None


class KeyMonitoringService:
    """Service for monitoring API key operations.

    This service is responsible for monitoring API key operations, detecting
    suspicious patterns, and sending alerts.
    """

    def __init__(self, settings: Settings | None = None):
        """Initialize the key monitoring service.

        Args:
            settings: Application settings or None to use defaults
        """
        self.settings = settings or get_settings()
        self.cache_service: CacheService | None = None
        self.database_service: DatabaseService | None = None
        self.suspicious_patterns: set[str] = set()
        self.alert_threshold = {
            KeyOperation.CREATE: 5,  # 5 creates in 10 minutes
            KeyOperation.DELETE: 5,  # 5 deletes in 10 minutes
            KeyOperation.VALIDATE: 10,  # 10 validations in 10 minutes
            KeyOperation.ROTATE: 3,  # 3 rotations in 10 minutes
        }
        self.pattern_timeframe = 600  # 10 minutes

    async def initialize(self):
        """Initialize the cache and database services."""
        if not self.cache_service:
            self.cache_service = await get_cache_service()
        if not self.database_service:
            self.database_service = await get_database_service()

    async def log_operation(
        self,
        operation: KeyOperation,
        user_id: str,
        *,
        key_id: str | None = None,
        service: str | None = None,
        success: bool = True,
        metadata: JSONObject | None = None,
    ) -> None:
        """Log an API key operation with structured data.

        Args:
            operation: The operation performed
            user_id: The user ID
            key_id: The API key ID (if applicable)
            service: The API service (if applicable)
            success: Whether the operation succeeded
            metadata: Additional metadata for the log
        """
        # Initialize services
        await self.initialize()

        # Validate services for type checkers
        assert self.cache_service is not None

        timestamp = datetime.now(UTC)
        metadata_payload: JSONObject = metadata or {}

        # Store operation in cache for pattern detection
        await self._store_operation_for_pattern_detection(operation, user_id)

        # Check for suspicious patterns
        suspicious = await self._check_suspicious_patterns(operation, user_id)
        if suspicious:
            self.suspicious_patterns.add(f"{user_id}:{operation.value}")

        entry = KeyOperationLogEntry(
            timestamp=timestamp,
            operation=operation,
            user_id=user_id,
            key_id=key_id,
            service=service,
            success=success,
            metadata=metadata_payload,
            suspicious=suspicious,
        )
        log_data = entry.model_dump(mode="json")

        # Log the operation with logging module
        if success:
            logger.info(
                "API key %s",
                operation.value,
                extra=log_data,
            )
        else:
            logger.warning(
                "Failed API key %s",
                operation.value,
                extra=log_data,
            )

        # Store the log in cache for persistence
        log_key = f"key_logs:{user_id}"
        existing_logs_raw = await self.cache_service.get_json(log_key, default=[])
        logs: list[KeyOperationLogEntry] = []
        if isinstance(existing_logs_raw, Sequence) and not isinstance(
            existing_logs_raw, (str, bytes, bytearray)
        ):
            logs.extend(
                KeyOperationLogEntry.model_validate(item)
                for item in existing_logs_raw
                if isinstance(item, Mapping)
            )
        logs.append(entry)
        if len(logs) > 1000:
            logs = logs[-1000:]
        await self.cache_service.set_json(
            log_key,
            [log.model_dump(mode="json") for log in logs],
            ttl=2592000,
        )  # 30 days

        # If this is a suspicious pattern, send an alert
        if suspicious:
            await self._send_alert(operation, user_id, entry)

    async def _store_operation_for_pattern_detection(
        self, operation: KeyOperation, user_id: str
    ) -> None:
        """Store an operation in cache for pattern detection.

        Args:
            operation: The operation performed
            user_id: The user ID
        """
        # Store operation in cache with expiration
        await self.initialize()
        assert self.cache_service is not None
        key = f"key_ops:{user_id}:{operation.value}"
        existing_ops_raw = await self.cache_service.get_json(key, default=[])
        operations: list[str] = []
        if isinstance(existing_ops_raw, list):
            operations = [str(op) for op in existing_ops_raw]
        # Add new timestamp
        operations.append(datetime.now(UTC).isoformat())
        # Keep only recent operations within timeframe
        cutoff_time = datetime.now(UTC) - timedelta(seconds=self.pattern_timeframe)
        operations = [
            op for op in operations if datetime.fromisoformat(op) > cutoff_time
        ]
        # Store back
        await self.cache_service.set_json(key, operations, ttl=self.pattern_timeframe)

    async def _check_suspicious_patterns(
        self, operation: KeyOperation, user_id: str
    ) -> bool:
        """Check for suspicious patterns in API key operations.

        Args:
            operation: The operation performed
            user_id: The user ID

        Returns:
            True if a suspicious pattern is detected, False otherwise
        """
        # Skip for LIST operation
        if operation == KeyOperation.LIST:
            return False

        # Get recent operations from cache
        await self.initialize()
        assert self.cache_service is not None
        key = f"key_ops:{user_id}:{operation.value}"
        operations_raw = await self.cache_service.get_json(key, default=[])
        operations: list[str] = []
        if isinstance(operations_raw, list):
            operations = [str(op) for op in operations_raw]

        # Count operations
        count = len(operations)

        # Check against threshold
        threshold = self.alert_threshold.get(operation, 5)
        return count >= threshold

    async def _send_alert(
        self, operation: KeyOperation, user_id: str, entry: KeyOperationLogEntry
    ) -> None:
        """Send an alert for suspicious key operations.

        Args:
            operation: The operation performed
            user_id: The user ID
            entry: Structured log entry associated with the alert
        """
        # Create alert message
        alert_message = (
            f"ALERT: Suspicious API key {operation.value} activity detected "
            f"for user {user_id}"
        )

        # Log the alert
        logger.exception(
            alert_message,
            extra={
                "operation": operation.value,
                "user_id": user_id,
                "count": entry.metadata.get("count"),
                "timeframe": self.pattern_timeframe,
            },
        )

        # Store the alert in cache
        await self.initialize()
        assert self.cache_service is not None
        alert_key = "key_alerts"
        existing_alerts_raw = await self.cache_service.get_json(alert_key, default=[])
        alerts: list[KeyOperationAlert] = []
        if isinstance(existing_alerts_raw, Sequence) and not isinstance(
            existing_alerts_raw, (str, bytes, bytearray)
        ):
            alerts.extend(
                KeyOperationAlert.model_validate(item)
                for item in existing_alerts_raw
                if isinstance(item, Mapping)
            )
        alerts.append(
            KeyOperationAlert(
                message=alert_message,
                operation=operation,
                user_id=user_id,
                data=entry.model_dump(mode="json"),
            )
        )
        # Keep only last 1000 alerts
        if len(alerts) > 1000:
            alerts = alerts[-1000:]
        await self.cache_service.set_json(
            alert_key,
            [alert.model_dump(mode="json") for alert in alerts],
            ttl=2592000,
        )  # 30 days

    async def get_user_operations(
        self, user_id: str, limit: int = 100
    ) -> list[KeyOperationLogEntry]:
        """Get recent key operations for a user.

        Args:
            user_id: The user ID
            limit: Max number of operations to return

        Returns:
            List of recent key operations
        """
        # Initialize services
        await self.initialize()
        assert self.cache_service is not None

        # Get operations from cache
        log_key = f"key_logs:{user_id}"
        logs_raw = await self.cache_service.get_json(log_key, default=[])
        entries: list[KeyOperationLogEntry] = []
        if isinstance(logs_raw, Sequence) and not isinstance(
            logs_raw, (str, bytes, bytearray)
        ):
            entries.extend(
                KeyOperationLogEntry.model_validate(dict(item))
                for item in logs_raw
                if isinstance(item, Mapping)
            )
        return entries[-limit:] if len(entries) > limit else entries

    async def get_alerts(self, limit: int = 100) -> list[KeyOperationAlert]:
        """Get recent key operation alerts.

        Args:
            limit: Max number of alerts to return

        Returns:
            List of recent alerts
        """
        # Initialize services
        await self.initialize()
        assert self.cache_service is not None

        # Get alerts from cache
        alerts_raw = await self.cache_service.get_json("key_alerts", default=[])
        alerts: list[KeyOperationAlert] = []
        if isinstance(alerts_raw, Sequence) and not isinstance(
            alerts_raw, (str, bytes, bytearray)
        ):
            alerts.extend(
                KeyOperationAlert.model_validate(dict(item))
                for item in alerts_raw
                if isinstance(item, Mapping)
            )
        return alerts[-limit:] if len(alerts) > limit else alerts

    async def is_rate_limited(self, user_id: str, operation: KeyOperation) -> bool:
        """Check if a user is rate limited for an operation.

        Args:
            user_id: The user ID
            operation: The operation to check

        Returns:
            True if rate limited, False otherwise
        """
        # Initialize services
        await self.initialize()
        assert self.cache_service is not None

        # Create a cache key
        rate_limit_key = f"rate_limit:key_ops:{user_id}:{operation.value}"

        # Get current count
        current_count = await self.cache_service.get(rate_limit_key)
        if current_count is None:
            # First operation
            await self.cache_service.set(rate_limit_key, "1", ttl=60)  # 1 minute window
            return False

        # Check if over limit
        count = int(current_count)
        if count >= 10:  # 10 operations per minute
            return True

        # Increment counter
        await self.cache_service.incr(rate_limit_key)
        return False


def monitor_key_operation(
    operation: KeyOperation,
) -> Callable[[Callable[P, Awaitable[ReturnT]]], Callable[P, Awaitable[ReturnT]]]:
    """Decorator to monitor API key operations."""

    def decorator(
        func: Callable[P, Awaitable[ReturnT]],
    ) -> Callable[P, Awaitable[ReturnT]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> ReturnT:
            # Get monitoring service from args or kwargs
            monitoring_service: KeyMonitoringService | None = None
            for arg in args:
                if isinstance(arg, KeyMonitoringService):
                    monitoring_service = arg
                    break

            if not monitoring_service:
                for value in kwargs.values():
                    if isinstance(value, KeyMonitoringService):
                        monitoring_service = value
                        break

            if not monitoring_service:
                # Create a new monitoring service if not found
                monitoring_service = KeyMonitoringService()

            # Get user ID from args or kwargs
            user_id = cast(str | None, kwargs.get("user_id"))
            if not user_id:
                # Try to find it in args using inspection
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                for i, param in enumerate(params):
                    if param == "user_id" and i < len(args):
                        user_id = cast(str | None, args[i])
                        break

            # Get key ID from args or kwargs
            key_id = cast(str | None, kwargs.get("key_id"))
            if not key_id:
                # Try to find it in args using inspection
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                for i, param in enumerate(params):
                    if param == "key_id" and i < len(args):
                        key_id = cast(str | None, args[i])
                        break

            # Get service from args or kwargs
            service = cast(str | None, kwargs.get("service"))
            key_data_obj = kwargs.get("key_data")
            if (
                not service
                and key_data_obj is not None
                and hasattr(key_data_obj, "service")
            ):
                service = cast(str | None, getattr(key_data_obj, "service", None))

            # Execute the function
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                success = True
            except (
                ValueError,
                PermissionError,
                LookupError,
                RuntimeError,
                TypeError,
            ) as e:
                success = False
                if monitoring_service and user_id:
                    await monitoring_service.log_operation(
                        operation=operation,
                        user_id=user_id,
                        key_id=key_id,
                        service=service,
                        success=False,
                        metadata={"error": str(e)},
                    )
                raise

            # Log the operation
            if monitoring_service and user_id:
                # Calculate execution time
                execution_time = time.time() - start_time

                # Log the operation
                await monitoring_service.log_operation(
                    operation=operation,
                    user_id=user_id,
                    key_id=key_id,
                    service=service,
                    success=success,
                    metadata={"execution_time": execution_time},
                )

            return result

        return wrapper

    return decorator


def secure_random_token(length: int = 64) -> str:
    """Generate a secure random token.

    Args:
        length: The length of the token in bytes

    Returns:
        A secure random token
    """
    return secrets.token_hex(length // 2)


def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time.

    This function compares two strings in a way that is resistant to
    timing attacks, which is important for comparing sensitive values
    like API keys.

    Args:
        a: First string
        b: Second string

    Returns:
        True if the strings are equal, False otherwise
    """
    return secrets.compare_digest(a.encode(), b.encode())


def clear_sensitive_data(data: JSONObject, keys: list[str]) -> JSONObject:
    """Clear sensitive data from a dictionary.

    Args:
        data: Dictionary containing sensitive data
        keys: Keys of sensitive data to clear

    Returns:
        Dictionary with sensitive data cleared
    """
    result = data.copy()
    for key in keys:
        if key in result:
            result[key] = "[REDACTED]"
    return result


async def check_key_expiration(
    monitoring_service: KeyMonitoringService, days_before: int = 7
) -> list[JSONObject]:
    """Check for API keys that are about to expire.

    Args:
        monitoring_service: Key monitoring service
        days_before: Days before expiration to check

    Returns:
        List of keys that are about to expire
    """
    # Initialize services
    await monitoring_service.initialize()

    # Get date threshold
    threshold = datetime.now(UTC) + timedelta(days=days_before)

    # Get expiring keys from database
    from tripsage_core.exceptions.exceptions import CoreServiceError

    assert monitoring_service.database_service is not None
    try:
        result = await monitoring_service.database_service.select(
            "api_keys",
            "*",
            filters={"expires_at": {"lte": threshold.isoformat()}},
        )
        return list(result) if result else []
    except CoreServiceError:
        logger.exception("Failed to check key expiration")
        return []


async def get_key_health_metrics() -> KeyHealthMetrics:
    """Get health metrics for API keys.

    Returns:
        Dictionary with key health metrics
    """
    # Get database service
    from tripsage_core.exceptions.exceptions import CoreServiceError

    try:
        db_service = await get_database_service()

        # Get total count of keys
        total_count = await db_service.count("api_keys")

        # Get count of keys by service
        service_result = await db_service.select("api_keys", "service")
        service_count: dict[str, int] = {}
        if service_result:
            for mapping in service_result:
                service = str(mapping.get("service", "unknown"))
                service_count[service] = service_count.get(service, 0) + 1

        # Get count of expired keys
        now = datetime.now(UTC)
        expired_count = await db_service.count(
            "api_keys", {"expires_at": {"lte": now.isoformat()}}
        )

        # Get count of keys expiring in next 30 days
        future_date = now + timedelta(days=30)
        expiring_result = await db_service.select(
            "api_keys",
            "*",
            filters={
                "expires_at": {
                    "gt": now.isoformat(),
                    "lte": future_date.isoformat(),
                }
            },
        )
        expiring_count = len(expiring_result) if expiring_result else 0

        # Get count of keys by user
        user_result = await db_service.select("api_keys", "user_id")
        user_count: dict[str, int] = {}
        if user_result:
            for mapping in user_result:
                user_id = str(mapping.get("user_id", "unknown"))
                user_count[user_id] = user_count.get(user_id, 0) + 1

        return KeyHealthMetrics(
            total_count=total_count,
            service_count=[
                KeyHealthServiceCount(service=service, count=count)
                for service, count in service_count.items()
            ],
            expired_count=expired_count,
            expiring_count=expiring_count,
            user_count=[
                KeyHealthUserCount(user_id=user, count=count)
                for user, count in user_count.items()
            ],
        )

    except CoreServiceError:
        logger.exception("Failed to get key health metrics")
        return KeyHealthMetrics(
            total_count=0,
            service_count=[],
            expired_count=0,
            expiring_count=0,
            user_count=[],
            error="database_error",
        )
