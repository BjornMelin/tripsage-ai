"""Validation mixin for common validation patterns.

This mixin provides common validation methods that are shared across
multiple services to reduce code duplication.
"""

import logging
from typing import Any


logger = logging.getLogger(__name__)


class ValidationMixin:
    """Mixin providing common validation patterns."""

    def _validate_required(self, value: Any, field_name: str) -> bool:
        """Validate that a required field is present and not empty.

        Args:
            value: The value to validate
            field_name: Name of the field for error messages

        Returns:
            True if valid, False otherwise
        """
        if not value:
            logger.warning(
                "Required field '%s' is missing or empty",
                field_name,
                extra={"field": field_name},
            )
            return False
        return True

    def _validate_user_id(self, user_id: str | None) -> bool:
        """Validate that user_id is present and valid.

        Args:
            user_id: The user ID to validate

        Returns:
            True if valid, False otherwise
        """
        return self._validate_required(user_id, "user_id")

    def _validate_entity_exists(
        self,
        entity: Any,
        entity_type: str,
        entity_id: str | None = None,
    ) -> bool:
        """Validate that an entity exists.

        Args:
            entity: The entity to check
            entity_type: Type of entity (e.g., 'user', 'trip')
            entity_id: Optional ID for logging

        Returns:
            True if entity exists, False otherwise
        """
        if not entity:
            logger.warning(
                "%s not found",
                entity_type,
                extra={"entity_type": entity_type, "entity_id": entity_id},
            )
            return False
        return True

    def _validate_list_not_empty(self, items: list[Any], list_name: str) -> bool:
        """Validate that a list is not empty.

        Args:
            items: The list to validate
            list_name: Name of the list for error messages

        Returns:
            True if list has items, False otherwise
        """
        if not items:
            logger.warning(
                "List '%s' is empty",
                list_name,
                extra={"list_name": list_name},
            )
            return False
        return True

    def _validate_string_length(
        self,
        value: object,
        field_name: str,
        min_length: int = 1,
        max_length: int | None = None,
    ) -> bool:
        """Validate string length constraints.

        Args:
            value: The string to validate
            field_name: Name of the field
            min_length: Minimum allowed length
            max_length: Maximum allowed length (optional)

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(value, str):
            logger.warning(
                "Field '%s' must be a string",
                field_name,
                extra={"field": field_name},
            )
            return False

        if len(value) < min_length:
            logger.warning(
                "Field '%s' is too short (min: %d)",
                field_name,
                min_length,
                extra={"field": field_name, "min_length": min_length},
            )
            return False

        if max_length is not None and len(value) > max_length:
            logger.warning(
                "Field '%s' is too long (max: %d)",
                field_name,
                max_length,
                extra={"field": field_name, "max_length": max_length},
            )
            return False

        return True

    def _validate_numeric_range(
        self,
        value: object,
        field_name: str,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> bool:
        """Validate numeric value is within range.

        Args:
            value: The numeric value to validate
            field_name: Name of the field
            min_value: Minimum allowed value (optional)
            max_value: Maximum allowed value (optional)

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(value, (int, float)):
            logger.warning(
                "Field '%s' must be numeric",
                field_name,
                extra={"field": field_name},
            )
            return False

        if min_value is not None and value < min_value:
            logger.warning(
                "Field '%s' is below minimum (%s)",
                field_name,
                min_value,
                extra={"field": field_name, "min_value": min_value},
            )
            return False

        if max_value is not None and value > max_value:
            logger.warning(
                "Field '%s' is above maximum (%s)",
                field_name,
                max_value,
                extra={"field": field_name, "max_value": max_value},
            )
            return False

        return True
