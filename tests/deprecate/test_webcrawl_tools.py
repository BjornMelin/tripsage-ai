"""
Tests for webcrawl_tools.py with Crawl4AI primary + Playwright fallback architecture.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.services.webcrawl_service import WebCrawlResult
from tripsage.tools.webcrawl.models import UnifiedCrawlResult
from tripsage.tools.webcrawl_tools import (
    _crawl_with_playwright_fallback,
    crawl_booking_site,
    crawl_event_listing,
    crawl_travel_blog,
    crawl_website_content,
)


class TestCrawlWebsiteContent:
    """Test the main crawl_website_content function."""

    @pytest.mark.asyncio
    async def test_successful_crawl4ai_primary(self):
        """Test successful crawling with Crawl4AI primary engine."""
        # Mock the webcrawl service
        with (
            patch("tripsage.tools.webcrawl_tools.get_webcrawl_service") as mock_service,
            patch("tripsage.tools.webcrawl_tools.get_performance_metrics"),
        ):
            # Setup mocks
            mock_webcrawl_service = AsyncMock()
            mock_service.return_value = mock_webcrawl_service

            mock_result = WebCrawlResult(
                success=True,
                url="https://example.com",
                extracted_content="Test content",
                performance_metrics={"duration_ms": 500},
            )
            mock_webcrawl_service.crawl_url.return_value = mock_result

            # Mock the result normalizer
            with patch(
                "tripsage.tools.webcrawl_tools.ResultNormalizer"
            ) as mock_normalizer_class:
                mock_normalizer = AsyncMock()
                mock_normalizer_class.return_value = mock_normalizer

                expected_result = UnifiedCrawlResult(
                    url="https://example.com",
                    status="success",
                    main_content_text="Test content",
                    metadata={"source_crawler": "crawl4ai_direct"},
                )
                mock_normalizer.normalize_direct_crawl4ai_output.return_value = (
                    expected_result
                )

                # Execute the function
                result = await crawl_website_content("https://example.com")

                # Assertions
                assert result.url == "https://example.com"
                assert result.status == "success"
                assert result.source_crawler == "crawl4ai_direct"
                assert result.main_content_text == "Test content"

                # Verify service was called
                mock_webcrawl_service.crawl_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_crawl4ai_failure_with_playwright_fallback_disabled(self):
        """Test Crawl4AI failure without Playwright fallback."""
        with patch(
            "tripsage.tools.webcrawl_tools.get_webcrawl_service"
        ) as mock_service:
            # Setup service to fail
            mock_webcrawl_service = AsyncMock()
            mock_service.return_value = mock_webcrawl_service
            mock_webcrawl_service.crawl_url.side_effect = Exception("Crawl4AI failed")

            # Execute with fallback disabled
            result = await crawl_website_content(
                "https://example.com", enable_playwright_fallback=False
            )

            # Assertions
            assert result.status == "error"
            assert result.source_crawler == "failed_all"
            assert "All crawling methods failed" in result.error_message

    @pytest.mark.asyncio
    async def test_crawl4ai_failure_with_successful_playwright_fallback(self):
        """Test Crawl4AI failure with successful Playwright fallback."""
        with (
            patch("tripsage.tools.webcrawl_tools.get_webcrawl_service") as mock_service,
            patch(
                "tripsage.tools.webcrawl_tools._crawl_with_playwright_fallback"
            ) as mock_fallback,
            patch(
                "tripsage.tools.webcrawl_tools.get_performance_metrics"
            ) as mock_metrics,
        ):
            # Setup service to fail
            mock_webcrawl_service = AsyncMock()
            mock_service.return_value = mock_webcrawl_service
            mock_webcrawl_service.crawl_url.side_effect = Exception("Crawl4AI failed")

            # Setup successful fallback
            fallback_result = UnifiedCrawlResult(
                url="https://example.com",
                status="success",
                main_content_text="Fallback content",
                metadata={"source_crawler": "playwright_fallback"},
            )
            mock_fallback.return_value = fallback_result

            # Setup metrics mock
            mock_metrics_instance = MagicMock()
            mock_metrics.return_value = mock_metrics_instance

            # Execute with fallback enabled
            result = await crawl_website_content(
                "https://example.com", enable_playwright_fallback=True
            )

            # Assertions
            assert result.status == "success"
            assert result.source_crawler == "playwright_fallback"
            assert result.main_content_text == "Fallback content"

            # Verify fallback was called
            mock_fallback.assert_called_once()

            # Verify metrics were recorded
            mock_metrics_instance.add_playwright_fallback_result.assert_called_once_with(
                True
            )


class TestPlaywrightFallback:
    """Test the Playwright fallback implementation."""

    @pytest.mark.asyncio
    async def test_playwright_fallback_success(self):
        """Test successful Playwright fallback crawling."""
        # Mock the entire Playwright chain
        with patch("tripsage.tools.webcrawl_tools.async_playwright") as mock_playwright:
            # Setup mock hierarchy
            mock_playwright_instance = AsyncMock()
            mock_playwright.return_value.__aenter__.return_value = (
                mock_playwright_instance
            )

            mock_browser = AsyncMock()
            mock_playwright_instance.chromium.launch.return_value = mock_browser

            mock_context = AsyncMock()
            mock_browser.new_context.return_value = mock_context

            mock_page = AsyncMock()
            mock_context.new_page.return_value = mock_page

            # Setup page methods
            mock_page.title.return_value = "Test Page"
            mock_page.inner_text.return_value = "Test content from Playwright"
            mock_page.content.return_value = "<html><body>Test content</body></html>"
            mock_page.query_selector_all.return_value = []  # No JSON-LD scripts

            # Execute the fallback
            result = await _crawl_with_playwright_fallback(
                "https://example.com", extract_structured_data=True
            )

            # Assertions
            assert result.url == "https://example.com"
            assert result.status == "success"
            assert result.source_crawler == "playwright_fallback"
            assert result.title == "Test Page"
            assert result.main_content_text == "Test content from Playwright"
            assert result.html_content == "<html><body>Test content</body></html>"

            # Verify Playwright calls
            mock_playwright_instance.chromium.launch.assert_called_once()
            mock_browser.new_context.assert_called_once()
            mock_page.goto.assert_called_once_with(
                "https://example.com", wait_until="domcontentloaded", timeout=30000
            )


class TestConvenienceFunctions:
    """Test the specialized convenience functions."""

    @pytest.mark.asyncio
    async def test_crawl_travel_blog(self):
        """Test travel blog crawling function."""
        with patch("tripsage.tools.webcrawl_tools.crawl_website_content") as mock_crawl:
            expected_result = UnifiedCrawlResult(
                url="https://blog.example.com",
                status="success",
                source_crawler="crawl4ai_direct",
            )
            mock_crawl.return_value = expected_result

            result = await crawl_travel_blog(
                "https://blog.example.com", extract_insights=True
            )

            # Verify it calls the main function with correct parameters
            mock_crawl.assert_called_once_with(
                url="https://blog.example.com",
                extract_structured_data=True,
                content_type="travel_blog",
                requires_javascript=False,
                use_cache=True,
            )

            assert result == expected_result

    @pytest.mark.asyncio
    async def test_crawl_booking_site(self):
        """Test booking site crawling function."""
        with patch("tripsage.tools.webcrawl_tools.crawl_website_content") as mock_crawl:
            expected_result = UnifiedCrawlResult(
                url="https://booking.example.com",
                status="success",
                source_crawler="crawl4ai_direct",
            )
            mock_crawl.return_value = expected_result

            result = await crawl_booking_site(
                "https://booking.example.com", extract_prices=True
            )

            # Verify it calls the main function with correct parameters
            mock_crawl.assert_called_once_with(
                url="https://booking.example.com",
                extract_structured_data=True,
                content_type="booking",
                requires_javascript=True,  # Booking sites usually need JS
                use_cache=True,
            )

            assert result == expected_result

    @pytest.mark.asyncio
    async def test_crawl_event_listing(self):
        """Test event listing crawling function."""
        with patch("tripsage.tools.webcrawl_tools.crawl_website_content") as mock_crawl:
            expected_result = UnifiedCrawlResult(
                url="https://events.example.com",
                status="success",
                source_crawler="crawl4ai_direct",
            )
            mock_crawl.return_value = expected_result

            result = await crawl_event_listing(
                "https://events.example.com", extract_dates=True
            )

            # Verify it calls the main function with correct parameters
            mock_crawl.assert_called_once_with(
                url="https://events.example.com",
                extract_structured_data=True,
                content_type="events",
                requires_javascript=True,  # Event sites often need JS
                use_cache=True,
            )

            assert result == expected_result
