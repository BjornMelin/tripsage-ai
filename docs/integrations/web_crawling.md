# Web Crawling MCP Server Implementation Specification

## Overview

The Web Crawling MCP Server provides TripSage with the ability to extract, process, and analyze travel-related information from websites. It enables the system to gather up-to-date details on destinations, attractions, accommodations, and events that may not be available through standard APIs. The server follows TripSage's dual storage architecture, storing extracted data in both Supabase and the knowledge graph.

## MCP Tools to Expose

### 1. `webcrawl.extract_page_content`

```python
def extract_page_content(url: str, content_selectors: Optional[dict] = None) -> dict:
    """Extract specific content from a single webpage using optional CSS selectors.

    Args:
        url: The full URL of the webpage to crawl
        content_selectors: Optional dictionary of CSS selectors for targeted extraction
            {
                "title": "h1.main-title",
                "description": "div.description p",
                "images": "div.gallery img"
            }

    Returns:
        Dict containing extracted content sections
    """
```

### 2. `webcrawl.search_destination_info`

```python
def search_destination_info(destination: str, info_type: str) -> dict:
    """Search for specific information about a travel destination.

    Args:
        destination: Name of the destination (city, country, attraction)
        info_type: Type of information to search for
                  (e.g., "attractions", "local_customs", "safety", "transportation")

    Returns:
        Dict containing extracted and structured information about the destination
    """
```

### 3. `webcrawl.monitor_price_changes`

```python
def monitor_price_changes(url: str, price_selector: str, check_frequency: str) -> dict:
    """Set up monitoring for price changes on a specific travel webpage.

    Args:
        url: The full URL of the webpage to monitor
        price_selector: CSS selector for the price element
        check_frequency: How often to check for changes ("hourly", "daily", "weekly")

    Returns:
        Dict containing monitoring configuration and initial price
    """
```

### 4. `webcrawl.get_latest_events`

```python
def get_latest_events(location: str, start_date: str, end_date: str) -> dict:
    """Find upcoming events at a destination during a specific time period.

    Args:
        location: Name of the destination
        start_date: Start date in ISO format
        end_date: End date in ISO format

    Returns:
        Dict containing event listings with details
    """
```

### 5. `webcrawl.crawl_travel_blog`

```python
def crawl_travel_blog(blog_url: str, max_posts: int = 10) -> dict:
    """Extract travel insights and recommendations from travel blogs.

    Args:
        blog_url: URL of the travel blog
        max_posts: Maximum number of posts to process (default: 10)

    Returns:
        Dict containing extracted travel insights organized by topic
    """
```

## API Integrations

The Web Crawling MCP Server will integrate with established web scraping and processing services:

### Primary API: Firecrawl API (Existing MCP)

- Endpoints:
  - Single page scraping: `firecrawl_scrape`
  - URL discovery: `firecrawl_map`
  - Multi-page crawling: `firecrawl_crawl`
  - Structured extraction: `firecrawl_extract`
  - Deep research: `firecrawl_deep_research`
- Documentation: Refer to existing Firecrawl MCP documentation

### Secondary API: Playwright (Existing MCP)

- Features:
  - Browser automation for dynamic content
  - Form submission and interaction
  - Screenshot capture
  - Content extraction
- Documentation: Refer to existing Playwright MCP documentation

### Tertiary API: Puppeteer API (Node.js based)

- Endpoints:
  - Page rendering: `/render`
  - Full page screenshot: `/screenshot`
  - PDF generation: `/pdf`
  - DOM extraction: `/extract`
- Authentication: API key
- Rate limits: 100 requests per minute (configurable)
- Documentation: <https://pptr.dev/api/>

## Connection Points to Existing Architecture

### Integration with Travel Agent

