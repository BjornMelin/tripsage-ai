"""Error handling mixin for standardized error patterns across services.

This mixin provides common error handling methods with consistent
exception handling, logging, and error transformation across all TripSage services.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from tripsage_core.exceptions import (
    RECOVERABLE_ERRORS,
    CoreServiceError as ServiceError,
)


logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorHandlingMixin:
    """Mixin providing standardized error handling patterns."""

    @property
    def logger(self) -> logging.Logger:
        """Get the logger for this class."""
        return logging.getLogger(self.__class__.__module__)

    async def handle_service_operation(
        self,
        operation: str,
        operation_func: Callable[[], Awaitable[T]],
        user_id: str | None = None,
        entity_id: str | None = None,
        **extra: Any,
    ) -> T:
        """Handle a service operation with standardized error handling.

        Args:
            operation: Name of the operation for logging
            operation_func: Async function to execute
            user_id: User ID if applicable
            entity_id: Entity ID if applicable
            **extra: Additional structured data for logging

        Returns:
            Result of the operation function

        Raises:
            ServiceError: If operation fails
        """
        try:
            return await operation_func()
        except RECOVERABLE_ERRORS as error:
            log_data: dict[str, Any] = {"operation": operation, "error": str(error)}
            if user_id:
                log_data["user_id"] = user_id
            if entity_id:
                log_data["entity_id"] = entity_id
            log_data.update(extra)

            self.logger.exception("Operation failed: %s", operation, extra=log_data)
            raise ServiceError(f"Operation failed: {operation}") from error

    def handle_validation_error(
        self,
        operation: str,
        error: Exception,
        user_id: str | None = None,
        **extra: Any,
    ) -> None:
        """Handle validation errors with standardized logging.

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

    def handle_entity_not_found(
        self,
        entity_type: str,
        entity_id: str,
        user_id: str | None = None,
        **extra: Any,
    ) -> None:
        """Handle entity not found errors with standardized logging.

        Args:
            entity_type: Type of entity (e.g., 'api_key')
            entity_id: ID of the entity
            user_id: User ID if applicable
            **extra: Additional structured data
        """
        log_data: dict[str, Any] = {"entity_type": entity_type, "entity_id": entity_id}
        if user_id:
            log_data["user_id"] = user_id
        log_data.update(extra)

        self.logger.warning("%s not found", entity_type, extra=log_data)

    def handle_external_api_error(
        self,
        service: str,
        operation: str,
        error: Exception,
        user_id: str | None = None,
        **extra: Any,
    ) -> None:
        """Handle external API errors with standardized logging.

        Args:
            service: External service name
            operation: API operation
            error: The exception that occurred
            user_id: User ID if applicable
            **extra: Additional structured data
        """
        log_data: dict[str, Any] = {
            "service": service,
            "operation": operation,
            "error": str(error),
            "error_type": type(error).__name__,
        }
        if user_id:
            log_data["user_id"] = user_id
        log_data.update(extra)

        self.logger.exception(
            "External API call failed: %s.%s", service, operation, extra=log_data
        )

    def handle_cache_error(
        self,
        operation: str,
        error: Exception,
        cache_key: str | None = None,
        user_id: str | None = None,
        **extra: Any,
    ) -> None:
        """Handle cache operation errors with standardized logging.

        Args:
            operation: Cache operation (get/set/delete)
            error: The exception that occurred
            cache_key: Cache key if applicable
            user_id: User ID if applicable
            **extra: Additional structured data
        """
        log_data: dict[str, Any] = {
            "operation": operation,
            "error": str(error),
            "error_type": type(error).__name__,
        }
        if cache_key:
            log_data["cache_key"] = cache_key
        if user_id:
            log_data["user_id"] = user_id
        log_data.update(extra)

        self.logger.warning("Cache operation failed: %s", operation, extra=log_data)

    def handle_encryption_error(
        self,
        operation: str,
        error: Exception,
        key_length: int | None = None,
        **extra: Any,
    ) -> None:
        """Handle encryption/decryption errors with standardized logging.

        Args:
            operation: Encryption operation (encrypt/decrypt)
            error: The exception that occurred
            key_length: Length of the key being processed
            **extra: Additional structured data
        """
        log_data: dict[str, Any] = {
            "operation": operation,
            "error": str(error),
            "error_type": type(error).__name__,
        }
        if key_length is not None:
            log_data["key_length"] = key_length
        log_data.update(extra)

        self.logger.exception(
            "Encryption operation failed: %s", operation, extra=log_data
        )
