# TripSage MCP Servers

This section provides detailed documentation for all Model Context Protocol (MCP) servers utilized and implemented within the TripSage AI Travel Planning System. MCP servers are specialized microservices that expose tools and functionalities, enabling AI agents and other backend components to interact with external APIs, databases, and custom business logic in a standardized way.

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

## Development and Integration

When developing new features that require external service interaction or specialized processing, consider whether a new MCP tool or server is appropriate. Refer to the `GENERAL_MCP_IMPLEMENTATION_PATTERNS.md` for guidance.
