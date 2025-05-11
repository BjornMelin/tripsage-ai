"""Interface for web crawling sources."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypedDict, Union


class ExtractionOptions(TypedDict, total=False):
    """Options for content extraction."""

    selectors: Optional[List[str]]
    include_images: bool
    format: str
    timeout: int
    wait: int


class ExtractedContent(TypedDict):
    """Structure of extracted content."""

    url: str
    title: str
    content: str
    images: Optional[List[str]]
    metadata: Optional[Dict[str, Any]]
    format: str


class TopicResult(TypedDict):
    """Structure of a topic search result."""

    title: str
    content: str
    source: str
    url: str
    confidence: float


class DestinationInfo(TypedDict):
    """Structure of destination information."""

    destination: str
    topics: Dict[str, List[TopicResult]]
    sources: List[str]


class MonitorOptions(TypedDict, total=False):
    """Options for price monitoring."""

    frequency: str
    notification_threshold: float
    start_date: Optional[str]
    end_date: Optional[str]


class PriceEntry(TypedDict):
    """Structure of a price history entry."""

    timestamp: str
    amount: float
    currency: str
    change_percent: Optional[float]


class PriceInfo(TypedDict, total=False):
    """Structure of price information."""

    amount: float
    currency: str
    timestamp: str


class PriceMonitorResult(TypedDict):
    """Structure of price monitoring result."""

    url: str
    initial_price: Optional[PriceInfo]
    current_price: Optional[PriceInfo]
    monitoring_id: str
    status: str
    history: Optional[List[PriceEntry]]
    next_check: Optional[str]


class DateRange(TypedDict):
    """Structure of a date range."""

    start_date: str
    end_date: str


class Event(TypedDict, total=False):
    """Structure of an event."""

    name: str
    description: str
    category: str
    date: str
    time: Optional[str]
    venue: Optional[str]
    address: Optional[str]
    url: Optional[str]
    price_range: Optional[str]
    image_url: Optional[str]
    source: str


class EventList(TypedDict):
    """Structure of event listings."""

    destination: str
    date_range: DateRange
    events: List[Event]
    sources: List[str]


class BlogTopic(TypedDict):
    """Structure of a blog topic."""

    title: str
    summary: str
    key_points: List[str]
    sentiment: str
    source_index: int


class BlogSource(TypedDict, total=False):
    """Structure of a blog source."""

    url: str
    title: str
    author: Optional[str]
    publish_date: Optional[str]
    reputation_score: Optional[float]


class BlogInsights(TypedDict):
    """Structure of blog insights."""

    destination: str
    topics: Dict[str, List[BlogTopic]]
    sources: List[BlogSource]
    extraction_date: str


class CrawlSource(ABC):
    """Abstract base class for crawling sources."""

    @abstractmethod
    async def extract_page_content(
        self, url: str, options: Optional[ExtractionOptions] = None
    ) -> ExtractedContent:
        """Extract content from a webpage.

        Args:
            url: The URL of the webpage to extract content from
            options: Optional extraction options

        Returns:
            The extracted content
        """
        pass

    @abstractmethod
    async def search_destination_info(
        self, destination: str, topics: Optional[List[str]] = None, max_results: int = 5
    ) -> DestinationInfo:
        """Search for information about a travel destination.

        Args:
            destination: The name of the destination (e.g., 'Paris, France')
            topics: Optional list of topics to search for
            max_results: Maximum number of results per topic

        Returns:
            Information about the destination
        """
        pass

    @abstractmethod
    async def monitor_price_changes(
        self, url: str, price_selector: str, options: Optional[MonitorOptions] = None
    ) -> PriceMonitorResult:
        """Set up monitoring for price changes on a webpage.

        Args:
            url: The URL of the webpage to monitor
            price_selector: CSS selector for the price element
            options: Optional monitoring options

        Returns:
            The price monitoring result
        """
        pass

    @abstractmethod
    async def get_latest_events(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        categories: Optional[List[str]] = None,
    ) -> EventList:
        """Get latest events for a destination.

        Args:
            destination: The name of the destination
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            categories: Optional list of event categories

        Returns:
            List of events
        """
        pass

    @abstractmethod
    async def crawl_travel_blog(
        self,
        destination: str,
        topics: Optional[List[str]] = None,
        max_blogs: int = 3,
        recent_only: bool = True,
    ) -> BlogInsights:
        """Extract insights from travel blogs.

        Args:
            destination: The name of the destination
            topics: Optional list of topics to extract
            max_blogs: Maximum number of blogs to crawl
            recent_only: Whether to only crawl recent blogs

        Returns:
            The extracted insights
        """
        pass
