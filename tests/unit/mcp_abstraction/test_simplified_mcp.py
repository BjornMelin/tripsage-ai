"""
Tests for the simplified MCP abstraction layer for Airbnb.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.mcp_abstraction import (
    AirbnbMCPWrapper,
    BaseMCPWrapper,
    MCPAuthenticationError,
    MCPClientError,
    MCPInvocationError,
    MCPManager,
    MCPMethodNotFoundError,
    MCPRateLimitError,
    MCPRegistrationError,
    MCPTimeoutError,
    mcp_manager,
    registry,
)


class TestMCPManager:
    """Test the simplified MCPManager for Airbnb operations."""

    @pytest.fixture
    def manager(self):
        """Create a fresh MCPManager instance."""
        return MCPManager()

    @pytest.fixture
    def mock_wrapper(self):
        """Create a mock AirbnbMCPWrapper."""
        wrapper = MagicMock(spec=AirbnbMCPWrapper)
        wrapper.invoke_method = AsyncMock()
        wrapper.get_available_methods.return_value = [
            "search_listings",
            "get_listing_details",
        ]
        return wrapper

    async def test_initialize_creates_wrapper(self, manager):
        """Test that initialize creates an AirbnbMCPWrapper."""
        with patch(
            "tripsage.mcp_abstraction.manager.AirbnbMCPWrapper"
        ) as mock_wrapper_class:
            mock_wrapper_class.return_value = MagicMock(spec=AirbnbMCPWrapper)

            wrapper = await manager.initialize()

            assert wrapper is not None
            assert manager._wrapper is wrapper
            mock_wrapper_class.assert_called_once()

    async def test_initialize_returns_existing_wrapper(self, manager, mock_wrapper):
        """Test that initialize returns existing wrapper if already initialized."""
        manager._wrapper = mock_wrapper

        wrapper = await manager.initialize()

        assert wrapper is mock_wrapper

    async def test_initialize_handles_errors(self, manager):
        """Test that initialize properly handles initialization errors."""
        with patch(
            "tripsage.mcp_abstraction.manager.AirbnbMCPWrapper",
            side_effect=ValueError("Config error"),
        ):
            with pytest.raises(MCPInvocationError) as exc_info:
                await manager.initialize()

            assert "Failed to initialize Airbnb MCP" in str(exc_info.value)
            assert exc_info.value.mcp_name == "airbnb"

    async def test_invoke_initializes_if_needed(self, manager):
        """Test that invoke initializes the wrapper if not already done."""
        mock_wrapper = MagicMock(spec=AirbnbMCPWrapper)
        mock_wrapper.invoke_method = AsyncMock(return_value={"results": []})

        async def mock_initialize():
            manager._wrapper = mock_wrapper
            return mock_wrapper

        with patch.object(
            manager, "initialize", side_effect=mock_initialize
        ) as mock_init:
            manager._wrapper = None  # Ensure wrapper is None to trigger initialization

            result = await manager.invoke("search_listings", location="Paris")

            mock_init.assert_called_once()
            assert result == {"results": []}

    async def test_invoke_calls_wrapper_method(self, manager, mock_wrapper):
        """Test that invoke calls the wrapper's invoke_method."""
        manager._wrapper = mock_wrapper
        mock_wrapper.invoke_method.return_value = {"listings": ["listing1", "listing2"]}

        result = await manager.invoke(
            "search_listings", params={"location": "London"}, adults=2
        )

        mock_wrapper.invoke_method.assert_called_once_with(
            "search_listings", location="London", adults=2
        )
        assert result == {"listings": ["listing1", "listing2"]}

    async def test_invoke_handles_timeout_error(self, manager, mock_wrapper):
        """Test that invoke properly maps timeout errors."""
        manager._wrapper = mock_wrapper
        mock_wrapper.invoke_method.side_effect = TimeoutError("Request timed out")

        with pytest.raises(MCPTimeoutError) as exc_info:
            await manager.invoke("search_listings")

        assert "timed out" in str(exc_info.value).lower()
        assert exc_info.value.mcp_name == "airbnb"

    async def test_invoke_handles_auth_error(self, manager, mock_wrapper):
        """Test that invoke properly maps authentication errors."""
        manager._wrapper = mock_wrapper
        mock_wrapper.invoke_method.side_effect = Exception("401 Unauthorized")

        with pytest.raises(MCPAuthenticationError) as exc_info:
            await manager.invoke("search_listings")

        assert exc_info.value.mcp_name == "airbnb"

    async def test_invoke_handles_rate_limit_error(self, manager, mock_wrapper):
        """Test that invoke properly maps rate limit errors."""
        manager._wrapper = mock_wrapper
        mock_wrapper.invoke_method.side_effect = Exception("429 Rate limit exceeded")

        with pytest.raises(MCPRateLimitError) as exc_info:
            await manager.invoke("search_listings")

        assert exc_info.value.mcp_name == "airbnb"

    async def test_invoke_handles_method_not_found(self, manager, mock_wrapper):
        """Test that invoke properly maps method not found errors."""
        manager._wrapper = mock_wrapper
        mock_wrapper.invoke_method.side_effect = Exception("Unknown method: foo")

        with pytest.raises(MCPMethodNotFoundError) as exc_info:
            await manager.invoke("foo")

        assert exc_info.value.mcp_name == "airbnb"
        assert exc_info.value.method_name == "foo"

    async def test_invoke_handles_generic_error(self, manager, mock_wrapper):
        """Test that invoke handles generic errors."""
        manager._wrapper = mock_wrapper
        mock_wrapper.invoke_method.side_effect = Exception("Something went wrong")

        with pytest.raises(MCPInvocationError) as exc_info:
            await manager.invoke("search_listings")

        assert "Failed to invoke airbnb.search_listings" in str(exc_info.value)

    def test_get_available_methods_without_initialization(self, manager):
        """Test get_available_methods returns default methods without init."""
        methods = manager.get_available_methods()

        assert "search_listings" in methods
        assert "get_listing_details" in methods
        assert "check_availability" in methods

    def test_get_available_methods_with_wrapper(self, manager, mock_wrapper):
        """Test get_available_methods delegates to wrapper when initialized."""
        manager._wrapper = mock_wrapper

        methods = manager.get_available_methods()

        mock_wrapper.get_available_methods.assert_called_once()
        assert methods == ["search_listings", "get_listing_details"]


