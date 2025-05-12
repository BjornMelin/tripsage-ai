"""
Tests for the WebCrawl MCP client.

This module contains tests for the WebCrawl MCP client implementation
that interfaces with the Firecrawl web crawling services.
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.mcp.webcrawl.client import WebCrawlMCPClient
from src.utils.error_handling import MCPError
from src.mcp.webcrawl.models import (
    ScrapeParams,
    ScrapeResponse,
)


@pytest.fixture
def client():
    """Create a test client instance."""
    return WebCrawlMCPClient()


@pytest.fixture
def mock_scrape_response():
    """Create a mock response for extract_page_content."""
    return {
        "url": "https://example.com",
        "title": "Example Website",
        "formats": {
            "markdown": "# Example Website\n\nThis is an example website content.",
            "html": (
                "<h1>Example Website</h1><p>This is an example website content.</p>"
            ),
        },
    }


@pytest.fixture
def mock_search_response():
    """Create a mock response for search_destination_info."""
    return {
        "query": "Paris attractions",
        "count": 2,
        "results": [
            {
                "url": "https://example.com/paris/eiffel-tower",
                "title": "Eiffel Tower - Paris",
                "description": "Visit the iconic Eiffel Tower in Paris.",
            },
            {
                "url": "https://example.com/paris/louvre",
                "title": "Louvre Museum - Paris",
                "description": "Explore the world-famous Louvre Museum.",
            },
        ],
    }


@pytest.fixture
def mock_deep_research_response():
    """Create a mock response for deep_research."""
    return {
        "query": "best time to visit Paris",
        "summary": (
            "The best time to visit Paris is during the spring (April to June) or "
            "fall (September to November) when the weather is mild and crowds are "
            "smaller. Summer can be crowded and hot, while winter is cold but offers "
            "fewer tourists."
        ),
        "sources": [
            {
                "url": "https://example.com/paris/travel-guide",
                "title": "Paris Travel Guide",
                "content_excerpt": (
                    "Spring and fall are ideal seasons to visit Paris... "
                    "Summer can be crowded and hot, while winter is cold but offers "
                    "fewer tourists."
                ),
            }
        ],
        "insights": [
            "Spring (April-June) offers pleasant weather and blooming gardens",
            "Fall (September-November) has fewer tourists and comfortable temperatures",
            "Summer (June-August) is peak tourist season with longer days but larger "
            "crowds",
            "Winter (December-February) is less crowded but often cold and rainy",
        ],
    }


@pytest.fixture
def mock_monitor_price_changes_response():
    """Create a mock response for monitor_price_changes."""
    return {
        "data": {
            "url": "https://example.com/hotel/paris",
            "monitoring_id": "mon_12345",
            "initial_price": 199.99,
            "currency": "USD",
            "frequency": "daily",
            "notification_threshold": 5.0,
        }
    }


@pytest.fixture
def mock_events_response():
    """Create a mock response for get_latest_events."""
    return {
        "data": {
            "destination": "Paris",
            "date_range": "2025-06-01 to 2025-06-07",
            "events": [
                {
                    "name": "Outdoor Jazz Concert",
                    "date": "2025-06-02",
                    "time": "19:00",
                    "location": "Luxembourg Gardens",
                    "category": "Music",
                },
                {
                    "name": "Food Festival",
                    "date": "2025-06-05",
                    "time": "12:00",
                    "location": "Champs-Élysées",
                    "category": "Food",
                },
            ],
        }
    }


@pytest.fixture
def mock_blog_response():
    """Create a mock response for crawl_travel_blog."""
    return {
        "data": {
            "destination": "Paris",
            "blogs_crawled": 2,
            "insights": {
                "hidden_gems": [
                    "Canal Saint-Martin is a less touristy area with great cafes",
                    "Parc des Buttes-Chaumont offers spectacular views of the city",
                ],
                "local_tips": [
                    "Visit bakeries early in the morning for the freshest pastries",
                    "Many museums are free on the first Sunday of each month",
                ],
            },
        }
    }


class TestWebCrawlMCPClient:
    """Tests for the WebCrawlMCPClient class."""

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test_extract_page_content(
        self, mock_call_tool, client, mock_scrape_response
    ):
        """Test extracting content from a webpage."""
        mock_call_tool.return_value = mock_scrape_response

        # Test with valid parameters
        result = await client.extract_page_content(
            url="https://example.com",
            selectors=["main", "article"],
            include_images=True,
            format="markdown",
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "mcp__webcrawl__firecrawl_scrape"
        assert isinstance(call_args[1], dict)

        # Verify tool parameters
        tool_params = call_args[1]
        assert tool_params.get("url") == "https://example.com"
        assert tool_params.get("formats") == ["markdown"]
        assert tool_params.get("includeTags") == ["main", "article"]
        assert tool_params.get("removeBase64Images") is False

        # Verify result parsing
        assert isinstance(result, dict)
        assert result["url"] == "https://example.com"
        assert result["title"] == "Example Website"
        assert "markdown" in result["formats"]
        assert "html" in result["formats"]

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test_extract_page_content_validation_error(self, mock_call_tool, client):
        """Test validation error handling for extract_page_content."""
        # Simulate validation error
        mock_call_tool.side_effect = ValidationError.from_exception_data(
            title="ValidationError",
            exc_info={"url": ["URL must be a valid HTTP or HTTPS URL"]},
        )

        # Test with invalid URL
        with pytest.raises(MCPError) as exc_info:
            await client.extract_page_content(url="invalid-url", format="markdown")

        assert "Invalid parameters" in str(exc_info.value)

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test_extract_page_content_api_error(self, mock_call_tool, client):
        """Test API error handling for extract_page_content."""
        # Simulate API error
        mock_call_tool.side_effect = Exception("Connection error")

        # Test with API error
        with pytest.raises(MCPError) as exc_info:
            await client.extract_page_content(
                url="https://example.com", format="markdown"
            )

        assert "MCP error: Connection error" in str(exc_info.value)

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test_search_destination_info(
        self, mock_call_tool, client, mock_search_response
    ):
        """Test searching for destination information."""
        mock_call_tool.return_value = mock_search_response

        # Test with valid parameters
        result = await client.search_destination_info(
            destination="Paris",
            topics=["attractions", "museums"],
            max_results=5,
            traveler_profile="family",
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "mcp__webcrawl__firecrawl_search"

        # Verify tool parameters
        tool_params = call_args[1]
        assert "Paris attractions museums for family" in tool_params.get("query")
        assert tool_params.get("limit") == 5

        # Verify result parsing
        assert isinstance(result, dict)
        assert result["query"] == "Paris attractions"
        assert result["count"] == 2
        assert len(result["results"]) == 2
        assert "Eiffel Tower" in result["results"][0]["title"]
        assert "Louvre Museum" in result["results"][1]["title"]

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test_search_destination_info_validation_error(
        self, mock_call_tool, client
    ):
        """Test validation error handling for search_destination_info."""
        # Simulate validation error
        mock_call_tool.side_effect = ValidationError.from_exception_data(
            title="ValidationError",
            exc_info={"query": ["Search query cannot be empty"]},
        )

        # Test with empty destination
        with pytest.raises(MCPError) as exc_info:
            await client.search_destination_info(destination="", max_results=5)

        assert "Invalid parameters" in str(exc_info.value)

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test_monitor_price_changes(
        self, mock_call_tool, client, mock_monitor_price_changes_response
    ):
        """Test setting up price change monitoring."""
        mock_call_tool.return_value = mock_monitor_price_changes_response

        # Test with valid parameters
        result = await client.monitor_price_changes(
            url="https://example.com/hotel/paris",
            price_selector=".price-value",
            frequency="daily",
            notification_threshold=5.0,
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "mcp__webcrawl__monitor_price_changes"

        # Verify tool parameters
        tool_params = call_args[1]
        assert tool_params.get("url") == "https://example.com/hotel/paris"
        assert tool_params.get("price_selector") == ".price-value"
        assert tool_params.get("frequency") == "daily"
        assert tool_params.get("notification_threshold") == 5.0

        # Verify result parsing
        assert isinstance(result, dict)
        assert result["url"] == "https://example.com/hotel/paris"
        assert result["monitoring_id"] == "mon_12345"
        assert result["initial_price"] == 199.99
        assert result["frequency"] == "daily"

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test_get_latest_events(
        self, mock_call_tool, client, mock_events_response
    ):
        """Test getting latest events at a destination."""
        mock_call_tool.return_value = mock_events_response

        # Test with valid parameters
        result = await client.get_latest_events(
            destination="Paris",
            start_date="2025-06-01",
            end_date="2025-06-07",
            categories=["Music", "Food"],
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "mcp__webcrawl__get_latest_events"

        # Verify tool parameters
        tool_params = call_args[1]
        assert tool_params.get("destination") == "Paris"
        assert tool_params.get("start_date") == "2025-06-01"
        assert tool_params.get("end_date") == "2025-06-07"
        assert tool_params.get("categories") == ["Music", "Food"]

        # Verify result parsing
        assert isinstance(result, dict)
        assert result["destination"] == "Paris"
        assert result["date_range"] == "2025-06-01 to 2025-06-07"
        assert len(result["events"]) == 2
        assert result["events"][0]["name"] == "Outdoor Jazz Concert"
        assert result["events"][1]["name"] == "Food Festival"

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test_crawl_travel_blog(self, mock_call_tool, client, mock_blog_response):
        """Test crawling travel blogs for insights."""
        mock_call_tool.return_value = mock_blog_response

        # Test with valid parameters
        result = await client.crawl_travel_blog(
            destination="Paris",
            topics=["hidden_gems", "local_tips"],
            max_blogs=3,
            recent_only=True,
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "mcp__webcrawl__crawl_travel_blog"

        # Verify tool parameters
        tool_params = call_args[1]
        assert tool_params.get("destination") == "Paris"
        assert tool_params.get("topics") == ["hidden_gems", "local_tips"]
        assert tool_params.get("max_blogs") == 3
        assert tool_params.get("recent_only") is True

        # Verify result parsing
        assert isinstance(result, dict)
        assert result["destination"] == "Paris"
        assert result["blogs_crawled"] == 2
        assert "hidden_gems" in result["insights"]
        assert "local_tips" in result["insights"]
        assert len(result["insights"]["hidden_gems"]) == 2
        assert len(result["insights"]["local_tips"]) == 2

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test_deep_research(
        self, mock_call_tool, client, mock_deep_research_response
    ):
        """Test conducting deep research."""
        mock_call_tool.return_value = mock_deep_research_response

        # Test with valid parameters
        result = await client.deep_research(
            query="best time to visit Paris", max_depth=3, max_urls=20, time_limit=120
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "mcp__webcrawl__firecrawl_deep_research"

        # Verify tool parameters are validated by Pydantic
        params = call_args[1]
        assert params.get("query") == "best time to visit Paris"
        assert params.get("maxDepth") == 3
        assert params.get("maxUrls") == 20
        assert params.get("timeLimit") == 120

        # Verify result parsing
        assert isinstance(result, dict)
        assert result["query"] == "best time to visit Paris"
        assert "spring" in result["summary"].lower()
        assert "fall" in result["summary"].lower()
        assert len(result["sources"]) >= 1
        assert len(result["insights"]) >= 4

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test_deep_research_validation_error(self, mock_call_tool, client):
        """Test validation error handling for deep_research."""
        # Simulate validation error
        mock_call_tool.side_effect = ValidationError.from_exception_data(
            title="ValidationError",
            exc_info={"query": ["Research query cannot be empty"]},
        )

        # Test with empty query
        with pytest.raises(MCPError) as exc_info:
            await client.deep_research(query="", max_depth=3)

        assert "Invalid parameters" in str(exc_info.value)

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test_tool_error_handling(self, mock_call_tool, client):
        """Test handling of error responses from the MCP tool."""
        # Simulate tool error response
        mock_call_tool.return_value = {
            "error": {
                "code": "CRAWL_ERROR",
                "message": "Failed to crawl the requested URL",
            }
        }

        # Test handling of error response
        with pytest.raises(MCPError) as exc_info:
            await client.extract_page_content(
                url="https://example.com", format="markdown"
            )

        assert "MCP error: Failed to crawl the requested URL" in str(exc_info.value)

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test_websearch_tool_guidance(self, mock_call_tool, client):
        """Test handling of websearch tool guidance responses."""
        # Simulate websearch guidance response
        mock_call_tool.return_value = {
            "error": {
                "code": "USE_WEBSEARCH",
                "message": "Consider using websearch tool instead",
            },
            "data": {
                "websearch_tool_guidance": {
                    "query": "Paris tourist attractions",
                    "tool": "search-web",
                }
            },
        }

        # Test handling of websearch guidance response
        result = await client.search_destination_info(
            destination="Paris", topics=["tourist attractions"]
        )

        # Verify the guidance is returned without raising an exception
        assert isinstance(result, dict)
        assert "data" in result
        assert "websearch_tool_guidance" in result["data"]
        assert (
            result["data"]["websearch_tool_guidance"]["query"]
            == "Paris tourist attractions"
        )
        assert result["data"]["websearch_tool_guidance"]["tool"] == "search-web"

    @patch("src.mcp.base_mcp_client.BaseMCPClient.call_tool")
    async def test__call_validate_tool(
        self, mock_call_tool, client, mock_scrape_response
    ):
        """Test the _call_validate_tool method directly."""
        mock_call_tool.return_value = mock_scrape_response

        # Create valid parameters
        params = ScrapeParams(url="https://example.com", options=None)

        # Test with valid parameters and response model
        result = await client._call_validate_tool(
            "mcp__webcrawl__firecrawl_scrape", params, ScrapeResponse
        )

        # Verify parameters were dumped correctly
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "mcp__webcrawl__firecrawl_scrape"
        assert call_args[1] == {"url": "https://example.com", "options": None}

        # Verify result was validated
        assert isinstance(result, dict)  # In practice, this would be a ScrapeResponse
        assert result["url"] == "https://example.com"
        assert result["title"] == "Example Website"
        assert "markdown" in result["formats"]