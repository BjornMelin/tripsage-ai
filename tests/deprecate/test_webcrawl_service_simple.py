"""
Simple integration tests for WebCrawlService - focused on what matters.
"""

from unittest.mock import AsyncMock, patch

import pytest

from tripsage.services.webcrawl_service import (
    WebCrawlParams,
    WebCrawlResult,
    WebCrawlService,
    get_webcrawl_service,
)


class TestWebCrawlServiceIntegration:
    """Integration tests for WebCrawlService with proper mocking."""

    @pytest.fixture
    def service(self):
        """Create WebCrawlService instance."""
        return WebCrawlService()

    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initializes correctly."""
        assert service is not None
        assert isinstance(service, WebCrawlService)

    @pytest.mark.asyncio
    async def test_health_check_success(self, service):
        """Test health check returns success."""
        with patch.object(service, "crawl_url") as mock_crawl:
            mock_crawl.return_value = WebCrawlResult(
                success=True,
                url="https://httpbin.org/status/200",
                title="Test",
                markdown="Test content",
            )

            result = await service.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, service):
        """Test health check handles failures."""
        with patch.object(service, "crawl_url") as mock_crawl:
            mock_crawl.return_value = WebCrawlResult(
                success=False,
                url="https://httpbin.org/status/200",
                error_message="Network error",
            )

            result = await service.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_crawl_url_with_mock(self, service):
        """Test URL crawling with proper mocking."""
        url = "https://example.com"
        params = WebCrawlParams(extract_markdown=True)

        # Mock the AsyncWebCrawler directly
        mock_result = AsyncMock()
        mock_result.success = True
        mock_result.markdown = "# Example Page\nTest content"
        mock_result.html = (
            "<html><head><title>Example Page</title></head><body>Test</body></html>"
        )
        mock_result.cleaned_html = mock_result.html
        mock_result.extracted_content = "Example Page Test content"
        mock_result.metadata = {"title": "Example Page"}
        mock_result.links = {"internal": [], "external": []}
        mock_result.media = {"images": [], "videos": [], "audios": []}
        mock_result.screenshot = b""
        mock_result.pdf = None
        mock_result.status_code = 200

        with patch("crawl4ai.AsyncWebCrawler") as mock_crawler_class:
            # Create proper async context manager mock
            mock_crawler = AsyncMock()
            mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler.__aexit__ = AsyncMock(return_value=None)
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler_class.return_value = mock_crawler

            result = await service.crawl_url(url, params)

            # Verify the result
            assert result.success is True
            assert result.url == url
            assert "Example Page" in result.markdown
            assert result.status_code == 200

            # Verify the crawler was called correctly
            mock_crawler.arun.assert_called_once()


class TestWebCrawlParams:
    """Test parameter models."""

    def test_default_values(self):
        """Test default parameter values."""
        params = WebCrawlParams()

        assert params.javascript_enabled is True
        assert params.extract_markdown is True
        assert params.extract_html is False
        assert params.use_cache is True
        assert params.timeout == 30

    def test_custom_values(self):
        """Test custom parameter values."""
        params = WebCrawlParams(
            javascript_enabled=False,
            extract_html=True,
            timeout=60,
        )

        assert params.javascript_enabled is False
        assert params.extract_html is True
        assert params.timeout == 60


class TestWebCrawlResult:
    """Test result models."""

    def test_successful_result(self):
        """Test successful result creation."""
        result = WebCrawlResult(
            success=True,
            url="https://example.com",
            title="Test Page",
            markdown="# Test Content",
        )

        assert result.success is True
        assert result.url == "https://example.com"
        assert result.title == "Test Page"
        assert result.markdown == "# Test Content"

    def test_failed_result(self):
        """Test failed result creation."""
        result = WebCrawlResult(
            success=False,
            url="https://example.com",
            error_message="Network timeout",
        )

        assert result.success is False
        assert result.error_message == "Network timeout"


def test_get_webcrawl_service():
    """Test service factory function."""
    service = get_webcrawl_service()
    assert isinstance(service, WebCrawlService)
