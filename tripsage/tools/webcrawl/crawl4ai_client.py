"""Crawl4AI direct SDK client for TripSage.

Provides direct integration with Crawl4AI SDK for web crawling and content extraction.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any, cast

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.deep_crawling import (
    BestFirstCrawlingStrategy,
    BFSDeepCrawlStrategy,
    DFSDeepCrawlStrategy,
)
from crawl4ai.deep_crawling.filters import (
    ContentRelevanceFilter,
    ContentTypeFilter,
    DomainFilter,
    FilterChain,
    SEOFilter,
    URLFilter,
    URLPatternFilter,
)
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from pydantic import BaseModel, Field

from tripsage.tools.memory_tools import ConversationMessage, get_memory_service
from tripsage_core.services.business.memory_service import (
    ConversationMemoryRequest,
)
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class Crawl4AIClient:
    """Async Crawl4AI client that exposes streaming and aggregated APIs."""

    def __init__(self, max_concurrent_crawls: int = 5):
        """Initialize the Crawl4AI client.

        Args:
            max_concurrent_crawls: Maximum concurrent Crawl4AI runs allowed.
        """
        self._semaphore = asyncio.Semaphore(max_concurrent_crawls)

    class DeepCrawlConfig(BaseModel):
        """Deep crawling configuration."""

        strategy: str = Field(
            default="bfs",
            pattern="^(bfs|dfs|bestfirst)$",
            description="Deep crawl strategy identifier.",
        )
        max_depth: int = Field(
            default=0,
            ge=0,
            le=5,
            description="Levels beyond the origin page to traverse.",
        )
        max_pages: int | None = Field(
            default=None,
            ge=1,
            description="Optional hard page limit for the crawl session.",
        )
        include_external: bool = Field(
            default=False,
            description="Allow traversal to external domains when True.",
        )
        keywords: Sequence[str] = Field(
            default_factory=tuple,
            description=("Keywords used by keyword scorer when strategy is bestfirst."),
        )
        keyword_weight: float = Field(
            default=0.7,
            ge=0.0,
            le=1.0,
            description="Weight applied to keyword scorer results.",
        )
        url_patterns: Sequence[str] = Field(
            default_factory=tuple,
            description="Glob patterns for URL filtering.",
        )
        allowed_domains: Sequence[str] = Field(
            default_factory=tuple,
            description="Domains explicitly allowed for crawling.",
        )
        blocked_domains: Sequence[str] = Field(
            default_factory=tuple,
            description="Domains excluded from crawling.",
        )
        content_types: Sequence[str] = Field(
            default_factory=tuple,
            description="Accepted HTTP content types.",
        )
        relevance_query: str | None = Field(
            default=None,
            description=("Optional semantic relevance query for content filtering."),
        )
        relevance_threshold: float = Field(
            default=0.7,
            ge=0.0,
            le=1.0,
            description="Threshold for relevance filter when enabled.",
        )
        seo_keywords: Sequence[str] = Field(
            default_factory=tuple,
            description="Keywords for the SEO filter.",
        )
        seo_threshold: float = Field(
            default=0.5,
            ge=0.0,
            le=1.0,
            description="Threshold for SEO filter scoring.",
        )

        def build_strategy(
            self,
        ) -> BFSDeepCrawlStrategy | DFSDeepCrawlStrategy | BestFirstCrawlingStrategy:
            """Construct the Crawl4AI deep crawl strategy."""
            strategy_lower = str(self.strategy).lower()
            filter_chain = self._build_filter_chain()

            if strategy_lower == "bestfirst":
                scorer = None
                if self.keywords:
                    scorer = KeywordRelevanceScorer(
                        keywords=list(self.keywords),
                        weight=self.keyword_weight,
                    )

                return BestFirstCrawlingStrategy(
                    max_depth=self.max_depth,
                    include_external=self.include_external,
                    max_pages=self.max_pages or 0,
                    filter_chain=filter_chain or FilterChain([]),  # type: ignore[arg-type]
                    url_scorer=scorer,
                )

            strategy_type = BFSDeepCrawlStrategy
            if strategy_lower == "dfs":
                strategy_type = DFSDeepCrawlStrategy

            return strategy_type(
                max_depth=self.max_depth,
                include_external=self.include_external,
                max_pages=self.max_pages or 0,
                filter_chain=filter_chain or FilterChain([]),  # type: ignore[arg-type]
            )

        def _build_filter_chain(self) -> FilterChain | None:
            filters: list[URLFilter] = []

            # Apply domain gating first to reduce queue churn on disallowed hosts.
            if self.allowed_domains or self.blocked_domains:
                filters.append(
                    DomainFilter(
                        allowed_domains=list(self.allowed_domains)
                        if self.allowed_domains
                        else [],
                        blocked_domains=list(self.blocked_domains)
                        if self.blocked_domains
                        else [],
                    )
                )

            if self.url_patterns:
                # Patterns restrict traversal to semantically relevant paths.
                filters.append(URLPatternFilter(patterns=list(self.url_patterns)))

            if self.content_types:
                # Content-type guard prevents binary or media heavy responses.
                filters.append(
                    ContentTypeFilter(allowed_types=list(self.content_types))
                )

            if self.relevance_query:
                filters.append(
                    ContentRelevanceFilter(
                        query=self.relevance_query,
                        threshold=self.relevance_threshold,
                    )
                )

            if self.seo_keywords:
                filters.append(
                    SEOFilter(
                        threshold=self.seo_threshold,
                        keywords=list(self.seo_keywords),
                    )
                )

            if not filters:
                return FilterChain([])

            return FilterChain(filters)

    class ScrapeConfig(BaseModel):
        """Configuration for scraping URLs."""

        full_page: bool = Field(
            default=False, description="Whether to get the full page content"
        )
        extract_images: bool = Field(
            default=False, description="Whether to extract image data"
        )
        extract_links: bool = Field(
            default=False, description="Whether to extract links"
        )
        specific_selector: str | None = Field(
            default=None, description="CSS selector to target specific content"
        )
        js_enabled: bool = Field(
            default=True, description="Whether to enable JavaScript execution"
        )
        stream: bool = Field(
            default=False,
            description="Return streaming async iterator when True.",
        )
        deep_crawl: Crawl4AIClient.DeepCrawlConfig | None = Field(
            default=None,
            description="Optional deep crawling configuration.",
        )
        word_count_threshold: int = Field(
            default=10,
            ge=0,
            description="Minimum words required for extracted blocks.",
        )

    async def stream_url(
        self,
        url: str,
        config: ScrapeConfig | None = None,
    ) -> AsyncIterator[Any]:
        """Stream raw Crawl4AI results for a URL.

        Args:
            url: Target URL to crawl.
            config: Optional scrape configuration.

        Yields:
            Each `CrawlResult` item produced by Crawl4AI.
        """
        scrape_config = config or self.ScrapeConfig()
        browser_config = self._build_browser_config(scrape_config)
        run_config = self._build_run_config(scrape_config)

        async with self._semaphore, AsyncWebCrawler(config=browser_config) as crawler:
            crawl_callable = cast(Callable[..., Awaitable[Any]], crawler.arun)  # type: ignore[arg-type]
            crawl_result = await crawl_callable(url=url, config=run_config)

        if scrape_config.stream:
            if isinstance(crawl_result, list):
                typed_crawl_result = cast(list[Any], crawl_result)
                for item in typed_crawl_result:
                    yield item
                return

            async_iterator = getattr(crawl_result, "__aiter__", None)
            if async_iterator is None:
                yield crawl_result
                return

            iterator = cast(AsyncIterator[Any], crawl_result)
            async for page in iterator:
                yield page
            return

        yield crawl_result

    async def scrape_url(
        self,
        url: str,
        config: ScrapeConfig | None = None,
    ) -> dict[str, Any]:
        """Collect crawl results and return formatted aggregate output.

        Args:
            url: Target URL to crawl.
            config: Optional scrape configuration.

        Returns:
            Aggregated crawl payload containing formatted items or an error.
        """
        results = [item async for item in self.stream_url(url=url, config=config)]
        return self._format_aggregate(url, results)

    async def gather_results(
        self,
        url: str,
        config: ScrapeConfig | None = None,
    ) -> list[Any]:
        """Return the raw list of Crawl4AI results for a URL."""
        return [item async for item in self.stream_url(url=url, config=config)]

    async def stream_blog(self, url: str, max_pages: int = 1) -> AsyncIterator[Any]:
        """Stream blog crawl results using deep crawling when requested.

        Args:
            url: Blog root URL.
            max_pages: Maximum pages to crawl; >1 enables deep crawling.

        Yields:
            Each `CrawlResult` item produced by Crawl4AI.
        """
        deep_config = None
        if max_pages > 1:
            deep_config = self.DeepCrawlConfig(
                strategy="bfs",
                max_depth=max(max_pages - 1, 0),
                max_pages=max_pages,
                include_external=False,
            )

        scrape_config = self.ScrapeConfig(
            stream=max_pages > 1,
            word_count_threshold=50,
            deep_crawl=deep_config,
        )

        async for page in self.stream_url(url=url, config=scrape_config):
            yield page

    async def crawl_blog(
        self, url: str, extract_type: str, max_pages: int = 1
    ) -> dict[str, Any]:
        """Aggregate blog crawl results into a formatted payload."""
        results = [
            item async for item in self.stream_blog(url=url, max_pages=max_pages)
        ]
        payload = self._format_aggregate(url, results)
        if payload.get("success"):
            payload["extract_type"] = extract_type
        return payload

    async def extract_travel_insights(
        self,
        content: str,
        url: str,
        user_id: str | None = None,
        content_type: str = "web_content",
    ) -> dict[str, Any]:
        """Extract travel-related insights from web content using Mem0.

        Args:
            content: Text content to analyze
            url: Source URL
            user_id: Optional user ID for personalized extraction
            content_type: Type of content (web_content, blog, review, etc.)

        Returns:
            Extracted insights and memory storage result
        """
        try:
            memory_service = await get_memory_service()

            # Create conversation messages for memory extraction
            system_prompt = (
                "Extract travel-related information from web content. "
                "Focus on destinations, activities, tips, recommendations, "
                f"and practical travel advice. Source: {url}"
            )

            messages = [
                ConversationMessage(role="system", content=system_prompt),
                ConversationMessage(
                    role="user",
                    content=f"Web content from {url}:\n\n{content[:2000]}...",
                ),
            ]

            # Create memory request
            memory_request = ConversationMemoryRequest(
                messages=[
                    {"role": msg.role, "content": msg.content} for msg in messages
                ],
                session_id=None,
                trip_id=None,
                metadata={
                    "source_url": url,
                    "content_type": content_type,
                    "extraction_type": "travel_insights",
                    "domain": "travel_planning",
                },
            )

            # Extract memories using Mem0
            memory_result = await memory_service.add_conversation_memory(
                user_id=user_id or "web_crawler",
                memory_request=memory_request,
            )

            # Parse extracted insights
            memory_payload = memory_result
            insights = self._parse_travel_insights(
                memory_payload,
                content,
                url,
            )

            insight_count = len(insights.get("insights", []))
            logger.info(
                "Extracted travel insights from %s",
                url,
                extra={"insights_count": insight_count},
            )

            return {
                "success": True,
                "url": url,
                "insights": insights,
                "memory_result": memory_result,
                "extracted_count": len(memory_payload.get("results", [])),
            }

        except Exception as e:
            logger.exception("Failed to extract travel insights")
            return {"success": False, "url": url, "error": str(e), "insights": {}}

    def _parse_travel_insights(
        self, memory_result: dict[str, Any], content: str, url: str
    ) -> dict[str, Any]:
        """Parse and categorize travel insights from memory extraction result.

        Args:
            memory_result: Result from memory service
            content: Original content
            url: Source URL

        Returns:
            Categorized travel insights
        """
        insights: dict[str, Any] = {
            "destinations": [],
            "activities": [],
            "tips": [],
            "recommendations": [],
            "practical_info": [],
            "budget_info": [],
            "timing": [],
        }

        # Extract memories and categorize them
        for memory in memory_result.get("results", []):
            memory_text = memory.get("memory", "")
            memory_lower = memory_text.lower()

            # Categorize based on content keywords
            destination_words = ["visit", "destination", "city", "country", "place"]
            activity_words = ["activity", "do", "experience", "tour", "attraction"]
            tip_words = ["tip", "advice", "recommend", "suggest", "should"]
            recommendation_words = ["restaurant", "hotel", "stay", "eat", "food"]
            practical_words = [
                "transport",
                "flight",
                "train",
                "bus",
                "visa",
                "passport",
            ]
            budget_words = ["cost", "price", "budget", "money", "expensive", "cheap"]
            timing_words = ["time", "season", "weather", "month", "when"]

            if any(word in memory_lower for word in destination_words):
                insights["destinations"].append(memory_text)
            elif any(word in memory_lower for word in activity_words):
                insights["activities"].append(memory_text)
            elif any(word in memory_lower for word in tip_words):
                insights["tips"].append(memory_text)
            elif any(word in memory_lower for word in recommendation_words):
                insights["recommendations"].append(memory_text)
            elif any(word in memory_lower for word in practical_words):
                insights["practical_info"].append(memory_text)
            elif any(word in memory_lower for word in budget_words):
                insights["budget_info"].append(memory_text)
            elif any(word in memory_lower for word in timing_words):
                insights["timing"].append(memory_text)

        # Add content statistics
        insights["metadata"] = {
            "url": url,
            "content_length": len(content),
            "total_memories": len(memory_result.get("results", [])),
            "extraction_successful": memory_result.get("success", False),
        }

        return insights

    async def scrape_with_memory_extraction(
        self,
        url: str,
        user_id: str | None = None,
        config: ScrapeConfig | None = None,
    ) -> dict[str, Any]:
        """Scrape URL and extract travel insights to memory.

        This method combines web scraping with automatic travel insight extraction
        and storage in the user's memory for future personalization.

        Args:
            url: The URL to scrape
            user_id: User ID for personalized memory storage
            config: Configuration for the scrape operation

        Returns:
            Combined scraping and memory extraction result
        """
        if config is None:
            config = self.ScrapeConfig()

        # First, scrape the content
        scrape_result = await self.scrape_url(
            url=url,
            config=config,
        )

        if not scrape_result.get("success"):
            return scrape_result

        # Extract content for memory processing
        content = ""
        items = scrape_result.get("items", [])
        if items:
            content = items[0].get("content", "")

        # Extract travel insights if content is available
        insights_result: dict[str, Any] = {}
        if content and len(content.strip()) > 50:  # Only process substantial content
            insights_result = await self.extract_travel_insights(
                content=content, url=url, user_id=user_id, content_type="web_scrape"
            )

        # Combine results
        return {
            **scrape_result,
            "memory_extraction": insights_result,
            "has_insights": insights_result.get("success", False),
            "insights_count": insights_result.get("extracted_count", 0),
        }

    def _build_metadata(self, result: Any, markdown_content: str) -> dict[str, Any]:
        """Build metadata dictionary for a crawl result."""
        metadata: dict[str, Any] = {
            "word_count": len(markdown_content.split()) if markdown_content else 0,
            "links": getattr(result, "links", {}),
        }

        if hasattr(result, "metadata"):
            crawl_metadata = getattr(result, "metadata", {}) or {}
            metadata.update(
                {
                    "depth": crawl_metadata.get("depth", 0),
                    "score": crawl_metadata.get("score"),
                }
            )

        return metadata

    def _build_browser_config(self, config: ScrapeConfig) -> BrowserConfig:
        """Build browser configuration for Crawl4AI."""
        return BrowserConfig(headless=True, java_script_enabled=config.js_enabled)

    def _build_run_config(self, config: ScrapeConfig) -> CrawlerRunConfig:
        """Build crawler run configuration from scrape configuration."""
        # Configure single page fetch with caller supplied extraction hints.
        base_config = CrawlerRunConfig(
            css_selector=config.specific_selector or "",
            word_count_threshold=config.word_count_threshold,
            process_iframes=False,
            stream=config.stream,
        )

        if not config.deep_crawl:
            return base_config

        deep_strategy = config.deep_crawl.build_strategy()
        return base_config.model_copy(update={"deep_crawl_strategy": deep_strategy})

    def _format_aggregate(self, url: str, results: list[Any]) -> dict[str, Any]:
        """Format aggregated crawl results into a standardized payload."""
        if not results:
            return {
                "success": False,
                "url": url,
                "error": "No data returned from Crawl4AI",
                "items": [],
            }

        failures = [res for res in results if not getattr(res, "success", True)]
        if failures:
            first_failure = failures[0]
            return {
                "success": False,
                "url": getattr(first_failure, "url", url),
                "error": getattr(first_failure, "error_message", "Crawl failed"),
                "items": [],
            }

        items = self._format_items(results, url)
        return {
            "success": True,
            "url": url,
            "items": items,
            "formatted": f"Successfully extracted {len(items)} item(s) from {url}",
        }

    def _format_items(
        self, results: list[Any], fallback_url: str
    ) -> list[dict[str, Any]]:
        """Format raw Crawl4AI results into item dictionaries."""
        items: list[dict[str, Any]] = []
        for result in results:
            markdown_field = getattr(result, "markdown", "")
            raw_markdown = getattr(markdown_field, "raw_markdown", None)
            markdown_content = (
                raw_markdown if raw_markdown is not None else markdown_field
            )
            items.append(
                {
                    "title": getattr(result, "title", "") or "",
                    "content": markdown_content or "",
                    "url": getattr(result, "url", fallback_url),
                    "metadata": self._build_metadata(result, markdown_content),
                }
            )
        return items


async def gather_crawl(
    url: str,
    *,
    client: Crawl4AIClient | None = None,
    config: Crawl4AIClient.ScrapeConfig | None = None,
) -> list[Any]:
    """Convenience helper to gather raw crawl results eagerly."""
    crawler_client = client or Crawl4AIClient()
    return await crawler_client.gather_results(url=url, config=config)


class SyncWebCrawlClient:
    """Synchronous facade over the async Crawl4AI client."""

    def __init__(self, *, max_concurrent_crawls: int = 5):
        """Initialize the sync facade.

        Args:
            max_concurrent_crawls: Maximum concurrent Crawl4AI runs for the
                underlying client.
        """
        self._client = Crawl4AIClient(max_concurrent_crawls=max_concurrent_crawls)

    def gather_results(
        self,
        url: str,
        config: Crawl4AIClient.ScrapeConfig | None = None,
    ) -> list[Any]:
        """Synchronously gather raw crawl results."""
        return asyncio.get_event_loop().run_until_complete(
            self._client.gather_results(url=url, config=config)
        )

    def scrape_url(
        self,
        url: str,
        config: Crawl4AIClient.ScrapeConfig | None = None,
    ) -> dict[str, Any]:
        """Synchronously retrieve aggregated crawl output."""
        return asyncio.get_event_loop().run_until_complete(
            self._client.scrape_url(url=url, config=config)
        )

    def crawl_blog(
        self,
        url: str,
        extract_type: str,
        max_pages: int = 1,
    ) -> dict[str, Any]:
        """Synchronously crawl a blog and return aggregated output."""
        return asyncio.get_event_loop().run_until_complete(
            self._client.crawl_blog(
                url=url, extract_type=extract_type, max_pages=max_pages
            )
        )
