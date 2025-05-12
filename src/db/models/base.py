"""
Base model classes for TripSage database entities.

This module provides base classes for all TripSage database models,
implementing common functionality.
"""

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# Define a type variable for the model
T = TypeVar("T", bound="BaseDBModel")


class BaseDBModel(BaseModel):
    """
    Base class for all database models.

    This class provides common fields and functionality for all database models.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="ignore",
    )

    # Table name in the database - to be overridden by subclasses
    __tablename__: ClassVar[str] = ""

    # Primary key field name - to be overridden by subclasses if different
    __primary_key__: ClassVar[str] = "id"

    id: Optional[int] = Field(None, description="Unique identifier")
    created_at: Optional[datetime] = Field(
        None, description="Timestamp when the record was created"
    )
    updated_at: Optional[datetime] = Field(
        None, description="Timestamp when the record was last updated"
    )

    @property
    def is_new(self) -> bool:
        """Check if this is a new record (no ID assigned yet)."""
        return self.id is None

    @property
    def pk_value(self) -> Optional[Any]:
        """Get the value of the primary key field."""
        return getattr(self, self.__class__.__primary_key__)

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """
        Convert the model to a dictionary suitable for database operations.

        Args:
            exclude_none: Whether to exclude None values from the dictionary.

        Returns:
            Dictionary representation of the model.
        """
        # Convert to dict using model_dump
        model_dict = self.model_dump(exclude_none=exclude_none)

        # Handle nested models
        for key, value in model_dict.items():
            if isinstance(value, BaseDBModel):
                model_dict[key] = value.to_dict(exclude_none=exclude_none)
            elif (
                isinstance(value, list) and value and isinstance(value[0], BaseDBModel)
            ):
                model_dict[key] = [
                    item.to_dict(exclude_none=exclude_none) for item in value
                ]

        return model_dict

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create a model instance from a dictionary.

        Args:
            data: Dictionary containing model data.

        Returns:
            Instance of the model.
        """
        return cls(**data)

    @classmethod
    def from_row(cls: Type[T], row: Dict[str, Any]) -> T:
        """
        Create a model instance from a database row.

        Args:
            row: Dictionary containing database row data.

        Returns:
            Instance of the model.
        """
        return cls.from_dict(row)

    @classmethod
    def from_rows(cls: Type[T], rows: List[Dict[str, Any]]) -> List[T]:
        """
        Create model instances from a list of database rows.

        Args:
            rows: List of dictionaries containing database row data.

        Returns:
            List of model instances.
        """
        return [cls.from_row(row) for row in rows]

    def __str__(self) -> str:
        """String representation of the model."""
        return f"{self.__class__.__name__}(id={self.id})"

    def __repr__(self) -> str:
        """Detailed representation of the model."""
        items = ", ".join([f"{k}={v}" for k, v in self.to_dict().items()])
        return f"{self.__class__.__name__}({items})"
