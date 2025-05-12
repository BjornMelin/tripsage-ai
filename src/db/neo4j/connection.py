"""
Neo4j connection management.

This module provides a connection manager for Neo4j database,
handling connection pooling, query execution, and transactions.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from neo4j import Driver, GraphDatabase

from src.db.neo4j.config import neo4j_config
from src.db.neo4j.exceptions import Neo4jConnectionError, Neo4jQueryError
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class Neo4jConnection:
    """Manages Neo4j database connections and query execution."""

    _instance = None
    _driver = None

    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(Neo4jConnection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the Neo4j connection."""
        if self._initialized:
            return

        self._initialized = True
        self._config = neo4j_config
        self._driver = None
        self._connect()

    def _connect(self) -> None:
        """Establish a connection to the Neo4j database.

        Raises:
            Neo4jConnectionError: If connection fails
        """
        try:
            # Validate configuration
            self._config.validate()

            # Create the driver
            self._driver = GraphDatabase.driver(
                self._config.uri,
                auth=(self._config.user, self._config.password),
                max_connection_lifetime=self._config.max_connection_lifetime,
                max_connection_pool_size=self._config.max_connection_pool_size,
                connection_acquisition_timeout=self._config.connection_acquisition_timeout,
            )

            # Verify the connection by running a simple query
            with self._driver.session(database=self._config.database) as session:
                result = session.run("RETURN 1 AS test")
                assert result.single()["test"] == 1

            logger.info(
                "Successfully connected to Neo4j database at %s", self._config.uri
            )
        except Exception as e:
            logger.error("Failed to connect to Neo4j database: %s", str(e))
            raise Neo4jConnectionError(
                f"Failed to connect to Neo4j database: {str(e)}"
            ) from e

    def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    def get_driver(self) -> Driver:
        """Get the Neo4j driver.

        Returns:
            Neo4j driver instance

        Raises:
            Neo4jConnectionError: If connection is not established
        """
        if not self._driver:
            self._connect()
        return self._driver

    def run_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Run a Cypher query and return the results.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name (defaults to configuration)
            timeout: Query timeout in seconds (defaults to configuration)

        Returns:
            List of dictionaries with query results

        Raises:
            Neo4jQueryError: If query execution fails
        """
        if not self._driver:
            self._connect()

        # Use default values from configuration if not provided
        if database is None:
            database = self._config.database

        if timeout is None:
            timeout = self._config.default_query_timeout

        parameters = parameters or {}
        start_time = time.time()

        try:
            with self._driver.session(database=database) as session:
                result = session.run(query, parameters, timeout=timeout)
                records = [record.data() for record in result]

                execution_time = time.time() - start_time
                logger.debug(
                    "Query executed in %.2f seconds: %s", execution_time, query
                )

                return records
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "Query failed after %.2f seconds: %s - %s",
                execution_time,
                query,
                str(e),
            )
            raise Neo4jQueryError(f"Query execution failed: {str(e)}") from e

    def run_transaction(
        self,
        statements: List[Dict[str, Any]],
        database: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> List[List[Dict[str, Any]]]:
        """Run multiple statements in a transaction.

        Args:
            statements: List of statement dictionaries, each containing
                'query' and 'parameters'
            database: Database name (defaults to configuration)
            timeout: Transaction timeout in seconds (defaults to configuration)

        Returns:
            List of results for each statement

        Raises:
            Neo4jQueryError: If transaction execution fails
        """
        if not self._driver:
            self._connect()

        # Use default values from configuration if not provided
        if database is None:
            database = self._config.database

        if timeout is None:
            timeout = self._config.default_query_timeout

        start_time = time.time()

        try:
            with self._driver.session(database=database) as session:

                def _run_transaction(tx):
                    results = []
                    for statement in statements:
                        query = statement["query"]
                        parameters = statement.get("parameters", {})
                        result = tx.run(query, parameters)
                        results.append([record.data() for record in result])
                    return results

                results = session.execute_write(_run_transaction)

                execution_time = time.time() - start_time
                logger.debug(
                    "Transaction executed in %.2f seconds with %d statements",
                    execution_time,
                    len(statements),
                )

                return results
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "Transaction failed after %.2f seconds: %s", execution_time, str(e)
            )
            raise Neo4jQueryError(f"Transaction execution failed: {str(e)}") from e

    async def run_query_async(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Run a Cypher query asynchronously.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name (defaults to configuration)
            timeout: Query timeout in seconds (defaults to configuration)

        Returns:
            List of dictionaries with query results

        Raises:
            Neo4jQueryError: If query execution fails
        """
        # Run in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.run_query(query, parameters, database, timeout)
        )

    async def run_transaction_async(
        self,
        statements: List[Dict[str, Any]],
        database: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> List[List[Dict[str, Any]]]:
        """Run multiple statements in a transaction asynchronously.

        Args:
            statements: List of statement dictionaries, each containing
                'query' and 'parameters'
            database: Database name (defaults to configuration)
            timeout: Transaction timeout in seconds (defaults to configuration)

        Returns:
            List of results for each statement

        Raises:
            Neo4jQueryError: If transaction execution fails
        """
        # Run in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.run_transaction(statements, database, timeout)
        )

    def is_connected(self) -> bool:
        """Check if the connection to Neo4j is active.

        Returns:
            True if connected, False otherwise
        """
        if not self._driver:
            return False

        try:
            with self._driver.session(database=self._config.database) as session:
                result = session.run("RETURN 1 AS test")
                return result.single()["test"] == 1
        except Exception:
            return False
