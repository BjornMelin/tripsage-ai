# Flights MCP Server Guide

This document provides the comprehensive implementation guide and specification for the Flights MCP Server within the TripSage AI Travel Planning System.

## 1. Overview

The Flights MCP Server is a core component of TripSage, responsible for providing all flight-related functionalities, including searching for flight offers, retrieving offer details, managing bookings, and tracking prices. It acts as an abstraction layer over one or more flight data providers, with the primary integration being the Duffel API.

The server is implemented using **FastMCP 2.0** (JavaScript/Node.js version, as per original detailed docs, though a Python FastMCP 2.0 version would also align with general strategy if preferred for consistency) and exposes its functionalities as standardized MCP tools.

## 2. Architecture and Design Choices

* **Primary API Integration**: Duffel API.
  * **Rationale**: Duffel provides access to content from over 300 airlines, including NDC, GDS, and LCC channels, through a modern, developer-friendly API. Its transaction-based pricing model is suitable for TripSage.
* **MCP Framework**: FastMCP 2.0 (JavaScript/Node.js).
  * **Rationale**: Provides a standardized way to build MCP servers, ensuring compatibility with the TripSage ecosystem (OpenAI Agents SDK, Claude Desktop).
* **Caching**: Redis is used for caching search results, offer details, and other frequently accessed data to improve performance and reduce Duffel API call volume.
* **Data Transformation**: A dedicated transformer module (`duffel_transformer.js`) converts Duffel API responses into a standardized TripSage flight data model.
* **Error Handling**: Robust error handling with retries (exponential backoff) for API calls and clear error reporting to MCP clients.
* **Price History**: Integration with Supabase for storing historical pricing data for trend analysis and user recommendations.

## 3. Exposed MCP Tools

The Flights MCP Server exposes the following tools:

### 3.1. `search_flights`

* **Description**: Searches for one-way or round-trip flight offers.
* **Input Schema (Zod for JS FastMCP, or Pydantic for Python FastMCP)**:

    ```javascript
    // Zod schema example (for JS FastMCP)
    z.object({
      origin: z.string().length(3).describe("Origin airport IATA code (e.g., 'LAX')"),
      destination: z.string().length(3).describe("Destination airport IATA code (e.g., 'JFK')"),
      departure_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).describe("Departure date (YYYY-MM-DD)"),
      return_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional().describe("Return date (YYYY-MM-DD)"),
      adults: z.number().int().min(1).default(1).describe("Number of adult passengers"),
      children: z.number().int().min(0).default(0).describe("Number of child passengers (2-11 years)"),
      infants: z.number().int().min(0).default(0).describe("Number of infant passengers (<2 years)"),
      cabin_class: z.enum(["economy", "premium_economy", "business", "first"]).default("economy"),
      max_connections: z.number().int().min(0).nullish().describe("Max connections per slice"),
      airline_codes: z.array(z.string()).default([]).describe("Preferred airline IATA codes"),
      currency: z.string().length(3).default("USD").describe("Currency for prices (ISO 4217)")
    })
    ```

* **Output**: Formatted search results including a list of flight offers, airline details, and metadata (count, lowest price). (See `duffel_transformer.js` for detailed output structure).
* **Handler Logic**:
    1. Validates input parameters.
    2. Generates a cache key based on input.
    3. Checks Redis cache for existing results. Returns cached data if fresh.
    4. If cache miss, constructs payload for Duffel's Offer Request API.
    5. Calls `duffelService.createOfferRequest()` then `duffelService.getOffers()`.
    6. Transforms Duffel API response using `formatSearchResults` from `duffel_transformer.js`.
    7. Caches the transformed results in Redis with an appropriate TTL (e.g., 5-10 minutes).
    8. Returns the results.

### 3.2. `search_multi_city`

* **Description**: Searches for multi-city flight itineraries.
* **Input Schema**:

    ```javascript
    z.object({
      slices: z.array(z.object({
        origin: z.string().length(3),
        destination: z.string().length(3),
        departure_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/)
      })).min(2).describe("List of flight slices for the multi-city trip"),
      // ... (passengers, cabin_class, etc. similar to search_flights)
    })
    ```

