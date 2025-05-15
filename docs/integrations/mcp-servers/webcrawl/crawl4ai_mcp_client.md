# Crawl4AI MCP Client Documentation

## Overview

The Crawl4AI MCP Client is a Python client that integrates with the [Crawl4AI](https://github.com/unclecode/crawl4ai) Model Context Protocol (MCP) server. This client provides web crawling, content extraction, and question-answering capabilities through both WebSocket and Server-Sent Events (SSE) connections.

## Features

- **Multiple Output Formats**: Extract content as markdown, HTML, screenshots, or PDFs
- **JavaScript Execution**: Execute custom JavaScript on crawled pages
- **Question Answering**: Ask questions about content from multiple URLs
- **Batch Operations**: Crawl multiple URLs efficiently
- **Caching**: Automatic content caching with TTL support
- **Stateful Sessions**: Support for session-based crawling

## Installation

The Crawl4AI MCP client is included as part of the TripSage project. No additional installation is required if you have TripSage set up.

## Configuration

Configure the client through environment variables or the `mcp_settings.py` file:

```python
# Environment variables (prefix: TRIPSAGE_MCP_CRAWL4AI_)
TRIPSAGE_MCP_CRAWL4AI_URL=ws://localhost:11235/mcp/ws
TRIPSAGE_MCP_CRAWL4AI_ENABLED=true
TRIPSAGE_MCP_CRAWL4AI_TIMEOUT=30
TRIPSAGE_MCP_CRAWL4AI_MAX_PAGES=10
```

Default configuration:
- **URL**: `ws://localhost:11235/mcp/ws` (WebSocket) or `http://localhost:11235/mcp/sse` (SSE)
- **Timeout**: 30 seconds
- **Max Pages**: 10 pages for multi-page crawls
- **Cache TTL**: Varies by content type (1-24 hours)

## Usage

### Basic Initialization

```python
from tripsage.clients.webcrawl.crawl4ai_mcp_client import get_crawl4ai_client

# Get singleton client instance
client = get_crawl4ai_client()
```

### Extract Markdown Content

```python
# Simple markdown extraction
result = await client.extract_markdown("https://example.com")
print(result['content'])

# With session ID for stateful crawling
result = await client.extract_markdown(
    "https://example.com",
    session_id="my-session"
)
```

### Multi-Format Crawling

```python
from tripsage.clients.webcrawl.crawl4ai_mcp_client import Crawl4AICrawlParams

params = Crawl4AICrawlParams(
    url="https://example.com",
    markdown=True,
    html=True,
    screenshot=True,
    pdf=True
)

result = await client.crawl_url("https://example.com", params)

# Access different formats
markdown_content = result.get('markdown')
html_content = result.get('html')
screenshot_base64 = result.get('screenshot')
pdf_base64 = result.get('pdf')
```

### Execute JavaScript

```python
# Execute custom JavaScript on a page
js_code = """
return {
    title: document.title,
    links: Array.from(document.links).map(a => a.href),
    timestamp: new Date().toISOString()
};
"""

result = await client.execute_js("https://example.com", js_code)
print(result)  # Contains JS execution results
```

### Question Answering

```python
# Ask questions about content from multiple URLs
urls = [
    "https://docs.example.com/feature1",
    "https://docs.example.com/feature2"
]

question = "What are the main features described in these documents?"

result = await client.ask(urls, question)
print(result['answer'])
```

### Batch Crawling

```python
# Crawl multiple URLs in batch
urls = [
    "https://example.com/page1",
    "https://example.com/page2",
    "https://example.com/page3"
]

results = await client.batch_crawl(urls, markdown=True, html=False)

for result in results:
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Content: {result['markdown'][:100]}...")
```

### Advanced Crawling Parameters

```python
params = Crawl4AICrawlParams(
    url="https://example.com",
    session_id="my-session",
    wait_for="div.content",  # CSS selector to wait for
    css="body { font-size: 16px; }",  # Custom CSS
    extraction_strategy="LLM",  # Use LLM for extraction
    seed_urls=["https://example.com/sitemap"],
    max_pages=5,
    allowed_domains=["example.com"],
    exclude_patterns=["*/admin/*", "*/private/*"]
)

result = await client.crawl_url("https://example.com", params)
```

## Caching Strategy

The client implements intelligent caching based on content type:

- **Booking Sites** (Airbnb, Hotels.com): 1 hour TTL
- **Static Content**: 24 hours TTL
- **Screenshots**: 12 hours TTL
- **Question Answers**: 12 hours TTL
- **JavaScript Results**: 5 minutes TTL (dynamic content)

To disable caching for a specific request:

```python
result = await client.crawl_url(url, use_cache=False)
```

## Error Handling

All methods include automatic error handling with the `@with_error_handling` decorator:

```python
try:
    result = await client.crawl_url("https://example.com")
except Exception as e:
    logger.error(f"Crawling failed: {e}")
    # Handle error appropriately
```

## Available Tools

The Crawl4AI MCP server provides the following tools:

1. **md**: Extract markdown content
2. **html**: Extract HTML content
3. **screenshot**: Take page screenshots
4. **pdf**: Generate PDF from pages
5. **execute_js**: Execute JavaScript code
6. **crawl**: Comprehensive crawling with multiple options
7. **ask**: Question answering about crawled content

## Connection Types

The client supports both WebSocket and SSE connections:

```python
# WebSocket (default)
TRIPSAGE_MCP_CRAWL4AI_URL=ws://localhost:11235/mcp/ws

# Server-Sent Events
TRIPSAGE_MCP_CRAWL4AI_URL=http://localhost:11235/mcp/sse
```

## Best Practices

1. **Use Sessions**: For multi-page crawls, use session IDs to maintain state
2. **Cache Wisely**: Enable caching for static content, disable for dynamic content
3. **Batch Operations**: Use `batch_crawl` for multiple URLs to improve efficiency
4. **Error Recovery**: Implement proper error handling for network issues
5. **Resource Management**: Use context managers or ensure proper cleanup

```python
# Using context manager
async with get_crawl4ai_client() as client:
    result = await client.crawl_url("https://example.com")
```

## Integration with TripSage

The Crawl4AI client integrates seamlessly with TripSage's web operations:

```python
from tripsage.utils.cache import ContentType

# Content-aware caching
result = await client.crawl_url(
    url,
    cache_key=f"travel:destination:{destination_id}",
    content_type=ContentType.SEMI_STATIC,
    ttl_minutes=480  # 8 hours for destination info
)
```

## Troubleshooting

Common issues and solutions:

1. **Connection Refused**: Ensure Crawl4AI server is running on the specified port
2. **Timeout Errors**: Increase timeout in configuration or params
3. **Cache Misses**: Check Redis connection and cache key generation
4. **JavaScript Errors**: Validate JavaScript code syntax before execution

## Example Configuration

```env
# .env file
TRIPSAGE_MCP_CRAWL4AI_URL=ws://localhost:11235/mcp/ws
TRIPSAGE_MCP_CRAWL4AI_ENABLED=true
TRIPSAGE_MCP_CRAWL4AI_TIMEOUT=60
TRIPSAGE_MCP_CRAWL4AI_MAX_PAGES=20
TRIPSAGE_MCP_CRAWL4AI_EXTRACT_IMAGES=false
TRIPSAGE_MCP_CRAWL4AI_RAG_ENABLED=true
```

## Running the Crawl4AI Server

To use the client, you need to run the Crawl4AI server with MCP support:

```bash
# Using Docker
docker run -p 11235:11235 unclecode/crawl4ai:mcp

# Or install and run locally
pip install crawl4ai[mcp]
crawl4ai-mcp-server --port 11235
```

Refer to the [Crawl4AI documentation](https://github.com/unclecode/crawl4ai) for detailed server setup instructions.