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

An **Intelligent Source Selector** dynamically chooses the best crawling backend based on domain, content type, and historical success rates:

- **Crawl4AI (Primary)** for most informational/static sites.
- **Playwright (Fallback)** for JavaScript-heavy or interactive pages.
- If all fail, a WebSearchTool fallback approach is possible.

### 2.3. Tool Comparison Summary

| Feature             | Crawl4AI (Self-Hosted) | Firecrawl (Cloud API)     | Playwright (Self-Hosted)   |
| ------------------- | ---------------------- | ------------------------- | -------------------------- |
| **Primary Use**     | Informational, Bulk    | AI-Optimized, dynamic     | Dynamic, Interactive       |
| **Performance**     | High throughput        | Good, depends on API      | Slower (browser rendering) |
| **TripSage Choice** | **Primary Engine**     | Not chosen for main usage | **Fallback/Interactive**   |

### 2.4. Result Normalization

A `ResultNormalizer` ensures consistent output (title, content, metadata) regardless of source.

## 3. Exposed MCP Tools

### 3.1. `mcp__webcrawl__extract_page_content`

Extracts content from a single webpage.

### 3.2. `mcp__webcrawl__search_destination_info`

Searches a destination for specified topics (e.g., attractions, cuisine).

### 3.3. `mcp__webcrawl__monitor_price_changes`

Watches a webpage for price changes over time.

### 3.4. `mcp__webcrawl__get_latest_events`

Finds upcoming events at a destination.

### 3.5. `mcp__webcrawl__crawl_travel_blog`

Extracts insights from travel blogs.

Each tool has input schemas for parameters (e.g., URL, selectors, or topic lists) and returns standardized data.

## 4. Key Service Components

- **`Crawl4AISource`**: Manages interaction with a self-hosted Crawl4AI engine.
- **`PlaywrightSource`**: Manages browser-based extraction for dynamic sites.
- **`CacheService`**: Uses Redis for caching results (e.g., HTML content, extracted data).
- **`ResultNormalizer`**: Outputs data in a consistent schema.

## 5. Integration with TripSage Ecosystem

Agents call these tools via a Python `WebCrawlMCPClient`. Extracted or summarized data can be stored in Supabase or the Memory MCP (Neo4j).

## 6. Ethical Crawling and Performance

- Respect `robots.txt`, domain-based rate limiting, user-agent disclosure.
- Timeout, retry, and concurrency controls.

## 7. Deployment

- Python FastMCP 2.0 app, Dockerized.
- Requires Redis, network access to the crawling engines (Crawl4AI, possibly Firecrawl or Playwright).
- Centralized config for environment variables.

## 8. Future Enhancements

- ML-based categorization, advanced sentiment, content deduplication, cross-source consistency checks.

This WebCrawl MCP architecture provides a powerful, adaptable approach to gathering diverse travel information from the web.
