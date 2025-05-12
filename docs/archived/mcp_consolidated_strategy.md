# TripSage MCP Integration Strategy

This document presents a consolidated strategy for implementing Model Context Protocol (MCP) servers within the TripSage travel planning system. It combines insights from multiple technical analyses and evaluations to provide a definitive implementation plan.

## Overview

TripSage will implement a suite of specialized MCP servers to provide enhanced capabilities for travel planning. The architecture employs a dual-storage approach (Supabase + knowledge graph) with plans to add semantic search capabilities through vector embeddings post-MVP.

## Architecture

```plaintext
┌─────────────────────────────────────────────────────────────────────┐
│                     TripSage Orchestration Layer                     │
├─────────┬─────────┬─────────┬──────────┬──────────┬─────────────────┤
│ Weather │  Web    │ Flights │Accommoda-│ Calendar │    Memory       │
│   MCP   │ Crawl   │   MCP   │tion MCP  │   MCP    │     MCP         │
│ Server  │ MCP     │ Server  │ Server   │  Server  │    Server       │
│         │ Server  │         │          │          │                 │
├─────────┴─────────┴─────────┴──────────┴──────────┼─────────────────┤
│                    Integration & Abstraction Layer │  Vector Search  │
├─────────────────────────────────────────────────────────────────────┤
│                     OpenAI Agents SDK Adapters                       │
├─────────────────────────────────────────────────────────────────────┤
│                       Agent Implementation                           │
├───────────────────┬───────────────────────┬─────────────────────────┤
│  Travel Planning  │   Budget Planning     │  Itinerary Planning     │
│       Agent       │       Agent           │        Agent            │
├───────────────────┴───────────────────────┴─────────────────────────┤
│                        FastAPI Backend                               │
├─────────────────────────────────────────────────────────────────────┤
│                      Supabase Database                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Technology Selections

After thorough analysis of available options, we have selected the following technologies:

| Component            | Selected Technology                        | Rationale                                                       |
| -------------------- | ------------------------------------------ | --------------------------------------------------------------- |
| MCP Server Framework | **Python FastMCP 2.0**                     | Reduced boilerplate, better OpenAPI support, active development |
| Knowledge Graph      | **Neo4j** with official `mcp-neo4j-memory` | Mature graph database with official MCP integration             |
| Vector Search        | **Qdrant** (planned post-MVP)              | Production-ready, horizontal scaling, rich filtering            |
| Timezone Management  | Official **Time MCP**                      | Standardized implementation, maintained by community            |
| API Integration      | FastMCP 2.0's **OpenAPI integration**      | Automatic MCP generation from OpenAPI specs                     |
| Caching              | **Redis**                                  | High-performance, TTL support, widely adopted                   |

## MCP Servers Implementation

### 1. Weather MCP Server

- **Purpose**: Provide weather data for travel destinations
- **API Integration**: OpenWeatherMap (primary), Weather.gov (US locations)
- **Implementation**: Python FastMCP 2.0 with OpenAPI integration
- **Data Format**: Standard weather information with travel recommendations

### 2. Web Crawling MCP Server

- **Purpose**: Facilitate destination research and content extraction
- **API Integration**: Firecrawl API (native MCP support)
- **Implementation**: Direct integration with existing Firecrawl MCP
- **Data Format**: Structured destination information, travel advisories

### 3. Flights MCP Server

- **Purpose**: Handle flight search, details, tracking, and booking
- **API Integration**: Duffel API via OpenAPI specification
- **Implementation**: Python FastMCP 2.0 with OpenAPI integration
- **Data Format**: Standardized flight information with price tracking

### 4. Accommodation MCP Server

- **Purpose**: Manage accommodation search, details, comparison
- **API Integration**: OpenBnB, Apify Booking.com Scraper
- **Implementation**: Python FastMCP 2.0 with custom mappings
- **Data Format**: Unified accommodation schema with semantic search capabilities

### 5. Calendar MCP Server

- **Purpose**: Facilitate calendar integration for travel planning
- **API Integration**: Google Calendar API
- **Implementation**: Python FastMCP 2.0 with explicit OAuth flow
- **Data Format**: Standardized events with travel metadata

### 6. Memory MCP Server

- **Purpose**: Manage knowledge graph for travel entities and relationships
- **API Integration**: Neo4j via official `mcp-neo4j-memory`
- **Implementation**: Direct integration with existing Neo4j MCP
- **Data Format**: Graph entities with relationships and semantic annotations

## Planned Vector Search Integration (Post-MVP)

After the MVP is complete, Qdrant will be integrated alongside Neo4j to provide enhanced semantic search capabilities:

- **Storage**: Vector embeddings of destinations, accommodations, activities
- **Indexing**: HNSW algorithm with cosine similarity
- **Integration**: Python SDK with async support
- **Use Cases**: Similar destination search, preference matching, semantic recommendations

## Implementation Timeline

| Phase                      | Timeline  | Focus                                  | Key Deliverables                                                     |
| -------------------------- | --------- | -------------------------------------- | -------------------------------------------------------------------- |
| 1: Foundation              | Weeks 1-2 | Infrastructure & Weather/Crawling MCPs | Python FastMCP 2.0 setup, Weather & Web Crawling MCPs                |
| 2: Travel Services         | Weeks 3-4 | Flight & Accommodation MCPs            | Flight search/booking, Accommodation search with vector capabilities |
| 3: Personal Data           | Weeks 5-6 | Calendar & Neo4j Integration           | Calendar integration, Knowledge graph implementation                 |
| 4: Finalization            | Weeks 7-8 | Testing & Production Readiness         | Performance optimization, Documentation, Deployment pipeline         |
| Future: Vector Enhancement | Post-MVP  | Qdrant Implementation                  | Semantic search capabilities, Vector-based recommendations           |

## Technical Architecture Approach

### MCP Server Creation Pattern

```python
# Example using Python FastMCP 2.0
from fastmcp import FastMCP, Tool, Resource
from typing import List, Optional
from pydantic import BaseModel

