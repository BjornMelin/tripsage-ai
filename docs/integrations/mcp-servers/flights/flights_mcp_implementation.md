# Flights MCP Server Implementation

This document provides the detailed implementation specification for the Flights MCP Server in TripSage.

## Overview

The Flights MCP Server provides comprehensive flight search, booking, and management capabilities for the TripSage platform. It integrates with the Duffel API to access content from more than 300 airlines through a single platform, including NDC, GDS, and LCC distribution channels.

## MCP Server Architecture

For TripSage, we're implementing a flight search MCP server using FastMCP 2.0 to ensure consistency with other MCP implementations in the system. This approach provides a standardized solution that ensures compatibility with both Claude Desktop and OpenAI Agents SDK.

The flight MCP server follows our standard FastMCP 2.0 architecture pattern:

- Server definition with metadata (name, version, description)
- Tool definitions with TypeScript schema validation
- Clean separation between API integration and MCP interface
- Support for both stdio and HTTP transport mechanisms

## MCP Tools Exposed

```typescript
// index.ts
import { FastMCP } from "fastmcp";
import {
  searchFlights,
  searchMultiCity,
  getOfferDetails,
  getFareRules,
  createOrder,
  getOrder,
  trackPrices,
} from "./tools";

// Create MCP server
const server = new FastMCP({
  name: "flights-mcp",
  version: "1.0.0",
  description: "Flights MCP Server for flight search and booking",
});

// Register tools
server.registerTool(searchFlights);
server.registerTool(searchMultiCity);
server.registerTool(getOfferDetails);
server.registerTool(getFareRules);
server.registerTool(createOrder);
server.registerTool(getOrder);
server.registerTool(trackPrices);

// Start the server
server.start();
```

Tool definitions:

```typescript
// tools/search_flights.ts
import { z } from "zod";
import { createTool } from "fastmcp";
import { DuffelService } from "../services/duffel_service";
import { formatSearchResults } from "../transformers/duffel_transformer";
import { cacheResults } from "../utils/cache";

export const searchFlights = createTool({
  name: "search_flights",
  description: "Search for flights between origin and destination",
  input: z.object({
    origin: z
      .string()
      .min(3)
      .max(3)
      .describe("Origin airport code (e.g., 'LAX')"),
    destination: z
      .string()
      .min(3)
      .max(3)
      .describe("Destination airport code (e.g., 'JFK')"),
    departure_date: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/)
      .describe("Departure date in YYYY-MM-DD format"),
    return_date: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/)
      .optional()
      .describe("Return date in YYYY-MM-DD format for round trips"),
    adults: z
      .number()
      .int()
      .min(1)
      .default(1)
      .describe("Number of adult passengers"),
    children: z
      .number()
      .int()
      .min(0)
      .default(0)
      .describe("Number of child passengers (2-11 years)"),
    infants: z
      .number()
      .int()
      .min(0)
      .default(0)
      .describe("Number of infant passengers (<2 years)"),
    cabin_class: z
      .enum(["economy", "premium_economy", "business", "first"])
      .default("economy")
      .describe("Preferred cabin class"),
    max_connections: z
      .number()
      .int()
      .min(0)
      .nullable()
      .default(null)
      .describe("Maximum number of connections per slice"),
    airline_codes: z
      .array(z.string())
      .default([])
      .describe("Limit results to specific airlines (IATA codes)"),
    currency: z
      .string()
      .min(3)
      .max(3)
      .default("USD")
      .describe("Currency for prices (ISO 4217 code)"),
  }),
  handler: async ({ input, context }) => {
    try {
      // Generate cache key based on search parameters
      const cacheKey = `flights_search:${JSON.stringify(input)}`;

      // Check cache first
      const cachedResults = await context.cache.get(cacheKey);
      if (cachedResults) {
        return cachedResults;
      }

      // Initialize Duffel service
      const duffelService = new DuffelService();

      // Create slices array for request
      const slices = [];

      // Add outbound flight
      slices.push({
        origin: input.origin,
        destination: input.destination,
        departure_date: input.departure_date,
      });

      // Add return flight if return_date is provided
      if (input.return_date) {
        slices.push({
          origin: input.destination,
          destination: input.origin,
          departure_date: input.return_date,
        });
      }

      // Create passengers array
      const passengers = [];

      // Add adult passengers
      for (let i = 0; i < input.adults; i++) {
        passengers.push({ type: "adult" });
      }

      // Add child passengers
      for (let i = 0; i < input.children; i++) {
        passengers.push({ type: "child" });
      }

      // Add infant passengers
      for (let i = 0; i < input.infants; i++) {
        passengers.push({ type: "infant_without_seat" });
      }

      // Build request payload
      const payload = {
        slices,
        passengers,
        cabin_class: input.cabin_class,
        return_offers: true,
      };

      // Add optional parameters
      if (input.max_connections !== null) {
        payload.max_connections = input.max_connections;
      }

      if (input.airline_codes.length > 0) {
        payload.airline_iata_codes = input.airline_codes;
      }

      // Make API request
      const offerRequest = await duffelService.createOfferRequest(payload);
      const offers = await duffelService.getOffers(offerRequest.id);

      // Transform and format results
      const results = formatSearchResults(offers, input.currency);

      // Cache results
      await cacheResults(cacheKey, results, 300); // Cache for 5 minutes

      return results;
    } catch (error) {
      throw new Error(`Failed to search flights: ${error.message}`);
    }
  },
});
```

