# Hybrid Search Strategy: WebSearchTool, Web Crawling, and Browser Automation

This document defines TripSage's hybrid search strategy, which combines OpenAI's WebSearchTool with specialized web crawling and browser automation capabilities to create a comprehensive web information ecosystem.

## Architecture Overview

TripSage implements a hierarchical search strategy that leverages different tools based on the complexity of the search query, depth of information required, and the type of interaction needed:

```plaintext
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                       TripSage Travel Agent                          │
│                                                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                      Hybrid Search Strategy                          │
│                                                                      │
├─────────────┬─────────────────────────┬──────────────────────────────┤
│             │                         │                              │
│  ┌──────────▼─────────┐    ┌──────────▼─────────┐    ┌───────────────▼──────┐
│  │                    │    │                    │    │                      │
│  │   WebSearchTool    │    │  WebCrawl MCP      │    │  Browser MCP         │
│  │   (Primary)        │    │  (Specialized)     │    │  (Interactive)       │
│  │                    │    │                    │    │                      │
│  └────────────────────┘    └────────────────────┘    └──────────────────────┘
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                       Dual Storage Architecture                      │
│                                                                      │
├───────────────────────────────┬──────────────────────────────────────┤
│                               │                                      │
│     Supabase (Structured)     │     Memory MCP (Knowledge Graph)     │
│                               │                                      │
└───────────────────────────────┴──────────────────────────────────────┘
```

## Tool Selection Strategy

The TripSage Agent makes tool selection decisions based on the following criteria:

### 1. WebSearchTool (Primary for General Queries)

**When to use:**

- General travel information needs
- Current events and news related to destinations
- Initial research phase
- Quick fact-checking
- Recent information not available in specialized databases

**Configuration:**

- Travel-optimized domain allowlists:

  ```python
  allowed_domains=[
      # Travel information and guides
      "tripadvisor.com", "lonelyplanet.com", "wikitravel.org", "travel.state.gov",
      "wikivoyage.org", "frommers.com", "roughguides.com", "fodors.com",

      # Flight and transportation
      "kayak.com", "skyscanner.com", "expedia.com", "booking.com",
      "hotels.com", "airbnb.com", "vrbo.com", "orbitz.com",

      # Airlines
      "united.com", "aa.com", "delta.com", "southwest.com", "britishairways.com",
      "lufthansa.com", "emirates.com", "cathaypacific.com", "qantas.com",

      # Weather and climate
      "weather.com", "accuweather.com", "weatherspark.com", "climate.gov",

      # Government travel advisories
      "travel.state.gov", "smartraveller.gov.au", "gov.uk/foreign-travel-advice",

      # Social and review sites
      "tripadvisor.com", "yelp.com"
  ]
  ```

- Domain blocklists to filter low-quality content:

  ```python
  blocked_domains=["pinterest.com", "quora.com"]
  ```

**Example implementation:**

```python
# TravelAgent (travel_agent.py)
self.web_search_tool = WebSearchTool(
    allowed_domains=AllowedDomains(domains=[
        "tripadvisor.com", "lonelyplanet.com", "wikitravel.org",
        # ... more travel domains
    ]),
    blocked_domains=["pinterest.com", "quora.com"]
)
self.agent.tools.append(self.web_search_tool)
```

### 2. WebCrawl MCP (For Specialized/Deep Travel Content)

**When to use:**

- Detailed destination research requiring structured data
- Travel blog analysis for local insights
- Price monitoring and comparison
- Event discovery at specific destinations
- Content from dynamic sites not easily indexed

**Implementation:**
The WebCrawl MCP uses a source selection strategy that determines the appropriate backend:

- **Crawl4AI** (primary): For static content, batch processing
- **Playwright** (fallback): For dynamic content requiring JavaScript

**Example tools:**

```python
@function_tool
async def search_destination_info(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search for comprehensive information about a travel destination."""
    # Implementation that combines WebSearchTool results with WebCrawl MCP
    # for deeper, more structured information
```

### 3. Browser Automation MCP (For Interactive Tasks)

**When to use:**

- Flight status checking requiring form submissions
- Booking verification that needs authentication
- Price monitoring on sites with anti-bot measures
- Check-in processes and interactive workflows
- Tasks requiring screenshots or visual verification

**Implementation:**
The Browser Automation MCP is built on Playwright with Python and provides:

- Browser context management for efficient resource usage
- Authentication handling and session persistence
- Screenshot capabilities for visual verification
- Form interaction for complex workflows

**Example tools:**

```python
@function_tool
async def check_flight_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Check flight status on airline website using browser automation."""
    # Implementation using Browser MCP
```

## Tool Chaining Strategy

The TripSage hybrid search strategy implements intelligent tool chaining to maximize the strengths of each component:

1. **Sequential Deepening**:

   - Start with WebSearchTool for initial broad information
   - Use WebCrawl MCP for deeper, structured information on specific topics
   - Deploy Browser Automation MCP for interactive verification when needed

2. **Parallel Research**:

   - Perform searches across multiple tools simultaneously
   - Combine and cross-validate results for comprehensive answers
   - Present unified information to users

3. **Fallback Mechanisms**:
   - If WebSearchTool fails to retrieve needed information, fall back to WebCrawl MCP
   - If WebCrawl MCP cannot extract content, escalate to Browser Automation MCP
   - Always provide graceful degradation with clear user messaging