# Define data models
class WeatherCondition(BaseModel):
    temperature: float
    feels_like: float
    description: str
    humidity: int
    wind_speed: float

class LocationWeather(BaseModel):
    location: str
    country: str
    current: WeatherCondition
    forecast: List[WeatherCondition]
    travel_advice: List[str]

# Create MCP server
app = FastMCP()

@app.tool()
async def get_current_weather(location: str, units: str = "metric") -> LocationWeather:
    """Get current weather for a travel destination"""
    # Implementation using OpenWeatherMap API
    # ...

@app.tool()
async def get_travel_recommendation(
    location: str,
    start_date: str,
    end_date: str,
    activities: Optional[List[str]] = None
) -> dict:
    """Get weather-based travel recommendations for a destination"""
    # Implementation logic
    # ...

# Start the server
if __name__ == "__main__":
    app.serve()
```

### OpenAPI Integration Pattern

```python
from fastmcp import FastMCP
from fastmcp.openapi import create_mcp_from_openapi

# Create MCP server from OpenAPI spec
app = FastMCP()

# Add tools from OpenAPI spec
create_mcp_from_openapi(
    app,
    openapi_url="https://api.duffel.com/openapi/v1.json",
    base_url="https://api.duffel.com/v1",
    headers={"Authorization": "Bearer {{DUFFEL_API_KEY}}"}
)

# Start the server
if __name__ == "__main__":
    app.serve()
```

## Standardization Benefits

Standardizing on Python FastMCP 2.0 provides several key advantages:

1. **Reduced Development Time**: Decorator-based API minimizes boilerplate code
2. **OpenAPI Integration**: Automatic generation of MCP servers from external API specs
3. **Consistency**: Uniform patterns across all MCP servers
4. **Maintainability**: Simpler code with better separation of concerns
5. **Ecosystem Compatibility**: Better alignment with data science and AI tools

## Caching Strategy

A multi-level caching strategy using Redis will be implemented:

- **Weather Data**: Cache for 30 minutes
- **Flight Search Results**: Cache for 15 minutes
- **Accommodation Information**: Cache for 1 hour
- **Destination Details**: Cache for 24 hours
- **Travel Recommendations**: Cache for 6 hours

## Implementation Considerations

1. **Authentication & Security**:

   - Secure API key storage using environment variables
   - OAuth flow for user-specific services (Google Calendar)
   - Rate limiting and request validation

2. **Error Handling & Resilience**:

   - Consistent error response format across all MCP servers
   - Fallback mechanisms for service unavailability
   - Circuit breakers to prevent cascading failures

3. **Performance Optimization**:
   - Parallel API calls where appropriate
   - Batch operations for efficiency
   - Response compression for network optimization

## Conclusion

This consolidated MCP integration strategy provides a clear roadmap for implementing the TripSage travel planning system. By standardizing on Python FastMCP 2.0 and adopting official MCP implementations where available, we achieve a balance of development speed, maintainability, and feature richness.

Once the MVP is stable, the planned addition of Qdrant for vector search capabilities will complement the Neo4j knowledge graph, enabling both structured relationship navigation and semantic similarity searches. This future dual approach will provide the foundation for more sophisticated travel recommendations and personalized planning features.
