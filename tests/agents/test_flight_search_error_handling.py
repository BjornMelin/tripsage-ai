"""
Tests for error handling in flight search module.

This module verifies that the error handling decorator correctly handles
exceptions in the flight search methods.
"""

import pytest

# Import the decorator to test
from tripsage.utils.decorators import with_error_handling


class TestFlightSearchErrorHandling:
    """Tests for error handling in flight search module."""

    @pytest.mark.asyncio
    async def test_search_flights_with_error_handling(self):
        """Test that search_flights with error handling
        handles exceptions properly."""

        # Create a mock implementation similar to search_flights
        @with_error_handling
        async def mock_search_flights(params):
            """Mocked search_flights function."""
            if "trigger_error" in params:
                raise ValueError("Simulated error")
            return {"success": True, "data": params}

        # Test normal operation
        result = await mock_search_flights({"origin": "JFK", "destination": "LAX"})
        assert "success" in result
        assert result["success"] is True

        # Test error handling
        result = await mock_search_flights({"trigger_error": True})
        assert "error" in result
        assert "Simulated error" in result["error"]

    @pytest.mark.asyncio
    async def test_add_price_history_with_error_handling(self):
        """Test that _add_price_history with error handling
        handles exceptions properly."""

        # Create a mock implementation similar to _add_price_history
        @with_error_handling
        async def mock_add_price_history(results):
            """Mocked _add_price_history function."""
            if "trigger_error" in results:
                raise ValueError("Price calculation error")
            return {"enhanced": True, **results}

        # Test normal operation
        test_results = {"origin": "JFK", "destination": "LAX"}
        result = await mock_add_price_history(test_results)
        assert "enhanced" in result
        assert result["enhanced"] is True

        # Test error handling
        result = await mock_add_price_history({"trigger_error": True})
        assert "error" in result
        assert "Price calculation error" in result["error"]

    @pytest.mark.asyncio
    async def test_get_price_history_with_error_handling(self):
        """Test that _get_price_history with error handling
        handles exceptions properly."""

        # Create a mock implementation similar to _get_price_history
        @with_error_handling
        async def mock_get_price_history(origin, destination, departure_date):
            """Mocked _get_price_history function."""
            if origin == "ERROR":
                raise ValueError("API connection error")
            return {
                "prices": [100, 120, 110],
                "dates": ["2025-06-01", "2025-06-02", "2025-06-03"],
            }

        # Test normal operation
        result = await mock_get_price_history("JFK", "LAX", "2025-06-01")
        assert "prices" in result
        assert len(result["prices"]) == 3

        # Test error handling
        result = await mock_get_price_history("ERROR", "LAX", "2025-06-01")
        assert "error" in result
        assert "API connection error" in result["error"]

    @pytest.mark.asyncio
    async def test_search_flexible_dates_with_error_handling(self):
        """Test that search_flexible_dates with error handling
        handles exceptions properly."""

        # Create a mock implementation similar to search_flexible_dates
        @with_error_handling
        async def mock_search_flexible_dates(params):
            """Mocked search_flexible_dates function."""
            if "date_from" not in params or "date_to" not in params:
                raise ValueError("Missing required parameters")
            if params.get("trigger_error"):
                raise ValueError("Date processing error")
            return {"flexible": True, "options": 5}

        # Test normal operation
        result = await mock_search_flexible_dates(
            {
                "origin": "JFK",
                "destination": "LAX",
                "date_from": "2025-06-01",
                "date_to": "2025-06-10",
            }
        )
        assert "flexible" in result
        assert result["flexible"] is True

        # Test error handling - missing params
        result = await mock_search_flexible_dates(
            {"origin": "JFK", "destination": "LAX"}
        )
        assert "error" in result
        assert "Missing required parameters" in result["error"]

        # Test error handling - processing error
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
        assert "Date processing error" in result["error"]
