"""
Tests for the application of decorators in flight_search.py.

This module verifies that the error handling decorator correctly handles
exceptions in the flight search module methods.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tripsage.agents.flight_search import TripSageFlightSearch


class TestFlightSearchDecorators:
    """Test suite for flight search decorators."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, monkeypatch):
        """Set up global mocks needed for all tests."""
        # Mock redis cache
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        monkeypatch.setattr("src.agents.flight_search.redis_cache", mock_redis)

        # Mock logger
        mock_logger = MagicMock()
        monkeypatch.setattr("src.agents.flight_search.logger", mock_logger)

    @pytest.fixture
    def mock_flights_client(self):
        """Mock flights client fixture."""
        client = AsyncMock()
        client.search_flights = AsyncMock(return_value={"offers": []})
        client.get_flight_prices = AsyncMock(return_value={"prices": [], "dates": []})
        return client

    @pytest.fixture
    def mock_flights_service(self):
        """Mock flights service fixture."""
        service = AsyncMock()
        service.search_best_flights = AsyncMock(return_value={"offers": []})
        return service

    @pytest.fixture
    def flight_search(self, mock_flights_client, mock_flights_service):
        """Flight search instance with mocked dependencies."""
        return TripSageFlightSearch(
            flights_client=mock_flights_client, flights_service=mock_flights_service
        )

    @pytest.mark.asyncio
    async def test_search_flights_error_handling(
        self, flight_search, mock_flights_service
    ):
        """Test error handling in search_flights method."""
        # Setup: Configure service to raise exception
        mock_flights_service.search_best_flights.side_effect = ValueError(
            "Service error"
        )
        flight_search.flights_client.search_flights.side_effect = ValueError(
            "Client error"
        )

        # Execute: Call the method
        result = await flight_search.search_flights(
            {"origin": "JFK", "destination": "LAX", "departure_date": "2025-06-01"}
        )

        # Verify: Check error response format
        assert "error" in result
        assert "error" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_add_price_history_error_handling(self, flight_search):
        """Test error handling in _add_price_history method."""
        # Setup: Create a test result that should trigger an error in price calculation
        test_results = {
            "origin": "JFK",
            "destination": "LAX",
            "offers": [{"total_amount": 500}],
        }

        # Mock _get_price_history to return data that will cause an error in calculation
        flight_search._get_price_history = AsyncMock(
            return_value={
                "prices": [],  # Empty prices will cause division by zero
                "dates": [],
            }
        )

        # Execute
        result = await flight_search._add_price_history(test_results)

        # Verify: Should return the original results without crashing
        assert result == test_results

    @pytest.mark.asyncio
    async def test_get_price_history_error_handling(self, flight_search, monkeypatch):
        """Test error handling in _get_price_history method."""
        # Setup: Configure client to raise exception
        flight_search.flights_client.get_flight_prices.side_effect = ValueError(
            "API error"
        )

        # Mock db client to also raise exception for complete coverage
        mock_db_client = AsyncMock()
        mock_db_client.get_flight_price_history = AsyncMock(
            side_effect=ValueError("DB error")
        )
        mock_get_db_client = MagicMock(return_value=mock_db_client)
        monkeypatch.setattr(
            "src.agents.flight_search.get_db_client", mock_get_db_client
        )

        # Execute
        result = await flight_search._get_price_history("JFK", "LAX", "2025-06-01")

        # Verify: Should return empty history without crashing
        assert "prices" in result
        assert len(result["prices"]) == 0
        assert "dates" in result
        assert len(result["dates"]) == 0
        assert "count" in result
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_search_flexible_dates_error_handling(self, flight_search):
        """Test error handling in search_flexible_dates method."""
        # Setup: Configure the search_flights method to raise an exception
        flight_search.search_flights = AsyncMock(side_effect=ValueError("Search error"))

        # Execute: Call with valid parameters
        result = await flight_search.search_flexible_dates(
            {
                "origin": "JFK",
                "destination": "LAX",
                "date_from": "2025-06-01",
                "date_to": "2025-06-10",
            }
        )

        # Verify: Should return structured response with empty results
        assert "origin" in result
        assert "destination" in result
        assert "date_range" in result
        assert "all_dates" in result
        assert len(result["all_dates"]) == 0
        assert result["total_options"] == 0