## API Integrations

### Primary: Duffel API

- **Key Endpoints**:

  - `/air/offer_requests` - Create flight search requests
  - `/air/offers` - Get flight offers
  - `/air/orders` - Create and manage bookings
  - `/air/seat_maps` - Get seat maps for flights
  - `/air/payment_intents` - Process payments

- **Authentication**:

  - Bearer token authentication with API key
  - API key is sent in the Authorization header
  - Version header (`Duffel-Version`) required on all requests

- **Rate Limits**:
  - Limit varies by subscription tier
  - Default is 10 requests per second

### Secondary: Cache & Price Tracking

- **In-Memory/Redis Cache**:

  - Caches search results to reduce API calls
  - Expires after configurable TTL (time-to-live)

- **Supabase Database**:
  - Stores historical pricing data
  - Enables price trend analysis and alerts

## Integration with Agent Architecture

### OpenAI Agents SDK Integration

To integrate the Flights MCP Server with the OpenAI Agents SDK, we've added it to our standard MCP server configuration:

```javascript
// mcp_servers/openai_agents_config.js
module.exports = {
  mcpServers: {
    // Existing MCP servers...

    // Flights MCP Server
    flights: {
      command: "node",
      args: ["./src/mcp/flights/server.js"],
      env: {
        DUFFEL_API_KEY: "${DUFFEL_API_KEY}",
        DUFFEL_API_VERSION: "2023-06-02",
        REDIS_URL: "${REDIS_URL}",
      },
    },
  },
};
```

We then use our established `MCPServerManager` class to initialize and manage the server:

```python
# src/mcp/flights/client.py
from agents import function_tool
from src.mcp.base_mcp_client import BaseMCPClient
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class FlightsMCPClient(BaseMCPClient):
    """Client for the Flights MCP Server."""

    def __init__(self):
        """Initialize the Flights MCP client."""
        super().__init__(server_name="flights")
        logger.info("Initialized Flights MCP Client")

    @function_tool
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "economy",
        max_connections: int = None,
        airline_codes: list = None,
        currency: str = "USD"
    ) -> dict:
        """Search for flights between origin and destination.

        Args:
            origin: Origin airport code (e.g., 'LAX')
            destination: Destination airport code (e.g., 'JFK')
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format for round trips
            adults: Number of adult passengers
            children: Number of child passengers (2-11 years)
            infants: Number of infant passengers (<2 years)
            cabin_class: Preferred cabin class
            max_connections: Maximum number of connections per slice
            airline_codes: Limit results to specific airlines (IATA codes)
            currency: Currency for prices (ISO 4217 code)

        Returns:
            Dictionary with search results
        """
        try:
            # Call the MCP server
            server = await self.get_server()
            result = await server.invoke_tool(
                "search_flights",
                {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "adults": adults,
                    "children": children,
                    "infants": infants,
                    "cabin_class": cabin_class,
                    "max_connections": max_connections,
                    "airline_codes": airline_codes or [],
                    "currency": currency
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error searching flights: {str(e)}")
            return {
                "error": f"Failed to search flights: {str(e)}",
                "origin": origin,
                "destination": destination
            }

    # Additional methods for other MCP tools...
```

### Claude Desktop Integration

For Claude Desktop integration, we add the Flights MCP Server to the Claude Desktop configuration:

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "flights": {
      "command": "node",
      "args": ["./src/mcp/flights/server.js"],
      "env": {
        "DUFFEL_API_KEY": "${DUFFEL_API_KEY}",
        "DUFFEL_API_VERSION": "2023-06-02"
      }
    }
  }
}
```

## File Structure

```plaintext
src/
  mcp/
    flights/
      __init__.py                  # Package initialization
      client.py                    # Python client for the MCP server
      config.py                    # Client configuration settings
      server.js                    # FastMCP 2.0 server
      tools/                       # Tool implementations
        index.ts                   # Tool exports
        search_flights.ts          # Flight search tool
        search_multi_city.ts       # Multi-city search tool
        get_offer_details.ts       # Offer details tool
        get_fare_rules.ts          # Fare rules tool
        create_order.ts            # Order creation tool
        get_order.ts               # Order retrieval tool
        track_prices.ts            # Price tracking tool
      services/                    # API services
        duffel_service.ts          # Duffel API client
      transformers/                # Data transformers
        duffel_transformer.ts      # Transforms Duffel API responses
      utils/                       # Utility functions
        cache.ts                   # Caching implementation
        error_handling.ts          # Error handling utilities
        validation.ts              # Input validation utilities
      tests/
        __init__.py                # Test package initialization
        test_client.py             # Tests for the client
        fixtures/                  # Test fixtures
```

## Test Implementation

Here's an example test for the Flights MCP client:

```python
# src/mcp/flights/tests/test_client.py
import pytest
from unittest.mock import AsyncMock, patch
from datetime import date, timedelta

