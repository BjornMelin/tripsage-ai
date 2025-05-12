"""
Custom exceptions for Neo4j operations.

This module defines custom exceptions for Neo4j-related operations
to provide more specific error handling.
"""


class Neo4jError(Exception):
    """Base class for Neo4j-related exceptions."""

    pass


class Neo4jConnectionError(Neo4jError):
    """Raised when connection to Neo4j fails."""

    pass


class Neo4jQueryError(Neo4jError):
    """Raised when a Cypher query fails."""

    pass


class Neo4jValidationError(Neo4jError):
    """Raised when data validation fails."""

    pass


class Neo4jSchemaError(Neo4jError):
    """Raised when there's a schema-related error."""

    pass


class Neo4jDataError(Neo4jError):
    """Raised when there's a data-related error."""

    pass


class Neo4jTransactionError(Neo4jError):
    """Raised when a transaction fails."""

    pass
