"""
Tests for the Crawl4AI MCP client.

These tests verify the functionality of the Crawl4AI MCP client
including crawling, extraction, JavaScript execution, and caching.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tripsage.clients.webcrawl.crawl4ai_mcp_client import (
    Crawl4AIMCPClient,
    Crawl4AICrawlParams,
    Crawl4AIExecuteJsParams,
    Crawl4AIAskParams,
    get_crawl4ai_client,
)
from tripsage.utils.cache import ContentType


@pytest.fixture
async def mock_crawl4ai_client():
    """Create a mocked Crawl4AI client for testing."""
    with patch("tripsage.clients.webcrawl.crawl4ai_mcp_client.get_mcp_settings") as mock_settings:
        # Mock settings
        mock_config = MagicMock()
        mock_config.url = "ws://localhost:11235/mcp/ws"
        mock_config.timeout = 30
        mock_settings.return_value.crawl4ai = mock_config
        
        # Create client with mocked cache
        client = Crawl4AIMCPClient()
        client._cache = AsyncMock()
        client._send_request = AsyncMock()
        
        yield client


@pytest.mark.asyncio
async def test_singleton_pattern():
    """Test that the client follows singleton pattern."""
    client1 = get_crawl4ai_client()
    client2 = get_crawl4ai_client()
    assert client1 is client2


@pytest.mark.asyncio
async def test_crawl_url(mock_crawl4ai_client):
    """Test basic URL crawling."""
    client = mock_crawl4ai_client
    url = "https://example.com"
    
    # Mock response
    expected_response = {
        "url": url,
        "markdown": "# Example Domain\n\nThis domain is for use in illustrative examples.",
        "html": "<html><body><h1>Example Domain</h1></body></html>",
    }
    client._send_request.return_value = expected_response
    
    # Test crawling
    result = await client.crawl_url(url)
    
    # Verify the request
    client._send_request.assert_called_once()
    call_args = client._send_request.call_args
    assert call_args[0][0] == "crawl"  # tool_name
    assert call_args[0][1]["url"] == url  # arguments
    
    # Verify the response
    assert result == expected_response


@pytest.mark.asyncio
async def test_extract_markdown(mock_crawl4ai_client):
    """Test markdown extraction."""
    client = mock_crawl4ai_client
    url = "https://example.com"
    
    # Mock response
    expected_response = {
        "url": url,
        "content": "# Example Domain\n\nThis domain is for use in illustrative examples.",
    }
    client._send_request.return_value = expected_response
    
    # Test extraction
    result = await client.extract_markdown(url)
    
    # Verify the request
    client._send_request.assert_called_once()
    call_args = client._send_request.call_args
    assert call_args[0][0] == "md"  # tool_name
    assert call_args[0][1]["url"] == url  # arguments
    assert call_args[0][1]["markdown"] is True
    
    # Verify the response
    assert result == expected_response


@pytest.mark.asyncio
async def test_execute_js(mock_crawl4ai_client):
    """Test JavaScript execution."""
    client = mock_crawl4ai_client
    url = "https://example.com"
    js_code = "return document.title;"
    
    # Mock response
    expected_response = {
        "result": "Example Domain",
        "success": True,
    }
    client._send_request.return_value = expected_response
    
    # Test JS execution
    result = await client.execute_js(url, js_code)
    
    # Verify the request
    client._send_request.assert_called_once()
    call_args = client._send_request.call_args
    assert call_args[0][0] == "execute_js"  # tool_name
    assert call_args[0][1]["url"] == url  # arguments
    assert call_args[0][1]["jsCode"] == js_code
    
    # Verify the response
    assert result == expected_response


@pytest.mark.asyncio
async def test_ask_question(mock_crawl4ai_client):
    """Test question answering functionality."""
    client = mock_crawl4ai_client
    urls = ["https://example.com", "https://example.org"]
    question = "What is the purpose of these domains?"
    
    # Mock response
    expected_response = {
        "question": question,
        "answer": "These domains are reserved for use in documentation and examples.",
        "sources": urls,
    }
    client._send_request.return_value = expected_response
    
    # Test question answering
    result = await client.ask(urls, question)
    
    # Verify the request
    client._send_request.assert_called_once()
    call_args = client._send_request.call_args
    assert call_args[0][0] == "ask"  # tool_name
    assert call_args[0][1]["urls"] == urls  # arguments
    assert call_args[0][1]["question"] == question
    
    # Verify the response
    assert result == expected_response


@pytest.mark.asyncio
async def test_cache_interaction(mock_crawl4ai_client):
    """Test that caching is properly used."""
    client = mock_crawl4ai_client
    url = "https://example.com"
    
    # Mock cache hit
    cached_data = {"content": "Cached content"}
    client._cache.get.return_value = cached_data
    
    # Test with cache
    result = await client.extract_markdown(url, use_cache=True)
    
    # Verify cache was checked
    client._cache.get.assert_called_once()
    cache_key = client._cache.get.call_args[0][0]
    assert "crawl4ai:md:" in cache_key
    assert url in cache_key
    
    # Verify no actual request was made (cache hit)
    client._send_request.assert_not_called()
    
    # Verify cached result was returned
    assert result == cached_data


@pytest.mark.asyncio
async def test_cache_miss_and_set(mock_crawl4ai_client):
    """Test cache miss and subsequent cache set."""
    client = mock_crawl4ai_client
    url = "https://example.com"
    
    # Mock cache miss
    client._cache.get.return_value = None
    
    # Mock API response
    api_response = {"content": "Fresh content"}
    client._send_request.return_value = api_response
    
    # Test with cache
    result = await client.extract_markdown(url, use_cache=True)
    
    # Verify cache was checked
    client._cache.get.assert_called_once()
    
    # Verify request was made (cache miss)
    client._send_request.assert_called_once()
    
    # Verify result was cached
    client._cache.set.assert_called_once()
    set_call_args = client._cache.set.call_args
    assert set_call_args[0][0].startswith("crawl4ai:md:")  # cache key
    assert set_call_args[0][1] == api_response  # value
    assert set_call_args[1]["content_type"] == ContentType.MARKDOWN
    
    # Verify result
    assert result == api_response


@pytest.mark.asyncio
async def test_batch_crawl(mock_crawl4ai_client):
    """Test batch crawling functionality."""
    client = mock_crawl4ai_client
    urls = ["https://example.com", "https://example.org", "https://example.net"]
    
    # Mock responses for each URL
    responses = [
        {"url": urls[0], "markdown": "Content 1"},
        {"url": urls[1], "markdown": "Content 2"},
        {"url": urls[2], "markdown": "Content 3"},
    ]
    client._send_request.side_effect = responses
    
    # Test batch crawl
    results = await client.batch_crawl(urls)
    
    # Verify requests were made for each URL
    assert client._send_request.call_count == 3
    
    # Verify results
    assert len(results) == 3
    for i, result in enumerate(results):
        assert result == responses[i]


@pytest.mark.asyncio
async def test_error_handling(mock_crawl4ai_client):
    """Test error handling in batch operations."""
    client = mock_crawl4ai_client
    urls = ["https://example.com", "https://invalid-domain"]
    
    # Mock one success and one failure
    client._send_request.side_effect = [
        {"url": urls[0], "markdown": "Content"},
        Exception("Connection error"),
    ]
    
    # Test batch crawl with error
    results = await client.batch_crawl(urls)
    
    # Verify results include error
    assert len(results) == 2
    assert results[0]["url"] == urls[0]
    assert "error" in results[1]
    assert urls[1] in results[1]["url"]


@pytest.mark.asyncio
async def test_parameter_models():
    """Test Pydantic parameter models."""
    # Test Crawl4AICrawlParams
    params = Crawl4AICrawlParams(
        url="https://example.com",
        session_id="test-session",
        max_pages=5,
    )
    assert params.url == "https://example.com"
    assert params.session_id == "test-session"
    assert params.max_pages == 5
    
    # Test alias conversion
    params_dict = params.model_dump(by_alias=True)
    assert params_dict["sessionId"] == "test-session"
    assert params_dict["maxPages"] == 5
    
    # Test Crawl4AIExecuteJsParams
    js_params = Crawl4AIExecuteJsParams(
        url="https://example.com",
        js_code="return document.title;",
    )
    assert js_params.js_code == "return document.title;"
    
    # Test Crawl4AIAskParams
    ask_params = Crawl4AIAskParams(
        urls=["https://example.com"],
        question="What is this?",
    )
    assert ask_params.question == "What is this?"