```python
from agents import Agent, function_tool
from pydantic import BaseModel

class DestinationInfoParams(BaseModel):
    destination: str
    info_type: str

@function_tool
async def get_destination_insights(params: DestinationInfoParams) -> str:
    """Get comprehensive insights about a destination.

    Args:
        params: Destination information parameters

    Returns:
        Formatted string with destination insights
    """
    try:
        # Call Web Crawling MCP Server
        destination_info = await webcrawl_client.search_destination_info(
            params.destination,
            params.info_type
        )

        # Store in Supabase
        await supabase.table("destination_insights").insert({
            "destination": params.destination,
            "info_type": params.info_type,
            "data": destination_info,
            "crawled_at": "NOW()"
        })

        # Update knowledge graph
        await memory_client.create_entities([{
            "name": f"{params.destination}-{params.info_type}",
            "entityType": "DestinationInsight",
            "observations": [str(destination_info)]
        }])

        # Format response for agent
        return format_destination_insights(destination_info)
    except Exception as e:
        logger.error(f"Destination insights error: {e}")
        return f"Unable to retrieve destination insights: {str(e)}"
```

### Integration with Itinerary Agent

```python
# Example tool for itinerary agent to discover local events
@function_tool
async def discover_local_events(location: str, start_date: str, end_date: str) -> list:
    """Discover local events happening during a trip.

    Args:
        location: Destination city
        start_date: Trip start date (ISO format)
        end_date: Trip end date (ISO format)

    Returns:
        List of events with details
    """
    # Get events from web crawling
    events = await webcrawl_client.get_latest_events(
        location, start_date, end_date
    )

    # Store in knowledge graph for future reference
    await memory_client.create_entities([{
        "name": f"Events-{location}-{start_date}-to-{end_date}",
        "entityType": "LocalEvents",
        "observations": [str(events)]
    }])

    # Format for itinerary integration
    formatted_events = []
    for event in events.get("events", []):
        formatted_events.append({
            "name": event["name"],
            "date": event["date"],
            "location": event["venue"],
            "category": event["category"],
            "description": event["description"],
            "price_range": event.get("price_range", "Not specified"),
            "ticket_url": event.get("ticket_url", "")
        })

    return formatted_events
```

### Integration with Budget Agent

```python
# Example tool for price monitoring
@function_tool
async def setup_price_monitoring(url: str, price_selector: str) -> dict:
    """Set up monitoring for price changes on travel bookings.

    Args:
        url: URL of booking page
        price_selector: CSS selector for price element

    Returns:
        Dictionary with monitoring status and initial price
    """
    # Set up monitoring
    monitoring = await webcrawl_client.monitor_price_changes(
        url, price_selector, "daily"
    )

    # Store monitoring configuration
    await supabase.table("price_monitors").insert({
        "url": url,
        "selector": price_selector,
        "initial_price": monitoring["initial_price"],
        "currency": monitoring["currency"],
        "last_checked": "NOW()"
    })

    return {
        "status": "Monitoring activated",
        "initial_price": monitoring["initial_price"],
        "currency": monitoring["currency"],
        "check_frequency": "daily"
    }
```

## File Structure

```plaintext
src/
  mcp/
    webcrawl/
      __init__.py
      client.py              # Web Crawling MCP client implementation
      config.py              # Configuration and API keys
      models.py              # Pydantic models for data validation
      extractors/
        __init__.py
        content.py           # Content extraction logic
        events.py            # Event extraction for destinations
        prices.py            # Price monitoring implementation
        blogs.py             # Blog content analysis
        destination.py       # Destination-specific extraction
      sources/
        __init__.py
        firecrawl.py         # Firecrawl API integration
        playwright.py        # Playwright integration
        puppeteer.py         # Puppeteer API integration
      processors/
        __init__.py
        text.py              # Text processing and analysis
        html.py              # HTML parsing and cleaning
        image.py             # Image processing utilities
        structured.py        # Structured data extraction
      storage/
        __init__.py
        supabase.py          # Supabase storage implementation
        memory.py            # Knowledge graph storage implementation
      utils/
        __init__.py
        formatters.py        # Response formatting utilities
        validators.py        # URL and data validation utilities
        rate_limiting.py     # Rate limiting implementation
```

