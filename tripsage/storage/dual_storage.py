"""Dual storage implementation for both SQL and graph databases."""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel

from tripsage.storage.base import BaseStorage

T = TypeVar("T", bound=BaseModel)


class DualStorage(Generic[T]):
    """Dual storage implementation for both SQL and graph databases."""

    def __init__(
        self,
        sql_storage: BaseStorage[T],
        graph_storage: Optional[BaseStorage[T]] = None,
    ):
        """Initialize the dual storage.

        Args:
            sql_storage: The SQL storage implementation.
            graph_storage: Optional graph storage implementation.
        """
        self.sql_storage = sql_storage
        self.graph_storage = graph_storage

    async def create(self, item: T) -> T:
        """Create an item in both storages.

        Args:
            item: The item to create.

        Returns:
            The created item from the SQL storage.
        """
        sql_result = await self.sql_storage.create(item)
        if self.graph_storage:
            await self.graph_storage.create(item)
        return sql_result

    async def read(self, id: str) -> Optional[T]:
        """Read an item from the SQL storage.

        Args:
            id: The ID of the item to read.

        Returns:
            The item, or None if not found.
        """
        return await self.sql_storage.read(id)

    async def update(self, id: str, item: T) -> T:
        """Update an item in both storages.

        Args:
            id: The ID of the item to update.
            item: The updated item.

        Returns:
            The updated item from the SQL storage.
        """
        sql_result = await self.sql_storage.update(id, item)
        if self.graph_storage:
            await self.graph_storage.update(id, item)
        return sql_result

    async def delete(self, id: str) -> bool:
        """Delete an item from both storages.

        Args:
            id: The ID of the item to delete.

        Returns:
            True if the item was deleted from the SQL storage, False otherwise.
        """
        sql_result = await self.sql_storage.delete(id)
        if self.graph_storage:
            await self.graph_storage.delete(id)
        return sql_result

    async def list(self, filter: Optional[Dict[str, Any]] = None) -> List[T]:
        """List items from the SQL storage.

        Args:
            filter: Optional filter to apply.

        Returns:
            A list of items from the SQL storage.
        """
        return await self.sql_storage.list(filter)
