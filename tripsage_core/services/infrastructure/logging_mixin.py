"""Logging mixin for standardized logging patterns across services.

This mixin provides common logging methods with structured logging support
and consistent formatting across all TripSage services.
"""

import logging
from typing import Any


logger = logging.getLogger(__name__)


class LoggingMixin:
    """Mixin providing standardized logging patterns."""

    @property
    def logger(self) -> logging.Logger:
        """Get the logger for this class."""
        return logging.getLogger(self.__class__.__module__)

    def log_operation_start(
        self,
        operation: str,
        user_id: str | None = None,
        entity_id: str | None = None,
        **extra: Any,
    ) -> None:
        """Log the start of an operation.

        Args:
            operation: Name of the operation
            user_id: User ID if applicable
            entity_id: Entity ID if applicable
            **extra: Additional structured data
        """
        log_data: dict[str, Any] = {"operation": operation}
        if user_id:
            log_data["user_id"] = user_id
        if entity_id:
            log_data["entity_id"] = entity_id
        log_data.update(extra)

        self.logger.info("Starting %s", operation, extra=log_data)

    def log_operation_success(
        self,
        operation: str,
        user_id: str | None = None,
        entity_id: str | None = None,
        duration_ms: float | None = None,
        **extra: Any,
    ) -> None:
        """Log successful completion of an operation.

        Args:
            operation: Name of the operation
            user_id: User ID if applicable
            entity_id: Entity ID if applicable
            duration_ms: Operation duration in milliseconds
            **extra: Additional structured data
        """
        log_data: dict[str, Any] = {"operation": operation, "success": True}
        if user_id:
            log_data["user_id"] = user_id
        if entity_id:
            log_data["entity_id"] = entity_id
        if duration_ms is not None:
            log_data["duration_ms"] = duration_ms
        log_data.update(extra)

        self.logger.info("Completed %s", operation, extra=log_data)

    def log_operation_failure(
        self,
        operation: str,
        error: Exception,
        user_id: str | None = None,
        entity_id: str | None = None,
        **extra: Any,
    ) -> None:
        """Log failure of an operation.

        Args:
            operation: Name of the operation
            error: The exception that occurred
            user_id: User ID if applicable
            entity_id: Entity ID if applicable
            **extra: Additional structured data
        """
        log_data: dict[str, Any] = {
            "operation": operation,
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
        }
        if user_id:
            log_data["user_id"] = user_id
        if entity_id:
            log_data["entity_id"] = entity_id
        log_data.update(extra)

        self.logger.exception("Failed %s", operation, extra=log_data)

    def log_entity_not_found(
        self, entity_type: str, entity_id: str, user_id: str | None = None, **extra: Any
    ) -> None:
        """Log when an entity is not found.

        Args:
            entity_type: Type of entity (e.g., 'flight_booking')
            entity_id: ID of the entity
            user_id: User ID if applicable
            **extra: Additional structured data
        """
        log_data: dict[str, Any] = {"entity_type": entity_type, "entity_id": entity_id}
        if user_id:
            log_data["user_id"] = user_id
        log_data.update(extra)

        self.logger.warning("%s not found", entity_type, extra=log_data)

    def log_validation_error(
        self, operation: str, error: Exception, user_id: str | None = None, **extra: Any
    ) -> None:
        """Log validation errors.

        Args:
            operation: Name of the operation
            error: The validation exception
            user_id: User ID if applicable
            **extra: Additional structured data
        """
        log_data: dict[str, Any] = {
            "operation": operation,
            "error": str(error),
            "error_type": "validation_error",
        }
        if user_id:
            log_data["user_id"] = user_id
        log_data.update(extra)

        self.logger.warning("Validation failed for %s", operation, extra=log_data)

    def log_external_api_call(
        self,
        service: str,
        operation: str,
        success: bool,
        latency_ms: float | None = None,
        **extra: Any,
    ) -> None:
        """Log external API calls.

        Args:
            service: External service name
            operation: API operation
            success: Whether the call succeeded
            latency_ms: Call latency in milliseconds
            **extra: Additional structured data
        """
        log_data: dict[str, Any] = {
            "service": service,
            "operation": operation,
            "success": success,
        }
        if latency_ms is not None:
            log_data["latency_ms"] = latency_ms
        log_data.update(extra)

        level = logging.INFO if success else logging.WARNING
        self.logger.log(
            level,
            "External API call to %s.%s",
            service,
            operation,
            extra=log_data,
        )

    def log_cache_hit(
        self, cache_key: str, operation: str, user_id: str | None = None, **extra: Any
    ) -> None:
        """Log cache hits.

        Args:
            cache_key: Cache key that was hit
            operation: Operation that used the cache
            user_id: User ID if applicable
            **extra: Additional structured data
        """
        log_data: dict[str, Any] = {
            "cache_key": cache_key,
            "operation": operation,
            "cache_hit": True,
        }
        if user_id:
            log_data["user_id"] = user_id
        log_data.update(extra)

        self.logger.debug("Cache hit for %s", operation, extra=log_data)

    def log_cache_miss(
        self, cache_key: str, operation: str, user_id: str | None = None, **extra: Any
    ) -> None:
        """Log cache misses.

        Args:
            cache_key: Cache key that missed
            operation: Operation that missed the cache
            user_id: User ID if applicable
            **extra: Additional structured data
        """
        log_data: dict[str, Any] = {
            "cache_key": cache_key,
            "operation": operation,
            "cache_hit": False,
        }
        if user_id:
            log_data["user_id"] = user_id
        log_data.update(extra)

        self.logger.debug("Cache miss for %s", operation, extra=log_data)
