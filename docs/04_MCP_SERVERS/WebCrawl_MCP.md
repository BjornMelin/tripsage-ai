# WebCrawl MCP Server Guide

This document provides the comprehensive implementation guide, architecture, and strategy for the WebCrawl MCP Server within the TripSage AI Travel Planning System.

## 1. Overview

The WebCrawl MCP Server is a critical component for TripSage, enabling the system to extract, process, and analyze travel-related information from a wide array of websites. It allows TripSage to gather up-to-date details on destinations, attractions, accommodations, events, and local insights that may not be available through structured APIs. This capability is essential for providing rich, current, and comprehensive travel plans.

The server is designed with a hybrid approach, leveraging multiple crawling and scraping technologies, each optimized for different types of web content and extraction scenarios.

## 2. Architecture and Strategy

### 2.1. Hybrid Web Crawling Architecture

TripSage's WebCrawl MCP follows a **Crawl4AI-focused approach with Playwright as a fallback**, chosen for its optimal balance of performance, reliability, and cost-effectiveness.

```plaintext
┌─────────────────────────────────────────────────────────────┐
│                   TripSage Agent System                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    WebCrawl MCP Server                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐        ┌─────────────────────────┐     │
│  │  MCP Handler    │        │  Source Selection Logic │     │
│  │ (Tool Dispatch) │        │  (Intelligent Router)   │     │
│  └────────┬────────┘        └─────────┬───────────────┘     │
│           │                           │                     │
│           ▼                           ▼                     │
│  ┌─────────────────┐        ┌─────────────────────────┐     │
│  │  Cache Layer    │◄──────►│  Source Interface       │     │
│  │  (Redis)        │        │  (Abstraction)          │     │
│  └─────────────────┘        └────┬──────────────┬─────┘     │
│                                  │              │           │
│                                  ▼              ▼           │
│                          ┌─────────────┐  ┌────────────┐    │
│                          │  Crawl4AI   │  │ Playwright │    │
│                          │  (Primary)  │  │ (Fallback/ │    │
│                          │             │  │ Interactive)│    │
│                          └─────────────┘  └────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Result Normalization Service                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Dual Storage                           │
│   (Supabase for structured, Memory MCP for knowledge graph) │
└─────────────────────────────────────────────────────────────┘
```

### 2.2. Source Selection Strategy

An **Intelligent Source Selector** (`source_selector.py`) dynamically chooses the best crawling backend (Crawl4AI or Playwright) based on:

- **URL Characteristics & Domain Information**:
  - **Crawl4AI (Primary)**: Preferred for static content, informational sites, blogs, destination guides (e.g., Wikipedia, Wikitravel, Lonely Planet, government travel sites, many travel blogs). Optimized for high throughput and batch processing.
  - **Playwright (Fallback/Specialized)**: Used for JavaScript-heavy dynamic websites, sites requiring authentication or complex interactions (e.g., some booking portals like Airbnb, Booking.com for specific data points if APIs are insufficient, dynamic event sites).
- **Historical Success Rates**: The system can (or is planned to) track success rates for domains with each crawler to refine selection over time.
- **Operation Type**: Certain tools might default to a specific source (e.g., simple content extraction to Crawl4AI, interactive form submission to Playwright).

**Fallback Mechanism**:

1. Attempt with the primary selected source (usually Crawl4AI).
2. If the primary source fails or returns inadequate data, escalate to the fallback source (Playwright).
3. If all programmatic attempts fail, the system can generate **Structured WebSearchTool Fallback Guidance** for the AI agent to perform a more guided manual-like search using the general WebSearchTool.

### 2.3. Tool Comparison Summary (Crawl4AI vs. Firecrawl vs. Playwright)

| Feature             | Crawl4AI (Self-Hosted)         | Firecrawl (Cloud API + MCP) | Playwright (Self-Hosted via MCP) |
| ------------------- | ------------------------------ | --------------------------- | -------------------------------- |
| **Primary Use**     | Informational, Bulk            | AI-Optimized, Booking Sites | Dynamic, Interactive             |
| **Performance**     | High throughput (async, batch) | Good, API latency dependent | Slower (browser rendering)       |
| **JS Support**      | Configurable                   | Excellent                   | Comprehensive                    |
| **Cost**            | Infrastructure only            | Free tier + Paid plans      | Infrastructure only              |
| **TripSage Choice** | **Primary Engine**             | Considered, less control    | **Fallback/Interactive Engine**  |

