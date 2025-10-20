"""Result normalizer for web crawling tools.

This module provides functionality to normalize results from different web crawling
sources (Crawl4AI and Firecrawl) into a consistent UnifiedCrawlResult format.
"""

import re
from datetime import UTC, datetime
from typing import Any

from tripsage.tools.webcrawl.models import UnifiedCrawlResult
from tripsage_core.services.external_apis.webcrawl_service import WebCrawlResult
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class ResultNormalizer:
    """Normalizes results from different web crawling sources into UnifiedCrawlResult."""

    async def normalize_firecrawl_output(
        self, raw_output: dict[str, Any], original_url: str
    ) -> UnifiedCrawlResult:
        """Normalize Firecrawl MCP output to UnifiedCrawlResult.

        Args:
            raw_output: The raw output from FirecrawlMCPClient
            original_url: The URL that was crawled

        Returns:
            UnifiedCrawlResult instance
        """
        # Check if the crawl was successful
        if raw_output.get("error"):
            return UnifiedCrawlResult(
                url=original_url,
                status="error",
                error_message=raw_output.get("error"),
                metadata={
                    "source_crawler": "firecrawl",
                    "crawl_timestamp": datetime.now(UTC).isoformat(),
                },
            )

        # Extract main content from different formats
        markdown_content = raw_output.get("markdown")
        html_content = raw_output.get("html")

        # Extract structured data
        structured_data = {}
        if "metadata" in raw_output:
            metadata = raw_output["metadata"]
            # Extract OpenGraph data
            if "ogMetadata" in metadata:
                structured_data["openGraph"] = metadata["ogMetadata"]
            # Extract JSON-LD data
            if "jsonLd" in metadata:
                structured_data["jsonLd"] = metadata["jsonLd"]

        # Extract links if available
        if "links" in raw_output:
            structured_data["links"] = raw_output["links"]

        return UnifiedCrawlResult(
            url=original_url,
            title=raw_output.get("title"),
            main_content_markdown=markdown_content,
            main_content_text=raw_output.get("text"),
            html_content=html_content,
            structured_data=structured_data if structured_data else None,
            metadata={
                "source_crawler": "firecrawl",
                "crawl_timestamp": datetime.now(UTC).isoformat(),
                "content_length": len(markdown_content or ""),
                "has_screenshot": raw_output.get("screenshot") is not None,
                "original_metadata": raw_output.get("metadata", {}),
            },
            status="success",
        )

    async def normalize_crawl4ai_output(
        self, raw_output: dict[str, Any], original_url: str
    ) -> UnifiedCrawlResult:
        """Normalize Crawl4AI MCP output to UnifiedCrawlResult.

        Args:
            raw_output: The raw output from Crawl4AIMCPClient
            original_url: The URL that was crawled

        Returns:
            UnifiedCrawlResult instance
        """
        # Check if the crawl was successful
        if raw_output.get("error"):
            return UnifiedCrawlResult(
                url=original_url,
                status="error",
                error_message=raw_output.get("error"),
                metadata={
                    "source_crawler": "crawl4ai",
                    "crawl_timestamp": datetime.now(UTC).isoformat(),
                },
            )

        # Extract main content - Crawl4AI typically returns in result key
        result_data = raw_output.get("result", {})

        # Determine which content format is available
        markdown_content = result_data.get("markdown")
        html_content = result_data.get("html")
        text_content = result_data.get("cleaned_text") or result_data.get("text")

        # Extract structured data
        structured_data = {}
        if "extracted_content" in result_data:
            structured_data["extracted_content"] = result_data["extracted_content"]
        if "metadata" in result_data:
            structured_data["page_metadata"] = result_data["metadata"]

        # Extract additional fields if available
        metadata = {
            "source_crawler": "crawl4ai",
            "crawl_timestamp": datetime.now(UTC).isoformat(),
            "content_length": len(markdown_content or text_content or ""),
            "has_screenshot": result_data.get("screenshot") is not None,
            "extraction_method": result_data.get("extraction_method", "default"),
            "js_execution": result_data.get("js_executed", False),
        }

        # Add any custom metadata from the result
        if "crawl_metadata" in result_data:
            metadata["crawl_metadata"] = result_data["crawl_metadata"]

        return UnifiedCrawlResult(
            url=original_url,
            title=result_data.get("title"),
            main_content_markdown=markdown_content,
            main_content_text=text_content,
            html_content=html_content,
            structured_data=structured_data if structured_data else None,
            metadata=metadata,
            status="success",
        )

    async def normalize_search_results(
        self, raw_results: list[dict[str, Any]], source: str, query: str
    ) -> list[UnifiedCrawlResult]:
        """Normalize search results from either crawler into UnifiedCrawlResult list.

        Args:
            raw_results: List of raw search results
            source: The source crawler ("firecrawl" or "crawl4ai")
            query: The original search query

        Returns:
            List of UnifiedCrawlResult instances
        """
        normalized_results = []

        for idx, result in enumerate(raw_results):
            # Create a basic unified result for each search result
            unified_result = UnifiedCrawlResult(
                url=result.get("url", f"search-result-{idx}"),
                title=result.get("title"),
                main_content_text=result.get("snippet") or result.get("description"),
                metadata={
                    "source_crawler": source,
                    "search_query": query,
                    "result_position": idx + 1,
                    "crawl_timestamp": datetime.now(UTC).isoformat(),
                },
                status="success",
            )
            normalized_results.append(unified_result)

        return normalized_results

    async def normalize_playwright_mcp_output(
        self, raw_output: dict[str, Any], original_url: str
    ) -> UnifiedCrawlResult:
        """Normalize Playwright MCP output to UnifiedCrawlResult.

        Args:
            raw_output: The raw output from PlaywrightMCPClient
            original_url: The URL that was crawled

        Returns:
            UnifiedCrawlResult instance
        """
        # Check if there was an error
        if raw_output.get("error") or raw_output.get("status") == "error":
            return UnifiedCrawlResult(
                url=original_url,
                status="error",
                error_message=raw_output.get("error")
                or raw_output.get("error_message"),
                metadata={
                    "source_crawler": "playwright_mcp",
                    "crawl_timestamp": datetime.now(UTC).isoformat(),
                },
            )

        # Extract content based on what's available in the output
        # Playwright typically returns visible text and HTML
        text_content = raw_output.get("text") or raw_output.get("visible_text")
        html_content = raw_output.get("html") or raw_output.get("visible_html")
        title = raw_output.get("title")

        # Extract any metadata from the response
        metadata = {
            "source_crawler": "playwright_mcp",
            "crawl_timestamp": datetime.now(UTC).isoformat(),
            "content_length": len(text_content or ""),
            "browser_type": raw_output.get("browser_type", "chromium"),
        }

        # Add screenshot data if available
        if raw_output.get("screenshot"):
            metadata["has_screenshot"] = True
            if raw_output.get("screenshot_base64"):
                metadata["screenshot_base64"] = raw_output["screenshot_base64"]
            elif raw_output.get("screenshot_path"):
                metadata["screenshot_path"] = raw_output["screenshot_path"]

        # Add any custom metadata from the result
        if "metadata" in raw_output:
            metadata["browser_metadata"] = raw_output["metadata"]

        result = UnifiedCrawlResult(
            url=original_url,
            title=title,
            main_content_text=text_content,
            html_content=html_content,
            metadata=metadata,
            status="success",
            source_crawler="playwright_mcp",
        )

        logger.debug(f"Normalized Playwright MCP output for {original_url}")
        return result

    async def normalize_direct_crawl4ai_output(
        self, crawl_result: WebCrawlResult, url: str
    ) -> UnifiedCrawlResult:
        """Normalize direct Crawl4AI SDK output to UnifiedCrawlResult format.

        Args:
            crawl_result: Result from direct Crawl4AI SDK
            url: The original URL

        Returns:
            UnifiedCrawlResult with normalized content
        """
        try:
            if not crawl_result.success:
                return UnifiedCrawlResult(
                    url=url,
                    status="error",
                    error_message=crawl_result.error_message
                    or "Direct Crawl4AI failed",
                    metadata={
                        "source_crawler": "crawl4ai_direct",
                        **crawl_result.metadata,
                        "performance_metrics": crawl_result.performance_metrics,
                    },
                )

            # Extract main content
            main_content_markdown = crawl_result.markdown or ""
            main_content_text = self._markdown_to_text(main_content_markdown)

            # Build metadata
            metadata = {
                "source_crawler": "crawl4ai_direct",
                "word_count": len(main_content_text.split())
                if main_content_text
                else 0,
                "html_length": len(crawl_result.html) if crawl_result.html else 0,
                "status_code": crawl_result.status_code or 200,
                "has_screenshot": bool(crawl_result.screenshot),
                "has_pdf": bool(crawl_result.pdf),
                "crawler_type": "crawl4ai_direct",
                "performance_metrics": crawl_result.performance_metrics,
                **crawl_result.metadata,
            }

            # Performance metrics are included in metadata above

            result = UnifiedCrawlResult(
                url=url,
                title=crawl_result.title,
                main_content_markdown=main_content_markdown,
                main_content_text=main_content_text,
                html_content=crawl_result.html,
                structured_data=crawl_result.structured_data,
                metadata=metadata,
                status="success",
            )

            logger.debug(f"Normalized direct Crawl4AI output for {url}")
            return result

        except Exception as e:
            logger.exception(
                f"Error normalizing direct Crawl4AI output for {url}: {e!s}"
            )
            return UnifiedCrawlResult(
                url=url,
                status="error",
                error_message=f"Normalization error: {e!s}",
                metadata={
                    "source_crawler": "crawl4ai_direct",
                    "error_type": type(e).__name__,
                },
            )

    def _markdown_to_text(self, markdown: str) -> str:
        """Convert markdown to plain text by removing markdown formatting.

        Args:
            markdown: Markdown content

        Returns:
            Plain text content
        """
        if not markdown:
            return ""

        # Simple markdown to text conversion
        # Remove markdown headers
        text = re.sub(r"^#+\s+", "", markdown, flags=re.MULTILINE)
        # Remove bold and italic
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        # Remove links but keep text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # Remove code blocks
        text = re.sub(r"```[^`]*```", "", text, flags=re.DOTALL)
        text = re.sub(r"`([^`]+)`", r"\1", text)

        return text.strip()


# Singleton instance
result_normalizer = ResultNormalizer()


def get_normalizer() -> ResultNormalizer:
    """Get the singleton instance of the result normalizer.

    Returns:
        The normalizer instance
    """
    return result_normalizer
