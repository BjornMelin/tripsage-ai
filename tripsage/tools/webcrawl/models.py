"""Unified web crawl output schema for normalizing results from different crawlers."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class UnifiedCrawlResult(BaseModel):
    """
    Unified result schema for web crawling operations across different MCP clients.
    """

    url: str = Field(..., description="The URL that was crawled")
    title: Optional[str] = Field(
        None, description="Page title extracted from the content"
    )
    main_content_markdown: Optional[str] = Field(
        None, description="Main content in markdown format"
    )
    main_content_text: Optional[str] = Field(
        None, description="Main content as plain text"
    )
    html_content: Optional[str] = Field(
        None, description="Raw HTML content if available"
    )
    structured_data: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Structured data extracted from the page (e.g., JSON-LD, OpenGraph)"
        ),
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the crawl operation",
    )
    error_message: Optional[str] = Field(
        None, description="Error message if crawl failed"
    )
    status: str = Field("success", description="Status of the crawl operation")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "url": "https://example.com/page",
                "title": "Example Page",
                "main_content_markdown": (
                    "# Example Page\n\nThis is the main content..."
                ),
                "structured_data": {"type": "Article", "author": "John Doe"},
                "metadata": {
                    "crawl_timestamp": "2024-03-20T10:00:00Z",
                    "source_crawler": "firecrawl",
                    "content_length": 1234,
                },
                "status": "success",
            }
        }

    @property
    def crawl_timestamp(self) -> Optional[datetime]:
        """Get the crawl timestamp from metadata if available."""
        timestamp = self.metadata.get("crawl_timestamp")
        if timestamp and isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        elif isinstance(timestamp, datetime):
            return timestamp
        return None

    @property
    def source_crawler(self) -> Optional[str]:
        """Get the source crawler from metadata if available."""
        return self.metadata.get("source_crawler")

    def has_content(self) -> bool:
        """Check if the result contains any meaningful content."""
        return bool(
            self.main_content_markdown
            or self.main_content_text
            or self.html_content
            or self.structured_data
        )