**Decision**: Crawl4AI was chosen as the primary engine due to its benchmarked performance (potential 4x-10x speed improvements for suitable tasks), open-source nature (cost-effective for self-hosting), and high extraction accuracy. Playwright is retained for its strength in handling dynamic content and interactions. Firecrawl, while powerful, adds a cloud dependency and cost factor less ideal for a self-hostable primary solution.

### 2.4. Result Normalization

A `ResultNormalizer` service (`result_normalizer.py`) ensures consistent output structure, field naming, and confidence scoring regardless of the data source. Key features:

- Standardized data schemas for destinations, events, blogs, etc.
- Source-specific confidence scoring (e.g., Crawl4AI: 0.85, Playwright: 0.75).
- Content enrichment: automatic summarization, category detection, basic sentiment analysis.
- Comprehensive metadata tracking (source, timestamps, processing history).

(See `docs/04_MCP_SERVERS/WebCrawl_MCP.md` section on Result Normalization for more details).

## 3. Exposed MCP Tools

The WebCrawl MCP Server exposes the following tools, implemented in Python using FastMCP 2.0:

### 3.1. `mcp__webcrawl__extract_page_content`

- **Description**: Extracts content from a single webpage.
- **Parameters**:
  - `url` (string, required): URL of the webpage.
  - `selectors` (Optional[List[str]]): CSS selectors for targeted extraction.
  - `include_images` (bool, default: `False`): Whether to include image URLs.
  - `format` (str, enum: `["markdown", "text", "html"]`, default: `"markdown"`): Output format.
- **Output**: `ExtractedContent` model (title, content, images, metadata).
- **Internal Logic**: Uses `SourceSelector` to pick Crawl4AI or Playwright.

### 3.2. `mcp__webcrawl__search_destination_info`

- **Description**: Researches a travel destination for specified topics.
- **Parameters**:
  - `destination` (string, required): Destination name.
  - `topics` (Optional[List[str]]): Topics like "attractions", "local cuisine".
  - `max_results` (int, default: 5): Max results per topic.
- **Output**: `DestinationInfo` model (destination name, results grouped by topic, sources).
- **Internal Logic**: Primarily uses Crawl4AI for batch searching across topics. May fall back to Playwright for specific hard-to-crawl sources.

### 3.3. `mcp__webcrawl__monitor_price_changes`

- **Description**: Sets up monitoring for price changes on a webpage.
- **Parameters**:
  - `url` (string, required): URL of the page with the price.
  - `price_selector` (string, required): CSS selector for the price element.
  - `frequency` (str, enum: `["hourly", "daily", "weekly"]`, default: `"daily"`).
  - `notification_threshold` (float, default: 5.0): Percentage change to trigger notification.
- **Output**: `PriceMonitorResult` (monitoring ID, initial price, status).
- **Internal Logic**: Uses `SourceSelector`. Stores monitoring jobs and price history in Supabase.

### 3.4. `mcp__webcrawl__get_latest_events`

- **Description**: Finds upcoming events at a destination for a given period.
- **Parameters**:
  - `destination` (string, required): Destination name.
  - `start_date` (string, required, YYYY-MM-DD).
  - `end_date` (string, required, YYYY-MM-DD).
  - `categories` (Optional[List[str]]): Event categories (e.g., "music", "sports").
- **Output**: `EventList` model (list of events with details).
- **Internal Logic**: Uses `SourceSelector`. Crawl4AI for event listing sites, Playwright for dynamic event portals.

### 3.5. `mcp__webcrawl__crawl_travel_blog`

- **Description**: Extracts insights and recommendations from travel blogs about a destination.
- **Parameters**:
  - `destination` (string, required): Destination name.
  - `topics` (Optional[List[str]]): Specific topics to focus on (e.g., "hidden gems").
  - `max_blogs` (int, default: 3): Maximum number of blogs to process.
  - `recent_only` (bool, default: `True`): Only blogs from the past year.
- **Output**: `BlogInsights` model (summaries, key points, sentiment per topic, sources).
- **Internal Logic**: Primarily uses Crawl4AI. Involves searching for relevant blog posts then extracting content.

(Refer to `docs/integrations/data-gathering/web_crawling.md` or the specific tool schemas for detailed Pydantic input/output models for these tools.)

