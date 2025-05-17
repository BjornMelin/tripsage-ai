# Firecrawl MCP Client Design and Implementation

## Overview

The `FirecrawlMCPClient` has been implemented to integrate with the Firecrawl MCP server (<https://github.com/mendableai/firecrawl-mcp-server>) for advanced web scraping and crawling capabilities in TripSage.

## Design Choices

### 1. Client Architecture

- **Singleton Pattern**: Implemented to ensure only one client instance exists, reducing resource overhead and ensuring consistent configuration.
- **Async Architecture**: All methods are asynchronous using `httpx.AsyncClient` for non-blocking I/O operations.
- **Error Handling**: Uses the `@with_error_handling` decorator for consistent error handling across all methods.

### 2. Caching Strategy

The client implements intelligent caching based on content type and domain:

- **Dynamic Content (Booking Sites)**:
  - Sites like `airbnb.com`, `booking.com`, `hotels.com` get a shorter TTL of 1 hour
  - This accounts for frequently changing prices and availability
  
- **Static Content**:
  - General web content gets a 24-hour TTL
  - Search results get a 12-hour TTL
  - Structured extraction data gets a 24-hour TTL

### 3. API Method Mapping

The client provides high-level methods that map to Firecrawl MCP tools:

- `scrape_url()` → `firecrawl_scrape` tool
- `crawl_url()` → `firecrawl_crawl` tool
- `extract_structured_data()` → `firecrawl_extract` tool
- `search_web()` → `firecrawl_search` tool
- `batch_scrape()` → `firecrawl_batch_scrape` tool
- `check_crawl_status()` → `firecrawl_check_crawl_status` tool

### 4. Configuration Integration

The client integrates with TripSage's MCP configuration system:

- Uses `FirecrawlMCPConfig` from `mcp_settings.py`
- Supports environment variable configuration
- Allows for both cloud and self-hosted Firecrawl instances

### 5. Parameter Models

Created Pydantic models for request parameters:

- `FirecrawlScrapeParams`: For single URL scraping
- `FirecrawlCrawlParams`: For website crawling
- `FirecrawlExtractParams`: For structured data extraction

These models:

- Provide type safety and validation
- Handle camelCase to snake_case conversion for MCP compatibility
- Support optional parameters with sensible defaults

## Implementation Details

### Request Flow

1. Client receives a request (e.g., `scrape_url()`)
2. Checks cache for existing result (if caching enabled)
3. If cache miss, builds MCP request using `_build_mcp_request()`
4. Sends request to MCP server using `httpx`
5. Processes response and extracts data
6. Caches result with appropriate TTL
7. Returns data to caller

### Error Handling

- HTTP errors are caught and logged
- The `@with_error_handling` decorator provides consistent error responses
- Failed requests are not cached

### Cache Key Strategy

Cache keys are constructed based on:

- Tool name (e.g., "firecrawl:scrape")
- Primary identifier (URL, query, etc.)
- Relevant parameters that affect the result

Example: `firecrawl:scrape:https://example.com`

## Usage Examples

```python
# Get the singleton client
client = get_firecrawl_client()

# Scrape a single URL
result = await client.scrape_url(
    "https://www.airbnb.com/rooms/123",
    params=FirecrawlScrapeParams(
        formats=["markdown", "html"],
        only_main_content=True
    )
)

# Extract structured data from multiple URLs
extracted_data = await client.extract_structured_data(
    urls=["https://hotel1.com", "https://hotel2.com"],
    prompt="Extract hotel name, price, and amenities",
    params=FirecrawlExtractParams(
        schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number"},
                "amenities": {"type": "array", "items": {"type": "string"}}
            }
        }
    )
)

# Search the web with content scraping
search_results = await client.search_web(
    query="best hotels in Paris",
    limit=10,
    scrape_results=True
)
```

## Future Enhancements

1. **Batch Processing Optimization**: Implement better handling for large batch operations
2. **Rate Limiting**: Add client-side rate limiting to complement MCP server limits
3. **Webhook Support**: Add support for crawl webhooks for long-running operations
4. **Metrics Collection**: Integrate with TripSage's metrics system for monitoring
5. **Content Type Detection**: Auto-adjust caching strategy based on detected content type

## Integration with TripSage

The `FirecrawlMCPClient` will be used by:

1. `SourceSelectionLogic` in `source_selector.py` for determining when to use Firecrawl
2. Unified webcrawl tools in `webcrawl_tools.py` for agent access
3. Accommodation and flight search agents for scraping booking sites
4. Destination research agents for extracting structured travel information