## Caching Strategy

To optimize performance and reduce API costs, TripSage implements a comprehensive caching strategy:

```python
# Destination info caching example
cache_key = f"destination:{destination}:info_type:{info_type}"
cached_result = await redis_cache.get(cache_key)

if cached_result:
    search_results[info_type] = cached_result
else:
    # Perform search and store in cache
    result = await perform_search(...)
    await redis_cache.set(cache_key, result, ttl=cache_ttl)
```

### TTL (Time-To-Live) Configuration

| Content Type             | TTL        | Rationale                            |
| ------------------------ | ---------- | ------------------------------------ |
| General destination info | 7 days     | Changes infrequently                 |
| Weather data             | 1 hour     | Changes frequently                   |
| Flight prices            | 30 minutes | Volatile pricing                     |
| Events and activities    | 24 hours   | Medium update frequency              |
| Travel advisories        | 6 hours    | Important to keep relatively current |
| News articles            | 1 hour     | Highly time-sensitive                |
| Hotel availability       | 2 hours    | Changes with moderate frequency      |

## Specialized Tool Adapters

TripSage implements specialized tool adapters around WebSearchTool to provide structure and enhanced functionality:

### 1. Destination Research Adapter

```python
@function_tool
async def search_destination_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Search for comprehensive information about a travel destination."""
    # Extract parameters
    destination = params.get("destination")
    info_types = params.get("info_types", ["general"])

    # Build queries for each info type
    search_results = {}

    for info_type in info_types:
        query = self._build_destination_query(destination, info_type)

        # Check cache first
        cache_key = f"destination:{destination}:info_type:{info_type}"
        cached_result = await redis_cache.get(cache_key)

        if cached_result:
            search_results[info_type] = cached_result
        else:
            # Let the agent use WebSearchTool with structured guidance
            search_results[info_type] = {
                "query": query,
                "cache": "miss",
                "note": "Data will be provided by WebSearchTool and processed by the agent"
            }

    return {
        "destination": destination,
        "info_types": info_types,
        "search_results": search_results
    }
```

### 2. Travel Comparison Adapter

```python
@function_tool
async def compare_travel_options(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Compare travel options for a specific category."""
    # Extract parameters
    category = params.get("category")
    destination = params.get("destination")

    # Specialized handling based on category
    if category == "flights":
        origin = params.get("origin")
        # Build hybrid approach using WebSearchTool and Flights MCP
        return {
            "category": "flights",
            "origin": origin,
            "destination": destination,
            "search_strategy": "hybrid",
            "note": "The agent will use WebSearchTool for general information and Flights MCP for specific data"
        }

    # Similar implementations for other categories...
```

## Integration with OpenAI Agents SDK

The hybrid search strategy is seamlessly integrated with the OpenAI Agents SDK through:

1. **Explicit tool selection guidance in agent instructions**:

   ```python
   agent = Agent(
       name="Travel Planning Agent",
       instructions="""You are a travel planning assistant for TripSage.

       TOOL SELECTION GUIDELINES:
       - Use WebSearchTool for general travel information, current events, and initial research
       - Use WebCrawl MCP for detailed destination information and specialized travel content
       - Use Browser Automation for tasks requiring authentication or website interaction

       For research tasks:
       1. Start with WebSearchTool for broad information
       2. Use WebCrawl MCP tools for in-depth, structured information
       3. Use Browser Automation only when interaction is required
       """,
       tools=[web_search_tool, search_destination_info, compare_travel_options, ...]
   )
   ```

2. **Structured tool adapters** that encapsulate complex logic while providing consistent interfaces

3. **Domain-specific optimization** through WebSearchTool configuration

4. **Unified result processing** that presents consistent formats regardless of source

## Implementation Status

| Component                 | Status      | Notes                                                               |
| ------------------------- | ----------- | ------------------------------------------------------------------- |
| WebSearchTool integration | ✅ Complete | Implemented with travel-specific domain configuration               |
| Search tool adapters      | ✅ Complete | Destination info and comparison adapters implemented                |
| WebCrawl MCP Server       | 🔄 Pending  | Architecture defined but implementation incomplete                  |
| Browser Automation MCP    | 🔄 Pending  | Architecture defined with booking verification complete             |
| Caching infrastructure    | ⚠️ Partial  | Redis cache implemented but not fully integrated with WebSearchTool |
| Dual storage integration  | 🔄 Pending  | Defined but awaiting implementation                                 |

## Next Steps

1. Complete WebCrawl MCP Server implementation (WEBCRAWL-001 through WEBCRAWL-005)
2. Finalize Browser Automation MCP implementation (BROWSER-001 through BROWSER-006)
3. Enhance WebSearchTool integration with additional specialized adapters
4. Implement comprehensive testing suite for the hybrid search strategy
5. Optimize caching parameters based on real-world usage patterns

## Conclusion

TripSage's hybrid search strategy creates a comprehensive web information ecosystem that leverages the strengths of each component:

- **WebSearchTool**: Provides broad coverage and current information with minimal implementation overhead
- **WebCrawl MCP**: Delivers specialized, structured travel information with depth and precision
- **Browser Automation MCP**: Enables interactive capabilities for complex travel-related tasks

This approach offers an optimal balance between implementation complexity, information quality, and resource efficiency, particularly for personal deployment scenarios where users bring their own API keys.
