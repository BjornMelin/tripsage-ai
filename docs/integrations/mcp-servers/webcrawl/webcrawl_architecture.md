# WebCrawl MCP Architecture

## Overview

The TripSage WebCrawl MCP implementation follows a Crawl4AI-focused approach with Playwright as a fallback for dynamic content. This architecture was selected based on our evaluation (see `web_crawling_evaluation.md`) for its optimal performance, reliability, and cost-effectiveness.

## Architecture Diagram

```plaintext
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                   TripSage Agent System                     │
│                                                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    WebCrawl MCP Server                      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐        ┌─────────────────────────┐     │
│  │                 │        │                         │     │
│  │  MCP Handler    │        │  Source Selection       │     │
│  │                 │        │                         │     │
│  └────────┬────────┘        └─────────┬───────────────┘     │
│           │                           │                     │
│           ▼                           ▼                     │
│  ┌─────────────────┐        ┌─────────────────────────┐     │
│  │                 │        │                         │     │
│  │  Cache Layer    │◄──────►│  Source Interface       │     │
│  │                 │        │                         │     │
│  └─────────────────┘        └────┬──────────────┬─────┘     │
│                                  │              │           │
│                                  ▼              ▼           │
│                          ┌─────────────┐  ┌────────────┐    │
│                          │             │  │            │    │
│                          │  Crawl4AI   │  │ Playwright │    │
│                          │  (Primary)  │  │ (Fallback) │    │
│                          │             │  │            │    │
│                          └─────────────┘  └────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                      Dual Storage                           │
│                                                             │
├────────────────────────────┬────────────────────────────────┤
│                            │                                │
│   Supabase (Structured)    │   Memory MCP (Knowledge Graph) │
│                            │                                │
└────────────────────────────┴────────────────────────────────┘
```

## Source Selection Strategy

The system dynamically selects the appropriate crawling source based on content characteristics:

### 1. Crawl4AI (Primary Source)

Used as the default for most URLs and operations:

- Static content websites
- Blog sites
- Informational pages
- Destination research queries
- Historical data extraction

Key advantages:

- 10× higher throughput compared to sequential crawling
- Batch processing capabilities
- Lower cost per request (the most cost-effective option)
- Superior content extraction for most travel content
- Self-hosted with full control over configuration

### 2. Playwright (Fallback Source)

Used selectively for specific scenarios and as a fallback:

- Dynamic JavaScript-heavy websites (Booking.com, Airbnb, etc.)
- Sites requiring authentication
- Interactive elements like forms
- Travel booking sites with dynamic pricing
- Dynamic event sites for major cities
- When Crawl4AI extraction fails

Key advantages:

- Browser automation capabilities
- Handles JavaScript rendering
- Can interact with website elements
- Provides screenshots if needed

## Fallback Mechanism

When a source fails to extract or process content, the system implements the following fallback logic:

1. If Crawl4AI fails → Try Playwright
2. If Playwright fails → Return appropriate error with suggestions

This ensures maximum content availability while efficiently using resources by prioritizing the higher-throughput Crawl4AI solution for most operations.

## MCP Tools Exposed

The WebCrawl MCP server exposes five main tools:

1. **extract_page_content**: Get content from specific webpages
2. **search_destination_info**: Research travel destinations
3. **monitor_price_changes**: Track prices on travel websites
4. **get_latest_events**: Find events at destinations
5. **crawl_travel_blog**: Extract insights from travel blogs

Each tool utilizes the appropriate source based on the content type and the source selection strategy.

## Ethical and Performance Considerations

- **Rate Limiting**: Adaptive, per-domain rate limiting
- **Caching**: Content-aware TTL ranging from 1 hour to 1 week
- **Respect for Website Policies**: robots.txt parsing and adherence
- **Error Handling**: Detailed logging and circuit breaker pattern
- **Performance Optimization**: Parallel processing with controlled concurrency

## Benefits of This Architecture

- **Optimal Resource Utilization**: Uses the most efficient tool for each task
- **Cost Efficiency**: Minimizes unnecessary browser automation costs
- **Reliability**: Provides fallback mechanisms for resilience
- **Scalability**: Each component can scale independently
- **Maintainability**: Clean interfaces simplify future updates