## Key Functions and Interfaces

### Client Interface

```python
class WebCrawlClient:
    """Client for interacting with Web Crawling MCP Server."""

    async def extract_page_content(
        self,
        url: str,
        content_selectors: Optional[dict] = None
    ) -> dict:
        """Extract content from a webpage."""
        pass

    async def search_destination_info(
        self,
        destination: str,
        info_type: str
    ) -> dict:
        """Search for specific information about a destination."""
        pass

    async def monitor_price_changes(
        self,
        url: str,
        price_selector: str,
        check_frequency: str
    ) -> dict:
        """Set up price change monitoring."""
        pass

    async def get_latest_events(
        self,
        location: str,
        start_date: str,
        end_date: str
    ) -> dict:
        """Get latest events at a destination."""
        pass

    async def crawl_travel_blog(
        self,
        blog_url: str,
        max_posts: int = 10
    ) -> dict:
        """Extract insights from travel blogs."""
        pass
```

### Extractor Interface

```python
class Extractor(ABC):
    """Abstract base class for content extractors."""

    @abstractmethod
    async def extract(self, url: str, options: dict) -> dict:
        """Extract content from a webpage."""
        pass

    @abstractmethod
    async def validate(self, extracted_data: dict) -> bool:
        """Validate extracted content."""
        pass

    @abstractmethod
    async def clean(self, extracted_data: dict) -> dict:
        """Clean and normalize extracted content."""
        pass
```

### Source Interface

```python
class CrawlingSource(ABC):
    """Abstract base class for crawling sources."""

    @abstractmethod
    async def fetch_page(self, url: str) -> dict:
        """Fetch a page from the source."""
        pass

    @abstractmethod
    async def search(self, query: str, options: dict) -> dict:
        """Search for content using the source."""
        pass

    @abstractmethod
    async def monitor(self, url: str, selector: str, options: dict) -> dict:
        """Set up monitoring with the source."""
        pass
```

## Data Formats

### Input Formats

#### URL Format

```python
# Standard URL format
url = "https://example.com/destination/paris"
```

#### CSS Selector Format

```python
# Dictionary of named selectors
content_selectors = {
    "title": "h1.article-title",
    "description": "div.main-content p",
    "images": "div.gallery img",
    "prices": "span.price"
}
```

#### Date Range Format

```python
# ISO 8601 format for dates
start_date = "2025-06-15"
end_date = "2025-06-20"
```

### Output Formats

#### Page Content Response

```python
{
    "url": "https://example.com/destination/paris",
    "title": "Paris: The Ultimate Travel Guide",
    "metadata": {
        "author": "Travel Experts",
        "published_date": "2025-03-15",
        "last_updated": "2025-05-20"
    },
    "extracted_content": {
        "title": "Paris: The Ultimate Travel Guide",
        "description": "Discover the magic of Paris with our comprehensive guide to the City of Light...",
        "images": [
            {
                "src": "https://example.com/images/eiffel-tower.jpg",
                "alt": "Eiffel Tower at sunset",
                "width": 800,
                "height": 600
            },
            // Additional images...
        ],
        "sections": [
            {
                "heading": "Best Time to Visit",
                "content": "Spring (April to June) and Fall (September to November) are the best times to visit Paris..."
            },
            {
                "heading": "Top Attractions",
                "content": "1. Eiffel Tower\n2. Louvre Museum\n3. Notre-Dame Cathedral...",
                "subsections": [
                    // Additional structured content...
                ]
            }
            // Additional sections...
        ]
    },
    "crawl_timestamp": "2025-06-14T15:30:00Z",
    "source": "firecrawl"
}
```

#### Destination Info Response

