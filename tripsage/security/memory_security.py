"""Security implementation for memory service.

This module provides encryption, rate limiting, audit logging, and access controls
for the memory service to ensure data privacy and security.
"""

import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional, Set

from cryptography.fernet import Fernet
from pydantic import BaseModel, Field

from tripsage.monitoring.telemetry import get_telemetry
from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure import get_cache_service
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)
settings = get_settings()
telemetry = get_telemetry()


class SecurityConfig(BaseModel):
    """Security configuration for memory service."""

    encryption_enabled: bool = Field(default=True, description="Enable encryption at rest")
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    audit_enabled: bool = Field(default=True, description="Enable audit logging")

    # Rate limiting settings
    rate_limit_window: int = Field(default=3600, description="Rate limit window in seconds")
    rate_limit_max_requests: int = Field(default=100, description="Max requests per window")
    rate_limit_burst: int = Field(default=10, description="Burst allowance")

    # Encryption settings
    encryption_key: Optional[str] = Field(default=None, description="Base64 encoded encryption key")

    # Access control settings
    allowed_operations: Set[str] = Field(
        default={"search", "add", "update", "delete"},
        description="Allowed memory operations",
    )
    sensitive_fields: Set[str] = Field(
        default={"personal_info", "financial_data", "health_info"},
        description="Fields requiring extra protection",
    )


class AuditLog(BaseModel):
    """Audit log entry for memory operations."""

    timestamp: datetime
    user_id: str
    operation: str
    resource_id: Optional[str] = None
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    session_id: Optional[str] = None


