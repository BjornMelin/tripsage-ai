# TripSage Service Integration Guide (MCP → SDK Migration)

**🚨 MAJOR ARCHITECTURE CHANGE 🚨**

TripSage is **migrating from MCP servers to direct SDK integration** for dramatically improved performance and simplified architecture. This section documents both legacy MCP implementations and the new unified SDK approach.

**NEW ARCHITECTURE**: 7 direct SDK integrations + 1 MCP server (Airbnb only) replacing 12 original MCP servers.

**PERFORMANCE GAINS**: 50-70% latency reduction, 6-10x crawling improvement, ~3000 lines code reduction.

## Standardization Update (January 2025)

**TripSage has standardized on the shell-script + Python-wrapper approach for all MCP server integrations.**

Key changes:

- ✅ Removed legacy `/mcp_servers/` directory (incompatible with FastMCP 2.0)
- ✅ Implemented unified launcher script (`scripts/mcp_launcher.py`)
- ✅ Created Docker-Compose orchestration (`docker-compose.mcp.yml`)
- ✅ Added service registry for dynamic management
- ✅ Enhanced configuration with runtime/transport options

For full details, see [MCP Server Standardization Strategy](../implementation/mcp_server_standardization.md).

## Overview of MCP Strategy

TripSage employs a hybrid MCP strategy:

1. **Official/External MCPs**: Wherever possible, TripSage integrates with existing, well-maintained official or community-provided MCP servers (e.g., Time MCP, Neo4j Memory MCP, Google Maps MCP, OpenBnB Airbnb MCP). This reduces development overhead and leverages specialized expertise.
2. **Custom MCP Servers**: For core TripSage-specific logic, or when external MCPs do not meet specific requirements (e.g., complex API orchestrations, unique data transformations), custom MCP servers are developed. These are built using **Python FastMCP 2.0** to ensure consistency, type safety, and ease of integration with the Python-based backend and agent system.

All interactions with MCP servers from within the TripSage application are managed through a unified **MCP Abstraction Layer**, which provides a consistent interface, standardized error handling, and centralized configuration.

## Contents

This section contains detailed guides for each MCP server, covering:

- **[General MCP Implementation Patterns](./GENERAL_MCP_IMPLEMENTATION_PATTERNS.md)**:
  - Standardized approaches, best practices, and common patterns for developing and integrating MCP servers within TripSage. Includes general evaluation criteria for choosing or building MCPs.

- **Specific MCP Server Guides**:
  - **[Flights MCP](./Flights_MCP.md)**: Handles flight search, booking, and management, primarily integrating with the Duffel API.
  - **[Weather MCP](./Weather_MCP.md)**: Provides weather forecasts and conditions by integrating with services like OpenWeatherMap.
  - **[Time MCP](./Time_MCP.md)**: Manages time-related operations, timezone conversions, and local time calculations, using the official Time MCP server.
  - **[Memory MCP (Neo4j)](./Memory_MCP.md)**: Interfaces with the Neo4j knowledge graph for storing and retrieving semantic travel data and user context, using the official Neo4j Memory MCP.
  - **[WebCrawl MCP](./WebCrawl_MCP.md)**: Facilitates web data extraction from various travel-related websites using a hybrid strategy (Crawl4AI, Firecrawl, Playwright).
  - **[Calendar MCP](./Calendar_MCP.md)**: Integrates with calendar services (e.g., Google Calendar) for itinerary scheduling.
  - **[Google Maps MCP](./GoogleMaps_MCP.md)**: Provides geospatial services like geocoding, place search, and directions, using the official Google Maps MCP.
  - **[Accommodations MCP](./Accommodations_MCP.md)**: Manages search and details for various lodging types, integrating with OpenBnB (for Airbnb) and Apify (for Booking.com).
  - **[Browser Automation Tools (via MCPs)](./BrowserAutomation_MCP.md)**: Details the integration with external Playwright and Stagehand MCPs for tasks requiring browser interaction.

Each specific MCP server document typically includes:
- An overview of its purpose and functionality.
- The MCP tools it exposes (schemas and descriptions).
- Details of any underlying API integrations.
- Key implementation aspects and design choices.
- Configuration requirements.
- Integration points with the TripSage agent architecture.

## Quick Start

### Using the Unified Launcher

Start a specific MCP server:

```bash
python scripts/mcp_launcher.py start supabase
```

List all available servers:

```bash
python scripts/mcp_launcher.py list
```

Start all auto-start servers:

```bash
python scripts/mcp_launcher.py start-all --auto-only
```

### Using Docker-Compose

Start all MCP servers in containers:

```bash
docker-compose -f docker-compose.mcp.yml up -d
```

Stop all servers:

```bash
docker-compose -f docker-compose.mcp.yml down
```

## Development and Integration

When developing new features that require external service interaction or specialized processing, consider whether a new MCP tool or server is appropriate. Refer to the `GENERAL_MCP_IMPLEMENTATION_PATTERNS.md` for guidance.

### Implementation Details

All MCP servers follow these patterns:

1. **Configuration**: Defined in `tripsage/config/mcp_settings.py`
2. **Wrappers**: Located in `tripsage/mcp_abstraction/wrappers/`
3. **Tools**: Exposed in `tripsage/tools/` directories
4. **Tests**: Coverage in `tests/mcp/` directories

For creating new MCP integrations, follow the patterns established in existing implementations.
