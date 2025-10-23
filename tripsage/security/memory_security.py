"""Security implementation for memory service.

This module provides encryption, rate limiting, audit logging, and access controls
for the memory service to ensure data privacy and security.
"""

import hashlib
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field

from tripsage_core.config import get_settings
from tripsage_core.observability.otel import get_meter, get_tracer
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)
settings = get_settings()
_tracer = get_tracer("tripsage.security.memory")
_meter = get_meter("tripsage.security.memory")
_op_counter = _meter.create_counter(
    "memory.operation.count", unit="1", description="Total memory operations"
)
_op_duration = _meter.create_histogram(
    "memory.operation.duration", unit="ms", description="Memory operation duration"
)


class SecurityConfig(BaseModel):
    """Security configuration for memory service."""

    encryption_enabled: bool = Field(
        default=True, description="Enable encryption at rest"
    )
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    audit_enabled: bool = Field(default=True, description="Enable audit logging")

    # Rate limiting settings
    rate_limit_window: int = Field(
        default=3600, description="Rate limit window in seconds"
    )
    rate_limit_max_requests: int = Field(
        default=100, description="Max requests per window"
    )
    rate_limit_burst: int = Field(default=10, description="Burst allowance")

    # Encryption settings
    encryption_key: str | None = Field(
        default=None, description="Base64 encoded encryption key"
    )

    # Access control settings
    allowed_operations: set[str] = Field(
        default={"search", "add", "update", "delete"},
        description="Allowed memory operations",
    )
    sensitive_fields: set[str] = Field(
        default={"personal_info", "financial_data", "health_info"},
        description="Fields requiring extra protection",
    )


class MemoryEncryption:
    """Handles encryption/decryption of memory content."""

    def __init__(self, key: str | None = None):
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

    def encrypt_dict(self, data: dict[str, Any], fields: set[str]) -> dict[str, Any]:
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

    def decrypt_dict(self, data: dict[str, Any], fields: set[str]) -> dict[str, Any]:
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
                except InvalidToken as decrypt_error:
                    logger.debug(
                        "Skipping decryption for field '%s': %s",
                        field,
                        decrypt_error,
                    )
                    # Field might not be encrypted, leave as is
        return result


from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditSeverity,
    audit_security_event,
)


class MemorySecurity:
    """Main security service for memory operations."""

    def __init__(self, config: SecurityConfig | None = None):
        """Initialize memory security components."""
        self.config = config or SecurityConfig()
        self.encryption = MemoryEncryption(self.config.encryption_key)
        # Rate limiting is centralized in API middleware; remove local limiter.

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
        ip_address: str | None = None,
        session_id: str | None = None,
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

        # Execute with monitoring
        start_time = time.time()
        success = False
        error = None
        result = None

        try:
            with _tracer.start_as_current_span(f"secure_{operation}") as span:
                span.set_attribute("enduser.id", user_id)
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
            attrs = {
                "operation": operation,
                "user_id": user_id,
                "success": "true" if success else "false",
            }
            if error:
                attrs["error"] = error
            _op_counter.add(1, attrs)
            _op_duration.record(duration_ms, attrs)
            # Centralized audit logging
            if self.config.audit_enabled:
                try:
                    await audit_security_event(
                        event_type=AuditEventType.DATA_ACCESS
                        if success
                        else AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY,
                        severity=AuditSeverity.INFORMATIONAL
                        if success
                        else AuditSeverity.LOW,
                        message=f"memory.{operation}",
                        actor_id=user_id,
                        ip_address=ip_address or "unknown",
                        target_resource="memory",
                        risk_score=None if success else 20,
                        duration_ms=duration_ms,
                        session_id=session_id,
                    )
                except Exception:  # noqa: BLE001 - do not break flow on audit failures
                    logger.debug(
                        "Audit logging failed for memory operation %s", operation
                    )


class SecurityError(Exception):
    """Security-related error."""


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
            return await security.secure_operation(
                operation, user_id, func, *args, **kwargs
            )

        return wrapper

    return decorator