```python
{
    "destination": "Paris, France",
    "info_type": "local_customs",
    "summary": "Understanding local customs in Paris will enhance your travel experience significantly.",
    "details": [
        {
            "title": "Greetings",
            "description": "Always greet shop owners with 'Bonjour' (Good day) when entering and 'Au revoir' (Goodbye) when leaving."
        },
        {
            "title": "Dining Etiquette",
            "description": "Dining is a leisurely affair in Paris. Expect longer meal times and don't rush through your meal."
        },
        {
            "title": "Tipping",
            "description": "Service is typically included in restaurant bills (look for 'service compris'), but rounding up or leaving a few euros for good service is appreciated."
        }
        // Additional custom details...
    ],
    "do_and_dont": {
        "do": [
            "Learn basic French phrases",
            "Dress nicely, especially when dining out",
            "Keep your voice down in public places"
        ],
        "dont": [
            "Don't speak loudly in public transportation",
            "Don't rush waiters in restaurants",
            "Don't expect stores to be open on Sundays"
        ]
    },
    "sources": [
        "https://example.com/paris-customs",
        "https://travel-blog.com/french-etiquette"
    ],
    "crawled_at": "2025-06-14T15:30:00Z"
}
```

#### Event Listings Response

```python
{
    "location": "Paris, France",
    "date_range": {
        "start": "2025-06-15",
        "end": "2025-06-20"
    },
    "events_count": 12,
    "events": [
        {
            "name": "Jazz Festival at Parc Floral",
            "date": "2025-06-16",
            "time": "19:00",
            "venue": "Parc Floral de Paris",
            "address": "Route de la Pyramide, 75012 Paris",
            "category": "Music",
            "description": "Annual jazz festival featuring international and local jazz musicians",
            "price_range": "€25-45",
            "ticket_url": "https://example.com/tickets/jazz-festival",
            "image_url": "https://example.com/events/jazz-festival.jpg"
        },
        // Additional events...
    ],
    "categories": {
        "Music": 4,
        "Art": 3,
        "Food": 2,
        "Cultural": 3
    },
    "crawl_sources": [
        "https://example.com/paris-events",
        "https://visitparis.com/whats-on"
    ],
    "generated_at": "2025-06-14T15:30:00Z"
}
```

#### Price Monitoring Response

```python
{
    "url": "https://example.com/hotels/paris-grand",
    "monitoring_id": "mon_12345abc",
    "selector": "span.room-price",
    "initial_price": {
        "amount": 195.50,
        "currency": "EUR",
        "extracted_text": "€195.50 per night"
    },
    "check_frequency": "daily",
    "next_check": "2025-06-15T15:30:00Z",
    "notification_method": "api_callback",
    "created_at": "2025-06-14T15:30:00Z"
}
```

## Implementation Notes

1. **Source Selection Strategy**:

   - Use Firecrawl for most standard extraction tasks
   - Fall back to Playwright for dynamic content requiring interaction
   - Use Puppeteer as a last resort for specialized rendering needs

2. **Rate Limiting and Politeness**:

   - Implement exponential backoff for retry attempts
   - Respect robots.txt directives
   - Add random delays between requests to the same domain
   - Maintain a domain-specific request quota

3. **Content Cleaning and Processing**:

   - Sanitize HTML to prevent XSS vulnerabilities
   - Standardize data formats (currencies, dates, times)
   - Apply NLP techniques to extract key information
   - Use structured data extraction where available

4. **Error Handling**:

   - Implement graceful degradation for failed extractions
   - Return partial results when complete extraction fails
   - Provide clear error messages with troubleshooting steps
   - Log detailed error information for debugging

5. **Storage Strategy**:

   - Store raw HTML temporarily (24 hours)
   - Store processed content in structured Supabase tables
   - Create knowledge graph entities for semantic relationships
   - Implement TTL (time-to-live) based on content freshness needs

6. **Security**:

   - Sanitize all external inputs
   - Implement URL validation and filtering
   - Use secure connection methods (HTTPS)
   - Scan content for potential malicious patterns

7. **Knowledge Graph Integration**:
   - Create destination entities with rich attribute sets
   - Build relationships between destinations and activities
   - Connect events to destinations with temporal attributes
   - Capture sentiment and ratings from extracted content
     EOL < /dev/null