* **Output**: Similar to `search_flights`, adapted for multi-city structure.
* **Handler Logic**: Similar to `search_flights`, but constructs a multi-slice Offer Request.

### 3.3. `get_offer_details`

* **Description**: Retrieves detailed information for a specific flight offer, including fare rules.
* **Input Schema**:

    ```javascript
    z.object({
      offer_id: z.string().describe("The Duffel offer ID"),
      currency: z.string().length(3).default("USD")
    })
    ```

* **Output**: Detailed offer information, including segment details, baggage allowance, and fare conditions. (See `duffel_transformer.js` `formatOfferDetails`).
* **Handler Logic**:
    1. Validates input.
    2. Generates cache key. Checks cache.
    3. Calls `duffelService.getOffer()` and `duffelService.getFareRules()`.
    4. Transforms and combines results.
    5. Caches and returns data. TTL typically shorter (e.g., 2-5 minutes).

### 3.4. `get_fare_rules` (Potentially merged into `get_offer_details` or kept separate)

* **Description**: Retrieves fare rules and conditions for a specific offer.
* **Input Schema**: `z.object({ offer_id: z.string() })`
* **Output**: Structured fare rule information.
* **Handler Logic**: Calls `duffelService.getFareRules()`, caches, and returns.

### 3.5. `create_order`

* **Description**: Creates a flight booking from a selected offer.
* **Input Schema**:

    ```javascript
    z.object({
      selected_offers: z.array(z.string()).min(1).describe("List of offer IDs to book"),
      passengers: z.array(z.object({ // Detailed passenger schema
        id: z.string().optional(),
        given_name: z.string(),
        family_name: z.string(),
        gender: z.enum(["m", "f"]),
        born_on: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
        // ... other required passenger fields by Duffel
      })),
      payments: z.array(z.object({
        type: z.enum(["balance", "arc_bsp_cash" /* ... other payment types */]),
        currency: z.string().length(3),
        amount: z.string() // Duffel expects amount as string
      })),
      // ... other necessary booking fields like contact info
    })
    ```

* **Output**: Order confirmation details from Duffel.
* **Handler Logic**:
    1. Validates input.
    2. Calls `duffelService.createOrder()`.
    3. **Important**: Does NOT cache booking responses.
    4. Returns Duffel's order confirmation.
    5. (Agent-level logic will then store this booking in Supabase and the Knowledge Graph).

### 3.6. `get_order`

* **Description**: Retrieves details of an existing booking.
* **Input Schema**: `z.object({ order_id: z.string() })`
* **Output**: Detailed order information.
* **Handler Logic**: Calls `duffelService.getOrder()`. Does NOT cache.

### 3.7. `track_prices`

* **Description**: Sets up price tracking for a specific flight route or offer.
* **Input Schema**:

    ```javascript
    z.object({
      origin: z.string().length(3),
      destination: z.string().length(3),
      departure_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
      return_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
      // ... passenger details, cabin_class ...
      user_id: z.string().optional().describe("User ID for associating the tracking"),
      email: z.string().email().optional().describe("Email for notifications"),
      threshold_percentage: z.number().min(0).default(5).describe("Min change % to notify")
    })
    ```

* **Output**: Confirmation of tracking setup, including tracking ID.
* **Handler Logic**:
    1. Validates input.
    2. Stores tracking request in Supabase (`price_tracking` table).
    3. Optionally performs an initial search to establish a baseline price and stores it in `price_history`.
    4. (A separate scheduled worker/job, not part of this MCP tool, would periodically re-check prices and send notifications).

## 4. Duffel API Service (`duffel_service.js` or `.ts`)

This service encapsulates all direct interactions with the Duffel API.