class MemoryEncryption:
    """Handles encryption/decryption of memory content."""

    def __init__(self, key: Optional[str] = None):
        """Initialize encryption with key.

        Args:
            key: Base64 encoded encryption key, generates new if None
        """
        if key:
            self.cipher = Fernet(key.encode())
        else:
            # Generate new key if none provided
            self.cipher = Fernet(Fernet.generate_key())

    def encrypt(self, content: str) -> str:
        """Encrypt memory content.

        Args:
            content: Plain text content

        Returns:
            Encrypted content as base64 string
        """
        return self.cipher.encrypt(content.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        """Decrypt memory content.

        Args:
            encrypted: Encrypted content

        Returns:
            Decrypted plain text
        """
        return self.cipher.decrypt(encrypted.encode()).decode()

    def encrypt_dict(self, data: Dict[str, Any], fields: Set[str]) -> Dict[str, Any]:
        """Encrypt specific fields in dictionary.

        Args:
            data: Dictionary to process
            fields: Fields to encrypt

        Returns:
            Dictionary with encrypted fields
        """
        result = data.copy()
        for field in fields:
            if field in result and isinstance(result[field], str):
                result[field] = self.encrypt(result[field])
        return result

    def decrypt_dict(self, data: Dict[str, Any], fields: Set[str]) -> Dict[str, Any]:
        """Decrypt specific fields in dictionary.

        Args:
            data: Dictionary to process
            fields: Fields to decrypt

        Returns:
            Dictionary with decrypted fields
        """
        result = data.copy()
        for field in fields:
            if field in result and isinstance(result[field], str):
                try:
                    result[field] = self.decrypt(result[field])
                except Exception:
                    # Field might not be encrypted, leave as is
                    pass
        return result


class RateLimiter:
    """Token bucket rate limiter for memory operations."""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.buckets: Dict[str, Dict[str, Any]] = defaultdict(self._create_bucket)

    def _create_bucket(self) -> Dict[str, Any]:
        """Create a new token bucket."""
        return {
            "tokens": self.config.rate_limit_burst,
            "last_update": time.time(),
        }

    async def check_rate_limit(self, user_id: str, operation: str) -> bool:
        """Check if operation is allowed under rate limit.

        Args:
            user_id: User identifier
            operation: Operation being performed

        Returns:
            True if allowed, False if rate limited
        """
        if not self.config.rate_limit_enabled:
            return True

        key = f"{user_id}:{operation}"
        bucket = self.buckets[key]

        # Update tokens based on time passed
        now = time.time()
        time_passed = now - bucket["last_update"]
        bucket["last_update"] = now

        # Add tokens based on time (token/second rate)
        rate = self.config.rate_limit_max_requests / self.config.rate_limit_window
        bucket["tokens"] = min(self.config.rate_limit_burst, bucket["tokens"] + (time_passed * rate))

        # Check if we have tokens
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1

            # Cache the rate limit state
            cache = await get_cache_service()
            await cache.set(
                f"rate_limit:{key}",
                json.dumps(bucket),
                ex=self.config.rate_limit_window,
            )

            return True

        # Log rate limit hit
        logger.warning(f"Rate limit hit for user {user_id} on operation {operation}")
        telemetry.record_memory_operation(
            operation=operation,
            duration_ms=0,
            user_id=user_id,
            success=False,
            error="rate_limited",
        )

        return False


class AuditLogger:
    """Handles audit logging for memory operations."""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.cache_service = None

    async def log(
        self,
        user_id: str,
        operation: str,
        success: bool,
        resource_id: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log an audit entry.

        Args:
            user_id: User performing operation
            operation: Operation name
            success: Whether operation succeeded
            resource_id: Optional resource identifier
            error: Optional error message
            metadata: Optional additional metadata
            ip_address: Optional IP address
            session_id: Optional session ID
        """
        if not self.config.audit_enabled:
            return

        audit_entry = AuditLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            operation=operation,
            resource_id=resource_id,
            success=success,
            error=error,
            metadata=metadata or {},
            ip_address=ip_address,
            session_id=session_id,
        )

        # Store in cache for quick access
        if not self.cache_service:
            self.cache_service = await get_cache_service()

        key = f"audit:{user_id}:{int(time.time())}"
        await self.cache_service.set(
            key,
            audit_entry.model_dump_json(),
            ex=86400 * 30,  # Keep for 30 days
        )

        # Log to monitoring
        logger.info(f"Audit: {audit_entry.model_dump_json()}")

        # Check for suspicious patterns
        await self._check_suspicious_patterns(user_id, operation)

    async def _check_suspicious_patterns(self, user_id: str, operation: str) -> None:
        """Check for suspicious access patterns.

        Args:
            user_id: User to check
            operation: Current operation
        """
        # Get recent operations
        # Pattern would be f"audit:{user_id}:*"
        # Implement pattern checking logic here

        # Example: Check for rapid operations
        now = int(time.time())
        count = 0

        for i in range(60):  # Check last minute
            key = f"audit:{user_id}:{now - i}"
            if await self.cache_service.exists(key):
                count += 1

        if count > 20:  # More than 20 operations in a minute
            logger.warning(f"Suspicious activity detected for user {user_id}: {count} operations in 60s")
            telemetry.record_memory_operation(
                operation="suspicious_activity",
                duration_ms=0,
                user_id=user_id,
                success=False,
                error=f"high_frequency_access:{count}",
            )


class MemorySecurity:
    """Main security service for memory operations."""

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self.encryption = MemoryEncryption(self.config.encryption_key)
        self.rate_limiter = RateLimiter(self.config)
        self.audit_logger = AuditLogger(self.config)

    def sanitize_input(self, text: str) -> str:
        """Sanitize user input to prevent injection attacks.

        Args:
            text: Input text to sanitize

        Returns:
            Sanitized text
        """
        # Remove potential SQL injection patterns
        dangerous_patterns = [
            "';",
            '";',
            "--",
            "/*",
            "*/",
            "xp_",
            "sp_",
            "DROP",
            "DELETE",
            "INSERT",
            "UPDATE",
            "EXEC",
            "<script",
            "</script>",
            "javascript:",
            "onerror=",
        ]

        sanitized = text
        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern.lower(), "")
            sanitized = sanitized.replace(pattern.upper(), "")

        # Limit length to prevent DoS
        max_length = 10000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized.strip()

    def validate_operation(self, operation: str) -> bool:
        """Validate if operation is allowed.

        Args:
            operation: Operation to validate

        Returns:
            True if allowed, False otherwise
        """
        return operation in self.config.allowed_operations

    def hash_user_id(self, user_id: str) -> str:
        """Hash user ID for privacy.

        Args:
            user_id: Original user ID

        Returns:
            Hashed user ID
        """
        return hashlib.sha256(f"{user_id}:{settings.secret_key}".encode()).hexdigest()

    async def secure_operation(
        self,
        operation: str,
        user_id: str,
        func: Callable,
        *args,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Execute operation with security checks.

        Args:
            operation: Operation name
            user_id: User identifier
            func: Function to execute
            args: Function arguments
            ip_address: Optional IP address
            session_id: Optional session ID
            kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            SecurityError: If security check fails
        """
        # Validate operation
        if not self.validate_operation(operation):
            raise SecurityError(f"Operation '{operation}' not allowed")

        # Check rate limit
        if not await self.rate_limiter.check_rate_limit(user_id, operation):
            raise SecurityError("Rate limit exceeded")

        # Execute with monitoring
        start_time = time.time()
        success = False
        error = None
        result = None

        try:
            with telemetry.span(f"secure_{operation}", {"user_id": user_id}):
                result = await func(*args, **kwargs)
                success = True
                return result

        except Exception as e:
            error = str(e)
            raise

        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Record telemetry
            telemetry.record_memory_operation(
                operation=operation,
                duration_ms=duration_ms,
                user_id=user_id,
                success=success,
                error=error,
            )

            # Audit log
            await self.audit_logger.log(
                user_id=user_id,
                operation=operation,
                success=success,
                error=error,
                metadata={"duration_ms": duration_ms},
                ip_address=ip_address,
                session_id=session_id,
            )


class SecurityError(Exception):
    """Security-related error."""

    pass


# Decorator for securing functions
def secure_memory_operation(operation: str):
    """Decorator to secure memory operations.

    Args:
        operation: Operation name

    Example:
        @secure_memory_operation("search")
        async def search_memories(user_id: str, query: str):
            # Function implementation
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from arguments
            user_id = kwargs.get("user_id")
            if not user_id and len(args) > 0:
                user_id = args[0]

            if not user_id:
                raise SecurityError("User ID required for security checks")

            # Get security service
            security = MemorySecurity()

            # Execute with security
            return await security.secure_operation(operation, user_id, func, *args, **kwargs)

        return wrapper

    return decorator