## 4. Key Service Components

### 4.1. `Crawl4AISource` (`crawl4ai_source.py`)

- Manages interaction with the self-hosted Crawl4AI engine.
- Implements the `CrawlSource` interface.
- Handles batch requests, parameter mapping, and response parsing for Crawl4AI.
- **Client Features**:
  - Supports multiple output formats (markdown, HTML, screenshot, PDF via Crawl4AI).
  - JavaScript execution on crawled pages.
  - Question answering over crawled content.
  - Stateful session support for multi-page crawls.
- **Configuration**: Endpoint URL, API key (if secured), timeout, max pages, cache TTLs.

  ```python
  # Example Crawl4AI Client Configuration (from settings)
  # TRIPSAGE_MCP_CRAWL4AI_URL=ws://localhost:11235/mcp/ws # Or http for SSE
  # TRIPSAGE_MCP_CRAWL4AI_ENABLED=true
  # TRIPSAGE_MCP_CRAWL4AI_TIMEOUT=60
  ```

### 4.2. `PlaywrightSource` (`playwright_source.py`)

- Manages interaction with the Playwright infrastructure (likely via a Playwright MCP or direct Playwright scripting if embedded).
- Implements the `CrawlSource` interface.
- Handles browser launch, navigation, interaction, and content extraction.

### 4.3. `CacheService` (`cache.py`)

- Uses Redis (via `RedisCache` utility) for caching responses from Crawl4AI and Playwright.
- Implements content-aware TTLs:
  - Booking sites (dynamic): 1 hour.
  - Static informational content: 24 hours.
  - Screenshots: 12 hours.
  - Question/Answer results: 12 hours.
  - JS execution results (highly dynamic): 5 minutes.
- Provides methods like `get(key)`, `set(key, value, ttl)`, `invalidate(key)`.

### 4.4. `ResultNormalizer` (`result_normalizer.py`)

- Takes raw output from any source (Crawl4AI, Playwright, WebSearchTool fallback).
- Transforms it into a standardized TripSage schema for the specific data type (destination info, event list, etc.).
- Assigns confidence scores.
- Performs content enrichment (summarization, categorization, sentiment).

## 5. Integration with TripSage Ecosystem

- **Agent System**: The WebCrawl MCP tools are exposed to AI agents (Travel Agent, Destination Research Agent, Budget Agent, Itinerary Agent) via the `WebCrawlMCPClient`.
- **Dual Storage**:
  - **Supabase**: Stores structured, extracted data (e.g., key facts about a destination, event details, monitored prices).
  - **Memory MCP (Neo4j)**: Stores relationships (e.g., "Eiffel Tower" `LOCATED_IN` "Paris") and semantic insights derived from crawled content.
- **Hybrid Search Strategy**: The WebCrawl MCP is a key component of the broader search strategy, providing deep, structured information that complements the general WebSearchTool.

## 6. Ethical Crawling and Performance

- **Rate Limiting**: Adaptive, per-domain rate limiting and politeness delays.
- **Robots.txt**: Respect for `robots.txt` directives.
- **User-Agent**: Clear identification of the TripSage crawler.
- **Error Handling**: Circuit breakers for problematic sites, robust retry mechanisms.
- **Concurrency**: Controlled parallel processing for Crawl4AI and Playwright tasks.

## 7. Deployment

- The WebCrawl MCP Server is a Python FastMCP 2.0 application.
- It's containerized using Docker for deployment.
- Requires access to a Redis instance for caching.
- Requires network access to the self-hosted Crawl4AI engine and the internet for Playwright.
- Configuration is managed via centralized settings (environment variables).

## 8. Future Enhancements (from `webcrawl_mcp_improvements.md`)

- **Machine Learning Categorization**: Replace rule-based content categorization with ML models.
- **Advanced Sentiment Analysis**: Use more sophisticated NLP for sentiment.
- **Content Deduplication & Verification**: Identify duplicate content and cross-reference information.
- **Dynamic Confidence Scoring**: Adjust confidence based on cross-source consistency.
- **Knowledge Graph Expansion**: More granular entity and relation extraction for the Memory MCP.
- **Cache Enhancements**: Partial cache updates, cache warming, predictive caching.

This WebCrawl MCP architecture provides TripSage with a powerful, adaptable, and cost-effective solution for gathering diverse travel information from the web.
