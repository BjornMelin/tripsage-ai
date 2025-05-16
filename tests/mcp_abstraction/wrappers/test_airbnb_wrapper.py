"""Test suite for AirbnbMCPWrapper."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage.mcp_abstraction.exceptions import MCPClientError
from tripsage.mcp_abstraction.wrappers.airbnb_wrapper import AirbnbMCPWrapper


@pytest.fixture
def mock_airbnb_client():
    """Create a mock Airbnb MCP client."""
    client = Mock()
    client.search_accommodations = AsyncMock()
    client.get_listing_details = AsyncMock()
    return client


@pytest.fixture
def mock_settings():
    """Create mock settings with valid configuration."""
    settings = Mock()
    settings.airbnb_enabled = True
    settings.airbnb_config = {
        "command": "uvx",
        "args": ["--from", "airbnb-mcp", "airbnb-mcp"],
        "env": {
            "AIRBNB_CLIENT_ID": "test_client_id",
            "AIRBNB_CLIENT_SECRET": "test_client_secret"
        }
    }
    return settings


@pytest.fixture
def mock_disabled_settings():
    """Create mock settings with disabled Airbnb MCP."""
    settings = Mock()
    settings.airbnb_enabled = False
    settings.airbnb_config = None
    return settings


class TestAirbnbMCPWrapper:
    """Test AirbnbMCPWrapper functionality."""

    def test_initialization_enabled(self, mock_settings):
        """Test initialization with enabled configuration."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_settings):
            wrapper = AirbnbMCPWrapper()
            assert wrapper.client_type == "airbnb"
            assert wrapper.enabled is True
            assert wrapper.config == mock_settings.airbnb_config

    def test_initialization_disabled(self, mock_disabled_settings):
        """Test initialization with disabled configuration."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_disabled_settings):
            wrapper = AirbnbMCPWrapper()
            assert wrapper.client_type == "airbnb"
            assert wrapper.enabled is False
            assert wrapper.config is None

    def test_build_method_map(self, mock_settings, mock_airbnb_client):
        """Test method map building."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_settings):
            wrapper = AirbnbMCPWrapper()
            wrapper._client = mock_airbnb_client
            wrapper._build_method_map()
            
            # Check that all standardized methods are mapped
            expected_methods = [
                'search', 'search_listings', 'search_accommodations',
                'get_listing', 'get_details', 'get_listing_details',
                'get_accommodation_details', 'check_availability',
                'check_listing_availability'
            ]
            
            for method in expected_methods:
                assert method in wrapper.method_map

    @pytest.mark.asyncio
    async def test_invoke_search_methods(self, mock_settings, mock_airbnb_client):
        """Test invoking search-related methods."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_settings):
            wrapper = AirbnbMCPWrapper()
            wrapper._client = mock_airbnb_client
            await wrapper.initialize()
            
            # Test search method variants
            search_params = {
                "location": "Paris",
                "adults": 2,
                "check_in": "2024-05-01",
                "check_out": "2024-05-05"
            }
            
            # Mock response
            mock_response = [
                {"id": "1", "title": "Paris Studio", "price": 50},
                {"id": "2", "title": "Cozy Apartment", "price": 75}
            ]
            mock_airbnb_client.search_accommodations.return_value = mock_response
            
            # Test different method variants
            methods = ['search', 'search_listings', 'search_accommodations']
            for method in methods:
                result = await wrapper.invoke(method, **search_params)
                assert result == mock_response
                mock_airbnb_client.search_accommodations.assert_called_with(**search_params)

    @pytest.mark.asyncio
    async def test_invoke_get_listing_methods(self, mock_settings, mock_airbnb_client):
        """Test invoking get listing methods."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_settings):
            wrapper = AirbnbMCPWrapper()
            wrapper._client = mock_airbnb_client
            await wrapper.initialize()
            
            # Test get listing method variants
            listing_params = {"listing_id": "12345"}
            
            # Mock response
            mock_response = {
                "id": "12345",
                "title": "Beautiful Apartment",
                "description": "A lovely place to stay",
                "price": 100,
                "amenities": ["WiFi", "Kitchen"]
            }
            mock_airbnb_client.get_listing_details.return_value = mock_response
            
            # Test different method variants
            methods = [
                'get_listing', 'get_details', 'get_listing_details',
                'get_accommodation_details'
            ]
            for method in methods:
                result = await wrapper.invoke(method, **listing_params)
                assert result == mock_response
                mock_airbnb_client.get_listing_details.assert_called_with(**listing_params)

    @pytest.mark.asyncio
    async def test_invoke_check_availability_methods(self, mock_settings,
                                              mock_airbnb_client):
        """Test invoking check availability methods."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_settings):
            wrapper = AirbnbMCPWrapper()
            wrapper._client = mock_airbnb_client
            await wrapper.initialize()
            
            # Test check availability method variants
            availability_params = {
                "listing_id": "12345",
                "check_in": "2024-05-01",
                "check_out": "2024-05-05"
            }
            
            # Mock response (using get_listing_details as stated in wrapper)
            mock_response = {
                "id": "12345",
                "availability": [
                    {"date": "2024-05-01", "available": True},
                    {"date": "2024-05-02", "available": True},
                    {"date": "2024-05-03", "available": True},
                    {"date": "2024-05-04", "available": True}
                ]
            }
            mock_airbnb_client.get_listing_details.return_value = mock_response
            
            # Test different method variants
            methods = ['check_availability', 'check_listing_availability']
            for method in methods:
                result = await wrapper.invoke(method, **availability_params)
                assert result == mock_response
                mock_airbnb_client.get_listing_details.assert_called_with(**availability_params)

    @pytest.mark.asyncio
    async def test_invoke_with_error(self, mock_settings, mock_airbnb_client):
        """Test error handling during method invocation."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_settings):
            wrapper = AirbnbMCPWrapper()
            wrapper._client = mock_airbnb_client
            await wrapper.initialize()
            
            # Mock error response
            error = Exception("API Error")
            mock_airbnb_client.search_accommodations.side_effect = error
            
            with pytest.raises(MCPClientError) as exc_info:
                await wrapper.invoke("search", location="Paris")
            
            assert "Failed to execute search" in str(exc_info.value)
            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_disabled_client(self, mock_disabled_settings):
        """Test invoking methods on disabled client."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_disabled_settings):
            wrapper = AirbnbMCPWrapper()
            
            with pytest.raises(MCPClientError) as exc_info:
                await wrapper.invoke("search", location="Paris")
            
            assert "Airbnb MCP is not enabled" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_not_initialized(self, mock_settings):
        """Test invoking methods before initialization."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_settings):
            wrapper = AirbnbMCPWrapper()
            
            with pytest.raises(MCPClientError) as exc_info:
                await wrapper.invoke("search", location="Paris")
            
            assert "Airbnb MCP client not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_unknown_method(self, mock_settings, mock_airbnb_client):
        """Test invoking unknown method."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_settings):
            wrapper = AirbnbMCPWrapper()
            wrapper._client = mock_airbnb_client
            await wrapper.initialize()
            
            with pytest.raises(MCPClientError) as exc_info:
                await wrapper.invoke("unknown_method")
            
            assert "Unknown method: unknown_method" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_function_wrapper(self, mock_settings, mock_airbnb_client):
        """Test that async functions are properly wrapped."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_settings):
            wrapper = AirbnbMCPWrapper()
            wrapper._client = mock_airbnb_client
            await wrapper.initialize()
            
            # Create a non-async mock function
            sync_func = Mock(return_value={"result": "sync"})
            
            # Test wrapping sync function
            wrapped = wrapper._ensure_async_function(sync_func)
            result = await wrapped(test_param="value")
            
            assert result == {"result": "sync"}
            sync_func.assert_called_once_with(test_param="value")
            
            # Test wrapping async function
            async_func = AsyncMock(return_value={"result": "async"})
            wrapped = wrapper._ensure_async_function(async_func)
            result = await wrapped(test_param="value")
            
            assert result == {"result": "async"}
            async_func.assert_called_once_with(test_param="value")

    @pytest.mark.asyncio
    async def test_get_available_methods(self, mock_settings, mock_airbnb_client):
        """Test getting available methods."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_settings):
            wrapper = AirbnbMCPWrapper()
            wrapper._client = mock_airbnb_client
            await wrapper.initialize()
            
            methods = await wrapper.get_available_methods()
            
            # Check that all expected methods are available
            expected_methods = [
                'search', 'search_listings', 'search_accommodations',
                'get_listing', 'get_details', 'get_listing_details',
                'get_accommodation_details', 'check_availability',
                'check_listing_availability'
            ]
            
            for method in expected_methods:
                assert method in methods

    @pytest.mark.asyncio
    async def test_initialization_with_client_class(self, mock_settings):
        """Test initialization attempts to create client."""
        # Mock the AirbnbMCPClient class
        mock_client_class = Mock()
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        client_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.AirbnbMCPClient'
        with patch(settings_path, mock_settings):
            with patch(client_path, mock_client_class):
                wrapper = AirbnbMCPWrapper()
                await wrapper.initialize()
                
                # Check client was created (normal behavior in tests)
                mock_client_class.assert_called_once()
                assert wrapper._client == mock_client_instance

    def test_method_map_construction(self, mock_settings):
        """Test that method map is properly constructed."""
        settings_path = 'tripsage.mcp_abstraction.wrappers.airbnb_wrapper.mcp_settings'
        with patch(settings_path, mock_settings):
            wrapper = AirbnbMCPWrapper()
            wrapper._client = Mock()
            
            # Add actual methods to mock client
            wrapper._client.search_accommodations = Mock()
            wrapper._client.get_listing_details = Mock()
            
            wrapper._build_method_map()
            
            # Verify search methods map to search_accommodations
            search_methods = ['search', 'search_listings', 'search_accommodations']
            for method in search_methods:
                assert wrapper.method_map[method] == wrapper._ensure_async_function(
                    wrapper._client.search_accommodations
                )
            
            # Verify get methods map to get_listing_details
            get_methods = [
                'get_listing', 'get_details', 'get_listing_details',
                'get_accommodation_details'
            ]
            for method in get_methods:
                assert wrapper.method_map[method] == wrapper._ensure_async_function(
                    wrapper._client.get_listing_details
                )
            
            # Verify availability methods map to get_listing_details
            availability_methods = ['check_availability', 'check_listing_availability']
            for method in availability_methods:
                assert wrapper.method_map[method] == wrapper._ensure_async_function(
                    wrapper._client.get_listing_details
                )