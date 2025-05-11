"""
Exceptions for the TripSage database module.

This module provides custom exceptions for database operations,
which helps with properly categorizing and handling different
types of database errors across providers.
"""

from typing import Any, Dict, Optional


class DatabaseError(Exception):
    """Base class for all database-related exceptions."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the database exception.

        Args:
            message: The error message.
            details: Additional details about the error.
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ConnectionError(DatabaseError):
    """Exception raised when a database connection fails."""

    pass


class QueryError(DatabaseError):
    """Exception raised when a database query fails."""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the query error.

        Args:
            message: The error message.
            query: The query that caused the error.
            params: The parameters used in the query.
            details: Additional details about the error.
        """
        self.query = query
        self.params = params
        super().__init__(message, details)


class NotConnectedError(DatabaseError):
    """Exception raised when attempting to use a database client that's not connected."""

    pass


class ProviderError(DatabaseError):
    """Exception raised when there's an issue with a database provider."""

    pass


class MigrationError(DatabaseError):
    """Exception raised when a database migration fails."""

    def __init__(
        self,
        message: str,
        migration_file: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the migration error.

        Args:
            message: The error message.
            migration_file: The migration file that caused the error.
            details: Additional details about the error.
        """
        self.migration_file = migration_file
        super().__init__(message, details)


class ConfigurationError(DatabaseError):
    """Exception raised when there's an issue with database configuration."""

    pass
