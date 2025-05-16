"""
Tests for BaseMCPWrapper.

This module tests the abstract base wrapper class that all MCP wrappers inherit from.
"""


import pytest

from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper
from tripsage.mcp_abstraction.exceptions import TripSageMCPError


class TestWrapper(BaseMCPWrapper):
    """Concrete test implementation of BaseMCPWrapper."""

    def __init__(self, service_name="test-service"):
        self.service_name = service_name
        self.initialized = False
        self.method_mapping = {
            "test_method": "mapped_method",
            "another_method": "another_mapped_method",
        }

    async def initialize(self):
        """Initialize the wrapper."""
        self.initialized = True

    async def shutdown(self):
        """Shutdown the wrapper."""
        self.initialized = False

    async def mapped_method(self, **kwargs):
        """A mapped method for testing."""
        return {"result": "success", "params": kwargs}

    async def another_mapped_method(self, **kwargs):
        """Another mapped method for testing."""
        return {"result": "another success", "params": kwargs}


class ErrorWrapper(BaseMCPWrapper):
    """Wrapper that raises errors for testing error handling."""

    def __init__(self):
        self.service_name = "error-service"
        self.method_mapping = {"error_method": "raise_error"}

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    async def raise_error(self, **kwargs):
        """Method that always raises an error."""
        raise TripSageMCPError("Test error")


class TestBaseMCPWrapper:
    """Tests for BaseMCPWrapper functionality."""

    def test_abstract_base_class(self):
        """Test that BaseMCPWrapper cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseMCPWrapper()

    def test_concrete_implementation(self):
        """Test creating a concrete implementation."""
        wrapper = TestWrapper()

        assert wrapper.service_name == "test-service"
        assert wrapper.initialized is False
        assert wrapper.method_mapping is not None

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test wrapper initialization."""
        wrapper = TestWrapper()

        # Initially not initialized
        assert wrapper.initialized is False

        # Initialize
        await wrapper.initialize()

        # Now initialized
        assert wrapper.initialized is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test wrapper shutdown."""
        wrapper = TestWrapper()

        # Initialize first
        await wrapper.initialize()
        assert wrapper.initialized is True

        # Shutdown
        await wrapper.shutdown()

        # Now not initialized
        assert wrapper.initialized is False

    @pytest.mark.asyncio
    async def test_invoke_method_success(self):
        """Test successful method invocation."""
        wrapper = TestWrapper()

        # Test mapped method invocation
        result = await wrapper.invoke_method(
            "test_method", {"param1": "value1", "param2": 42}
        )

        # Verify result
        assert result["result"] == "success"
        assert result["params"] == {"param1": "value1", "param2": 42}

    @pytest.mark.asyncio
    async def test_invoke_method_not_found(self):
        """Test invocation of non-existent method."""
        wrapper = TestWrapper()

        # Test non-existent method
        with pytest.raises(TripSageMCPError) as exc_info:
            await wrapper.invoke_method("non_existent_method", {})

        assert "Method 'non_existent_method' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_method_with_error(self):
        """Test method invocation that raises an error."""
        wrapper = ErrorWrapper()

        # Test method that raises error
        with pytest.raises(TripSageMCPError) as exc_info:
            await wrapper.invoke_method("error_method", {})

        assert "Test error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_method_with_empty_params(self):
        """Test method invocation with empty parameters."""
        wrapper = TestWrapper()

        # Test with empty params
        result = await wrapper.invoke_method("test_method", {})

        # Verify result
        assert result["result"] == "success"
        assert result["params"] == {}

    @pytest.mark.asyncio
    async def test_multiple_method_mappings(self):
        """Test wrapper with multiple method mappings."""
        wrapper = TestWrapper()

        # Test first method
        result1 = await wrapper.invoke_method("test_method", {"param": "value1"})
        assert result1["result"] == "success"

        # Test second method
        result2 = await wrapper.invoke_method("another_method", {"param": "value2"})
        assert result2["result"] == "another success"

    def test_service_name_property(self):
        """Test service name property."""
        wrapper = TestWrapper("custom-service")
        assert wrapper.service_name == "custom-service"

    @pytest.mark.asyncio
    async def test_method_mapping_validation(self):
        """Test that method mapping is validated."""

        class InvalidWrapper(BaseMCPWrapper):
            def __init__(self):
                self.service_name = "invalid"
                self.method_mapping = {
                    "method1": "non_existent_method"  # Maps to non-existent method
                }

            async def initialize(self):
                pass

            async def shutdown(self):
                pass

        wrapper = InvalidWrapper()

        # Should raise error when trying to invoke
        with pytest.raises(TripSageMCPError) as exc_info:
            await wrapper.invoke_method("method1", {})

        assert "not found in wrapper" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test using wrapper as async context manager."""
        wrapper = TestWrapper()

        # Use as context manager
        async with wrapper:
            assert wrapper.initialized is True

            # Make a call within context
            result = await wrapper.invoke_method("test_method", {"param": "value"})
            assert result["result"] == "success"

        # After context exit
        assert wrapper.initialized is False
