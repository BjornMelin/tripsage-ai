# TripSage Agent Optimization Guide

This guide contains comprehensive optimization strategies for TripSage's AI agent implementation, API integrations, and overall system architecture. Based on extensive research, these recommendations aim to maximize efficiency, user experience, and developer productivity.

## Table of Contents

1. [Agent Prompt Optimization](#agent-prompt-optimization)
2. [MCP Server Orchestration](#mcp-server-orchestration)
3. [API Response Normalization](#api-response-normalization)
4. [Optimal API & MCP Server Combinations](#optimal-api--mcp-server-combinations)
5. [Search Integration Strategy](#search-integration-strategy)
6. [Caching Strategy](#caching-strategy)
7. [Implementation Phasing](#implementation-phasing)

## Agent Prompt Optimization

### Key Principles

- **Structured Knowledge** - Provide agent with clear travel domain structure (flights, accommodations, activities, etc.)
- **Context Window Management** - Minimize token usage through progressive disclosure
- **Specific Instructions** - Use precise language for expected outputs and reasoning
- **Tool Calling Guidance** - Explicit instructions for when/how to call APIs

### Recommended Prompt Structure

```plaintext
You are TripSage, an AI travel assistant specializing in comprehensive trip planning.

CAPABILITIES:
- Search and book flights using Duffel API
- Find accommodations through OpenBnB (Airbnb data) and Apify (Booking.com)
- Locate attractions and restaurants via Google Maps Platform
- Access real-time travel information through web search

INTERACTION GUIDELINES:
1. Always gather key trip parameters first (dates, destination, budget, preferences)
2. Use appropriate API calls based on the user's query stage:
   - Initial planning: Use lightweight search APIs first
   - Specific requests: Use specialized booking APIs
3. Present options clearly with price, ratings, and key features
4. Maintain state between interactions to avoid repeating information
5. Offer recommendations based on user preferences and constraints

When calling tools:
- For flights: Always include departure/arrival cities, dates, and class
- For accommodations: Include location, dates, guests, and price range
- For attractions: Include location and search radius
- For restaurants: Include cuisine preferences and dietary restrictions

IMPORTANT: Handle API errors gracefully. If data is unavailable, explain why and suggest alternatives.
```

### Token Optimization Techniques

1. **Progressive Loading**: Request data in stages rather than all at once
2. **Selective Detail**: Include only essential information in initial responses
3. **User-Directed Exploration**: Let users request additional details on specific options
4. **Memory Management**: Maintain key user preferences in a dedicated data store

## MCP Server Orchestration

### Architecture Pattern

Implement a centralized MCP orchestration layer that abstracts API complexity from the agent:

```javascript
class MCPOrchestrator {
  constructor(config) {
    this.servers = {};
    this.initializeServers(config);
  }

  async initializeServers(config) {
    // Initialize MCP servers based on configuration
    for (const [name, serverConfig] of Object.entries(config.servers)) {
      this.servers[name] = new MCPServer(serverConfig);
      await this.servers[name].initialize();
    }
  }

  async routeRequest(toolName, params) {
    // Determine appropriate server and route request
    const serverName = this.mapToolToServer(toolName);
    return this.servers[serverName].callTool(toolName, params);
  }

  mapToolToServer(toolName) {
    // Map tool names to server names
    const mapping = {
      search_flights: "duffel",
      search_accommodations: "openbnb",
      search_booking: "apify",
      search_location: "google_maps",
      // Add more mappings as needed
    };
    return mapping[toolName] || "default";
  }
}
```

### Server Communication Patterns

1. **Request Batching**: Group related API calls (e.g., flight searches across providers)
2. **Parallel Processing**: Execute independent requests concurrently
3. **Lazy Loading**: Initialize servers on demand rather than at startup
4. **Graceful Degradation**: Handle server unavailability with fallbacks

### Error Handling Strategy

Implement consistent error handling across all MCP servers:

- Service unavailable errors (retry with exponential backoff)
- Rate limiting errors (queue requests with appropriate delays)
- Data format errors (normalize and sanitize incomplete responses)

## API Response Normalization

### Unified Data Models

Create unified data models for core travel entities to normalize responses from different APIs:

```typescript
// Flight data model
interface Flight {
  id: string;
  carrier: {
    code: string;
    name: string;
    logo_url?: string;
  };
  departure: {
    airport: string;
    terminal?: string;
    time: string; // ISO format
  };
  arrival: {
    airport: string;
    terminal?: string;
    time: string; // ISO format
  };
  duration: number; // minutes
  price: {
    amount: number;
    currency: string;
  };
  cabin_class: string;
  stops: number;
  source: string; // API source identifier
}

// Accommodation data model
interface Accommodation {
  id: string;
  name: string;
  type: string; // hotel, apartment, house, etc.
  location: {
    address: string;
    coordinates: {
      lat: number;
      lng: number;
    };
  };
  price: {
    amount: number;
    currency: string;
    per_night: boolean;
  };
  rating?: number;
  amenities: string[];
  images: string[];
  source: string; // API source identifier
}
```

### Normalization Functions

Create adapter functions to convert API-specific responses to unified models:

```javascript
// Example adapter for Duffel API flight offers
function normalizeDuffelFlights(duffelOffers) {
  return duffelOffers.map((offer) => ({
    id: offer.id,
    carrier: {
      code: offer.slices[0].segments[0].operating_carrier.iata_code,
      name: offer.slices[0].segments[0].operating_carrier.name,
      logo_url: offer.owner.logo_symbol_url,
    },
    departure: {
      airport: offer.slices[0].segments[0].origin.iata_code,
      terminal: offer.slices[0].segments[0].origin.terminal,
      time: offer.slices[0].segments[0].departing_at,
    },
    arrival: {
      airport:
        offer.slices[0].segments[offer.slices[0].segments.length - 1]
          .destination.iata_code,
      terminal:
        offer.slices[0].segments[offer.slices[0].segments.length - 1]
          .destination.terminal,
      time: offer.slices[0].segments[offer.slices[0].segments.length - 1]
        .arriving_at,
    },
    duration: calculateDuration(
      offer.slices[0].segments[0].departing_at,
      offer.slices[0].segments[offer.slices[0].segments.length - 1].arriving_at
    ),
    price: {
      amount: parseInt(offer.total_amount),
      currency: offer.total_currency,
    },
    cabin_class: offer.slices[0].segments[0].cabin_class,
    stops: offer.slices[0].segments.length - 1,
    source: "duffel",
  }));
}

// Example adapter for OpenBnB accommodation data
function normalizeOpenBnBAccommodations(openBnBListings) {
  return openBnBListings.map((listing) => ({
    id: listing.id,
    name: listing.name,
    type: listing.property_type,
    location: {
      address: listing.address,
      coordinates: {
        lat: listing.lat,
        lng: listing.lng,
      },
    },
    price: {
      amount: listing.price,
      currency: listing.currency,
      per_night: true,
    },
    rating: listing.rating,
    amenities: listing.amenities || [],
    images: listing.images || [],
    source: "openbnb",
  }));
}
```

## Optimal API & MCP Server Combinations

Based on comprehensive research, here are the optimal combinations for TripSage:

### Primary APIs

| Category       | Primary API                 | Alternative API        | MCP Server                  |
| -------------- | --------------------------- | ---------------------- | --------------------------- |
| Flights        | Duffel API                  | Amadeus                | Custom MCP w/ Node.js SDK   |
| Accommodations | OpenBnB                     | Apify (Booking.com)    | openbnb-mcp-server          |
| Maps & POI     | Google Maps Platform        | Mapbox                 | Google Maps MCP             |
| Search         | Linkup for specific queries | OpenAI built-in search | Built-in w/ custom fallback |

### Integration Architecture

![TripSage API Integration Architecture](https://i.imgur.com/placeholder.png)

The optimal architecture uses a service-oriented approach:

1. **API Gateway Layer**: Centralized authentication, rate limiting, and request routing
2. **Service Layer**: Separate services for flights, accommodations, locations
3. **MCP Server Layer**: Dedicated MCP servers for each primary API
4. **Cache Layer**: Redis for high-speed caching with TTL based on data volatility
5. **Agent Layer**: OpenAI Assistants API agents with optimized prompts

## Search Integration Strategy

### Hybrid Search Approach

Implement a hybrid search approach that leverages both OpenAI's built-in search and Linkup:

```javascript
async function hybridSearch(query, searchType = "auto") {
  // Analyze query intent to determine search type
  const searchIntent = await analyzeSearchIntent(query);

  // Determine which search to use based on intent and type
  if (
    searchType === "specific" ||
    searchIntent.includes("specific_fact") ||
    searchIntent.includes("location_details")
  ) {
    return await linkupSearch(query, "deep");
  } else {
    // Use built-in search for general queries
    return await openAIBuiltInSearch(query);
  }
}

async function linkupSearch(query, depth = "standard") {
  // Implementation for Linkup search
  const result = await mcpClient.call("linkup", "search-web", {
    query,
    depth,
  });
  return result;
}

async function openAIBuiltInSearch(query) {
  // Use OpenAI's built-in search capability
  // This is handled automatically by the Assistants API
  return { usedBuiltInSearch: true };
}
```

### Decision Matrix for Search Method

| Query Type               | Example                                   | Recommended Method |
| ------------------------ | ----------------------------------------- | ------------------ |
| General travel knowledge | "Best time to visit Barcelona"            | OpenAI built-in    |
| Specific details         | "Current entry requirements for Japan"    | Linkup (deep)      |
| Pricing comparisons      | "Average hotel prices in Manhattan"       | Linkup (standard)  |
| Subjective advice        | "Is Barcelona or Madrid better for food?" | OpenAI built-in    |
| Time-sensitive info      | "Current flight delays at JFK"            | Linkup (deep)      |

## Caching Strategy

### Multi-Level Cache Design

Implement a Redis-based multi-level caching strategy with TTL based on data volatility:

```javascript
class TravelDataCache {
  constructor(redisClient) {
    this.redis = redisClient;
    this.prefixMap = {
      flights: "tripsage:flights:",
      accommodations: "tripsage:accommodations:",
      locations: "tripsage:locations:",
      search: "tripsage:search:",
    };
    this.ttlMap = {
      flights: 15 * 60, // 15 minutes
      accommodations: 60 * 60, // 1 hour
      locations: 24 * 60 * 60, // 1 day
      search: 12 * 60 * 60, // 12 hours
    };
  }

  async get(category, key) {
    const prefix = this.prefixMap[category] || "tripsage:general:";
    const data = await this.redis.get(prefix + key);
    return data ? JSON.parse(data) : null;
  }

  async set(category, key, value) {
    const prefix = this.prefixMap[category] || "tripsage:general:";
    const ttl = this.ttlMap[category] || 3600; // Default 1 hour
    await this.redis.set(prefix + key, JSON.stringify(value), "EX", ttl);
  }

  generateKey(params) {
    return Object.entries(params)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([k, v]) => `${k}:${v}`)
      .join("|");
  }
}
```

### Cache Invalidation Strategy

1. **Time-Based**: Primary strategy using TTL values based on data volatility
2. **Event-Based**: Invalidate specific cache entries on booking confirmations
3. **Bulk Invalidation**: Daily cleanup of low-priority cached data

## Implementation Phasing

### Phase 1: Core Search Capabilities

- Implement Duffel API integration for flight search
- Implement OpenBnB MCP server for accommodation search
- Build basic agent prompt with search capabilities
- Implement Redis caching for search results

### Phase 2: Enhanced User Experience

- Add Google Maps integration for location search and POI
- Implement response normalization for consistent data presentation
- Enhance agent prompt with specialized travel knowledge
- Add Linkup search integration for real-time information

### Phase 3: Booking and Confirmation

- Implement Duffel booking capabilities
- Add accommodation booking through direct links
- Enhance agent with booking guidance and confirmation logic
- Implement comprehensive error handling and fallbacks

### Phase 4: Advanced Features

- Multi-destination trip planning
- Personalized recommendations based on user preferences
- Integration with weather data for trip timing suggestions
- Expense tracking and budget optimization features

## Conclusion

This optimization guide provides a comprehensive roadmap for implementing and enhancing TripSage's AI travel planning capabilities. By following these patterns and recommendations, the system will provide an efficient, responsive, and user-friendly travel planning experience while maintaining developer productivity and system sustainability.

The combination of optimized agent prompts, efficient MCP server orchestration, appropriate API selection, and strategic caching will allow TripSage to deliver high-quality travel planning assistance while managing computing resources effectively.
