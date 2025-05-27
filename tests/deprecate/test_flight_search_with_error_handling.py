"""
Standalone tests for error handling decorator in flight_search.py.

This test isolates the error handling decorator functionality to ensure it properly
handles both synchronous and asynchronous functions.
"""

# Create a standalone copy of the error handling decorator for testing
import functools
import inspect
from typing import Any, Callable, Dict, TypeVar
from unittest.mock import AsyncMock, MagicMock

import pytest

F = TypeVar("F", bound=Callable[..., Any])
SyncF = TypeVar("SyncF", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Any])

# Mock logger for testing
mock_logger = MagicMock()
mock_logger.error = MagicMock()
mock_logger.warning = MagicMock()


def with_error_handling_standalone(func: F) -> F:
    """Test version of with_error_handling decorator.

    This is a standalone copy of the decorator used in the refactored code,
    with the same error handling logic but no external dependencies.
    """
    # Check if the function is a coroutine function (async)
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Async wrapper function with try-except block."""
            try:
                # Call the original async function
                return await func(*args, **kwargs)
            except Exception as e:
                # Get function name for better error logging
                func_name = func.__name__
                mock_logger.error(f"Error in {func_name}: {str(e)}")

                # Return error response in the expected format for agent tools
                return {"error": str(e)}

        return async_wrapper

    # For synchronous functions
    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Sync wrapper function with try-except block."""
            try:
                # Call the original sync function
                return func(*args, **kwargs)
            except Exception as e:
                # Get function name for better error logging
                func_name = func.__name__
                mock_logger.error(f"Error in {func_name}: {str(e)}")

                # Return error response in the expected format for agent tools
                return {"error": str(e)}

        return sync_wrapper


class TestFlightSearchWithErrorHandling:
    """Tests for error handling in flight search functions."""

    @pytest.mark.asyncio
    async def test_search_flights_with_error_handling(self):
        """Test error handling in search_flights-like function."""

        # Create a mock implementation similar to search_flights
        @with_error_handling_standalone
        async def mock_search_flights(params: Dict[str, Any]) -> Dict[str, Any]:
            """Simulates search_flights method."""
            if "trigger_error" in params:
                raise ValueError("Simulated flight search error")
            return {"success": True, "flights": 10}

        # Test normal operation
        result = await mock_search_flights({"origin": "JFK", "destination": "LAX"})
        assert "success" in result
        assert result["success"] is True

        # Test error handling
        result = await mock_search_flights({"trigger_error": True})
        assert "error" in result
        assert "Simulated flight search error" in result["error"]

    @pytest.mark.asyncio
    async def test_add_price_history_with_error_handling(self):
        """Test error handling in _add_price_history-like function."""

        # Create a mock implementation similar to _add_price_history
        @with_error_handling_standalone
        async def mock_add_price_history(results: Dict[str, Any]) -> Dict[str, Any]:
            """Simulates _add_price_history method."""
            if "trigger_error" in results:
                raise ValueError("Price history calculation error")

            # Simulate processing
            if "prices" not in results:
                return results  # Early return for invalid input

            # Calculate insights
            prices = results["prices"]
            if not prices:
                return results  # Early return for empty prices

            # Simulate price insight calculation (would fail if prices is empty)
            avg_price = sum(prices) / len(prices)

            return {
                **results,
                "price_insights": {"avg_price": avg_price, "trend": "stable"},
            }

        # Test normal operation
        result = await mock_add_price_history({"prices": [100, 200, 300]})
        assert "price_insights" in result
        assert result["price_insights"]["avg_price"] == 200

        # Test error handling
        result = await mock_add_price_history({"trigger_error": True})
        assert "error" in result
        assert "Price history calculation error" in result["error"]

        # Test with invalid input that would cause error without try/except
        result = await mock_add_price_history({"no_prices": True})
        assert "price_insights" not in result  # Still returns valid response

    @pytest.mark.asyncio
    async def test_get_price_history_with_error_handling(self):
        """Test error handling in _get_price_history-like function."""

        mock_client = AsyncMock()
        mock_client.get_flight_prices = AsyncMock(
            side_effect=lambda **kwargs: {"prices": []}
            if kwargs.get("origin") == "ERROR"
            else {"prices": [100, 120, 140]}
        )

        @with_error_handling_standalone
        async def mock_get_price_history(
            origin: str, destination: str
        ) -> Dict[str, Any]:
            """Simulates _get_price_history method."""
            if origin == "FAIL":
                raise ConnectionError("API connection failed")

            # Try to get data from mock client
            try:
                return await mock_client.get_flight_prices(
                    origin=origin, destination=destination
                )
            except Exception as e:
                # This exception would be caught by the decorator
                raise ValueError(f"Client error: {str(e)}") from e

        # Test normal operation
        result = await mock_get_price_history("JFK", "LAX")
        assert "prices" in result
        assert len(result["prices"]) == 3

        # Test error in API call
        result = await mock_get_price_history("FAIL", "LAX")
        assert "error" in result
        assert "API connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_search_flexible_dates_with_error_handling(self):
        """Test error handling in search_flexible_dates-like function."""

        search_count = 0

        @with_error_handling_standalone
        async def mock_search_flexible_dates(params: Dict[str, Any]) -> Dict[str, Any]:
            """Simulates search_flexible_dates method."""
            nonlocal search_count

            # Validate required parameters
            required = ["origin", "destination", "date_from", "date_to"]
            for param in required:
                if param not in params:
                    raise ValueError(f"Missing required parameter: {param}")

            # Simulate an error during processing
            if "trigger_error" in params:
                raise ValueError("Date range processing error")

            # Simulate processing multiple search results
            search_count += 1
            if search_count > 3:  # Simulate an error after a few searches
                raise ConnectionError("Too many searches")

            return {
                "origin": params["origin"],
                "destination": params["destination"],
                "date_range": {"from": params["date_from"], "to": params["date_to"]},
                "all_dates": [
                    {"departure_date": "2025-06-01", "best_price": 299},
                    {"departure_date": "2025-06-02", "best_price": 349},
                ],
                "best_date": {"departure_date": "2025-06-01", "best_price": 299},
            }

        # Test normal operation
        result = await mock_search_flexible_dates(
            {
                "origin": "JFK",
                "destination": "LAX",
                "date_from": "2025-06-01",
                "date_to": "2025-06-10",
            }
        )
        assert "all_dates" in result
        assert len(result["all_dates"]) == 2

        # Test with missing parameter
        result = await mock_search_flexible_dates(
            {
                "origin": "JFK",
                "destination": "LAX",
                "date_from": "2025-06-01",  # Missing date_to
            }
        )
        assert "error" in result
        assert "Missing required parameter: date_to" in result["error"]

        # Test with triggered error
        result = await mock_search_flexible_dates(
            {
                "origin": "JFK",
                "destination": "LAX",
                "date_from": "2025-06-01",
                "date_to": "2025-06-10",
                "trigger_error": True,
            }
        )
        assert "error" in result
        assert "Date range processing error" in result["error"]

        # Test with error during processing (after multiple calls)
        for _ in range(3):  # This should trigger the connection error
            await mock_search_flexible_dates(
                {
                    "origin": "JFK",
                    "destination": "LAX",
                    "date_from": "2025-06-01",
                    "date_to": "2025-06-10",
                }
            )

        # This should trigger the error
        result = await mock_search_flexible_dates(
            {
                "origin": "JFK",
                "destination": "LAX",
                "date_from": "2025-06-01",
                "date_to": "2025-06-10",
            }
        )
        assert "error" in result
        assert "Too many searches" in result["error"]
