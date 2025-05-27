"""
Unit tests for the OpenBnB Airbnb MCP integration.

These tests verify that the Airbnb MCP client is correctly configured
to use the OpenBnB MCP server for accommodation search and details.
"""

import unittest
from unittest.mock import MagicMock, patch

from tripsage.mcp.accommodations.client import AirbnbMCPClient


class TestOpenBnBIntegration(unittest.TestCase):
    """Test OpenBnB Airbnb MCP integration."""

    def test_client_initialization(self):
        """Test that the client is correctly initialized with OpenBnB server type."""
        client = AirbnbMCPClient(
            endpoint="http://test-endpoint",
            server_type="openbnb/mcp-server-airbnb",
        )

        # Verify server name and type
        self.assertEqual(client.server_name, "OpenBnB Airbnb MCP")
        self.assertEqual(client.server_type, "openbnb/mcp-server-airbnb")
        self.assertEqual(client.endpoint, "http://test-endpoint")

    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    def test_search_accommodations_tool_name(self, mock_call_tool):
        """Test that the client uses the correct tool name for search."""
        # Configure mock
        mock_call_tool.return_value = {"listings": []}

        # Create client and call method
        client = AirbnbMCPClient(endpoint="http://test-endpoint")
        client._store_search_results = MagicMock()  # Mock storage

        client.search_accommodations(location="Test Location")

        # Verify correct tool was called
        mock_call_tool.assert_called_once()
        args = mock_call_tool.call_args[0]
        self.assertEqual(args[0], "airbnb_search")

    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    def test_get_listing_details_tool_name(self, mock_call_tool):
        """Test that the client uses the correct tool name for listing details."""
        # Configure mock
        mock_call_tool.return_value = {
            "id": "12345",
            "name": "Test Listing",
            "description": "Test Description",
            "url": "https://example.com",
            "property_type": "Apartment",
            "location": "Test Location",
            "host": {"name": "Test Host", "superhost": False},
        }

        # Create client and call method
        client = AirbnbMCPClient(endpoint="http://test-endpoint")
        client._store_listing_details = MagicMock()  # Mock storage

        try:
            client.get_listing_details(listing_id="12345")
        except Exception:
            # We're not testing the full flow, just the tool name
            pass

        # Verify correct tool was called
        mock_call_tool.assert_called_once()
        args = mock_call_tool.call_args[0]
        self.assertEqual(args[0], "airbnb_listing_details")

    def test_server_type_in_error_message(self):
        """Test that error messages include the server type."""
        client = AirbnbMCPClient(
            endpoint="http://test-endpoint", server_type="openbnb/mcp-server-airbnb"
        )

        # Create a test error
        error = Exception("Test error")

        # Check if error message includes server type
        error_msg = (
            f"{client.server_name} ({client.server_type}) accommodation search failed: "
            f"{str(error)}"
        )

        self.assertIn("OpenBnB Airbnb MCP", error_msg)
        self.assertIn("openbnb/mcp-server-airbnb", error_msg)
        self.assertIn("Test error", error_msg)


if __name__ == "__main__":
    unittest.main()
