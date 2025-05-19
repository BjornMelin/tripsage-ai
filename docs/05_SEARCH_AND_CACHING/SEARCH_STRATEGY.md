# TripSage Hybrid Search Strategy

This document defines TripSage's comprehensive hybrid search strategy, which integrates OpenAI's WebSearchTool, specialized web crawling (via WebCrawl MCP), and browser automation (via BrowserAutomation MCP) to create a robust and versatile web information retrieval ecosystem for travel planning.

## 1. Architecture Overview

TripSage implements a hierarchical and federated search strategy. The AI Travel Agent intelligently selects or combines tools based on the query's nature, required information depth, and interaction complexity.

```plaintext
┌──────────────────────────────────────────────────────────────────────┐
│                       TripSage Travel Agent                          │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ (Tool Selection & Orchestration)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Hybrid Search Strategy Layer                      │
├─────────────┬─────────────────────────┬──────────────────────────────┤
│             │                         │                              │
│  ┌──────────▼─────────┐    ┌──────────▼─────────┐    ┌───────────────▼──────┐
│  │   WebSearchTool    │    │  WebCrawl MCP      │    │  BrowserAutomation   │
│  │   (General Web     │    │  (Deep Content &   │    │  MCP (Interactive &  │
│  │    Queries)        │    │   Structured Data) │    │   Authenticated)     │
│  └────────────────────┘    └────────────────────┘    └──────────────────────┘
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                                │ (Aggregated & Normalized Results)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Dual Storage Architecture                       │
│   (Supabase for structured cache, Memory MCP for knowledge graph)    │
└──────────────────────────────────────────────────────────────────────┘
```

## 2. Tool Selection Strategy and Use Cases

### 2.1. WebSearchTool (Primary for General & Real-time Queries)

- **When to Use**:
  - General travel information (e.g., "best time to visit Barcelona").
  - Current events, news, or recent updates related to destinations.
  - Initial research phase for broad topics.
  - Quick fact-checking or finding specific, publicly indexed information.
  - When information is likely to be very recent and not yet captured by specialized crawlers.
- **Configuration**:
  - **Travel-Optimized Domain Allowlists** and Domain Blocklists.
  - **Integration**: Accessed via a `TravelWebSearchTool` adapter within the agent, applying domain configurations and caching.

### 2.2. WebCrawl MCP (For Specialized, Deep, or Structured Travel Content)

- **When to Use**:
  - Detailed destination research requiring extraction of structured data.
  - Analysis of travel blogs for local insights.
  - Monitoring specific webpages for changes.
  - Handling known, high-quality travel websites for specific info.
- **Implementation**: Uses **Crawl4AI** primarily, with Playwright as fallback for dynamic content.
- **Key Tools**: `extract_page_content`, `search_destination_info`, `monitor_price_changes`, `get_latest_events`, `crawl_travel_blog`.

### 2.3. BrowserAutomation MCP (For Interactive & Authenticated Tasks)

- **When to Use**:
  - Flight check-in, booking verification, or real-time flight status requiring form-based sites.
  - High dynamic pages or sites with stronger anti-bot measures.
- **Implementation**: Playwright MCP or Stagehand MCP for resilient DOM changes.
- **Key Tools**: `playwright_navigate`, `click`, `fill`, `get_text`, `screenshot`, etc.

## 3. Search Request Optimization and Query Processing

- **Query Preprocessing**: Normalize location names, date ranges, traveler numbers.
- **Query Parameterization**: For flexible date searching, geo-based radius, etc.
- **Search Parallelization**: `asyncio.gather` for concurrent searches (flights, hotels, etc.).

## 4. Tool Chaining and Fallback Strategy

1. **Sequential Deepening**: Start broad (WebSearchTool), get more specific (WebCrawl MCP), and move to interactive if needed (BrowserAutomation MCP).
2. **Parallel Research**: Combine sources simultaneously.
3. **Fallback**: If specialized tools fail, revert to structured guidance for the main `WebSearchTool`.

## 5. Machine Learning Integration (Future Enhancement)

- Personalized ranking, price prediction, anomaly detection.

## 6. Caching Strategy for Search

- **Redis** for content-aware TTL.
- See `CACHING_STRATEGY_AND_IMPLEMENTATION.md` for details.

## 7. Specialized Search Tool Adapters

- **`search_destination_info`**: Orchestrates comprehensive destination research.
- **`compare_travel_options`**: Compares flights/hotels with relevant fallback flows.

## 8. Integration with OpenAI Agents SDK

- **Agent Instructions**: Guidelines on when to use each tool.
- **Tool Registration**: Tools from `WebSearchTool`, `WebCrawlMCPClient`, and `BrowserAutomationClient` are exposed to the agent.
- **Structured Adapters**: Provide a well-defined approach for multi-step or complex queries.

## 9. Conclusion

The hybrid search strategy balances broad reach (WebSearchTool) with depth (WebCrawl MCP) and interactivity (BrowserAutomation MCP). Combined with caching, it forms an efficient system for retrieving the diverse information needed for travel planning.
