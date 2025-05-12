"""
Models for web crawling tools.

This module defines Pydantic models used by web crawling tools to validate
input parameters and response data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ExtractContentParams(BaseModel):
    """Parameters for extracting content from a webpage."""

    url: str = Field(..., description="The URL to extract content from")
    content_type: Optional[str] = Field(
        None, description="Type of content to extract (article, product, recipe, etc.)"
    )
    full_page: bool = Field(
        False, description="Whether to extract the full page or just the main content"
    )
    extract_images: bool = Field(False, description="Whether to extract image data")
    extract_links: bool = Field(False, description="Whether to extract links")
    specific_selector: Optional[str] = Field(
        None, description="CSS selector to target specific content"
    )


class SearchDestinationParams(BaseModel):
    """Parameters for searching information about a travel destination."""

    destination: str = Field(..., description="The destination to search for")
    query: str = Field(..., description="The specific query about the destination")
    search_depth: str = Field(
        "standard", description="Depth of search (standard or deep)"
    )

    @validator("search_depth")
    def validate_search_depth(cls, v):
        """Validate search depth."""
        if v not in ["standard", "deep"]:
            raise ValueError('search_depth must be "standard" or "deep"')
        return v


class PriceMonitorParams(BaseModel):
    """Parameters for monitoring price changes on travel sites."""

    url: str = Field(..., description="The URL of the travel product to monitor")
    product_type: str = Field(
        ..., description="Type of product (flight, hotel, car_rental, etc.)"
    )
    target_selectors: Optional[Dict[str, str]] = Field(
        None, description="CSS selectors for price elements"
    )
    frequency: Optional[str] = Field(
        "daily", description="Monitoring frequency (hourly, daily, weekly)"
    )

    @validator("frequency")
    def validate_frequency(cls, v):
        """Validate monitoring frequency."""
        if v not in ["hourly", "daily", "weekly"]:
            raise ValueError('frequency must be "hourly", "daily", or "weekly"')
        return v


class EventSearchParams(BaseModel):
    """Parameters for searching events at a destination."""

    destination: str = Field(..., description="The destination to search for events")
    event_type: Optional[str] = Field(
        None, description="Type of event (festival, concert, sports, etc.)"
    )
    start_date: Optional[str] = Field(
        None, description="Start date for event search (YYYY-MM-DD)"
    )
    end_date: Optional[str] = Field(
        None, description="End date for event search (YYYY-MM-DD)"
    )


class BlogCrawlParams(BaseModel):
    """Parameters for crawling travel blogs."""

    url: str = Field(..., description="The URL of the travel blog to crawl")
    extract_type: str = Field(
        "insights", description="What to extract (insights, itinerary, tips, places)"
    )
    max_pages: Optional[int] = Field(1, description="Maximum number of pages to crawl")

    @validator("extract_type")
    def validate_extract_type(cls, v):
        """Validate extract type."""
        valid_types = ["insights", "itinerary", "tips", "places"]
        if v not in valid_types:
            raise ValueError(f"extract_type must be one of {', '.join(valid_types)}")
        return v


class CrawlResultItem(BaseModel):
    """A single item in a crawl result."""

    title: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class CrawlResult(BaseModel):
    """Result of a web crawl operation."""

    success: bool = Field(..., description="Whether the crawl was successful")
    query: Optional[str] = None
    url: Optional[str] = None
    items: List[CrawlResultItem] = Field(default_factory=list)
    error: Optional[str] = None
    formatted: Optional[str] = None
