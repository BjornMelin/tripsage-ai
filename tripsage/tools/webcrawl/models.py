"""Pydantic schemas for normalized web crawl results."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UnifiedCrawlResult(BaseModel):
    """Unified result schema for web crawling operations.

    Supports different MCP clients.
    """

    # Core identifying fields included in every normalized result.
    url: str = Field(..., description="The URL that was crawled")
    title: str | None = Field(None, description="Page title extracted from the content")
    main_content_markdown: str | None = Field(
        None, description="Main content in markdown format"
    )
    main_content_text: str | None = Field(
        None, description="Main content as plain text"
    )
    html_content: str | None = Field(None, description="Raw HTML content if available")
    # Structured artifacts cover JSON-LD, OG metadata, etc.
    structured_data: dict[str, Any] | None = Field(
        None,
        description=(
            "Structured data extracted from the page (e.g., JSON-LD, OpenGraph)"
        ),
    )
    # crawl_metadata acts as an open payload for source specific details.
    crawl_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the crawl operation",
    )
    error_message: str | None = Field(None, description="Error message if crawl failed")
    status: str = Field("success", description="Status of the crawl operation")

    model_config = {
        "json_schema_extra": {
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
    }

    @property
    def crawl_timestamp(self) -> datetime | None:
        """Get the crawl timestamp from metadata if available."""
        metadata = dict(self.crawl_metadata)
        timestamp = metadata.get("crawl_timestamp")
        if timestamp and isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp)
            except (ValueError, AttributeError):
                pass
        elif isinstance(timestamp, datetime):
            return timestamp
        return None

    @property
    def source_crawler(self) -> str | None:
        """Get the source crawler from metadata if available."""
        metadata = dict(self.crawl_metadata)
        return metadata.get("source_crawler")

    def has_content(self) -> bool:
        """Check if the result contains any meaningful content."""
        return bool(
            self.main_content_markdown
            or self.main_content_text
            or self.html_content
            or self.structured_data
        )
