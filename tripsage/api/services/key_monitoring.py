"""Monitoring and security for API key operations.

This module provides monitoring, structured logging, and security features for
API key operations in TripSage.
"""

import inspect
import secrets
import time
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, cast

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from starlette.types import ASGIApp

from tripsage.api.core.config import Settings, get_settings
from tripsage.mcp_abstraction import mcp_manager

# Type hints
F = TypeVar("F", bound=Callable[..., Any])

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

# Create logger
logger = structlog.get_logger("key_operations")


class KeyOperation(str, Enum):
    """API key operations for monitoring."""

    CREATE = "create"
    LIST = "list"
    DELETE = "delete"
    VALIDATE = "validate"
    ROTATE = "rotate"
    ACCESS = "access"


class KeyMonitoringService:
    """Service for monitoring API key operations.

    This service is responsible for monitoring API key operations, detecting
    suspicious patterns, and sending alerts.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the key monitoring service.

        Args:
            settings: Application settings or None to use defaults
        """
        self.settings = settings or get_settings()
        self.redis_mcp = None
        self.suspicious_patterns: Set[str] = set()
        self.alert_threshold = {
            KeyOperation.CREATE: 5,  # 5 creates in 10 minutes
            KeyOperation.DELETE: 5,  # 5 deletes in 10 minutes
            KeyOperation.VALIDATE: 10,  # 10 validations in 10 minutes
            KeyOperation.ROTATE: 3,  # 3 rotations in 10 minutes
        }
        self.pattern_timeframe = 600  # 10 minutes

    async def initialize(self):
        """Initialize the Redis MCP client."""
        if not self.redis_mcp:
            self.redis_mcp = await mcp_manager.initialize_mcp("redis")

    async def log_operation(
        self,
        operation: KeyOperation,
        user_id: str,
        key_id: Optional[str] = None,
        service: Optional[str] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
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
        # Initialize Redis MCP
        await self.initialize()

        # Create a log entry
        log_data = {
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "operation": operation,
            "user_id": user_id,
            "key_id": key_id,
            "service": service,
            "success": success,
            "metadata": metadata or {},
        }

        # Store operation in Redis for pattern detection
        await self._store_operation_for_pattern_detection(operation, user_id)

        # Check for suspicious patterns
        suspicious = await self._check_suspicious_patterns(operation, user_id)
        if suspicious:
            log_data["suspicious"] = True
            self.suspicious_patterns.add(f"{user_id}:{operation}")

        # Log the operation with structlog
        if success:
            logger.info(
                f"API key {operation}",
                **log_data,
            )
        else:
            logger.warning(
                f"Failed API key {operation}",
                **log_data,
            )

        # Store the log in Redis for persistence
        await self.redis_mcp.invoke_method(
            "list_push",
            params={
                "key": f"key_logs:{user_id}",
                "value": log_data,
                "ttl": 2592000,  # 30 days
            },
        )

        # If this is a suspicious pattern, send an alert
        if suspicious:
            await self._send_alert(operation, user_id, log_data)

    async def _store_operation_for_pattern_detection(
        self, operation: KeyOperation, user_id: str
    ) -> None:
        """Store an operation in Redis for pattern detection.

        Args:
            operation: The operation performed
            user_id: The user ID
        """
        # Store operation in Redis with expiration
        key = f"key_ops:{user_id}:{operation}"
        await self.redis_mcp.invoke_method(
            "list_push",
            params={
                "key": key,
                "value": datetime.now(datetime.UTC).isoformat(),
                "ttl": self.pattern_timeframe,  # 10 minutes
            },
        )

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

        # Get recent operations from Redis
        key = f"key_ops:{user_id}:{operation}"
        result = await self.redis_mcp.invoke_method(
            "list_get",
            params={"key": key},
        )

        # Count operations
        operations = result.get("data", [])
        count = len(operations)

        # Check against threshold
        threshold = self.alert_threshold.get(operation, 5)
        return count >= threshold

    async def _send_alert(
        self, operation: KeyOperation, user_id: str, log_data: Dict[str, Any]
    ) -> None:
        """Send an alert for suspicious key operations.

        Args:
            operation: The operation performed
            user_id: The user ID
            log_data: The log data for the operation
        """
        # Create alert message
        alert_message = (
            f"ALERT: Suspicious API key {operation} activity "
            f"detected for user {user_id}"
        )

        # Log the alert
        logger.error(
            alert_message,
            operation=operation,
            user_id=user_id,
            count=log_data.get("count"),
            timeframe=self.pattern_timeframe,
        )

        # Store the alert in Redis
        await self.redis_mcp.invoke_method(
            "list_push",
            params={
                "key": "key_alerts",
                "value": {
                    "timestamp": datetime.now(datetime.UTC).isoformat(),
                    "message": alert_message,
                    "operation": operation,
                    "user_id": user_id,
                    "data": log_data,
                },
                "ttl": 2592000,  # 30 days
            },
        )

    async def get_user_operations(
        self, user_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent key operations for a user.

        Args:
            user_id: The user ID
            limit: Max number of operations to return

        Returns:
            List of recent key operations
        """
        # Initialize Redis MCP
        await self.initialize()

        # Get operations from Redis
        result = await self.redis_mcp.invoke_method(
            "list_get",
            params={"key": f"key_logs:{user_id}", "limit": limit},
        )

        return result.get("data", [])

    async def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent key operation alerts.

        Args:
            limit: Max number of alerts to return

        Returns:
            List of recent alerts
        """
        # Initialize Redis MCP
        await self.initialize()

        # Get alerts from Redis
        result = await self.redis_mcp.invoke_method(
            "list_get",
            params={"key": "key_alerts", "limit": limit},
        )

        return result.get("data", [])

    async def is_rate_limited(self, user_id: str, operation: KeyOperation) -> bool:
        """Check if a user is rate limited for an operation.

        Args:
            user_id: The user ID
            operation: The operation to check

        Returns:
            True if rate limited, False otherwise
        """
        # Initialize Redis MCP
        await self.initialize()

        # Create a Redis key
        redis_key = f"rate_limit:key_ops:{user_id}:{operation}"

        # Use Redis MCP to check and update rate limit
        result = await self.redis_mcp.invoke_method(
            "rate_limit",
            params={
                "key": redis_key,
                "limit": 10,  # 10 operations per minute
                "window": 60,  # 1 minute
            },
        )

        return result.get("limited", False)


class KeyOperationRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting API key operations.

    This middleware specifically rate limits API key operations,
    using more strict limits than the general API rate limiting.
    """

    def __init__(
        self,
        app: ASGIApp,
        monitoring_service: KeyMonitoringService,
        settings: Optional[Settings] = None,
    ):
        """Initialize the middleware.

        Args:
            app: The ASGI application
            monitoring_service: The key monitoring service
            settings: API settings or None to use the default
        """
        super().__init__(app)
        self.monitoring_service = monitoring_service
        self.settings = settings or get_settings()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process the request/response and handle rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the next middleware or endpoint
        """
        # Check if this is a key operation
        key_operation = self._get_key_operation(request)
        if not key_operation:
            return await call_next(request)

        # Get user ID
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            return await call_next(request)

        # Check if rate limited
        is_limited = await self.monitoring_service.is_rate_limited(
            user_id, key_operation
        )
        if is_limited:
            # Log the rate limit
            await self.monitoring_service.log_operation(
                operation=key_operation,
                user_id=user_id,
                success=False,
                metadata={"rate_limited": True},
            )

            # Return rate limit response
            return Response(
                content="Rate limit exceeded for API key operations",
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "60"},
            )

        # Process the request
        response = await call_next(request)

        return response

    def _get_key_operation(self, request: Request) -> Optional[KeyOperation]:
        """Get the key operation from the request.

        Args:
            request: The incoming request

        Returns:
            The key operation or None if not a key operation
        """
        path = request.url.path
        method = request.method

        # Check if this is a key operation
        if not path.startswith("/api/user/keys"):
            return None

        # Determine the operation based on path and method
        if path == "/api/user/keys" or path == "/api/user/keys/":
            if method == "GET":
                return KeyOperation.LIST
            elif method == "POST":
                return KeyOperation.CREATE
        elif path == "/api/user/keys/validate" or path == "/api/user/keys/validate/":
            if method == "POST":
                return KeyOperation.VALIDATE
        elif path.endswith("/rotate"):
            if method == "POST":
                return KeyOperation.ROTATE
        elif "/api/user/keys/" in path:  # Key ID in path
            if method == "DELETE":
                return KeyOperation.DELETE

        return None


def monitor_key_operation(
    operation: KeyOperation,
) -> Callable[[F], F]:
    """Decorator to monitor API key operations.

    This decorator logs API key operations and checks for suspicious patterns.

    Args:
        operation: The operation to monitor

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get monitoring service from args or kwargs
            monitoring_service = None
            for arg in args:
                if isinstance(arg, KeyMonitoringService):
                    monitoring_service = arg
                    break

            if not monitoring_service:
                for _, value in kwargs.items():
                    if isinstance(value, KeyMonitoringService):
                        monitoring_service = value
                        break

            if not monitoring_service:
                # Create a new monitoring service if not found
                monitoring_service = KeyMonitoringService()

            # Get user ID from args or kwargs
            user_id = kwargs.get("user_id")
            if not user_id:
                # Try to find it in args using inspection
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                for i, param in enumerate(params):
                    if param == "user_id" and i < len(args):
                        user_id = args[i]
                        break

            # Get key ID from args or kwargs
            key_id = kwargs.get("key_id")
            if not key_id:
                # Try to find it in args using inspection
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                for i, param in enumerate(params):
                    if param == "key_id" and i < len(args):
                        key_id = args[i]
                        break

            # Get service from args or kwargs
            service = kwargs.get("service")
            if not service and "key_data" in kwargs:
                # Try to get service from key_data
                if hasattr(kwargs["key_data"], "service"):
                    service = kwargs["key_data"].service

            # Execute the function
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                # Log the error with the monitoring service
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

        return cast(F, wrapper)

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


def clear_sensitive_data(data: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
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
) -> List[Dict[str, Any]]:
    """Check for API keys that are about to expire.

    Args:
        monitoring_service: Key monitoring service
        days_before: Days before expiration to check

    Returns:
        List of keys that are about to expire
    """
    # Initialize Redis MCP
    await monitoring_service.initialize()

    # Get date threshold
    threshold = datetime.now(datetime.UTC) + timedelta(days=days_before)

    # Use Supabase MCP to get expiring keys
    supabase_mcp = await mcp_manager.initialize_mcp("supabase")
    result = await supabase_mcp.invoke_method(
        "query",
        params={
            "table": "api_keys",
            "query": {
                "expires_at": f"lte.{threshold.isoformat()}",
                "select": "*",
            },
        },
    )

    if not result or not result.get("data"):
        return []

    return result["data"]


async def get_key_health_metrics() -> Dict[str, Any]:
    """Get health metrics for API keys.

    Returns:
        Dictionary with key health metrics
    """
    # Use Supabase MCP to get key metrics
    supabase_mcp = await mcp_manager.initialize_mcp("supabase")

    # Get total count of keys
    total_count = await supabase_mcp.invoke_method(
        "query",
        params={
            "table": "api_keys",
            "query": {"count": "exact"},
        },
    )

    # Get count of keys by service
    service_count = await supabase_mcp.invoke_method(
        "query",
        params={
            "table": "api_keys",
            "query": {"select": "service", "count": "exact", "group_by": "service"},
        },
    )

    # Get count of expired keys
    expired_count = await supabase_mcp.invoke_method(
        "query",
        params={
            "table": "api_keys",
            "query": {
                "expires_at": f"lte.{datetime.now(datetime.UTC).isoformat()}",
                "count": "exact",
            },
        },
    )

    # Get count of keys expiring in next 30 days
    now = datetime.now(datetime.UTC)
    future_date = now + timedelta(days=30)
    expiring_count = await supabase_mcp.invoke_method(
        "query",
        params={
            "table": "api_keys",
            "query": {
                "expires_at": (
                    f"gt.{now.isoformat()} and lte.{future_date.isoformat()}"
                ),
                "count": "exact",
            },
        },
    )

    # Get count of keys by user
    user_count = await supabase_mcp.invoke_method(
        "query",
        params={
            "table": "api_keys",
            "query": {"select": "user_id", "count": "exact", "group_by": "user_id"},
        },
    )

    return {
        "total_count": total_count.get("count", 0) if total_count else 0,
        "service_count": service_count.get("data", []) if service_count else [],
        "expired_count": expired_count.get("count", 0) if expired_count else 0,
        "expiring_count": expiring_count.get("count", 0) if expiring_count else 0,
        "user_count": user_count.get("data", []) if user_count else [],
    }
