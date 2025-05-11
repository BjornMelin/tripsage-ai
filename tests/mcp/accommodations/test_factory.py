"""
Tests for the Airbnb MCP client factory.
"""

from unittest.mock import patch

import pytest

from src.mcp.accommodations.client import AirbnbMCPClient
from src.mcp.accommodations.factory import create_airbnb_client


class TestAirbnbClientFactory:
    """Tests for Airbnb client factory function."""

    @patch("src.mcp.accommodations.factory.config")
    def test_create_airbnb_client(self, mock_config):
        """Test creating an Airbnb client with configuration."""
        # Configure mock
        mock_config.accommodations_mcp.airbnb.endpoint = "http://test-endpoint"
        mock_config.redis.ttl_medium = 7200  # 2 hours

        # Create client
        client = create_airbnb_client()

        # Verify client configuration
        assert isinstance(client, AirbnbMCPClient)
        assert client.endpoint == "http://test-endpoint"
        assert client.use_cache is True
        assert client.cache_ttl == 7200

    @patch("src.mcp.accommodations.factory.config")
    @patch("src.mcp.accommodations.factory.logger")
    def test_create_airbnb_client_logging(self, mock_logger, mock_config):
        """Test that client creation is properly logged."""
        # Configure mock
        mock_config.accommodations_mcp.airbnb.endpoint = "http://test-endpoint"
        mock_config.redis.ttl_medium = 3600

        # Create client
        client = create_airbnb_client()

        # Verify logging
        mock_logger.debug.assert_called_once_with(
            "Creating Airbnb MCP client with endpoint: %s", "http://test-endpoint"
        )
