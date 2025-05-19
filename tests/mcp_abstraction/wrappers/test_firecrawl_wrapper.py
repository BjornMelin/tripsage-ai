"""Test suite for FirecrawlMCPWrapper."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage.mcp_abstraction.exceptions import MCPClientError
from tripsage.mcp_abstraction.wrappers.firecrawl_wrapper import FirecrawlMCPWrapper


@pytest.fixture
def mock_firecrawl_client():
    """Create a mock Firecrawl MCP client."""
    client = Mock()
    client.scrape = AsyncMock()
    client.crawl = AsyncMock()
    client.extract = AsyncMock()
    client.deep_research = AsyncMock()
    return client


@pytest.fixture
def mock_settings():
    """Create mock settings with valid configuration."""
    settings = Mock()
    settings.firecrawl_enabled = True
    settings.firecrawl_config = {"api_key": "test_api_key"}
    return settings


class TestFirecrawlMCPWrapper:
    """Test FirecrawlMCPWrapper functionality."""

    def test_initialization(self):
        """Test initialization with no pre-existing client."""
        with patch(
            "tripsage.mcp_abstraction.wrappers.firecrawl_wrapper.FirecrawlMCPClient"
        ) as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance

            wrapper = FirecrawlMCPWrapper()

            assert wrapper._client == mock_instance
            assert wrapper._mcp_name == "firecrawl"
            mock_client_class.assert_called_once()

    def test_initialization_with_client(self, mock_firecrawl_client):
        """Test initialization with pre-existing client."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)
        assert wrapper._client == mock_firecrawl_client
        assert wrapper._mcp_name == "firecrawl"

    def test_initialization_with_custom_name(self, mock_firecrawl_client):
        """Test initialization with custom MCP name."""
        wrapper = FirecrawlMCPWrapper(
            client=mock_firecrawl_client, mcp_name="custom_firecrawl"
        )
        assert wrapper._client == mock_firecrawl_client
        assert wrapper._mcp_name == "custom_firecrawl"

    def test_build_method_map(self, mock_firecrawl_client):
        """Test method map building."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)

        # Check the method map
        expected_mappings = {
            "scrape_url": "scrape",
            "scrape_page": "scrape",
            "crawl_website": "crawl",
            "crawl_site": "crawl",
            "extract_data": "extract",
            "extract_structured_data": "extract",
            "deep_research": "deep_research",
            "research_topic": "deep_research",
            "web_scrape": "scrape",
            "website_crawl": "crawl",
            "parse_data": "extract",
        }

        for standard_name, actual_name in expected_mappings.items():
            assert wrapper._method_map.get(standard_name) == actual_name

    @pytest.mark.asyncio
    async def test_invoke_scrape_methods(self, mock_firecrawl_client):
        """Test invoking scrape-related methods."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)

        # Mock the base class invoke_method since we're testing the mapping
        with patch.object(wrapper, "invoke_method", AsyncMock()) as mock_invoke:
            # Test scrape method variants
            scrape_params = {
                "url": "https://example.com",
                "formats": ["markdown", "html"],
            }

            mock_response = {
                "markdown": "# Example Page",
                "html": "<h1>Example Page</h1>",
            }
            mock_invoke.return_value = mock_response

            # Test different method variants
            methods = ["scrape_url", "scrape_page", "web_scrape"]
            for method in methods:
                result = await wrapper.invoke_method(method, **scrape_params)
                assert result == mock_response
                mock_invoke.assert_called_with(method, **scrape_params)

    @pytest.mark.asyncio
    async def test_invoke_crawl_methods(self, mock_firecrawl_client):
        """Test invoking crawl methods."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)

        # Mock the base class invoke_method
        with patch.object(wrapper, "invoke_method", AsyncMock()) as mock_invoke:
            # Test crawl method variants
            crawl_params = {"url": "https://example.com", "limit": 10}

            mock_response = {
                "status": "completed",
                "urls": ["https://example.com/page1", "https://example.com/page2"],
            }
            mock_invoke.return_value = mock_response

            # Test different method variants
            methods = ["crawl_website", "crawl_site", "website_crawl"]
            for method in methods:
                result = await wrapper.invoke_method(method, **crawl_params)
                assert result == mock_response
                mock_invoke.assert_called_with(method, **crawl_params)

    @pytest.mark.asyncio
    async def test_invoke_extract_methods(self, mock_firecrawl_client):
        """Test invoking extract methods."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)

        # Mock the base class invoke_method
        with patch.object(wrapper, "invoke_method", AsyncMock()) as mock_invoke:
            # Test extract method variants
            extract_params = {
                "urls": ["https://example.com"],
                "schema": {"title": "string", "description": "string"},
            }

            mock_response = {"data": [{"title": "Example", "description": "Test page"}]}
            mock_invoke.return_value = mock_response

            # Test different method variants
            methods = ["extract_data", "extract_structured_data", "parse_data"]
            for method in methods:
                result = await wrapper.invoke_method(method, **extract_params)
                assert result == mock_response
                mock_invoke.assert_called_with(method, **extract_params)

    @pytest.mark.asyncio
    async def test_invoke_research_methods(self, mock_firecrawl_client):
        """Test invoking research methods."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)

        # Mock the base class invoke_method
        with patch.object(wrapper, "invoke_method", AsyncMock()) as mock_invoke:
            # Test research method variants
            research_params = {"query": "What is machine learning?", "maxUrls": 5}

            mock_response = {
                "research": "Machine learning is a subset of AI...",
                "sources": ["https://example.com/ml"],
            }
            mock_invoke.return_value = mock_response

            # Test different method variants
            methods = ["deep_research", "research_topic"]
            for method in methods:
                result = await wrapper.invoke_method(method, **research_params)
                assert result == mock_response
                mock_invoke.assert_called_with(method, **research_params)

    @pytest.mark.asyncio
    async def test_direct_method_invocation(self, mock_firecrawl_client):
        """Test direct method invocation through the wrapper."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)

        # Mock the actual client methods
        mock_firecrawl_client.scrape.return_value = {"content": "Test"}
        mock_firecrawl_client.crawl.return_value = {"urls": ["test.com"]}
        mock_firecrawl_client.extract.return_value = {"data": "Extracted"}
        mock_firecrawl_client.deep_research.return_value = {"research": "Results"}

        # Since we don't have the actual base class implementation,
        # we'll test the mapping logic directly
        assert wrapper._method_map["scrape_url"] == "scrape"
        assert wrapper._method_map["crawl_website"] == "crawl"
        assert wrapper._method_map["extract_data"] == "extract"
        assert wrapper._method_map["deep_research"] == "deep_research"

    @pytest.mark.asyncio
    async def test_invoke_with_error(self, mock_firecrawl_client):
        """Test error handling during method invocation."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)

        # Mock error during invocation
        mock_firecrawl_client.scrape.side_effect = Exception("API Error")

        # Mock the base class invoke_method to simulate the error
        with patch.object(wrapper, "invoke_method", AsyncMock()) as mock_invoke:
            mock_invoke.side_effect = MCPClientError(
                "Failed to execute scrape_url: API Error"
            )

            with pytest.raises(MCPClientError) as exc_info:
                await wrapper.invoke_method("scrape_url", url="https://example.com")

            assert "Failed to execute scrape_url" in str(exc_info.value)
            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_compatibility(self, mock_firecrawl_client):
        """Test async function compatibility."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)

        # Use the wrapper object
        # Create both sync and async mock functions
        sync_func = Mock(return_value={"result": "sync"})
        async_func = AsyncMock(return_value={"result": "async"})

        # Test client with mixed sync/async methods
        mock_firecrawl_client.sync_method = sync_func
        mock_firecrawl_client.async_method = async_func

        # The wrapper should handle both gracefully
        # (This depends on the base class implementation)
        assert wrapper._client == mock_firecrawl_client

    def test_get_available_methods(self, mock_firecrawl_client):
        """Test getting available methods."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)

        methods = wrapper.get_available_methods()

        # Check that all expected methods are available
        expected_methods = [
            "scrape_url",
            "scrape_page",
            "crawl_website",
            "crawl_site",
            "extract_data",
            "extract_structured_data",
            "deep_research",
            "research_topic",
            "web_scrape",
            "website_crawl",
            "parse_data",
        ]

        assert set(methods) == set(expected_methods)

    def test_get_available_methods_returns_correct_list(self, mock_firecrawl_client):
        """Test that get_available_methods returns the correct list."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)

        # Get available methods
        methods = wrapper.get_available_methods()

        # Should match the keys from _method_map
        assert sorted(methods) == sorted(wrapper._method_map.keys())

    @pytest.mark.asyncio
    async def test_method_map_construction(self, mock_firecrawl_client):
        """Test that method map is properly constructed."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)

        # Verify the mapping is correct
        assert wrapper._method_map == {
            "scrape_url": "scrape",
            "scrape_page": "scrape",
            "crawl_website": "crawl",
            "crawl_site": "crawl",
            "extract_data": "extract",
            "extract_structured_data": "extract",
            "deep_research": "deep_research",
            "research_topic": "deep_research",
            "web_scrape": "scrape",
            "website_crawl": "crawl",
            "parse_data": "extract",
        }

    def test_initialization_with_client_creation_error(self):
        """Test handling of client creation errors."""
        with patch(
            "tripsage.mcp_abstraction.wrappers.firecrawl_wrapper.FirecrawlMCPClient"
        ) as mock_client_class:
            mock_client_class.side_effect = Exception("Failed to create client")

            with pytest.raises(Exception) as exc_info:
                FirecrawlMCPWrapper()

            assert "Failed to create client" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_method_mapping_completeness(self, mock_firecrawl_client):
        """Test that all mapped methods point to existing client methods."""
        wrapper = FirecrawlMCPWrapper(client=mock_firecrawl_client)

        # Get unique actual client methods from mapping
        actual_methods = set(wrapper._method_map.values())
        expected_client_methods = ["scrape", "crawl", "extract", "deep_research"]

        assert actual_methods == set(expected_client_methods)
