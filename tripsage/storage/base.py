"""Base storage implementations for databases."""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseStorage(Generic[T]):
    """Base storage interface for database operations."""

    def __init__(self, connection_string: str):
        """Initialize the base storage.

        Args:
            connection_string: The connection string for the database.
        """
        self.connection_string = connection_string

    async def create(self, item: T) -> T:
        """Create an item in the database.

        Args:
            item: The item to create.

        Returns:
            The created item.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement create")

    async def read(self, id: str) -> Optional[T]:
        """Read an item from the database.

        Args:
            id: The ID of the item to read.

        Returns:
            The item, or None if not found.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement read")

    async def update(self, id: str, item: T) -> T:
        """Update an item in the database.

        Args:
            id: The ID of the item to update.
            item: The updated item.

        Returns:
            The updated item.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement update")

    async def delete(self, id: str) -> bool:
        """Delete an item from the database.

        Args:
            id: The ID of the item to delete.

        Returns:
            True if the item was deleted, False otherwise.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement delete")

    async def list(self, filter: Optional[Dict[str, Any]] = None) -> List[T]:
        """List items from the database.

        Args:
            filter: Optional filter to apply.

        Returns:
            A list of items.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement list")
