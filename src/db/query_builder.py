"""
Query builder base classes for TripSage database providers.

This module provides base classes for query building that can be used
by different database providers to reduce code duplication.
"""

from abc import abstractmethod
from typing import Any, Dict, Generic, List, TypeVar, Union

T = TypeVar("T")


class BaseQueryBuilder(Generic[T]):
    """
    Base query builder class for database providers.

    This provides common functionality for building SQL queries in a
    fluent interface style, similar to Supabase's query builder.
    """

    def __init__(self, table_name: str):
        """
        Initialize the base query builder.

        Args:
            table_name: The name of the table.
        """
        self.table_name = table_name
        self._select_columns = "*"
        self._where_clauses = []
        self._where_params = []
        self._param_counter = 0
        self._order_by = None
        self._limit_val = None
        self._offset_val = None
        self._range_from = None
        self._range_to = None
        self._operation = None
        self._data = None

    def select(self, columns: str) -> "BaseQueryBuilder":
        """
        Select columns from the table.

        Args:
            columns: Comma-separated list of columns to select.

        Returns:
            Self for method chaining.
        """
        self._select_columns = columns
        return self

    def eq(self, column: str, value: Any) -> "BaseQueryBuilder":
        """
        Add an equality condition to the query.

        Args:
            column: The column name.
            value: The value to compare against.

        Returns:
            Self for method chaining.
        """
        self._add_where_clause(f"{column} = ${self._next_param_index()}", value)
        return self

    def neq(self, column: str, value: Any) -> "BaseQueryBuilder":
        """
        Add a not-equal condition to the query.

        Args:
            column: The column name.
            value: The value to compare against.

        Returns:
            Self for method chaining.
        """
        self._add_where_clause(f"{column} != ${self._next_param_index()}", value)
        return self

    def gt(self, column: str, value: Any) -> "BaseQueryBuilder":
        """
        Add a greater-than condition to the query.

        Args:
            column: The column name.
            value: The value to compare against.

        Returns:
            Self for method chaining.
        """
        self._add_where_clause(f"{column} > ${self._next_param_index()}", value)
        return self

    def lt(self, column: str, value: Any) -> "BaseQueryBuilder":
        """
        Add a less-than condition to the query.

        Args:
            column: The column name.
            value: The value to compare against.

        Returns:
            Self for method chaining.
        """
        self._add_where_clause(f"{column} < ${self._next_param_index()}", value)
        return self

    def gte(self, column: str, value: Any) -> "BaseQueryBuilder":
        """
        Add a greater-than-or-equal condition to the query.

        Args:
            column: The column name.
            value: The value to compare against.

        Returns:
            Self for method chaining.
        """
        self._add_where_clause(f"{column} >= ${self._next_param_index()}", value)
        return self

    def lte(self, column: str, value: Any) -> "BaseQueryBuilder":
        """
        Add a less-than-or-equal condition to the query.

        Args:
            column: The column name.
            value: The value to compare against.

        Returns:
            Self for method chaining.
        """
        self._add_where_clause(f"{column} <= ${self._next_param_index()}", value)
        return self

    def order(self, column: str, ascending: bool = True) -> "BaseQueryBuilder":
        """
        Add an ORDER BY clause to the query.

        Args:
            column: The column to order by.
            ascending: Whether to sort in ascending order.

        Returns:
            Self for method chaining.
        """
        direction = "ASC" if ascending else "DESC"
        self._order_by = f"{column} {direction}"
        return self

    def limit(self, count: int) -> "BaseQueryBuilder":
        """
        Add a LIMIT clause to the query.

        Args:
            count: The maximum number of rows to return.

        Returns:
            Self for method chaining.
        """
        self._limit_val = count
        return self

    def offset(self, count: int) -> "BaseQueryBuilder":
        """
        Add an OFFSET clause to the query.

        Args:
            count: The number of rows to skip.

        Returns:
            Self for method chaining.
        """
        self._offset_val = count
        return self

    def range(self, from_val: int, to_val: int) -> "BaseQueryBuilder":
        """
        Set a range of rows to return, combining LIMIT and OFFSET.

        Args:
            from_val: The index of the first row to return.
            to_val: The index of the last row to return.

        Returns:
            Self for method chaining.
        """
        self._range_from = from_val
        self._range_to = to_val
        return self

    def insert(
        self, data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> "BaseQueryBuilder":
        """
        Set up an INSERT operation.

        Args:
            data: The data to insert, either a single record or a list of records.

        Returns:
            Self for method chaining.
        """
        self._operation = "INSERT"
        self._data = data if isinstance(data, list) else [data]
        return self

    def update(self, data: Dict[str, Any]) -> "BaseQueryBuilder":
        """
        Set up an UPDATE operation.

        Args:
            data: The data to update.

        Returns:
            Self for method chaining.
        """
        self._operation = "UPDATE"
        self._data = data
        return self

    def delete(self) -> "BaseQueryBuilder":
        """
        Set up a DELETE operation.

        Returns:
            Self for method chaining.
        """
        self._operation = "DELETE"
        return self

    def get_debug_query(self) -> str:
        """
        Get a debug-friendly representation of the current query.

        Returns:
            A string representation of the query.
        """
        query = ""
        if hasattr(self, "_operation") and self._operation:
            if self._operation == "INSERT":
                query = f"INSERT INTO {self.table_name} ..."
            elif self._operation == "UPDATE":
                query = f"UPDATE {self.table_name} SET ... "
                if self._where_clauses:
                    query += "WHERE " + " AND ".join(self._where_clauses)
            elif self._operation == "DELETE":
                query = f"DELETE FROM {self.table_name} "
                if self._where_clauses:
                    query += "WHERE " + " AND ".join(self._where_clauses)
        else:
            # SELECT
            query = f"SELECT {self._select_columns} FROM {self.table_name}"
            if self._where_clauses:
                query += " WHERE " + " AND ".join(self._where_clauses)
            if self._order_by:
                query += f" ORDER BY {self._order_by}"
            if self._limit_val:
                query += f" LIMIT {self._limit_val}"
            if self._offset_val:
                query += f" OFFSET {self._offset_val}"

        return query

    def _next_param_index(self) -> int:
        """
        Get the next parameter index.

        Returns:
            The next parameter index.
        """
        self._param_counter += 1
        return self._param_counter

    def _add_where_clause(self, clause: str, value: Any) -> None:
        """
        Add a WHERE clause to the query.

        Args:
            clause: The WHERE clause.
            value: The parameter value.
        """
        self._where_clauses.append(clause)
        self._where_params.append(value)

    @abstractmethod
    async def execute(self) -> Any:
        """
        Execute the query.

        Returns:
            The query result.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement execute()")