```javascript
// src/mcp/flights/services/duffel_service.js (Illustrative)
const { Duffel } = require("@duffel/api");
const config = require("../config"); // MCP server config
const logger = require("../utils/logger");
const { retryAxios } = require("../utils/error_handling"); // Assumes error_handling utility

class DuffelService {
  constructor() {
    if (!config.DUFFEL_API_KEY) {
      throw new Error("DUFFEL_API_KEY is not configured.");
    }
    this.duffel = new Duffel({
      token: config.DUFFEL_API_KEY,
      // apiVersion: config.DUFFEL_API_VERSION, // Handled by Duffel SDK or headers
    });
    // Default headers for Duffel API version
    this.defaultHeaders = { 'Duffel-Version': config.DUFFEL_API_VERSION };
  }

  async createOfferRequest(params) {
    try {
      logger.debug("Duffel: Creating offer request", { params });
      // Duffel SDK might handle retries, or use retryAxios if wrapping raw HTTP calls
      const offerRequest = await this.duffel.offerRequests.create(params, { headers: this.defaultHeaders });
      logger.info("Duffel: Offer request created", { id: offerRequest.data.id });
      return offerRequest.data; // Return data part
    } catch (error) {
      logger.error("Duffel: Error creating offer request", { error: error.message, details: error.response?.data });
      throw this._formatDuffelError(error, "Failed to create offer request");
    }
  }

  async getOffers(offerRequestId, limit = 50) {
    try {
      logger.debug("Duffel: Getting offers", { offerRequestId, limit });
      const offers = await this.duffel.offers.list({ offer_request_id: offerRequestId, limit }, { headers: this.defaultHeaders });
      logger.info(`Duffel: Retrieved ${offers.data.length} offers`);
      return offers.data;
    } catch (error) {
      logger.error("Duffel: Error getting offers", { error: error.message, details: error.response?.data });
      throw this._formatDuffelError(error, "Failed to get offers");
    }
  }

  async getOffer(offerId) {
    // ... similar implementation ...
  }

  async getFareRules(offerId) { // Duffel calls this "Offer Conditions"
    try {
        logger.debug("Duffel: Getting offer conditions (fare rules)", { offerId });
        // The Duffel SDK might have a specific method, or it might be part of the offer object.
        // This is a conceptual mapping. The actual Duffel SDK call might be different.
        // For example, conditions might be part of the offer object itself or a related call.
        // If it's part of the offer, this method might not call Duffel directly but extract from a full offer object.
        // Let's assume it's part of the offer details for now or a separate call if available.
        // This is a placeholder; actual implementation depends on Duffel SDK structure for fare rules.
        const offer = await this.duffel.offers.get(offerId, { headers: this.defaultHeaders });
        logger.info("Duffel: Offer conditions retrieved");
        return offer.data.conditions; // Assuming conditions are part of the offer data
    } catch (error) {
        logger.error("Duffel: Error getting offer conditions", { error: error.message, details: error.response?.data });
        throw this._formatDuffelError(error, "Failed to get offer conditions");
    }
  }
  
  async createOrder(params) {
    // ... similar implementation ...
  }

  async getOrder(orderId) {
    // ... similar implementation ...
  }
  
  _formatDuffelError(error, defaultMessage) {
    if (error.errors) { // Duffel SDK specific error structure
      const messages = error.errors.map(e => e.message || e.title).join('; ');
      return new Error(messages || defaultMessage);
    }
    if (error.response && error.response.data && error.response.data.errors) { // Axios-like error
      const messages = error.response.data.errors.map(e => e.message || e.title).join('; ');
      return new Error(messages || defaultMessage);
    }
    return new Error(error.message || defaultMessage);
  }
}

module.exports = DuffelService;
```

## 5. Data Transformation (`duffel_transformer.js` or `.ts`)

This module is responsible for converting raw Duffel API responses into the standardized TripSage flight data models.

Key transformation functions:

* `formatSearchResults(duffelOffers, currency)`: Transforms a list of Duffel offers.
* `formatOffer(duffelOffer, airlinesRef, currency)`: Formats a single offer.
* `formatSlice(duffelSlice, airlinesRef)`: Formats a flight slice (journey leg).
* `formatSegment(duffelSegment, airlinesRef)`: Formats an individual flight segment.
* `extractAirlines(duffelOffers)`: Creates a reference list of airlines.
* `formatOfferDetails(duffelOffer, duffelFareRules, currency)`: Combines offer and fare rule data.

