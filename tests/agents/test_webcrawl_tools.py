"""
Tests for webcrawl tools.

This module contains tests for the webcrawl tools used by TripSage agents.
"""

from unittest.mock import AsyncMock, patch

import pytest

from tripsage.agents.tools.webcrawl.models import (
    BlogCrawlParams,
    EventSearchParams,
    ExtractContentParams,
    PriceMonitorParams,
    SearchDestinationParams,
)
from tripsage.agents.webcrawl_tools import (
    crawl_travel_blog_tool,
    extract_page_content_tool,
    get_latest_events_tool,
    monitor_price_changes_tool,
    search_destination_info_tool,
    search_web_tool,
)


@pytest.fixture
def mock_webcrawl_client():
    """Create a mock for the unified WebCrawlMCPClient."""
    with patch("src.agents.webcrawl_tools.webcrawl_client") as mock:
        # Set up the mock methods
        mock.extract_page_content = AsyncMock(
            return_value={
                "success": True,
                "url": "https://example.com",
                "title": "Example Page",
                "content": "This is example content",
                "formats": {
                    "markdown": (
                        "# Example Website\n\nThis is an example website content."
                    )
                },
            }
        )

        mock.search_destination_info = AsyncMock(
            return_value={
                "success": True,
                "query": "test query",
                "count": 2,
                "results": [
                    {
                        "title": "Search Result 1",
                        "url": "https://example.com/result1",
                        "description": "This is search result 1",
                    },
                    {
                        "title": "Search Result 2",
                        "url": "https://example.com/result2",
                        "description": "This is search result 2",
                    },
                ],
            }
        )

        mock.monitor_price_changes = AsyncMock(
            return_value={
                "success": True,
                "url": "https://example.com/product",
                "monitoring_id": "mon_12345",
                "initial_price": 99.99,
                "currency": "USD",
                "frequency": "daily",
            }
        )

        mock.get_latest_events = AsyncMock(
            return_value={
                "success": True,
                "destination": "New York",
                "date_range": "2025-06-01 to 2025-06-30",
                "events": [
                    {
                        "name": "Example Event",
                        "date": "2025-06-01",
                        "time": "19:00",
                        "location": "Example Venue",
                        "category": "Concert",
                    }
                ],
            }
        )

        mock.crawl_travel_blog = AsyncMock(
            return_value={
                "success": True,
                "destination": "Paris",
                "blogs_crawled": 2,
                "insights": {
                    "hidden_gems": ["Hidden gem 1", "Hidden gem 2"],
                    "local_tips": ["Local tip 1", "Local tip 2"],
                },
            }
        )

        mock.deep_research = AsyncMock(
            return_value={
                "success": True,
                "query": "deep research query",
                "summary": "This is a summary of the deep research",
                "sources": [
                    {"url": "https://example.com/source1", "title": "Source 1"}
                ],
                "insights": ["Insight 1", "Insight 2", "Insight 3"],
            }
        )

        yield mock


@pytest.mark.asyncio
async def test_extract_page_content_tool(mock_webcrawl_client):
    """Test the extract_page_content_tool function."""
    params = ExtractContentParams(
        url="https://example.com",
        content_type="article",
        full_page=False,
        extract_images=False,
        extract_links=True,
    )

    result = await extract_page_content_tool(params)

    assert result["success"] is True
    assert result["url"] == "https://example.com"
    mock_webcrawl_client.extract_page_content.assert_called_once()


@pytest.mark.asyncio
async def test_search_destination_info_tool(mock_webcrawl_client):
    """Test the search_destination_info_tool function."""
    params = SearchDestinationParams(
        destination="Paris", query="best museums", search_depth="standard"
    )

    result = await search_destination_info_tool(params)

    assert result["success"] is True
    assert "results" in result
    assert len(result["results"]) == 2
    mock_webcrawl_client.search_destination_info.assert_called_once()


@pytest.mark.asyncio
async def test_monitor_price_changes_tool(mock_webcrawl_client):
    """Test the monitor_price_changes_tool function."""
    params = PriceMonitorParams(
        url="https://example.com/product",
        product_type="hotel",
        target_selectors={"price": ".price"},
    )

    result = await monitor_price_changes_tool(params)

    assert result["success"] is True
    assert result["url"] == "https://example.com/product"
    assert result["initial_price"] == 99.99
    mock_webcrawl_client.monitor_price_changes.assert_called_once()


@pytest.mark.asyncio
async def test_get_latest_events_tool(mock_webcrawl_client):
    """Test the get_latest_events_tool function."""
    params = EventSearchParams(
        destination="New York",
        event_type="concert",
        start_date="2025-06-01",
        end_date="2025-06-30",
    )

    result = await get_latest_events_tool(params)

    assert result["success"] is True
    assert result["destination"] == "New York"
    assert len(result["events"]) == 1
    mock_webcrawl_client.get_latest_events.assert_called_once()


@pytest.mark.asyncio
async def test_crawl_travel_blog_tool(mock_webcrawl_client):
    """Test the crawl_travel_blog_tool function."""
    params = BlogCrawlParams(
        url="https://example.com/blog/paris-travel-guide",
        extract_type="insights",
        max_pages=1,
    )

    result = await crawl_travel_blog_tool(params)

    assert result["success"] is True
    assert result["destination"] == "Paris"
    assert "insights" in result
    mock_webcrawl_client.crawl_travel_blog.assert_called_once()


@pytest.mark.asyncio
async def test_search_web_tool_standard(mock_webcrawl_client):
    """Test the search_web_tool function with standard depth."""
    result = await search_web_tool("travel tips", "standard")

    assert result["success"] is True
    assert "results" in result
    mock_webcrawl_client.search_destination_info.assert_called_once()
    mock_webcrawl_client.deep_research.assert_not_called()


@pytest.mark.asyncio
async def test_search_web_tool_deep(mock_webcrawl_client):
    """Test the search_web_tool function with deep depth."""
    result = await search_web_tool("travel tips", "deep")

    assert result["success"] is True
    assert "summary" in result
    assert "insights" in result
    mock_webcrawl_client.deep_research.assert_called_once()
    mock_webcrawl_client.search_destination_info.assert_not_called()


@pytest.mark.asyncio
async def test_extract_page_content_tool_error(mock_webcrawl_client):
    """Test error handling in extract_page_content_tool."""
    params = ExtractContentParams(url="https://example.com", content_type="article")

    # Make the client raise an exception
    mock_webcrawl_client.extract_page_content.side_effect = Exception("Test error")

    result = await extract_page_content_tool(params)

    assert result["success"] is False
    assert "error" in result
    assert "Test error" in result["error"]


def test_extract_destination_from_url():
    """Test the extract_destination_from_url function."""
    from tripsage.agents.webcrawl_tools import extract_destination_from_url

    # Test with city name in URL
    assert (
        extract_destination_from_url("https://example.com/paris-travel-guide")
        == "Paris"
    )
    assert (
        extract_destination_from_url("https://blog.example.com/visit-new-york")
        == "New York"
    )

    # Test with no match
    assert (
        extract_destination_from_url("https://example.com/generic-blog-post")
        == "unknown"
    )