class TestMCPRegistry:
    """Test the simplified MCPRegistry for Airbnb."""

    @pytest.fixture
    def test_registry(self):
        """Create a fresh registry instance."""
        from tripsage.mcp_abstraction.registry import MCPRegistry

        return MCPRegistry()

    def test_register_airbnb_validates_wrapper_class(self, test_registry):
        """Test that register_airbnb validates the wrapper class."""

        class InvalidWrapper:
            pass

        with pytest.raises(MCPRegistrationError) as exc_info:
            test_registry.register_airbnb(InvalidWrapper)

        assert "must inherit from BaseMCPWrapper" in str(exc_info.value)

    def test_register_airbnb_accepts_valid_wrapper(self, test_registry):
        """Test that register_airbnb accepts valid wrapper class."""

        class ValidWrapper(BaseMCPWrapper):
            def get_available_methods(self):
                return []

        test_registry.register_airbnb(ValidWrapper)

        assert test_registry._wrapper_class == ValidWrapper

    def test_get_airbnb_wrapper_auto_registers(self, test_registry):
        """Test that get_airbnb_wrapper auto-registers if needed."""
        with patch.object(test_registry, "_auto_register") as mock_auto:
            mock_auto.side_effect = lambda: setattr(
                test_registry, "_wrapper_class", AirbnbMCPWrapper
            )

            wrapper_class = test_registry.get_airbnb_wrapper()

            mock_auto.assert_called_once()
            assert wrapper_class == AirbnbMCPWrapper

    def test_get_airbnb_wrapper_raises_if_not_registered(self, test_registry):
        """Test that get_airbnb_wrapper raises if wrapper not registered."""
        with patch.object(test_registry, "_auto_register"):
            with pytest.raises(MCPRegistrationError) as exc_info:
                test_registry.get_airbnb_wrapper()

            assert "Airbnb MCP wrapper not registered" in str(exc_info.value)