(Refer to `docs/implementation/flight_search_booking_implementation.md` for an example of the Python data models these transformers would map to. The JS/TS transformer would produce a similar structure.)

## 6. Caching (`cache.js` or `.ts`)

* **Client**: `ioredis` for Node.js.
* **Key Generation**: Standardized functions like `generateSearchCacheKey(params)` and `generateOfferCacheKey(offerId)`.
* **TTL Strategy**:
  * Search Results: 5-10 minutes (configurable via `config.CACHE_TTL.SEARCH_RESULTS`).
  * Offer Details: 2-5 minutes (configurable via `config.CACHE_TTL.OFFER_DETAILS`).
  * Fare Rules: 60 minutes (configurable via `config.CACHE_TTL.FARE_RULES`).
  * Static data (Airlines, Airports): 24 hours.
* **Functions**: `cacheResults(key, data, ttl)`, `getCachedResults(key)`.

## 7. Python Client (`client.py`)

A Python client (`src/mcp/flights/client.py`) allows TripSage's Python backend and agents to interact with the (JavaScript/Node.js) Flights MCP Server. This client uses `BaseMCPClient` from the MCP Abstraction Layer.

```python
# src/mcp/flights/client.py
from typing import Dict, Any, List, Optional, Union
from datetime import date
from pydantic import BaseModel, Field, field_validator, ValidationInfo # Pydantic v2
from agents import function_tool # Assuming this is from OpenAI Agents SDK or similar
from ..base_mcp_client import BaseMCPClient # Part of your MCP Abstraction Layer
from ...utils.logging import get_module_logger
from ...utils.config import settings # Centralized settings

logger = get_module_logger(__name__)

# Pydantic models for input validation (matching Zod schemas on JS server)
class FlightSearchParams(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    departure_date: date # Pydantic will parse "YYYY-MM-DD" string to date object
    return_date: Optional[date] = None
    adults: int = Field(1, ge=1)
    children: int = Field(0, ge=0)
    infants: int = Field(0, ge=0)
    cabin_class: str = Field("economy", pattern="^(economy|premium_economy|business|first)$")
    max_connections: Optional[int] = Field(None, ge=0)
    airline_codes: List[str] = Field(default_factory=list)
    currency: str = Field("USD", min_length=3, max_length=3)

    @field_validator("origin", "destination")
    def validate_airport_code(cls, v: str) -> str:
        return v.upper()

    @field_validator('return_date')
    def validate_return_date(cls, v: Optional[date], info: ValidationInfo) -> Optional[date]:
        # Using info.data for Pydantic v2
        if v and 'departure_date' in info.data and info.data['departure_date'] and v < info.data['departure_date']:
            raise ValueError('Return date must be after departure date.')
        return v

class OfferDetailsParams(BaseModel):
    offer_id: str
    currency: str = Field("USD", min_length=3, max_length=3)

class PriceTrackingParams(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    departure_date: date
    return_date: Optional[date] = None
    # ... (adults, children, infants, cabin_class as in FlightSearchParams) ...
    adults: int = Field(1, ge=1)
    cabin_class: str = Field("economy", pattern="^(economy|premium_economy|business|first)$")
    frequency: str = Field("daily", pattern="^(hourly|daily|weekly)$")
    notify_when: str = Field("price_decrease", pattern="^(any_change|price_decrease|price_increase|availability_change)$")
    threshold_percentage: float = Field(5.0, ge=0)
    user_id: Optional[str] = None
    email: Optional[str] = None # Pydantic has EmailStr for email validation

class FlightsMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_name="flights", # Matches key in settings.mcp_servers
            endpoint=settings.mcp_servers.flights.endpoint,
            api_key=settings.mcp_servers.flights.api_key.get_secret_value() if settings.mcp_servers.flights.api_key else None
        )
        logger.info("Initialized Flights MCP Client")

    @function_tool
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: Union[str, date], # Allow string for flexibility, Pydantic handles parsing
        return_date: Optional[Union[str, date]] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "economy",
        max_connections: Optional[int] = None,
        airline_codes: Optional[List[str]] = None,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """Searches for flights using the Flights MCP server."""
        # Validate with Pydantic model
        validated_params = FlightSearchParams(
            origin=origin, destination=destination, departure_date=departure_date,
            return_date=return_date, adults=adults, children=children, infants=infants,
            cabin_class=cabin_class, max_connections=max_connections,
            airline_codes=airline_codes or [], currency=currency
        )
        # Convert Pydantic model to dict for sending, ensuring dates are ISO strings
        payload = validated_params.model_dump(mode="json")
        return await self.invoke_tool("search_flights", payload)

    @function_tool
    async def get_offer_details(self, offer_id: str, currency: str = "USD") -> Dict[str, Any]:
        """Retrieves detailed information for a specific flight offer."""
        validated_params = OfferDetailsParams(offer_id=offer_id, currency=currency)
        return await self.invoke_tool("get_offer_details", validated_params.model_dump(mode="json"))

    @function_tool
    async def track_prices(
        self,
        origin: str,
        destination: str,
        departure_date: Union[str, date],
        return_date: Optional[Union[str, date]] = None,
        adults: int = 1,
        cabin_class: str = "economy",
        frequency: str = "daily",
        notify_when: str = "price_decrease",
        threshold_percentage: float = 5.0,
        user_id: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sets up price tracking for a flight route."""
        validated_params = PriceTrackingParams(
            origin=origin, destination=destination, departure_date=departure_date,
            return_date=return_date, adults=adults, cabin_class=cabin_class,
            frequency=frequency, notify_when=notify_when,
            threshold_percentage=threshold_percentage, user_id=user_id, email=email
        )
        return await self.invoke_tool("track_prices", validated_params.model_dump(mode="json"))

    # ... Implement client methods for other tools like search_multi_city, create_order, get_order ...
```

