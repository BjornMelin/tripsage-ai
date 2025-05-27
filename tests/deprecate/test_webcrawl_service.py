"""
Tests for the WebCrawl service with direct Crawl4AI SDK integration.
Fixed version with proper mocking to eliminate real HTTP calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.services.webcrawl_service import (
    WebCrawlParams,
    WebCrawlResult,
    WebCrawlService,
    get_webcrawl_service,
)


class TestWebCrawlParams:
    """Test WebCrawlParams model."""

    def test_default_values(self):
        """Test default parameter values."""
        params = WebCrawlParams()

        assert params.javascript_enabled is True
        assert params.extract_markdown is True
        assert params.extract_html is False
        assert params.extract_structured_data is False
        assert params.use_cache is True
        assert params.screenshot is False
        assert params.pdf is False
        assert params.timeout == 30

    def test_custom_values(self):
        """Test custom parameter values."""
        params = WebCrawlParams(
            javascript_enabled=False,
            extract_html=True,
            screenshot=True,
            timeout=60,
        )

        assert params.javascript_enabled is False
        assert params.extract_html is True
        assert params.screenshot is True
        assert params.timeout == 60


class TestWebCrawlResult:
    """Test WebCrawlResult model."""

    def test_successful_result(self):
        """Test successful crawl result."""
        result = WebCrawlResult(
            success=True,
            url="https://example.com",
            title="Example Title",
            markdown="# Example Content",
            performance_metrics={"duration_ms": 1500},
        )

        assert result.success is True
        assert result.url == "https://example.com"
        assert result.title == "Example Title"
        assert result.markdown == "# Example Content"
        assert result.performance_metrics["duration_ms"] == 1500

    def test_failed_result(self):
        """Test failed crawl result."""
        result = WebCrawlResult(
            success=False,
            url="https://example.com",
            error_message="Network timeout",
        )

        assert result.success is False
        assert result.error_message == "Network timeout"


class TestWebCrawlService:
    """Test WebCrawlService class with proper mocking."""

    @pytest.fixture
    def service(self):
        """Create a WebCrawlService instance."""
        return WebCrawlService()

    @pytest.fixture
    def mock_crawl_result(self):
        """Create a mock Crawl4AI result."""
        result = MagicMock()
        result.success = True
        result.url = "https://example.com"
        result.markdown = "# Example Content\n\nThis is example content."
        result.html = "<html><body><h1>Example Content</h1></body></html>"
        result.metadata = {"title": "Example Page"}
        result.status_code = 200
        result.screenshot = None
        result.pdf = None
        result.extracted_content = None
        return result

    def test_init(self, service):
        """Test service initialization."""
        assert service._browser_config is not None
        assert service._browser_config.headless is True

    @pytest.mark.asyncio
    async def test_health_check_success(self, service):
        """Test successful health check."""
        with patch.object(service, "crawl_url") as mock_crawl:
            mock_crawl.return_value = WebCrawlResult(
                success=True,
                url="https://httpbin.org/html",
            )

            result = await service.health_check()
            assert result is True
            mock_crawl.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, service):
        """Test failed health check."""
        with patch.object(service, "crawl_url") as mock_crawl:
            mock_crawl.return_value = WebCrawlResult(
                success=False,
                url="https://httpbin.org/html",
                error_message="Connection failed",
            )

            result = await service.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self, service):
        """Test health check with exception."""
        with patch.object(service, "crawl_url") as mock_crawl:
            mock_crawl.side_effect = Exception("Network error")

            result = await service.health_check()
            assert result is False

    def test_build_crawler_config_default(self, service):
        """Test building crawler config with default params."""
        params = WebCrawlParams()
        config = service._build_crawler_config(params)

        assert config.cache_mode.value == "enabled"  # Default cache enabled
        assert config.screenshot is False
        assert config.pdf is False
        assert hasattr(config, "js_code")  # JS enabled by default

    def test_build_crawler_config_custom(self, service):
        """Test building crawler config with custom params."""
        params = WebCrawlParams(
            use_cache=False,
            javascript_enabled=False,
            screenshot=True,
            css_selector="div.content",
            excluded_tags=["script", "style"],
        )
        config = service._build_crawler_config(params)

        assert config.cache_mode.value == "bypass"
        assert config.screenshot is True
        assert config.css_selector == "div.content"
        assert config.excluded_tags == ["script", "style"]

    @pytest.mark.asyncio
    async def test_crawl_url_success_with_proper_mocking(
        self, service, mock_crawl_result
    ):
        """Test successful URL crawling with proper AsyncWebCrawler mocking."""
        url = "https://example.com"
        params = WebCrawlParams()

        # Mock the entire crawl4ai module at import level
        with patch(
            "tripsage.services.webcrawl_service.AsyncWebCrawler"
        ) as mock_crawler_class:
            # Create a proper async context manager mock
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_crawl_result)

            # Set up the async context manager protocol
            mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler.__aexit__ = AsyncMock(return_value=None)

            # Make the class return our mock instance
            mock_crawler_class.return_value = mock_crawler

            result = await service.crawl_url(url, params)

            # Verify the result
            assert result.success is True
            assert result.url == url
            assert result.title == "Example Page"
            assert "Example Content" in result.markdown
            assert result.performance_metrics["crawler_type"] == "crawl4ai_direct"
            assert "duration_ms" in result.performance_metrics

            # Verify the crawler was called correctly
            mock_crawler_class.assert_called_once()
            mock_crawler.arun.assert_called_once()

    @pytest.mark.asyncio
    async def test_crawl_url_crawl4ai_failure(self, service):
        """Test crawling when Crawl4AI result indicates failure."""
        url = "https://example.com"
        params = WebCrawlParams()

        mock_crawl_result = MagicMock()
        mock_crawl_result.success = False
        mock_crawl_result.error_message = "Page not found"

        with patch(
            "tripsage.services.webcrawl_service.AsyncWebCrawler"
        ) as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_crawl_result)
            mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler

            result = await service.crawl_url(url, params)

            assert result.success is False
            assert result.error_message == "Page not found"
            assert result.url == url

    @pytest.mark.asyncio
    async def test_crawl_url_exception(self, service):
        """Test crawling with exception during execution."""
        url = "https://example.com"
        params = WebCrawlParams()

        # Mock the AsyncWebCrawler to raise an exception
        with patch(
            "tripsage.services.webcrawl_service.AsyncWebCrawler"
        ) as mock_crawler_class:
            mock_crawler_class.side_effect = Exception("Network timeout")

            result = await service.crawl_url(url, params)

            assert result.success is False
            assert "Network timeout" in result.error_message
            assert result.performance_metrics["error_type"] == "Exception"

    def test_convert_crawl_result_success(self, service, mock_crawl_result):
        """Test successful result conversion."""
        url = "https://example.com"
        duration = 1500.0

        result = service._convert_crawl_result(mock_crawl_result, url, duration)

        assert result.success is True
        assert result.url == url
        assert result.title == "Example Page"
        assert "Example Content" in result.markdown
        assert result.performance_metrics["duration_ms"] == duration
        assert result.metadata["crawler_type"] == "crawl4ai_direct"

    def test_convert_crawl_result_failure(self, service):
        """Test failed result conversion."""
        url = "https://example.com"
        duration = 500.0

        mock_crawl_result = MagicMock()
        mock_crawl_result.success = False
        mock_crawl_result.error_message = "Connection failed"

        result = service._convert_crawl_result(mock_crawl_result, url, duration)

        assert result.success is False
        assert result.error_message == "Connection failed"
        assert result.performance_metrics["duration_ms"] == duration

    def test_convert_crawl_result_with_structured_data(self, service):
        """Test result conversion with structured data."""
        url = "https://example.com"
        duration = 1000.0

        mock_crawl_result = MagicMock()
        mock_crawl_result.success = True
        mock_crawl_result.markdown = "# Test"
        mock_crawl_result.html = "<html></html>"
        mock_crawl_result.metadata = {"title": "Test Page"}
        mock_crawl_result.extracted_content = '{"key": "value"}'
        mock_crawl_result.status_code = 200
        mock_crawl_result.screenshot = None
        mock_crawl_result.pdf = None

        result = service._convert_crawl_result(mock_crawl_result, url, duration)

        assert result.success is True
        assert result.structured_data == {"key": "value"}

    def test_convert_crawl_result_exception(self, service):
        """Test result conversion with exception."""
        url = "https://example.com"
        duration = 100.0

        # Create a mock that raises an exception when accessing attributes
        mock_crawl_result = MagicMock()
        mock_crawl_result.success = property(
            lambda self: (_ for _ in ()).throw(AttributeError("Test error"))
        )

        result = service._convert_crawl_result(mock_crawl_result, url, duration)

        assert result.success is False
        assert "Result conversion error" in result.error_message
        assert result.performance_metrics["error_type"] == "ValidationError"


class TestSingletonService:
    """Test singleton service getter."""

    def test_get_webcrawl_service_singleton(self):
        """Test that get_webcrawl_service returns the same instance."""
        service1 = get_webcrawl_service()
        service2 = get_webcrawl_service()

        assert service1 is service2
        assert isinstance(service1, WebCrawlService)

    def test_get_webcrawl_service_type(self):
        """Test that get_webcrawl_service returns correct type."""
        service = get_webcrawl_service()
        assert isinstance(service, WebCrawlService)


@pytest.mark.integration
class TestWebCrawlServiceIntegration:
    """Integration tests for WebCrawlService with mocked network calls."""

    @pytest.mark.asyncio
    async def test_mocked_integration_test(self):
        """Test integration workflow with mocked responses."""
        service = WebCrawlService()
        params = WebCrawlParams(
            javascript_enabled=False,
            use_cache=False,
        )

        # Mock a realistic response for integration testing
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Test Page\n\nThis is a test page with content."
        mock_result.html = (
            "<html><head><title>Test Page</title></head>"
            "<body><h1>Test Page</h1><p>This is a test page with content.</p>"
            "</body></html>"
        )
        mock_result.metadata = {"title": "Test Page"}
        mock_result.status_code = 200
        mock_result.screenshot = None
        mock_result.pdf = None
        mock_result.extracted_content = None

        with patch(
            "tripsage.services.webcrawl_service.AsyncWebCrawler"
        ) as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler

            result = await service.crawl_url("https://example.com", params)

            # Verify the integration result
            assert result.success is True
            assert result.url == "https://example.com"
            assert result.markdown is not None
            assert len(result.markdown) > 0
            assert result.performance_metrics["crawler_type"] == "crawl4ai_direct"
            assert result.performance_metrics["duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_mocked_health_check_integration(self):
        """Test health check integration with mocked response."""
        service = WebCrawlService()

        # Mock the crawl_url method to simulate a health check
        with patch.object(service, "crawl_url") as mock_crawl:
            mock_crawl.return_value = WebCrawlResult(
                success=True,
                url="https://httpbin.org/html",
                title="httpbin",
                markdown="# httpbin\nA simple HTTP request and response service.",
                performance_metrics={
                    "duration_ms": 800,
                    "crawler_type": "crawl4ai_direct",
                },
            )

            result = await service.health_check()

            # Should pass with mocked response
            assert result is True
            mock_crawl.assert_called_once()