class TestAirbnbMCPWrapper:
    """Test the AirbnbMCPWrapper implementation."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Airbnb MCP client."""
        client = MagicMock()
        client.search_accommodations = AsyncMock()
        client.get_listing_details = AsyncMock()
        return client

    @pytest.fixture
    def wrapper(self, mock_client):
        """Create an AirbnbMCPWrapper with mock client."""
        return AirbnbMCPWrapper(client=mock_client)

    def test_wrapper_initialization_with_client(self, mock_client):
        """Test wrapper initialization with provided client."""
        wrapper = AirbnbMCPWrapper(client=mock_client)

        assert wrapper._client == mock_client
        assert wrapper._mcp_name == "airbnb"

    @patch("tripsage.mcp_abstraction.wrappers.airbnb_wrapper.settings")
    @patch("tripsage.mcp_abstraction.wrappers.airbnb_wrapper.AirbnbMCPClient")
    def test_wrapper_initialization_without_client(
        self, mock_client_class, mock_settings
    ):
        """Test wrapper initialization creates client from config."""
        mock_settings.airbnb.enabled = True
        mock_settings.airbnb.url = "http://localhost:8080"
        mock_settings.airbnb.timeout = 30
        mock_settings.airbnb.retry_attempts = 3
        mock_settings.airbnb.retry_backoff = 1

        AirbnbMCPWrapper()

        mock_client_class.assert_called_once_with(
            endpoint="http://localhost:8080",
            timeout=30,
            use_cache=True,
            cache_ttl=60,
        )

    @patch("tripsage.mcp_abstraction.wrappers.airbnb_wrapper.settings")
    def test_wrapper_initialization_fails_if_disabled(self, mock_settings):
        """Test wrapper initialization fails if Airbnb is disabled."""
        mock_settings.airbnb.enabled = False

        with pytest.raises(ValueError) as exc_info:
            AirbnbMCPWrapper()

        assert "Airbnb MCP is not enabled" in str(exc_info.value)

    def test_get_available_methods(self, wrapper):
        """Test get_available_methods returns all supported methods."""
        methods = wrapper.get_available_methods()

        assert "search_listings" in methods
        assert "search_accommodations" in methods
        assert "search" in methods
        assert "get_listing_details" in methods
        assert "get_listing" in methods
        assert "get_details" in methods
        assert "get_accommodation_details" in methods
        assert "check_availability" in methods
        assert "check_listing_availability" in methods

    async def test_invoke_method_maps_search_methods(self, wrapper, mock_client):
        """Test invoke_method maps search method names correctly."""
        mock_client.search_accommodations.return_value = {"results": []}

        # Test various search method aliases
        for method in ["search_listings", "search_accommodations", "search"]:
            result = await wrapper.invoke_method(method, location="Paris")
            assert result == {"results": []}

        # All should call search_accommodations
        assert mock_client.search_accommodations.call_count == 3

    async def test_invoke_method_maps_details_methods(self, wrapper, mock_client):
        """Test invoke_method maps details method names correctly."""
        mock_client.get_listing_details.return_value = {"id": "123"}

        # Test various details method aliases
        for method in [
            "get_listing_details",
            "get_listing",
            "get_details",
            "get_accommodation_details",
            "check_availability",
            "check_listing_availability",
        ]:
            result = await wrapper.invoke_method(method, listing_id="123")
            assert result == {"id": "123"}

        # All should call get_listing_details
        assert mock_client.get_listing_details.call_count == 6

    async def test_invoke_method_validates_method_name(self, wrapper):
        """Test invoke_method validates the method name."""
        with pytest.raises(MCPMethodNotFoundError) as exc_info:
            await wrapper.invoke_method("invalid_method")

        assert "Method 'invalid_method' not available" in str(exc_info.value)
        assert exc_info.value.mcp_name == "airbnb"

    async def test_invoke_method_handles_client_errors(self, wrapper, mock_client):
        """Test invoke_method handles client errors properly."""
        mock_client.search_accommodations.side_effect = Exception("API error")

        with pytest.raises(MCPClientError) as exc_info:
            await wrapper.invoke_method("search", location="Paris")

        assert "Failed to invoke method 'search' on airbnb" in str(exc_info.value)
        assert exc_info.value.original_error is not None
        assert "API error" in str(exc_info.value.original_error)


class TestGlobalInstances:
    """Test global instances are properly initialized."""

    def test_global_mcp_manager_instance(self):
        """Test that global mcp_manager is initialized."""
        assert mcp_manager is not None
        assert isinstance(mcp_manager, MCPManager)

    def test_global_registry_instance(self):
        """Test that global registry is initialized."""
        assert registry is not None
        from tripsage.mcp_abstraction.registry import MCPRegistry

        assert isinstance(registry, MCPRegistry)