## 8. Integration with Agent Architecture

The `FlightsMCPClient` methods, decorated with `@function_tool`, are registered with the Travel Planning Agent and other relevant agents. This allows agents to naturally call these functions when flight-related information or actions are needed.

Example agent tool usage (conceptual):

```python
# In TravelAgent or a specialized FlightAgent
# ...
# tools=[
#    self.flights_mcp_client.search_flights,
#    self.flights_mcp_client.get_offer_details,
#    # ...
# ]
# ...
# During agent run, if it decides to search flights:
# tool_call_result = await self.flights_mcp_client.search_flights(
#     origin="SFO", destination="LHR", departure_date="2025-12-01"
# )
```

## 9. Deployment

* **Dockerfile**: A Node.js based Dockerfile for the Flights MCP Server.
* **Docker Compose**: Included in the main `docker-compose.yml` for local development, linking with Redis.
* **Kubernetes**: Manifests for deploying to staging/production Kubernetes clusters.
* **Environment Variables**: `DUFFEL_API_KEY`, `REDIS_URL`, `PORT`, `LOG_LEVEL` are critical.
* **Health Check**: Implement a `/health` endpoint in the FastMCP server for Kubernetes liveness/readiness probes.

## 10. Testing

* **Unit Tests**: For `duffel_service.js`, `duffel_transformer.js`, and individual tool handlers. Mock Duffel API responses.
* **Integration Tests**: Test the MCP server by making HTTP calls to its tool endpoints with a mock Duffel service.
* **Python Client Tests**: Unit test `FlightsMCPClient` by mocking `invoke_tool`.
* **End-to-End Tests**: (Limited due to external API dependency) Test basic search functionality against Duffel's test environment if feasible during CI, or as part of manual QA.

## 11. Monitoring and Logging

* **Logging**: Use a structured logger (e.g., Winston for Node.js) to log requests, responses, errors, and cache interactions.
* **Metrics**: Expose Prometheus metrics for request counts, latencies, error rates, cache hit/miss ratios.
* **Alerts**: Set up alerts for high error rates from Duffel API, high MCP server error rates, or cache failures.

This detailed guide provides a solid foundation for implementing the Flights MCP Server.
