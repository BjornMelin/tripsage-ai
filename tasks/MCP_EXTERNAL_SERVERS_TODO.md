# MCP External Servers Implementation TODO

This document tracks the implementation status of external MCP servers for TripSage, following the "External First" strategy outlined in GENERAL_MCP_IMPLEMENTATION_PATTERNS.md.

## Strategy Overview

✅ **External First**: Use existing, well-maintained external MCPs for all standard functionality
✅ **No Custom Servers**: We do NOT build custom MCP servers unless absolutely necessary
✅ **Thin Wrappers**: Create lightweight Python wrappers around external MCPs for integration

## Implementation Status

### ✅ Completed External MCP Integrations

1. **Supabase MCP** (Database Operations)
   - Server: `@supabase/mcp-server-supabase@latest`
   - Wrapper: `SupabaseMCPWrapper`
   - Status: ✅ Fully integrated with external server

2. **Redis MCP** (Caching)
   - Server: Official Redis MCP
   - Wrapper: `OfficialRedisMCPWrapper`
   - Status: ✅ Fully integrated

3. **Neo4j Memory MCP** (Knowledge Graph)
   - Server: `@neo4j/mcp-server-memory`
   - Wrapper: `Neo4jMemoryMCPWrapper`
   - Status: ✅ Fully integrated

4. **Duffel Flights MCP** (Flight Search)
   - Server: `@duffel/mcp-server-flights`
   - Wrapper: `DuffelFlightsMCPWrapper`
   - Status: ✅ Fully integrated

5. **Airbnb MCP** (Accommodation Search)
   - Server: `@openbnb/mcp-server-airbnb`
   - Wrapper: `AirbnbMCPWrapper`
   - Status: ✅ Fully integrated

6. **Google Maps MCP** (Location Services)
   - Server: `@googlemaps/mcp-server`
   - Wrapper: `GoogleMapsMCPWrapper`
   - Status: ✅ Fully integrated

7. **Weather MCP** (Weather Data)
   - Server: `@weather/mcp-server`
   - Wrapper: `WeatherMCPWrapper`
   - Status: ✅ Fully integrated

8. **Time MCP** (Timezone Operations)
   - Server: `@anthropic/mcp-server-time`
   - Wrapper: `TimeMCPWrapper`
   - Status: ✅ Fully integrated

9. **Firecrawl MCP** (Web Crawling)
   - Server: `@mendableai/firecrawl-mcp-server`
   - Wrapper: `FirecrawlMCPWrapper`
   - Status: ✅ Fully integrated

10. **Crawl4AI MCP** (AI Web Crawling)
    - Server: `@crawl4ai/mcp-server`
    - Wrapper: `Crawl4AIMCPWrapper`
    - Status: ✅ Fully integrated

11. **Playwright MCP** (Browser Automation)
    - Server: `@executeautomation/mcp-playwright`
    - Wrapper: `PlaywrightMCPWrapper`
    - Status: ✅ Fully integrated

### 🔄 In Progress

12. **Google Calendar MCP** (Calendar Integration)
    - Server: `@googleapis/mcp-calendar`
    - Wrapper: `GoogleCalendarMCPWrapper`
    - Status: 🔄 Wrapper created, needs testing

### 📋 Planned External MCP Integrations

13. **GitHub MCP** (Version Control)
    - Server: `@modelcontextprotocol/server-github`
    - Purpose: Itinerary versioning, collaborative planning
    - Priority: Medium

14. **Perplexity MCP** (Research)
    - Server: `@perplexity/mcp-server`
    - Purpose: Enhanced destination research
    - Priority: Medium

15. **Sequential Thinking MCP** (Planning)
    - Server: `@modelcontextprotocol/server-sequential-thinking`
    - Purpose: Complex travel planning logic
    - Priority: Low (evaluate need first)

16. **LinkUp MCP** (Web Search)
    - Server: `@linkup/mcp-server`
    - Purpose: Alternative web search provider
    - Priority: Low (have existing search)

17. **Exa MCP** (Web Search)
    - Server: `@exa/mcp-server`
    - Purpose: Alternative web search provider
    - Priority: Low (have existing search)

## Implementation Guidelines

### For Each External MCP Integration:

1. **Configuration**
   - Add config class to `mcp_settings.py`
   - Use appropriate base class (RestMCPConfig, DatabaseMCPConfig, etc.)
   - Configure command/args for external server launch

2. **Wrapper Implementation**
   - Create wrapper in `tripsage/mcp_abstraction/wrappers/`
   - Inherit from `BaseMCPWrapper`
   - Map user-friendly method names to MCP tool names
   - Use `ExternalMCPClient` pattern

3. **Registration**
   - Add to `registration.py`
   - Use lazy loading pattern

4. **Tool Creation**
   - Create tools in `tripsage/tools/`
   - Use `@function_tool` decorator
   - Integrate with `MCPManager`

5. **Testing**
   - Unit tests for wrapper
   - Integration tests for tool usage
   - Mock external server responses

## Important Notes

⚠️ **DO NOT CREATE CUSTOM MCP SERVERS** unless:
- The functionality is absolutely core to TripSage's unique business logic
- No external MCP server exists for the functionality
- Direct database integration is required that cannot be achieved otherwise
- Specific privacy/security requirements cannot be met

Currently, **NO CUSTOM MCP SERVERS ARE NEEDED** - all requirements are met by external servers.

## Next Steps

1. Complete Google Calendar MCP testing
2. Evaluate need for GitHub MCP for itinerary versioning
3. Consider Perplexity MCP for enhanced research capabilities
4. Continue monitoring MCP ecosystem for new useful servers