from src.mcp.flights.client import FlightsMCPClient

@pytest.fixture
def flight_client():
    """Create a flight client for testing."""
    return FlightsMCPClient()

@pytest.fixture
def mock_server():
    """Mock MCP server."""
    server_mock = AsyncMock()
    server_mock.invoke_tool = AsyncMock()
    return server_mock

@pytest.mark.asyncio
async def test_search_flights(flight_client, mock_server):
    """Test search_flights method."""
    # Setup mock
    with patch.object(flight_client, 'get_server', return_value=mock_server):
        # Create mock response
        mock_response = {
            "offers": [
                {
                    "id": "off_00001",
                    "price": {
                        "amount": 299.99,
                        "currency": "USD"
                    },
                    "airline": {
                        "code": "AA",
                        "name": "American Airlines"
                    }
                }
            ]
        }

        mock_server.invoke_tool.return_value = mock_response

        # Get tomorrow's date
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        next_week = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")

        # Call method
        result = await flight_client.search_flights(
            origin="LAX",
            destination="JFK",
            departure_date=tomorrow,
            return_date=next_week
        )

        # Assertions
        assert result == mock_response
        mock_server.invoke_tool.assert_called_once()
        args, kwargs = mock_server.invoke_tool.call_args

        # Verify tool name
        assert args[0] == "search_flights"

        # Verify parameters
        assert args[1]["origin"] == "LAX"
        assert args[1]["destination"] == "JFK"
        assert args[1]["departure_date"] == tomorrow
        assert args[1]["return_date"] == next_week
```

## Deployment Strategy

The Flights MCP Server will be containerized using Docker and deployed as a standalone service. This allows for independent scaling and updates:

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

ENV NODE_ENV=production
ENV PORT=3002

EXPOSE 3002

CMD ["node", "src/mcp/flights/server.js"]
```

### Resource Requirements

- **CPU**: Moderate (1-2 vCPU recommended, scales with traffic)
- **Memory**: 1GB minimum, 2GB recommended
- **Storage**: Minimal (primarily for code and logs)
- **Network**: Moderate to high (API calls to Duffel)

### Monitoring

- **Health Endpoint**: `/health` endpoint for monitoring
- **Metrics**: Request count, response time, error rate, cache hit rate
- **Logging**: Structured logs with request/response details
- **Alerts**: Set up for high error rates, slow responses, or payment failures

## Integration with Agent Architecture - Flights

The Flights MCP Server is integrated with the TripSage agent architecture to provide flight search and booking capabilities. The agent uses the following tools:

### Agent Integration

The Flights MCP client is integrated into the TripSage agent architecture to provide flight search capabilities:

```python
# src/agents/travel_agent.py
from src.mcp.flights.client import FlightsMCPClient
from src.mcp.time.client import TimeMCPClient
from src.mcp.openai_agents_integration import create_agent_with_mcp_servers

async def create_travel_agent():
    """Create a travel agent with flight search capabilities."""
    # Create MCP clients
    flights_client = FlightsMCPClient()
    time_client = TimeMCPClient()

    # Create agent with MCP servers
    agent = await create_agent_with_mcp_servers(
        name="TripSage Travel Agent",
        instructions="""You are a travel planning assistant that helps users find flights,
        accommodations, and activities. Use the appropriate tools to search for flights,
        convert time between timezones, and provide comprehensive travel plans.""",
        server_names=["flights", "time"],
        tools=[
            flights_client.search_flights,
            flights_client.search_multi_city,
            time_client.get_current_time,
            time_client.convert_time
        ],
        model="gpt-4o"
    )

    return agent
```

## Caching Strategy

- **Search Results**: Cache for 5-15 minutes depending on search popularity
- **Offer Details**: Cache for 2 minutes due to potential price changes
- **Flight Schedules**: Cache for longer periods (4-24 hours)
- **Price Tracking Data**: Store in database for long-term analysis
- **Use Redis** for distributed caching in production environments

## Error Handling

- **Rate Limiting**: Implement exponential backoff for API rate limit errors
- **Offer Staleness**: Special handling for stale offers with clear user feedback
- **Payment Failures**: Detailed error handling for payment issues
- **Network Timeouts**: Retry logic for network failures

## Performance Optimization

- **Parallel Processing**: Fetch offers from multiple airlines simultaneously
- **Batch Updates**: Group price tracking checks for efficiency
- **Response Compression**: Use gzip/brotli for network efficiency
- **Selective Fields**: Only request needed fields from Duffel API

## Security

- **API Key Management**: Secure storage and rotation of Duffel API keys
- **Payment Information**: Proper handling of sensitive payment data
- **User Data**: Secure storage of passenger information
- **Input Validation**: Thorough validation of all user inputs

## Conclusion

The Flights MCP Server provides a robust and standardized interface for flight search and booking operations in TripSage. By leveraging FastMCP 2.0 and integrating with the Duffel API, it offers comprehensive flight shopping capabilities while maintaining consistency with other MCP implementations in the system and compatibility with both OpenAI Agents SDK and Claude Desktop environments.
