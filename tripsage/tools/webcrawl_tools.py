"""Optimized web crawling tools backed by the WebCrawlService."""

# pylint: disable=duplicate-code

from __future__ import annotations

import time

from tripsage.monitoring.performance_metrics import record_webcrawl_request
from tripsage.tools.webcrawl.models import UnifiedCrawlResult
from tripsage.tools.webcrawl.result_normalizer import ResultNormalizer
from tripsage.tools.webcrawl.source_selector import WebCrawlSourceSelector
from tripsage_core.services.external_apis.webcrawl_service import (
    WebCrawlParams,
    WebCrawlService,
)
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


def _build_params(
    *,
    config: dict[str, bool],
    use_cache: bool,
) -> WebCrawlParams:
    """Create crawl parameters from selector config."""
    return WebCrawlParams(
        javascript_enabled=config["javascript_enabled"],
        extract_markdown=config["extract_markdown"],
        extract_html=config["extract_structured_data"],
        extract_structured_data=config["extract_structured_data"],
        use_cache=use_cache,
        screenshot=False,
        pdf=False,
    )


def _build_error_result(url: str, exc: Exception) -> UnifiedCrawlResult:
    """Create a normalized error response for crawl failures."""
    metadata = {
        "source_crawler": "crawl4ai_direct",
        "crawl4ai_error": type(exc).__name__,
    }
    return UnifiedCrawlResult(
        url=url,
        title=None,
        main_content_markdown=None,
        main_content_text=None,
        html_content=None,
        structured_data=None,
        status="error",
        error_message=f"Crawl4AI crawl failed: {exc!s}",
        crawl_metadata=metadata,
    )


@with_error_handling()
async def crawl_website_content(
    url: str,
    extract_structured_data: bool = False,
    content_type: str | None = None,
    requires_javascript: bool = False,
    use_cache: bool = True,
) -> UnifiedCrawlResult:
    """Crawl a website and normalize the result for downstream tools."""
    logger.info("Starting Crawl4AI crawl for %s", url)

    selector = WebCrawlSourceSelector()
    config = selector.get_optimized_config(
        content_type=content_type,
        requires_javascript=requires_javascript,
        extract_structured_data=extract_structured_data,
    )
    params = _build_params(config=config, use_cache=use_cache)

    service = WebCrawlService()
    await service.connect()
    normalizer = ResultNormalizer()
    start = time.perf_counter()

    try:
        crawl_result = await service.crawl_url(url, params)
        duration_ms = (time.perf_counter() - start) * 1000
        record_webcrawl_request(duration_ms, crawl_result.success)

        logger.info("Crawl4AI completed for %s, success=%s", url, crawl_result.success)
        return await normalizer.normalize_direct_crawl4ai_output(crawl_result, url)
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        record_webcrawl_request(duration_ms, False)
        logger.exception("Crawl4AI crawl failed for %s", url)
        return _build_error_result(url, exc)


@with_error_handling()
async def crawl_travel_blog(
    url: str,
    extract_insights: bool = True,
    use_cache: bool = True,
) -> UnifiedCrawlResult:
    """Crawl a travel blog using the travel_blog selector profile."""
    return await crawl_website_content(
        url=url,
        extract_structured_data=extract_insights,
        content_type="travel_blog",
        requires_javascript=False,
        use_cache=use_cache,
    )


@with_error_handling()
async def crawl_booking_site(
    url: str,
    extract_prices: bool = True,
    use_cache: bool = True,
) -> UnifiedCrawlResult:
    """Crawl a booking site using the booking selector profile."""
    return await crawl_website_content(
        url=url,
        extract_structured_data=extract_prices,
        content_type="booking",
        requires_javascript=True,
        use_cache=use_cache,
    )


@with_error_handling()
async def crawl_event_listing(
    url: str,
    extract_dates: bool = True,
    use_cache: bool = True,
) -> UnifiedCrawlResult:
    """Crawl an event listing using the events selector profile."""
    return await crawl_website_content(
        url=url,
        extract_structured_data=extract_dates,
        content_type="events",
        requires_javascript=True,
        use_cache=use_cache,
    )


# Compatibility alias for legacy imports/tests
crawl_website_content_tool = crawl_website_content
