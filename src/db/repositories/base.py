"""
Base repository for database operations.

This module provides a base repository class for interacting with the database.
It implements common CRUD operations and serves as a base for entity-specific repositories.
"""

import logging
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union

from src.db.client import get_supabase_client
from src.db.models.base import BaseDBModel
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)

# Type variable for the model
T = TypeVar("T", bound=BaseDBModel)


class BaseRepository(Generic[T]):
    """
    Base repository for database operations.

    This class provides common CRUD operations for database entities.
    """

    def __init__(self, model_class: Type[T]):
        """
        Initialize the repository with a model class.

        Args:
            model_class: The model class this repository will handle.
        """
        self.model_class = model_class
        self.table_name = model_class.__tablename__
        self.primary_key = model_class.__primary_key__

        if not self.table_name:
            raise ValueError(
                f"Model class {model_class.__name__} must define __tablename__"
            )

    def _get_client(self, use_service_key: bool = False):
        """
        Get the Supabase client.

        Args:
            use_service_key: Whether to use the service role key.

        Returns:
            The Supabase client.
        """
        return get_supabase_client(use_service_key=use_service_key)

    def _get_table(self, use_service_key: bool = False):
        """
        Get the Supabase table query builder.

        Args:
            use_service_key: Whether to use the service role key.

        Returns:
            The Supabase table query builder.
        """
        client = self._get_client(use_service_key=use_service_key)
        return client.table(self.table_name)

    async def create(self, entity: T) -> T:
        """
        Create a new entity in the database.

        Args:
            entity: The entity to create.

        Returns:
            The created entity with assigned ID.

        Raises:
            ValueError: If the entity already has an ID.
        """
        if not entity.is_new:
            raise ValueError(f"Entity already has an ID: {entity.id}")

        data = entity.to_dict(exclude_none=True)
        # Remove ID if it's None
        if "id" in data and data["id"] is None:
            del data["id"]

        # Remove created_at and updated_at to let the database set them
        if "created_at" in data:
            del data["created_at"]
        if "updated_at" in data:
            del data["updated_at"]

        try:
            response = self._get_table().insert(data).execute()
            if not response.data or len(response.data) == 0:
                logger.error(f"Failed to create entity: {entity}")
                raise RuntimeError(f"Failed to create entity: {entity}")

            # Create a new entity from the response data
            return self.model_class.from_row(response.data[0])
        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            raise

    async def update(self, entity: T) -> T:
        """
        Update an existing entity in the database.

        Args:
            entity: The entity to update.

        Returns:
            The updated entity.

        Raises:
            ValueError: If the entity does not have an ID.
        """
        if entity.is_new:
            raise ValueError("Cannot update entity without an ID")

        data = entity.to_dict(exclude_none=True)
        # No need to send id in the data for update
        if "id" in data:
            del data["id"]

        # Remove created_at to prevent updating it
        if "created_at" in data:
            del data["created_at"]
        # Remove updated_at to let the database update it
        if "updated_at" in data:
            del data["updated_at"]

        try:
            response = (
                self._get_table()
                .update(data)
                .eq(self.primary_key, entity.pk_value)
                .execute()
            )
            if not response.data or len(response.data) == 0:
                logger.error(f"Failed to update entity: {entity}")
                raise RuntimeError(f"Failed to update entity: {entity}")

            # Create a new entity from the response data
            return self.model_class.from_row(response.data[0])
        except Exception as e:
            logger.error(f"Error updating entity: {e}")
            raise

    async def delete(self, entity_or_id: Union[T, int]) -> bool:
        """
        Delete an entity from the database.

        Args:
            entity_or_id: The entity or entity ID to delete.

        Returns:
            True if the entity was deleted, False otherwise.
        """
        entity_id = (
            entity_or_id.pk_value
            if isinstance(entity_or_id, BaseDBModel)
            else entity_or_id
        )

        try:
            response = (
                self._get_table().delete().eq(self.primary_key, entity_id).execute()
            )
            return bool(response.data) and len(response.data) > 0
        except Exception as e:
            logger.error(f"Error deleting entity: {e}")
            raise

    async def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Get an entity by its ID.

        Args:
            entity_id: The ID of the entity to get.

        Returns:
            The entity if found, None otherwise.
        """
        try:
            response = (
                self._get_table().select("*").eq(self.primary_key, entity_id).execute()
            )
            if not response.data or len(response.data) == 0:
                return None

            return self.model_class.from_row(response.data[0])
        except Exception as e:
            logger.error(f"Error getting entity by ID: {e}")
            raise

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Get all entities, with pagination.

        Args:
            limit: Maximum number of entities to return.
            offset: Number of entities to skip.

        Returns:
            List of entities.
        """
        try:
            response = (
                self._get_table()
                .select("*")
                .range(offset, offset + limit - 1)
                .execute()
            )
            if not response.data:
                return []

            return self.model_class.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error getting all entities: {e}")
            raise

    async def count(self) -> int:
        """
        Count the number of entities in the table.

        Returns:
            The number of entities.
        """
        try:
            response = (
                self._get_client()
                .rpc("row_count", {"table_name": self.table_name})
                .execute()
            )

            if not response.data or len(response.data) == 0:
                return 0

            return response.data[0]
        except Exception as e:
            logger.error(f"Error counting entities: {e}")

            # Fallback if rpc isn't available
            try:
                response = self._get_table().select("*", count="exact").execute()
                return response.count if hasattr(response, "count") else 0
            except Exception as nested_e:
                logger.error(f"Error in fallback count: {nested_e}")
                raise

    async def save(self, entity: T) -> T:
        """
        Save an entity to the database.
        Creates a new entity if it doesn't have an ID, updates it otherwise.

        Args:
            entity: The entity to save.

        Returns:
            The saved entity.
        """
        if entity.is_new:
            return await self.create(entity)
        else:
            return await self.update(entity)

    async def find_by(self, **filters) -> List[T]:
        """
        Find entities matching the given filters.

        Args:
            **filters: Field-value pairs to filter by.

        Returns:
            List of matching entities.
        """
        query = self._get_table().select("*")

        for field, value in filters.items():
            query = query.eq(field, value)

        try:
            response = query.execute()
            if not response.data:
                return []

            return self.model_class.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding entities: {e}")
            raise

    async def find_one_by(self, **filters) -> Optional[T]:
        """
        Find a single entity matching the given filters.

        Args:
            **filters: Field-value pairs to filter by.

        Returns:
            The matching entity if found, None otherwise.
        """
        entities = await self.find_by(**filters)
        return entities[0] if entities else None

    async def execute_query(self, query_fn) -> List[T]:
        """
        Execute a custom query function against the table.

        Args:
            query_fn: Function that takes a query builder and returns a modified query.
                      Example: lambda q: q.select("*").eq("status", "active").order("created_at")

        Returns:
            List of entities matching the query.
        """
        query = self._get_table()
        result_query = query_fn(query)

        try:
            response = result_query.execute()
            if not response.data:
                return []

            return self.model_class.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error executing custom query: {e}")
            raise
