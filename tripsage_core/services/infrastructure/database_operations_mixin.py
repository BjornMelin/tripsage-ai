"""Database operations mixin for common database query patterns.

This mixin provides common database operation methods that are shared across
multiple services to reduce code duplication.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol


logger = logging.getLogger(__name__)


class DatabaseServiceProtocol(Protocol):
    """Protocol for database service interface."""

    async def get_flight_offer(
        self, offer_id: str, user_id: str | None = None
    ) -> dict[str, Any] | None:
        """Get a flight offer by ID.

        Args:
            offer_id: ID of the flight offer to retrieve
            user_id: Optional user ID for access validation
        """
        ...

    async def get_accommodation_listing(
        self, listing_id: str, user_id: str | None = None
    ) -> dict[str, Any] | None:
        """Get an accommodation listing by ID.

        Args:
            listing_id: ID of the accommodation listing to retrieve
            user_id: Optional user ID for access validation
        """
        ...

    async def store_flight_offer(
        self, offer_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Store a flight offer.

        Args:
            offer_data: Data to store
        """
        ...

    async def store_accommodation_listing(
        self, listing_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Store an accommodation listing.

        Args:
            listing_data: Data to store
        """
        ...

    async def get_flight_offers(
        self, filters: dict[str, Any], limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get flight offers with filters.

        Args:
            filters: Filters to apply
            limit: Optional limit on results
        """
        ...

    async def get_accommodation_listings(
        self, filters: dict[str, Any], limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get accommodation listings with filters.

        Args:
            filters: Filters to apply
            limit: Optional limit on results
        """
        ...

    async def update_flight_offer(
        self, offer_id: str, updates: dict[str, Any], user_id: str | None = None
    ) -> bool:
        """Update a flight offer.

        Args:
            offer_id: ID of the flight offer to update
            updates: Updates to apply
            user_id: Optional user ID for validation
        """
        ...

    async def update_accommodation_listing(
        self, listing_id: str, updates: dict[str, Any], user_id: str | None = None
    ) -> bool:
        """Update an accommodation listing.

        Args:
            listing_id: ID of the accommodation listing to update
            updates: Updates to apply
            user_id: Optional user ID for validation
        """
        ...


class DatabaseOperationsMixin:
    """Mixin providing common database operation patterns."""

    @property
    def db(self) -> DatabaseServiceProtocol:
        """Database service instance. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must provide a db property")

    async def _safe_db_operation(
        self,
        operation: str,
        operation_func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any | None:
        """Execute a database operation with error handling.

        Args:
            operation: Description of the operation for logging
            operation_func: The database operation function to call
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation or None if failed
        """
        try:
            result = await operation_func(*args, **kwargs)
            logger.info("Database %s completed successfully", operation)
            return result
        except Exception as error:
            logger.exception(
                "Database %s failed",
                operation,
                extra={"error": str(error), "operation": operation},
            )
            return None

    async def _get_entity_by_id(
        self,
        entity_type: str,
        entity_id: str,
        user_id: str | None = None,
        get_func: Callable[..., Awaitable[Any]] | None = None,
    ) -> dict[str, Any] | None:
        """Get an entity by ID with optional user validation.

        Args:
            entity_type: Type of entity (e.g., 'flight_offer', 'accommodation_listing')
            entity_id: ID of the entity to retrieve
            user_id: Optional user ID for access validation
            get_func: Database function to call (defaults to self.db.get_{entity_type})

        Returns:
            Entity data or None if not found
        """
        if get_func is None:
            get_func = getattr(self.db, f"get_{entity_type}")

        # Type assertion after None check
        assert get_func is not None
        result = await self._safe_db_operation(
            f"get {entity_type} by ID", get_func, entity_id, user_id
        )

        if not result:
            logger.warning(
                "%s not found",
                entity_type,
                extra={"entity_id": entity_id, "user_id": user_id},
            )

        return result

    async def _store_entity(
        self,
        entity_type: str,
        entity_data: dict[str, Any],
        store_func: Callable[..., Awaitable[Any]] | None = None,
    ) -> dict[str, Any] | None:
        """Store an entity in the database.

        Args:
            entity_type: Type of entity being stored
            entity_data: Data to store
            store_func: DB function to call (defaults to self.db.store_{entity_type})

        Returns:
            Stored entity data or None if failed
        """
        if store_func is None:
            store_func = getattr(self.db, f"store_{entity_type}")

        # Type assertion after None check
        assert store_func is not None
        return await self._safe_db_operation(
            f"store {entity_type}", store_func, entity_data
        )

    async def _get_entities_with_filters(
        self,
        entity_type: str,
        filters: dict[str, Any],
        limit: int | None = None,
        get_func: Callable[..., Awaitable[Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Get multiple entities with filters.

        Args:
            entity_type: Type of entities to retrieve
            filters: Filters to apply
            limit: Optional limit on results
            get_func: DB function to call (defaults to self.db.get_{entity_type}s)

        Returns:
            List of entity data
        """
        if get_func is None:
            get_func = getattr(self.db, f"get_{entity_type}s")

        # Type assertion after None check
        assert get_func is not None
        results = await self._safe_db_operation(
            f"get {entity_type}s with filters", get_func, filters, limit
        )

        return results or []

    async def _update_entity(
        self,
        entity_type: str,
        entity_id: str,
        updates: dict[str, Any],
        user_id: str | None = None,
        update_func: Callable[..., Awaitable[Any]] | None = None,
    ) -> bool:
        """Update an entity in the database.

        Args:
            entity_type: Type of entity being updated
            entity_id: ID of the entity to update
            updates: Update data
            user_id: Optional user ID for validation
            update_func: DB function to call (defaults to self.db.update_{entity_type})

        Returns:
            True if update succeeded, False otherwise
        """
        if update_func is None:
            update_func = getattr(self.db, f"update_{entity_type}")

        # Type assertion after None check
        assert update_func is not None
        success = await self._safe_db_operation(
            f"update {entity_type}", update_func, entity_id, updates, user_id
        )

        return bool(success)
