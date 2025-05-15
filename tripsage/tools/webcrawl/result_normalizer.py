"""
Result normalizer for web crawling tools.

This module provides functionality to normalize results from different web crawling
sources (Crawl4AI and Firecrawl) into a consistent UnifiedCrawlResult format.
"""

from datetime import datetime
from typing import Any, Dict, List

from tripsage.tools.webcrawl.models import UnifiedCrawlResult
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class ResultNormalizer:
    """
    Normalizes results from different web crawling sources into UnifiedCrawlResult.
    """

    async def normalize_firecrawl_output(
        self, raw_output: Dict[str, Any], original_url: str
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
                    "crawl_timestamp": datetime.utcnow().isoformat(),
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
                "crawl_timestamp": datetime.utcnow().isoformat(),
                "content_length": len(markdown_content or ""),
                "has_screenshot": raw_output.get("screenshot") is not None,
                "original_metadata": raw_output.get("metadata", {}),
            },
            status="success",
        )

    async def normalize_crawl4ai_output(
        self, raw_output: Dict[str, Any], original_url: str
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
                    "crawl_timestamp": datetime.utcnow().isoformat(),
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
            "crawl_timestamp": datetime.utcnow().isoformat(),
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
        self, raw_results: List[Dict[str, Any]], source: str, query: str
    ) -> List[UnifiedCrawlResult]:
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
                    "crawl_timestamp": datetime.utcnow().isoformat(),
                },
                status="success",
            )
            normalized_results.append(unified_result)

        return normalized_results


# Singleton instance
result_normalizer = ResultNormalizer()


def get_normalizer() -> ResultNormalizer:
    """Get the singleton instance of the result normalizer.

    Returns:
        The normalizer instance
    """
    return result_normalizer
