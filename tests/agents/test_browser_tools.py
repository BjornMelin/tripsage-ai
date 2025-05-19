"""
Tests for browser tools using external MCPs.

These tests verify that browser tools correctly interface with external Playwright
and Stagehand MCP servers.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.agents.tools.browser.browser_tools import (
    FlightInfo,
    browser_service,
    check_flight_status,
    monitor_price,
    verify_booking,
)


class TestBrowserTools:
    """Test cases for browser tools."""

    @pytest.fixture
    def mock_redis_cache(self):
        """Mock Redis cache for testing."""
        with patch("src.agents.tools.browser.browser_tools.redis_cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.set.return_value = True
            yield mock_cache

    @pytest.fixture
    def mock_playwright_client(self):
        """Mock Playwright MCP client for testing."""
        with patch.object(browser_service, "playwright_client") as mock_client:
            mock_client.execute = AsyncMock()
            yield mock_client

    @pytest.fixture
    def mock_stagehand_client(self):
        """Mock Stagehand MCP client for testing."""
        with patch.object(browser_service, "stagehand_client") as mock_client:
            mock_client.execute = AsyncMock()
            yield mock_client

    @pytest.mark.asyncio
    async def test_check_flight_status(self, mock_redis_cache, mock_playwright_client):
        """Test check_flight_status function."""
        # Setup
        flight_info = FlightInfo(
            airline="AA",
            flight_number="123",
            departure_airport="JFK",
            arrival_airport="LAX",
            scheduled_departure=datetime.utcnow(),
            scheduled_arrival=datetime.utcnow(),
            status="On Time",
        )

        mock_response = {
            "flight_info": flight_info.model_dump(),
            "sessionId": "test-session-id",
        }
        mock_playwright_client.execute.return_value = mock_response

        # Execute
        result = await check_flight_status(
            airline="AA", flight_number="123", date="2025-05-01"
        )

        # Verify
        assert result["success"] is True
        assert result["airline"] == "AA"
        assert result["flight_number"] == "123"
        assert result["date"] == "2025-05-01"
        assert result["session_id"] == "test-session-id"
        assert "flight_info" in result
        assert result["flight_info"]["airline"] == "AA"

        # Verify MCP client call
        mock_playwright_client.execute.assert_called_once_with(
            "checkFlightStatus",
            {
                "airline": "AA",
                "flightNumber": "123",
                "date": "2025-05-01",
            },
        )

        # Verify caching
        mock_redis_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_booking(
        self, mock_redis_cache, mock_stagehand_client, mock_playwright_client
    ):
        """Test verify_booking function."""
        # Setup
        booking_details = {
            "passengerName": "John Smith",
            "origin": "JFK",
            "destination": "LAX",
            "departureDate": "2025-05-01",
            "returnDate": "2025-05-10",
            "flightNumber": "AA123",
            "status": "confirmed",
        }

        # Mock Stagehand navigation
        mock_stagehand_client.execute.side_effect = [
            {"sessionId": "test-session-id"},  # navigate result
            {"data": {}, "sessionId": "test-session-id"},  # act result
            {"data": booking_details},  # extract result
        ]

        # Mock Playwright screenshot
        mock_playwright_client.execute.return_value = {
            "screenshot": "base64-screenshot-data",
        }

        # Execute
        result = await verify_booking(
            booking_type="flight",
            provider="aa",
            confirmation_code="ABC123",
            last_name="Smith",
        )

        # Verify
        assert result["success"] is True
        assert result["booking_type"] == "flight"
        assert result["provider"] == "aa"
        assert result["booking_reference"] == "ABC123"
        assert result["session_id"] == "test-session-id"
        assert "booking_details" in result
        assert result["booking_details"]["passenger_name"] == "John Smith"
        assert result["booking_details"]["status"] == "confirmed"

        # Verify caching
        mock_redis_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitor_price(self, mock_redis_cache, mock_playwright_client):
        """Test monitor_price function."""
        # Setup
        # Mock navigation
        mock_playwright_client.execute.side_effect = [
            {"sessionId": "test-session-id"},  # navigate result
            {},  # wait_for_selector result
            {"text": "$99.99"},  # get_text result
            {"screenshot": "base64-screenshot-data"},  # screenshot result
        ]

        # Execute
        result = await monitor_price(
            url="https://example.com/product",
            selector=".price",
            check_frequency="daily",
            notification_threshold=5.0,
        )

        # Verify
        assert result["success"] is True
        assert result["url"] == "https://example.com/product"
        assert result["check_frequency"] == "daily"
        assert "next_check" in result
        assert "monitoring_id" in result
        assert result["session_id"] == "test-session-id"
        assert "initial_price" in result
        assert result["initial_price"]["amount"] == 99.99
        assert result["initial_price"]["currency"] == "USD"

        # Verify caching
        mock_redis_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_flight_status_cached(
        self, mock_redis_cache, mock_playwright_client
    ):
        """Test check_flight_status function with cached result."""
        # Setup
        flight_info = FlightInfo(
            airline="AA",
            flight_number="123",
            departure_airport="JFK",
            arrival_airport="LAX",
            scheduled_departure=datetime.utcnow(),
            scheduled_arrival=datetime.utcnow(),
            status="On Time",
        )

        cached_response = {
            "success": True,
            "airline": "AA",
            "flight_number": "123",
            "date": "2025-05-01",
            "flight_info": flight_info.model_dump(),
            "session_id": "cached-session-id",
            "timestamp": datetime.utcnow().isoformat(),
        }

        mock_redis_cache.get.return_value = json.dumps(cached_response)

        # Execute
        result = await check_flight_status(
            airline="AA", flight_number="123", date="2025-05-01"
        )

        # Verify
        assert result["success"] is True
        assert result["airline"] == "AA"
        assert result["flight_number"] == "123"
        assert result["date"] == "2025-05-01"
        assert result["session_id"] == "cached-session-id"
        assert "flight_info" in result

        # Verify MCP client was not called (cached result used)
        mock_playwright_client.execute.assert_not_called()

        # Verify caching was checked
        mock_redis_cache.get.assert_called_once()
        mock_redis_cache.set.assert_not_called()
