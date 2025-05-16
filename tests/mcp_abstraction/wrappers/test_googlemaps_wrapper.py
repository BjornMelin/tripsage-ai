"""Tests for GoogleMapsMCPWrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.mcp_abstraction.exceptions import (
    MCPClientError,
    MCPInvocationError,
    MCPTimeoutError,
    TripSageMCPError,
)
from tripsage.mcp_abstraction.wrappers.googlemaps_wrapper import GoogleMapsMCPWrapper


class TestGoogleMapsMCPWrapper:
    """Test cases for GoogleMapsMCPWrapper."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock GoogleMapsMCPClient."""
        client = MagicMock()
        # Setup common methods
        client.geocode = AsyncMock(
            return_value={"location": {"lat": 40.7128, "lng": -74.0060}}
        )
        client.reverse_geocode = AsyncMock(return_value={"address": "123 Main St"})
        client.search_places = AsyncMock(
            return_value={"places": [{"name": "Restaurant"}]}
        )
        client.get_place_details = AsyncMock(return_value={"details": {"rating": 4.5}})
        client.get_directions = AsyncMock(return_value={"route": "Take I-95"})
        client.get_distance_matrix = AsyncMock(return_value={"distance": "10 miles"})
        return client

    @pytest.fixture
    def wrapper(self, mock_client):
        """Create a GoogleMapsMCPWrapper with mocked client."""
        return GoogleMapsMCPWrapper(client=mock_client, mcp_name="maps-test")

    def test_initialization_with_client(self, mock_client):
        """Test wrapper initialization with provided client."""
        wrapper = GoogleMapsMCPWrapper(client=mock_client, mcp_name="maps-test")
        assert wrapper.client == mock_client
        assert wrapper.mcp_name == "maps-test"

    @patch("tripsage.mcp_abstraction.wrappers.googlemaps_wrapper.GoogleMapsMCPClient")
    def test_initialization_without_client(self, MockGoogleMapsClient):
        """Test wrapper initialization without provided client."""
        mock_singleton = MagicMock()
        MockGoogleMapsClient.get_client.return_value = mock_singleton

        wrapper = GoogleMapsMCPWrapper()

        MockGoogleMapsClient.get_client.assert_called_once()
        assert wrapper.client == mock_singleton
        assert wrapper.mcp_name == "google_maps"

    def test_method_map(self, wrapper):
        """Test method mapping is correctly built."""
        method_map = wrapper._method_map

        # Verify core methods are mapped
        assert method_map["geocode"] == "geocode"
        assert method_map["reverse_geocode"] == "reverse_geocode"
        assert method_map["search_places"] == "search_places"
        assert method_map["get_place_details"] == "get_place_details"
        assert method_map["get_directions"] == "get_directions"
        assert method_map["get_distance_matrix"] == "get_distance_matrix"

        # Verify all expected methods exist
        expected_methods = {
            "geocode",
            "reverse_geocode",
            "search_places",
            "get_place_details",
            "search_places_nearby",
            "search_places_text",
            "get_directions",
            "get_distance_matrix",
            "get_timezone",
            "get_elevation",
            "get_place_photo",
        }
        assert set(method_map.keys()) == expected_methods

    def test_get_available_methods(self, wrapper):
        """Test getting available methods."""
        methods = wrapper.get_available_methods()
        assert "geocode" in methods
        assert "reverse_geocode" in methods
        assert "search_places" in methods
        assert len(methods) == 11  # All expected methods

    @pytest.mark.asyncio
    async def test_invoke_geocode(self, wrapper):
        """Test invoking geocode method."""
        result = await wrapper.invoke_method(
            "geocode", address="1600 Amphitheatre Parkway, Mountain View, CA"
        )
        assert result == {"location": {"lat": 40.7128, "lng": -74.0060}}
        wrapper.client.geocode.assert_called_once_with(
            address="1600 Amphitheatre Parkway, Mountain View, CA"
        )

    @pytest.mark.asyncio
    async def test_invoke_reverse_geocode(self, wrapper):
        """Test invoking reverse_geocode method."""
        result = await wrapper.invoke_method(
            "reverse_geocode", lat=40.7128, lng=-74.0060
        )
        assert result == {"address": "123 Main St"}
        wrapper.client.reverse_geocode.assert_called_once_with(
            lat=40.7128, lng=-74.0060
        )

    @pytest.mark.asyncio
    async def test_invoke_search_places(self, wrapper):
        """Test invoking search_places method."""
        result = await wrapper.invoke_method(
            "search_places",
            query="restaurants near Times Square",
            location={"lat": 40.758, "lng": -73.985},
        )
        assert result == {"places": [{"name": "Restaurant"}]}
        wrapper.client.search_places.assert_called_once_with(
            query="restaurants near Times Square",
            location={"lat": 40.758, "lng": -73.985},
        )

    @pytest.mark.asyncio
    async def test_invoke_get_directions(self, wrapper):
        """Test invoking get_directions method."""
        result = await wrapper.invoke_method(
            "get_directions",
            origin="New York, NY",
            destination="Boston, MA",
            mode="driving",
        )
        assert result == {"route": "Take I-95"}
        wrapper.client.get_directions.assert_called_once_with(
            origin="New York, NY", destination="Boston, MA", mode="driving"
        )

    @pytest.mark.asyncio
    async def test_invoke_unknown_method(self, wrapper):
        """Test invoking unknown method raises error."""
        with pytest.raises(MCPInvocationError, match="Method unknown_method not found"):
            await wrapper.invoke_method("unknown_method")

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, wrapper):
        """Test connection error handling."""
        wrapper.client.geocode.side_effect = ConnectionError("Network error")

        with pytest.raises(MCPClientError):
            await wrapper.invoke_method("geocode", address="123 Main St")

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, wrapper):
        """Test timeout error handling."""
        wrapper.client.geocode.side_effect = TimeoutError("Request timed out")

        with pytest.raises(MCPTimeoutError):
            await wrapper.invoke_method("geocode", address="123 Main St")

    @pytest.mark.asyncio
    async def test_generic_error_handling(self, wrapper):
        """Test generic error handling."""
        wrapper.client.geocode.side_effect = Exception("Something went wrong")

        with pytest.raises(TripSageMCPError):
            await wrapper.invoke_method("geocode", address="123 Main St")

    @pytest.mark.asyncio
    async def test_parameter_forwarding(self, wrapper):
        """Test that parameters are correctly forwarded to client methods."""
        # Test with multiple parameters
        await wrapper.invoke_method(
            "get_distance_matrix",
            origins=["New York, NY"],
            destinations=["Boston, MA", "Philadelphia, PA"],
            mode="driving",
            units="imperial",
        )

        wrapper.client.get_distance_matrix.assert_called_once_with(
            origins=["New York, NY"],
            destinations=["Boston, MA", "Philadelphia, PA"],
            mode="driving",
            units="imperial",
        )

    def test_context_manager(self, wrapper):
        """Test wrapper can be used as context manager."""
        with wrapper as w:
            assert w == wrapper

        # Verify no errors are raised
        assert True

    def test_repr(self, wrapper):
        """Test string representation."""
        assert repr(wrapper) == "<GoogleMapsMCPWrapper(mcp_name='maps-test')>"
