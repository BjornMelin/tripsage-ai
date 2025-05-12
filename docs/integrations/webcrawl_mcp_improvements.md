# WebCrawl MCP Implementation Improvements

This document describes the enhanced WebCrawl MCP implementation with improvements to support more robust and adaptable travel research capabilities.

## Table of Contents

- [Intelligent Source Selection](#intelligent-source-selection)
- [Structured WebSearchTool Fallback](#structured-websearchtool-fallback)
- [Future Improvements](#future-improvements)

## Intelligent Source Selection

### Overview

The intelligent source selection enhancement allows the WebCrawl MCP to dynamically choose between different web crawling sources (Crawl4AI and Playwright) based on URL characteristics, domain information, and historical success rates.

### Implementation Details

- Created a `SourceSelector` protocol in `source_interface.py` to define the interface for source selection strategies
- Implemented `IntelligentSourceSelector` in `source_selector.py` with the following features:
  - Domain-based selection rules for known dynamic/static sites
  - URL pattern matching for content type detection
  - Historical success rate tracking for continuous improvement
  - Singleton pattern to ensure consistent selection across requests

### Source Selection Strategy

The source selector uses the following criteria to select between Crawl4AI and Playwright:

1. **URL Characteristics**:

   - URLs with known dynamic content patterns (client-side rendering, JS-heavy sites) use Playwright
   - Static content sites (documentation, government pages, informational sites) use Crawl4AI

2. **Destination-specific rules**:

   - Certain destinations with known website characteristics have pre-configured source preferences
   - Different actions (search, events, blog crawling) have different optimal sources

3. **Adaptive Improvement**:
   - Success/failure reports from each request update source success rates
   - Over time, the system learns which sources work best for different sites and destinations

### Integration Points

The intelligent source selection has been integrated at multiple points:

- In the WebCrawl MCP server initialization
- In each handler method (extract_page_content, search_destination_info, etc.)
- With failure reporting to improve selection over time

## Structured WebSearchTool Fallback

### Overview

The structured WebSearchTool fallback enhancement provides detailed guidance when falling back to WebSearchTool, improving search quality and consistency when specialized crawling fails.

### Implementation Details

- Created the `search_helpers.py` utility module with:

  - `WebSearchFallbackGuide` class for structured guidance generation
  - Topic-specific query templates and extraction patterns
  - Domain configurations for targeted search
  - Response format guides for consistent results

- Enhanced handlers in `search_handler.py` to:

  - Provide structured guidance when both Crawl4AI and Playwright sources fail
  - Include traveler profile information for personalized results
  - Support additional contextual parameters for better guidance

- Updated client in `webcrawl/client.py` to:
  - Pass through structured guidance to agents without raising exceptions
  - Support traveler profile in search parameters
  - Detect and handle fallback scenarios gracefully

### Guidance Components

The structured WebSearchTool guidance includes:

1. **Search Plan**:

   - Optimized search queries based on destination and topic
   - Domain configurations for allowed/blocked domains
   - Multiple query suggestions with priorities
   - Traveler profile-specific information priorities

2. **Response Format Guide**:

   - Expected information structure by topic
   - Confidence scoring recommendations
   - Source verification guidance
   - Section structure for comprehensive results

3. **Extraction Patterns**:
   - Topic-specific data points to extract
   - Format recommendations
   - Source metadata requirements

### Integration with Destination Research Agent

The TripSage destination research agent now:

- Receives and utilizes structured guidance when WebCrawl fails
- Applies optimized search strategies based on guidance
- Returns more consistent results regardless of the underlying data source

## Result Normalization

### Overview

The result normalization enhancement ensures consistent data structures, field naming, and confidence scoring across different data sources (Crawl4AI, Playwright, WebSearchTool) used by the WebCrawl MCP.

### Implementation Details

- Created a `ResultNormalizer` class in `result_normalizer.py` with:

  - Specialized normalization methods for different data types (destinations, events, blogs)
  - Source-specific confidence scoring
  - Category detection based on content analysis
  - Automatic summarization for long content
  - Sentiment analysis for subjective content
  - Comprehensive metadata tracking

- Integrated normalization at key points:
  - In all handlers before returning results to clients
  - In fallback paths to ensure consistent output regardless of source
  - In error handling to provide structured error responses

### Normalization Features

1. **Data Structure Consistency**:

   - Standardized field names across all sources
   - Consistent nesting and object organization
   - Default values for missing fields

2. **Content Enrichment**:

   - Automatic summarization of long text
   - Category detection using keyword analysis
   - Sentiment analysis for blog content
   - Confidence scoring based on source reliability

3. **Metadata Enhancement**:
   - Source tracking for all data points
   - Timestamp information for extraction and normalization
   - Processing history for debugging and audit

See [WebCrawl Result Normalization](./webcrawl_result_normalization.md) for detailed documentation.

### Knowledge Graph Expansion (MEM-005)

- Create additional entity types beyond destinations
- Implement specialized relation types for travel entities
- Support more complex knowledge graph queries
- Enhance cross-reference capabilities between entities

### Cache Enhancements (CACHE-002)

- Implement partial cache updates for time-sensitive data
- Add cache warming for popular destinations
- Create cache statistics collection for optimization
- Implement predictive caching based on travel patterns

## Usage Examples

### Using Structured WebSearchTool Fallback

```python
from src.agents.destination_research import TripSageDestinationResearch

# Initialize the destination research component
research = TripSageDestinationResearch()

# Search for destination information with traveler profile
result = await research.search_destination_info({
    "destination": "Kyoto, Japan",
    "topics": ["attractions", "safety", "transportation"],
    "traveler_profile": "family_focused"
})

# Check if result has structured guidance for WebSearchTool
if "websearch_tool_guidance" in result:
    # Use the structured guidance to perform better web searches
    guidance = result["websearch_tool_guidance"]["attractions"]

    # Example of using the search plan from guidance
    search_plan = guidance["search_plan"]
    for query_info in search_plan["queries"]:
        if query_info["priority"] == "high":
            # Use the high priority query first
            primary_query = query_info["query"]
            # Configure domains based on guidance
            allowed_domains = search_plan["domain_configuration"]["allowed_domains"]

    # Use the response format guide for consistent extraction
    response_format = guidance["response_format"]
    # Structure results according to the specified sections
    expected_sections = [section["name"] for section in response_format["sections"]]
```
