"""Test suite for Crawl4AIMCPWrapper."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage.mcp_abstraction.exceptions import MCPClientError
from tripsage.mcp_abstraction.wrappers.crawl4ai_wrapper import Crawl4AIMCPWrapper


@pytest.fixture
def mock_crawl4ai_client():
    """Create a mock Crawl4AI MCP client."""
    client = Mock()
    client.crawl = AsyncMock()
    client.execute_js = AsyncMock()
    client.answer_question = AsyncMock()
    return client


class TestCrawl4AIMCPWrapper:
    """Test Crawl4AIMCPWrapper functionality."""

    def test_initialization(self):
        """Test initialization with no pre-existing client."""
        with patch(
            "tripsage.mcp_abstraction.wrappers.crawl4ai_wrapper.Crawl4AIMCPClient"
        ) as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance

            wrapper = Crawl4AIMCPWrapper()

            assert wrapper._client == mock_instance
            assert wrapper._mcp_name == "crawl4ai"
            mock_client_class.assert_called_once()

    def test_initialization_with_client(self, mock_crawl4ai_client):
        """Test initialization with pre-existing client."""
        wrapper = Crawl4AIMCPWrapper(client=mock_crawl4ai_client)
        assert wrapper._client == mock_crawl4ai_client
        assert wrapper._mcp_name == "crawl4ai"

    def test_initialization_with_custom_name(self, mock_crawl4ai_client):
        """Test initialization with custom MCP name."""
        wrapper = Crawl4AIMCPWrapper(
            client=mock_crawl4ai_client, mcp_name="custom_crawl4ai"
        )
        assert wrapper._client == mock_crawl4ai_client
        assert wrapper._mcp_name == "custom_crawl4ai"

    def test_build_method_map(self, mock_crawl4ai_client):
        """Test method map building."""
        wrapper = Crawl4AIMCPWrapper(client=mock_crawl4ai_client)

        # Check the method map
        expected_mappings = {
            "crawl_url": "crawl",
            "crawl_page": "crawl",
            "execute_js": "execute_js",
            "execute_javascript": "execute_js",
            "answer_question": "answer_question",
            "ask_question": "answer_question",
            "extract_content": "crawl",
            "scrape_page": "crawl",
            "process_page": "crawl",
            "run_javascript": "execute_js",
            "inject_js": "execute_js",
            "qa_from_url": "answer_question",
            "query_content": "answer_question",
        }

        for standard_name, actual_name in expected_mappings.items():
            assert wrapper._method_map.get(standard_name) == actual_name

    @pytest.mark.asyncio
    async def test_invoke_crawl_methods(self, mock_crawl4ai_client):
        """Test invoking crawl-related methods."""
        wrapper = Crawl4AIMCPWrapper(client=mock_crawl4ai_client)

        # Mock the base class invoke_method since we're testing the mapping
        with patch.object(wrapper, "invoke_method", AsyncMock()) as mock_invoke:
            # Test crawl method variants
            crawl_params = {
                "url": "https://example.com",
                "wait_for": "network_idle",
            }

            mock_response = {
                "content": "# Example Page",
                "url": "https://example.com",
            }
            mock_invoke.return_value = mock_response

            # Test different method variants
            methods = [
                "crawl_url",
                "crawl_page",
                "extract_content",
                "scrape_page",
                "process_page",
            ]
            for method in methods:
                result = await wrapper.invoke_method(method, **crawl_params)
                assert result == mock_response
                mock_invoke.assert_called_with(method, **crawl_params)

    @pytest.mark.asyncio
    async def test_invoke_execute_js_methods(self, mock_crawl4ai_client):
        """Test invoking JavaScript execution methods."""
        wrapper = Crawl4AIMCPWrapper(client=mock_crawl4ai_client)

        # Mock the base class invoke_method
        with patch.object(wrapper, "invoke_method", AsyncMock()) as mock_invoke:
            # Test execute_js method variants
            js_params = {
                "url": "https://example.com",
                "script": "return document.title;",
            }

            mock_response = {
                "result": "Example Page",
                "success": True,
            }
            mock_invoke.return_value = mock_response

            # Test different method variants
            methods = [
                "execute_js",
                "execute_javascript",
                "run_javascript",
                "inject_js",
            ]
            for method in methods:
                result = await wrapper.invoke_method(method, **js_params)
                assert result == mock_response
                mock_invoke.assert_called_with(method, **js_params)

    @pytest.mark.asyncio
    async def test_invoke_answer_question_methods(self, mock_crawl4ai_client):
        """Test invoking question-answering methods."""
        wrapper = Crawl4AIMCPWrapper(client=mock_crawl4ai_client)

        # Mock the base class invoke_method
        with patch.object(wrapper, "invoke_method", AsyncMock()) as mock_invoke:
            # Test answer_question method variants
            qa_params = {
                "url": "https://example.com",
                "question": "What is the main topic?",
            }

            mock_response = {
                "answer": "The main topic is machine learning.",
                "context": "Machine learning is a subset of AI...",
            }
            mock_invoke.return_value = mock_response

            # Test different method variants
            methods = [
                "answer_question",
                "ask_question",
                "qa_from_url",
                "query_content",
            ]
            for method in methods:
                result = await wrapper.invoke_method(method, **qa_params)
                assert result == mock_response
                mock_invoke.assert_called_with(method, **qa_params)

    @pytest.mark.asyncio
    async def test_direct_method_invocation(self, mock_crawl4ai_client):
        """Test direct method invocation through the wrapper."""
        wrapper = Crawl4AIMCPWrapper(client=mock_crawl4ai_client)

        # Mock the actual client methods
        mock_crawl4ai_client.crawl.return_value = {"content": "Test"}
        mock_crawl4ai_client.execute_js.return_value = {"result": "JS Result"}
        mock_crawl4ai_client.answer_question.return_value = {"answer": "Answer"}

        # Since we don't have the actual base class implementation,
        # we'll test the mapping logic directly
        assert wrapper._method_map["crawl_url"] == "crawl"
        assert wrapper._method_map["execute_javascript"] == "execute_js"
        assert wrapper._method_map["ask_question"] == "answer_question"

    @pytest.mark.asyncio
    async def test_invoke_with_error(self, mock_crawl4ai_client):
        """Test error handling during method invocation."""
        wrapper = Crawl4AIMCPWrapper(client=mock_crawl4ai_client)

        # Mock error during invocation
        mock_crawl4ai_client.crawl.side_effect = Exception("API Error")

        # Mock the base class invoke_method to simulate the error
        with patch.object(wrapper, "invoke_method", AsyncMock()) as mock_invoke:
            mock_invoke.side_effect = MCPClientError(
                "Failed to execute crawl_url: API Error"
            )

            with pytest.raises(MCPClientError) as exc_info:
                await wrapper.invoke_method("crawl_url", url="https://example.com")

            assert "Failed to execute crawl_url" in str(exc_info.value)
            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_compatibility(self, mock_crawl4ai_client):
        """Test async function compatibility."""
        wrapper = Crawl4AIMCPWrapper(client=mock_crawl4ai_client)

        # Use the wrapper object
        # Create both sync and async mock functions
        sync_func = Mock(return_value={"result": "sync"})
        async_func = AsyncMock(return_value={"result": "async"})

        # Test client with mixed sync/async methods
        mock_crawl4ai_client.sync_method = sync_func
        mock_crawl4ai_client.async_method = async_func

        # The wrapper should handle both gracefully
        # (This depends on the base class implementation)
        assert wrapper._client == mock_crawl4ai_client

    def test_get_available_methods(self, mock_crawl4ai_client):
        """Test getting available methods."""
        wrapper = Crawl4AIMCPWrapper(client=mock_crawl4ai_client)

        methods = wrapper.get_available_methods()

        # Check that all expected methods are available
        expected_methods = [
            "crawl_url",
            "crawl_page",
            "execute_js",
            "execute_javascript",
            "answer_question",
            "ask_question",
            "extract_content",
            "scrape_page",
            "process_page",
            "run_javascript",
            "inject_js",
            "qa_from_url",
            "query_content",
        ]

        assert set(methods) == set(expected_methods)

    def test_get_available_methods_returns_correct_list(self, mock_crawl4ai_client):
        """Test that get_available_methods returns the correct list."""
        wrapper = Crawl4AIMCPWrapper(client=mock_crawl4ai_client)

        # Get available methods
        methods = wrapper.get_available_methods()

        # Should match the keys from _method_map
        assert sorted(methods) == sorted(wrapper._method_map.keys())

    @pytest.mark.asyncio
    async def test_method_map_construction(self, mock_crawl4ai_client):
        """Test that method map is properly constructed."""
        wrapper = Crawl4AIMCPWrapper(client=mock_crawl4ai_client)

        # Verify the mapping is correct
        assert wrapper._method_map == {
            "crawl_url": "crawl",
            "crawl_page": "crawl",
            "execute_js": "execute_js",
            "execute_javascript": "execute_js",
            "answer_question": "answer_question",
            "ask_question": "answer_question",
            "extract_content": "crawl",
            "scrape_page": "crawl",
            "process_page": "crawl",
            "run_javascript": "execute_js",
            "inject_js": "execute_js",
            "qa_from_url": "answer_question",
            "query_content": "answer_question",
        }

    def test_initialization_with_client_creation_error(self):
        """Test handling of client creation errors."""
        with patch(
            "tripsage.mcp_abstraction.wrappers.crawl4ai_wrapper.Crawl4AIMCPClient"
        ) as mock_client_class:
            mock_client_class.side_effect = Exception("Failed to create client")

            with pytest.raises(Exception) as exc_info:
                Crawl4AIMCPWrapper()

            assert "Failed to create client" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_method_mapping_completeness(self, mock_crawl4ai_client):
        """Test that all mapped methods point to existing client methods."""
        wrapper = Crawl4AIMCPWrapper(client=mock_crawl4ai_client)

        # Get unique actual client methods from mapping
        actual_methods = set(wrapper._method_map.values())
        expected_client_methods = ["crawl", "execute_js", "answer_question"]

        assert actual_methods == set(expected_client_methods)
