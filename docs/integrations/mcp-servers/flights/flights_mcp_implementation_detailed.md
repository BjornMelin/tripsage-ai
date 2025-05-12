# Flights MCP Server Detailed Implementation Guide

This document provides a comprehensive implementation guide for the Flights MCP Server in the TripSage project, including code examples, integration details, and deployment strategies.

## 1. Overview

The Flights MCP Server is a critical component of the TripSage platform, providing comprehensive flight search, booking, and management capabilities. It integrates with the Duffel API to access content from more than 300 airlines through a single platform, leveraging New Distribution Capability (NDC), Global Distribution Systems (GDS), and Low-Cost Carrier (LCC) distribution channels.

## 2. Prerequisite Setup

### 2.1 Duffel API Registration

Before implementation, you need to obtain API credentials from Duffel:

1. Register at [Duffel.com](https://duffel.com)
2. Complete the API access request form
3. Receive and securely store your API key
4. Review API documentation at [https://duffel.com/docs/api](https://duffel.com/docs/api)

### 2.2 Required Environment Variables

```bash
# Add to .env
DUFFEL_API_KEY=duffel_test_your_api_key
DUFFEL_API_VERSION=2023-06-02
REDIS_URL=redis://localhost:6379
NODE_ENV=development
```

## 3. Project Structure

Create the following directory structure:

```plaintext
src/
  mcp/
    flights/
      __init__.py                  # Package initialization
      client.py                    # Python client for the MCP server
      config.py                    # Client configuration settings
      server.js                    # FastMCP 2.0 server
      tools/                       # Tool implementations
        index.js                   # Tool exports
        search_flights.js          # Flight search tool
        search_multi_city.js       # Multi-city search tool
        get_offer_details.js       # Offer details tool
        get_fare_rules.js          # Fare rules tool
        create_order.js            # Order creation tool
        get_order.js               # Order retrieval tool
        track_prices.js            # Price tracking tool
      services/                    # API services
        duffel_service.js          # Duffel API client
      transformers/                # Data transformers
        duffel_transformer.js      # Transforms Duffel API responses
      utils/                       # Utility functions
        cache.js                   # Caching implementation
        error_handling.js          # Error handling utilities
        validation.js              # Input validation utilities
      tests/
        __init__.py                # Test package initialization
        test_client.py             # Tests for the client
        fixtures/                  # Test fixtures
```

## 4. FastMCP 2.0 Server Implementation

### 4.1 Package Initialization

```javascript
// src/mcp/flights/package.json
{
  "name": "flights-mcp",
  "version": "1.0.0",
  "description": "Flights MCP Server for TripSage",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js",
    "test": "jest"
  },
  "dependencies": {
    "@duffel/api": "^1.5.5",
    "axios": "^1.6.2",
    "dotenv": "^16.3.1",
    "fastmcp": "^2.0.0",
    "ioredis": "^5.3.2",
    "zod": "^3.22.4",
    "winston": "^3.11.0"
  },
  "devDependencies": {
    "jest": "^29.7.0",
    "nodemon": "^3.0.1"
  }
}
```

### 4.2 Server Configuration

```javascript
// src/mcp/flights/config.js
require("dotenv").config();

module.exports = {
  DUFFEL_API_KEY: process.env.DUFFEL_API_KEY,
  DUFFEL_API_VERSION: process.env.DUFFEL_API_VERSION || "2023-06-02",
  REDIS_URL: process.env.REDIS_URL || "redis://localhost:6379",
  PORT: process.env.PORT || 3002,
  NODE_ENV: process.env.NODE_ENV || "development",
  LOG_LEVEL: process.env.LOG_LEVEL || "info",

  // Cache settings
  CACHE_TTL: {
    SEARCH_RESULTS: 10 * 60, // 10 minutes
    OFFER_DETAILS: 5 * 60, // 5 minutes
    FARE_RULES: 60 * 60, // 60 minutes
    PASSENGER_TYPES: 24 * 60 * 60, // 24 hours
    AIRLINES: 24 * 60 * 60, // 24 hours
  },

  // Rate limiting (requests per minute)
  RATE_LIMITS: {
    DUFFEL_SEARCH: 120,
    DUFFEL_OFFERS: 240,
    DUFFEL_ORDERS: 60,
  },
};
```

### 4.3 Main Server Implementation

```javascript
// src/mcp/flights/server.js
const { FastMCP } = require("fastmcp");
const {
  searchFlights,
  searchMultiCity,
  getOfferDetails,
  getFareRules,
  createOrder,
  getOrder,
  trackPrices,
} = require("./tools");
const logger = require("./utils/logger");
const config = require("./config");

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
server.listen(config.PORT, () => {
  logger.info(`Flights MCP Server running on port ${config.PORT}`);
});

// Handle process termination
process.on("SIGINT", () => {
  logger.info("Shutting down Flights MCP Server");
  server.close();
  process.exit(0);
});
```

### 4.4 Logger Implementation

```javascript
// src/mcp/flights/utils/logger.js
const winston = require("winston");
const config = require("../config");

const logger = winston.createLogger({
  level: config.LOG_LEVEL,
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: { service: "flights-mcp" },
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      ),
    }),
    new winston.transports.File({
      filename: "logs/flights-mcp-error.log",
      level: "error",
    }),
    new winston.transports.File({
      filename: "logs/flights-mcp.log",
    }),
  ],
});

// Create logs directory if it doesn't exist
const fs = require("fs");
if (!fs.existsSync("logs")) {
  fs.mkdirSync("logs");
}

module.exports = logger;
```

## 5. Duffel API Service

### 5.1 Service Implementation

```javascript
// src/mcp/flights/services/duffel_service.js
const { Duffel } = require("@duffel/api");
const config = require("../config");
const logger = require("../utils/logger");
const { redisClient } = require("../utils/cache");

class DuffelService {
  constructor() {
    this.duffel = new Duffel({
      token: config.DUFFEL_API_KEY,
      apiVersion: config.DUFFEL_API_VERSION,
    });
  }

  async createOfferRequest(params) {
    try {
      logger.debug("Creating offer request", { params });
      const offerRequest = await this.duffel.offerRequests.create(params);
      logger.debug("Offer request created", { id: offerRequest.id });
      return offerRequest;
    } catch (error) {
      logger.error("Error creating offer request", { error: error.message });
      throw new Error(`Failed to create offer request: ${error.message}`);
    }
  }

  async getOffers(requestId) {
    try {
      logger.debug("Getting offers", { requestId });
      const { data: offers } = await this.duffel.offers.list({
        offer_request_id: requestId,
        limit: 50,
      });
      logger.debug("Offers retrieved", { count: offers.length });
      return offers;
    } catch (error) {
      logger.error("Error getting offers", { error: error.message });
      throw new Error(`Failed to get offers: ${error.message}`);
    }
  }

  async getOffer(offerId) {
    try {
      logger.debug("Getting offer details", { offerId });
      const offer = await this.duffel.offers.get(offerId);
      logger.debug("Offer details retrieved");
      return offer;
    } catch (error) {
      logger.error("Error getting offer details", { error: error.message });
      throw new Error(`Failed to get offer details: ${error.message}`);
    }
  }

  async getFareRules(offerId) {
    try {
      // Check cache first
      const cacheKey = `fare_rules:${offerId}`;
      const cachedRules = await redisClient.get(cacheKey);

      if (cachedRules) {
        logger.debug("Fare rules retrieved from cache", { offerId });
        return JSON.parse(cachedRules);
      }

      logger.debug("Getting fare rules", { offerId });
      const fareRules = await this.duffel.offerConditions.get(offerId);

      // Cache the result
      await redisClient.set(
        cacheKey,
        JSON.stringify(fareRules),
        "EX",
        config.CACHE_TTL.FARE_RULES
      );

      logger.debug("Fare rules retrieved and cached");
      return fareRules;
    } catch (error) {
      logger.error("Error getting fare rules", { error: error.message });
      throw new Error(`Failed to get fare rules: ${error.message}`);
    }
  }

  async createOrder(params) {
    try {
      logger.debug("Creating order", { offerId: params.selected_offers[0] });
      const order = await this.duffel.orders.create(params);
      logger.debug("Order created", { id: order.id });
      return order;
    } catch (error) {
      logger.error("Error creating order", { error: error.message });
      throw new Error(`Failed to create order: ${error.message}`);
    }
  }

  async getOrder(orderId) {
    try {
      logger.debug("Getting order", { orderId });
      const order = await this.duffel.orders.get(orderId);
      logger.debug("Order retrieved");
      return order;
    } catch (error) {
      logger.error("Error getting order", { error: error.message });
      throw new Error(`Failed to get order: ${error.message}`);
    }
  }

  async getAirlines() {
    try {
      // Check cache first
      const cacheKey = "airlines_list";
      const cachedAirlines = await redisClient.get(cacheKey);

      if (cachedAirlines) {
        logger.debug("Airlines retrieved from cache");
        return JSON.parse(cachedAirlines);
      }

      logger.debug("Getting airlines list");
      const { data: airlines } = await this.duffel.airlines.list();

      // Cache the result
      await redisClient.set(
        cacheKey,
        JSON.stringify(airlines),
        "EX",
        config.CACHE_TTL.AIRLINES
      );

      logger.debug("Airlines retrieved and cached", { count: airlines.length });
      return airlines;
    } catch (error) {
      logger.error("Error getting airlines", { error: error.message });
      throw new Error(`Failed to get airlines: ${error.message}`);
    }
  }

  async getAirportsNear(latitude, longitude, radius = 500) {
    try {
      logger.debug("Getting airports near location", {
        latitude,
        longitude,
        radius,
      });
      const { data: airports } = await this.duffel.airports.list({
        latitude,
        longitude,
        radius,
      });
      logger.debug("Nearby airports retrieved", { count: airports.length });
      return airports;
    } catch (error) {
      logger.error("Error getting nearby airports", { error: error.message });
      throw new Error(`Failed to get nearby airports: ${error.message}`);
    }
  }
}

module.exports = DuffelService;
```

### 5.2 Cache Implementation

```javascript
// src/mcp/flights/utils/cache.js
const Redis = require("ioredis");
const config = require("../config");
const logger = require("./logger");

// Create Redis client
const redisClient = new Redis(config.REDIS_URL, {
  retryStrategy: (times) => {
    const delay = Math.min(times * 50, 2000);
    return delay;
  },
});

redisClient.on("error", (err) => {
  logger.error("Redis error", { error: err.message });
});

redisClient.on("connect", () => {
  logger.info("Connected to Redis");
});

// Cache helper functions
async function cacheResults(key, data, ttlSeconds) {
  try {
    await redisClient.set(key, JSON.stringify(data), "EX", ttlSeconds);
    logger.debug("Cached data", { key, ttl: ttlSeconds });
    return true;
  } catch (error) {
    logger.error("Error caching data", { key, error: error.message });
    return false;
  }
}

async function getCachedResults(key) {
  try {
    const cachedData = await redisClient.get(key);
    if (cachedData) {
      logger.debug("Cache hit", { key });
      return JSON.parse(cachedData);
    }
    logger.debug("Cache miss", { key });
    return null;
  } catch (error) {
    logger.error("Error retrieving cached data", { key, error: error.message });
    return null;
  }
}

// Generate standardized cache keys
function generateSearchCacheKey(params) {
  const {
    origin,
    destination,
    departure_date,
    return_date,
    adults,
    children,
    infants,
    cabin_class,
  } = params;

  return `flights:search:${origin}-${destination}:${departure_date}${
    return_date ? `:${return_date}` : ""
  }:${adults}_${children}_${infants}:${cabin_class}`;
}

function generateOfferCacheKey(offerId) {
  return `flights:offer:${offerId}`;
}

module.exports = {
  redisClient,
  cacheResults,
  getCachedResults,
  generateSearchCacheKey,
  generateOfferCacheKey,
};
```

## 6. Tool Implementations

### 6.1 Search Flights Tool

```javascript
// src/mcp/flights/tools/search_flights.js
const { z } = require("zod");
const { createTool } = require("fastmcp");
const DuffelService = require("../services/duffel_service");
const {
  cacheResults,
  getCachedResults,
  generateSearchCacheKey,
} = require("../utils/cache");
const { formatSearchResults } = require("../transformers/duffel_transformer");
const config = require("../config");
const logger = require("../utils/logger");

const searchFlights = createTool({
  name: "search_flights",
  description: "Search for flights between origin and destination",

  input: z.object({
    origin: z.string().length(3).describe("Origin airport code (e.g., 'LAX')"),
    destination: z
      .string()
      .length(3)
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
      .nullish()
      .describe("Maximum number of connections per slice"),
    airline_codes: z
      .array(z.string())
      .default([])
      .describe("Limit results to specific airlines (IATA codes)"),
    currency: z
      .string()
      .length(3)
      .default("USD")
      .describe("Currency for prices (ISO 4217 code)"),
  }),

  handler: async ({ input, context }) => {
    try {
      await context.info(
        `Searching flights from ${input.origin} to ${input.destination}`
      );

      // Report initial progress
      await context.report_progress(0.1, "Starting flight search");

      // Generate cache key based on search parameters
      const cacheKey = generateSearchCacheKey(input);

      // Check cache first
      const cachedResults = await getCachedResults(cacheKey);
      if (cachedResults) {
        await context.info("Flight search results found in cache");
        return cachedResults;
      }

      // Initialize Duffel service
      const duffelService = new DuffelService();

      // Update progress
      await context.report_progress(0.2, "Preparing search request");

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
      if (
        input.max_connections !== null &&
        input.max_connections !== undefined
      ) {
        payload.max_connections = input.max_connections;
      }

      if (input.airline_codes.length > 0) {
        payload.airline_iata_codes = input.airline_codes;
      }

      // Update progress
      await context.report_progress(0.3, "Submitting flight search request");

      // Make API request
      const offerRequest = await duffelService.createOfferRequest(payload);

      // Update progress
      await context.report_progress(0.6, "Processing search results");

      const offers = await duffelService.getOffers(offerRequest.id);

      // Update progress
      await context.report_progress(0.8, "Formatting results");

      // Transform and format results
      const results = formatSearchResults(offers, input.currency);

      // Update progress
      await context.report_progress(0.9, "Caching results");

      // Cache results
      await cacheResults(cacheKey, results, config.CACHE_TTL.SEARCH_RESULTS);

      // Complete progress
      await context.report_progress(1.0, "Flight search completed");

      await context.info(`Found ${results.offers.length} flight options`);

      return results;
    } catch (error) {
      await context.error(`Flight search error: ${error.message}`);
      throw new Error(`Failed to search flights: ${error.message}`);
    }
  },
});

module.exports = searchFlights;
```

### 6.2 Get Offer Details Tool

```javascript
// src/mcp/flights/tools/get_offer_details.js
const { z } = require("zod");
const { createTool } = require("fastmcp");
const DuffelService = require("../services/duffel_service");
const {
  cacheResults,
  getCachedResults,
  generateOfferCacheKey,
} = require("../utils/cache");
const { formatOfferDetails } = require("../transformers/duffel_transformer");
const config = require("../config");
const logger = require("../utils/logger");

const getOfferDetails = createTool({
  name: "get_offer_details",
  description: "Get detailed information for a specific flight offer",

  input: z.object({
    offer_id: z
      .string()
      .describe("The ID of the offer to retrieve details for"),
    currency: z
      .string()
      .length(3)
      .default("USD")
      .describe("Currency for prices (ISO 4217 code)"),
  }),

  handler: async ({ input, context }) => {
    try {
      await context.info(`Getting details for offer ${input.offer_id}`);

      // Report initial progress
      await context.report_progress(0.1, "Retrieving offer details");

      // Generate cache key
      const cacheKey = generateOfferCacheKey(input.offer_id);

      // Check cache first
      const cachedDetails = await getCachedResults(cacheKey);
      if (cachedDetails) {
        await context.info("Offer details found in cache");
        return cachedDetails;
      }

      // Initialize Duffel service
      const duffelService = new DuffelService();

      // Update progress
      await context.report_progress(0.3, "Fetching offer data");

      // Get offer details
      const offer = await duffelService.getOffer(input.offer_id);

      // Update progress
      await context.report_progress(0.6, "Getting fare rules");

      // Get fare rules
      const fareRules = await duffelService.getFareRules(input.offer_id);

      // Update progress
      await context.report_progress(0.8, "Formatting offer details");

      // Transform and format results
      const details = formatOfferDetails(offer, fareRules, input.currency);

      // Update progress
      await context.report_progress(0.9, "Caching results");

      // Cache results
      await cacheResults(cacheKey, details, config.CACHE_TTL.OFFER_DETAILS);

      // Complete progress
      await context.report_progress(1.0, "Offer details retrieval completed");

      await context.info("Offer details retrieved successfully");

      return details;
    } catch (error) {
      await context.error(`Error getting offer details: ${error.message}`);
      throw new Error(`Failed to get offer details: ${error.message}`);
    }
  },
});

module.exports = getOfferDetails;
```

### 6.3 Price Tracking Tool

```javascript
// src/mcp/flights/tools/track_prices.js
const { z } = require("zod");
const { createTool } = require("fastmcp");
const { Supabase } = require("../services/supabase_service");
const logger = require("../utils/logger");

const trackPrices = createTool({
  name: "track_prices",
  description: "Track price changes for a specific flight offer",

  input: z.object({
    origin: z.string().length(3).describe("Origin airport code (e.g., 'LAX')"),
    destination: z
      .string()
      .length(3)
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
    currency: z
      .string()
      .length(3)
      .default("USD")
      .describe("Currency for prices (ISO 4217 code)"),
    frequency: z
      .enum(["hourly", "daily", "weekly"])
      .default("daily")
      .describe("How often to check for price changes"),
    notify_when: z
      .enum([
        "any_change",
        "price_decrease",
        "price_increase",
        "availability_change",
      ])
      .default("price_decrease")
      .describe("When to send notifications"),
    threshold_percentage: z
      .number()
      .min(0)
      .default(5)
      .describe("Minimum percentage change to trigger notification"),
    user_id: z
      .string()
      .optional()
      .describe("User ID for associating the price tracking"),
    email: z
      .string()
      .email()
      .optional()
      .describe("Email address for notifications"),
  }),

  handler: async ({ input, context }) => {
    try {
      await context.info(
        `Setting up price tracking for ${input.origin} to ${input.destination}`
      );

      // Report initial progress
      await context.report_progress(0.2, "Configuring price tracking");

      // Initialize Supabase service
      const supabase = new Supabase();

      // Create tracking record in database
      const tracking = {
        search_params: {
          origin: input.origin,
          destination: input.destination,
          departure_date: input.departure_date,
          return_date: input.return_date,
          adults: input.adults,
          children: input.children,
          infants: input.infants,
          cabin_class: input.cabin_class,
        },
        frequency: input.frequency,
        notify_when: input.notify_when,
        threshold_percentage: input.threshold_percentage,
        currency: input.currency,
        user_id: input.user_id,
        email: input.email,
        status: "active",
        created_at: new Date().toISOString(),
      };

      // Update progress
      await context.report_progress(0.5, "Saving price tracking configuration");

      // Save to database
      const { data, error } = await supabase
        .from("price_tracking")
        .insert(tracking)
        .select();

      if (error) {
        throw new Error(`Failed to save price tracking: ${error.message}`);
      }

      const trackingId = data[0].id;

      // Immediately perform initial search to establish baseline
      await context.report_progress(0.7, "Performing initial price check");

      // Use search_flights tool via context to perform search
      const searchResults = await context.invoke_tool(
        "search_flights",
        tracking.search_params
      );

      // Save current price data
      const priceHistory = {
        tracking_id: trackingId,
        search_results: searchResults,
        timestamp: new Date().toISOString(),
      };

      await supabase.from("price_history").insert(priceHistory);

      // Complete progress
      await context.report_progress(1.0, "Price tracking setup completed");

      await context.info("Price tracking configured successfully");

      // Return tracking information
      return {
        tracking_id: trackingId,
        status: "active",
        search_params: tracking.search_params,
        frequency: input.frequency,
        notify_when: input.notify_when,
        threshold_percentage: input.threshold_percentage,
        message: `Price tracking has been set up for flights from ${
          input.origin
        } to ${input.destination}. You will be notified when prices ${
          input.notify_when === "price_decrease"
            ? "decrease"
            : input.notify_when === "price_increase"
            ? "increase"
            : "change"
        } by at least ${input.threshold_percentage}%.`,
      };
    } catch (error) {
      await context.error(`Error setting up price tracking: ${error.message}`);
      throw new Error(`Failed to set up price tracking: ${error.message}`);
    }
  },
});

module.exports = trackPrices;
```

## 7. Python Client Implementation

```python
# src/mcp/flights/client.py
from typing import Dict, List, Any, Optional, Union
import asyncio
import uuid
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from agents import function_tool
from src.mcp.base_mcp_client import BaseMCPClient
from src.utils.logging import get_module_logger
from src.db.repositories.price_history_repository import PriceHistoryRepository

logger = get_module_logger(__name__)

class FlightSearchParams(BaseModel):
    """Model for validating flight search parameters."""
    origin: str = Field(..., min_length=3, max_length=3,
                       description="Origin airport IATA code (e.g., 'SFO')")
    destination: str = Field(..., min_length=3, max_length=3,
                            description="Destination airport IATA code (e.g., 'JFK')")
    departure_date: date = Field(..., description="Departure date")
    return_date: Optional[date] = Field(None, description="Return date for round trips")
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    children: int = Field(0, ge=0, le=9, description="Number of child passengers (2-11 years)")
    infants: int = Field(0, ge=0, le=9, description="Number of infant passengers (<2 years)")
    cabin_class: str = Field("economy", description="Cabin class for flight")
    max_connections: Optional[int] = Field(None, ge=0, description="Maximum number of connections")
    airline_codes: List[str] = Field([], description="Limit to specific airlines (IATA codes)")
    currency: str = Field("USD", min_length=3, max_length=3, description="Currency for prices")

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate airport code format."""
        return v.upper()  # Ensure IATA codes are uppercase

    @field_validator("return_date")
    @classmethod
    def validate_return_date(cls, v: Optional[date], info: ValidationInfo) -> Optional[date]:
        """Ensure return_date is after departure_date if provided."""
        if v is not None and "departure_date" in info.data:
            if v <= info.data["departure_date"]:
                raise ValueError("Return date must be after departure date")
        return v

class OfferDetailsParams(BaseModel):
    """Model for validating offer details parameters."""
    offer_id: str = Field(..., description="The ID of the offer to retrieve details for")
    currency: str = Field("USD", min_length=3, max_length=3,
                          description="Currency for prices (ISO 4217 code)")

class PriceTrackingParams(BaseModel):
    """Model for validating price tracking parameters."""
    origin: str = Field(..., min_length=3, max_length=3,
                       description="Origin airport IATA code (e.g., 'SFO')")
    destination: str = Field(..., min_length=3, max_length=3,
                            description="Destination airport IATA code (e.g., 'JFK')")
    departure_date: date = Field(..., description="Departure date")
    return_date: Optional[date] = Field(None, description="Return date for round trips")
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    children: int = Field(0, ge=0, le=9, description="Number of child passengers (2-11 years)")
    infants: int = Field(0, ge=0, le=9, description="Number of infant passengers (<2 years)")
    cabin_class: str = Field("economy", description="Cabin class for flight")
    frequency: str = Field("daily", description="How often to check for price changes")
    notify_when: str = Field("price_decrease", description="When to send notifications")
    threshold_percentage: float = Field(5.0, ge=0, description="Minimum percentage change")
    user_id: Optional[str] = Field(None, description="User ID for associating the tracking")
    email: Optional[str] = Field(None, description="Email address for notifications")

class FlightsMCPClient(BaseMCPClient):
    """Client for the Flights MCP Server."""

    def __init__(self):
        """Initialize the Flights MCP client."""
        super().__init__(server_name="flights")
        self.price_history_repo = PriceHistoryRepository()
        logger.info("Initialized Flights MCP Client")

    @function_tool
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: Union[str, date],
        return_date: Optional[Union[str, date]] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "economy",
        max_connections: Optional[int] = None,
        airline_codes: Optional[List[str]] = None,
        currency: str = "USD"
    ) -> Dict[str, Any]:
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
            # Convert date objects to strings if needed
            if isinstance(departure_date, date):
                departure_date = departure_date.isoformat()

            if return_date and isinstance(return_date, date):
                return_date = return_date.isoformat()

            # Validate parameters
            params = FlightSearchParams(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                children=children,
                infants=infants,
                cabin_class=cabin_class,
                max_connections=max_connections,
                airline_codes=airline_codes or [],
                currency=currency
            )

            # Log search parameters
            logger.info(f"Searching flights from {params.origin} to {params.destination}")

            # Call the MCP server
            server = await self.get_server()
            result = await server.invoke_tool(
                "search_flights",
                params.model_dump(mode="json")
            )

            # Store search result in price history
            await self._store_price_history(params, result)

            return result
        except Exception as e:
            logger.error(f"Error searching flights: {str(e)}")
            return {
                "error": f"Failed to search flights: {str(e)}",
                "origin": origin,
                "destination": destination
            }

    @function_tool
    async def get_offer_details(
        self,
        offer_id: str,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """Get detailed information about a specific flight offer.

        Args:
            offer_id: The ID of the offer to retrieve details for
            currency: Currency for prices (ISO 4217 code)

        Returns:
            Dictionary with offer details
        """
        try:
            # Validate parameters
            params = OfferDetailsParams(
                offer_id=offer_id,
                currency=currency
            )

            logger.info(f"Getting details for offer {params.offer_id}")

            # Call the MCP server
            server = await self.get_server()
            result = await server.invoke_tool(
                "get_offer_details",
                params.model_dump(mode="json")
            )

            return result
        except Exception as e:
            logger.error(f"Error getting offer details: {str(e)}")
            return {
                "error": f"Failed to get offer details: {str(e)}",
                "offer_id": offer_id
            }

    @function_tool
    async def track_prices(
        self,
        origin: str,
        destination: str,
        departure_date: Union[str, date],
        return_date: Optional[Union[str, date]] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "economy",
        frequency: str = "daily",
        notify_when: str = "price_decrease",
        threshold_percentage: float = 5.0,
        user_id: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Track price changes for a flight route.

        Args:
            origin: Origin airport code (e.g., 'LAX')
            destination: Destination airport code (e.g., 'JFK')
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format for round trips
            adults: Number of adult passengers
            children: Number of child passengers (2-11 years)
            infants: Number of infant passengers (<2 years)
            cabin_class: Preferred cabin class
            frequency: How often to check for price changes
            notify_when: When to send notifications
            threshold_percentage: Minimum percentage change to trigger notification
            user_id: User ID for associating the price tracking
            email: Email address for notifications

        Returns:
            Dictionary with tracking information
        """
        try:
            # Convert date objects to strings if needed
            if isinstance(departure_date, date):
                departure_date = departure_date.isoformat()

            if return_date and isinstance(return_date, date):
                return_date = return_date.isoformat()

            # Validate parameters
            params = PriceTrackingParams(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                children=children,
                infants=infants,
                cabin_class=cabin_class,
                frequency=frequency,
                notify_when=notify_when,
                threshold_percentage=threshold_percentage,
                user_id=user_id,
                email=email
            )

            logger.info(f"Setting up price tracking for {params.origin} to {params.destination}")

            # Call the MCP server
            server = await self.get_server()
            result = await server.invoke_tool(
                "track_prices",
                params.model_dump(mode="json")
            )

            return result
        except Exception as e:
            logger.error(f"Error setting up price tracking: {str(e)}")
            return {
                "error": f"Failed to set up price tracking: {str(e)}",
                "origin": origin,
                "destination": destination
            }

    async def _store_price_history(self, params: FlightSearchParams, result: Dict[str, Any]) -> None:
        """Store search result in price history.

        Args:
            params: The search parameters
            result: The search results
        """
        try:
            # Skip if there's an error in the result
            if "error" in result:
                return

            # Extract price information from results
            price_data = {
                "search_id": str(uuid.uuid4()),
                "origin": params.origin,
                "destination": params.destination,
                "departure_date": params.departure_date.isoformat() if isinstance(params.departure_date, date) else params.departure_date,
                "return_date": params.return_date.isoformat() if params.return_date and isinstance(params.return_date, date) else params.return_date,
                "lowest_price": result.get("lowest_price", {}).get("amount", 0),
                "currency": params.currency,
                "adults": params.adults,
                "children": params.children,
                "infants": params.infants,
                "cabin_class": params.cabin_class,
                "offer_count": len(result.get("offers", [])),
                "timestamp": datetime.now().isoformat()
            }

            # Store in database
            await self.price_history_repo.create_price_history(price_data)

        except Exception as e:
            logger.error(f"Error storing price history: {str(e)}")
```

## 8. Integration with Travel Agent

```python
# src/agents/travel_agent.py
from typing import Dict, List, Any, Optional
from datetime import date, datetime, timedelta
import asyncio
import json
import uuid

from src.mcp.flights.client import FlightsMCPClient
from src.mcp.accommodations.client import AccommodationsMCPClient
from src.mcp.weather.client import WeatherMCPClient
from src.mcp.memory.client import MemoryClient
from src.utils.logging import get_module_logger
from src.agents.base_agent import BaseAgent

logger = get_module_logger(__name__)

class TravelAgent(BaseAgent):
    """Agent for comprehensive travel planning using multiple MCP services."""

    def __init__(self):
        """Initialize TravelAgent with MCP clients."""
        super().__init__(
            name="TripSage Travel Agent",
            instructions="""You are a comprehensive travel planning assistant that helps users find flights, accommodations, and activities. Use your tools to search for travel options, provide recommendations, and create detailed itineraries. Consider weather data and optimize for budget constraints. Learn from user preferences and leverage the knowledge graph to provide personalized suggestions."""
        )

        # Initialize MCP clients
        self.flights_client = FlightsMCPClient()
        self.accommodations_client = AccommodationsMCPClient()
        self.weather_client = WeatherMCPClient()
        self.memory_client = MemoryClient()

        # Register MCP tools
        self._register_mcp_client_tools()

    def _register_mcp_client_tools(self):
        """Register all MCP client tools."""
        # Register Flight MCP tools
        self.register_tool(self.flights_client.search_flights)
        self.register_tool(self.flights_client.get_offer_details)
        self.register_tool(self.flights_client.track_prices)

        # Register other MCP tools
        self.register_tool(self.accommodations_client.search_accommodations)
        self.register_tool(self.weather_client.get_forecast)
        self.register_tool(self.memory_client.search_nodes)

    async def plan_trip(self,
                       origin: str,
                       destination: str,
                       start_date: date,
                       end_date: date,
                       budget: float,
                       travelers: int = 1,
                       preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """Plan a complete trip.

        Args:
            origin: Origin location
            destination: Destination location
            start_date: Trip start date
            end_date: Trip end date
            budget: Total trip budget
            travelers: Number of travelers
            preferences: Optional user preferences

        Returns:
            Dictionary with trip plan
        """
        try:
            # Generate unique session ID
            session_id = f"trip_plan_{uuid.uuid4()}"

            # Get destination information from knowledge graph
            destination_nodes = await self.memory_client.search_nodes(destination)

            # Get weather forecast for destination
            weather = await self.weather_client.get_forecast(
                location=destination,
                days=(end_date - start_date).days + 1
            )

            # Search for flights
            flight_results = await self.flights_client.search_flights(
                origin=origin,
                destination=destination,
                departure_date=start_date,
                return_date=end_date,
                adults=travelers,
                children=0,
                infants=0,
                cabin_class="economy"
            )

            # Extract flight budget
            flight_budget = min(budget * 0.4, 2000.0)  # 40% of budget, max $2000

            # Filter flights by budget
            viable_flights = [
                offer for offer in flight_results.get("offers", [])
                if offer.get("price", {}).get("amount", float("inf")) <= flight_budget
            ]

            # Search for accommodations
            accommodation_budget = budget * 0.5  # 50% of budget
            daily_accommodation_budget = accommodation_budget / ((end_date - start_date).days)

            accommodations = await self.accommodations_client.search_accommodations(
                location=destination,
                check_in_date=start_date,
                check_out_date=end_date,
                adults=travelers,
                max_price=daily_accommodation_budget
            )

            # Determine best options based on budget and preferences
            selected_flight = viable_flights[0] if viable_flights else None
            selected_accommodation = accommodations.get("accommodations", [])[0] if accommodations.get("accommodations") else None

            # Calculate remaining budget
            flight_cost = selected_flight.get("price", {}).get("amount", 0) if selected_flight else 0
            accommodation_cost = (selected_accommodation.get("price", {}).get("amount", 0) *
                                (end_date - start_date).days) if selected_accommodation else 0

            remaining_budget = budget - flight_cost - accommodation_cost

            # Track flight prices if a good option is found
            if selected_flight:
                await self.flights_client.track_prices(
                    origin=origin,
                    destination=destination,
                    departure_date=start_date,
                    return_date=end_date,
                    adults=travelers,
                    notify_when="price_decrease"
                )

            # Create trip plan
            trip_plan = {
                "session_id": session_id,
                "origin": origin,
                "destination": destination,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "travelers": travelers,
                "budget": {
                    "total": budget,
                    "flight": flight_cost,
                    "accommodation": accommodation_cost,
                    "remaining": remaining_budget
                },
                "weather": {
                    "summary": weather.get("summary", "Weather data not available"),
                    "forecast": weather.get("forecast", [])
                },
                "flight": selected_flight,
                "accommodation": selected_accommodation,
                "activities": []  # To be filled later
            }

            # Store in knowledge graph
            await self._store_trip_in_knowledge_graph(trip_plan)

            return trip_plan

        except Exception as e:
            logger.error(f"Error planning trip: {str(e)}")
            return {
                "error": f"Failed to plan trip: {str(e)}",
                "origin": origin,
                "destination": destination
            }

    async def _store_trip_in_knowledge_graph(self, trip_plan: Dict[str, Any]) -> None:
        """Store trip information in the knowledge graph.

        Args:
            trip_plan: Complete trip plan
        """
        try:
            session_id = trip_plan["session_id"]

            # Create trip entity
            await self.memory_client.create_entities([{
                "name": session_id,
                "entityType": "Trip",
                "observations": [
                    f"Trip from {trip_plan['origin']} to {trip_plan['destination']}",
                    f"Date range: {trip_plan['start_date']} to {trip_plan['end_date']}",
                    f"Budget: {trip_plan['budget']['total']}"
                ]
            }])

            # Create destination entity if it doesn't exist
            destination_nodes = await self.memory_client.open_nodes([trip_plan["destination"]])
            if not destination_nodes:
                await self.memory_client.create_entities([{
                    "name": trip_plan["destination"],
                    "entityType": "Destination",
                    "observations": [
                        f"Weather: {trip_plan['weather']['summary']}",
                        f"Visited in trip: {session_id}"
                    ]
                }])

            # Create origin entity if it doesn't exist
            origin_nodes = await self.memory_client.open_nodes([trip_plan["origin"]])
            if not origin_nodes:
                await self.memory_client.create_entities([{
                    "name": trip_plan["origin"],
                    "entityType": "Origin",
                    "observations": [
                        f"Starting point for trip: {session_id}"
                    ]
                }])

            # Create relationships
            await self.memory_client.create_relations([
                {
                    "from": session_id,
                    "relationType": "DEPARTING_FROM",
                    "to": trip_plan["origin"]
                },
                {
                    "from": session_id,
                    "relationType": "GOING_TO",
                    "to": trip_plan["destination"]
                }
            ])

        except Exception as e:
            logger.error(f"Error storing trip in knowledge graph: {str(e)}")
```

## 9. Unit Tests

```python
# src/mcp/flights/tests/test_client.py
import pytest
from unittest.mock import AsyncMock, patch
from datetime import date, timedelta

from src.mcp.flights.client import FlightsMCPClient

@pytest.fixture
def flights_client():
    """Create a flights client for testing."""
    return FlightsMCPClient()

@pytest.fixture
def mock_server():
    """Mock MCP server."""
    server_mock = AsyncMock()
    server_mock.invoke_tool = AsyncMock()
    return server_mock

@pytest.mark.asyncio
async def test_search_flights(flights_client, mock_server):
    """Test search_flights method."""
    # Setup mock
    with patch.object(flights_client, 'get_server', return_value=mock_server):
        # Set up mock response
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
            ],
            "lowest_price": {
                "amount": 299.99,
                "currency": "USD"
            },
            "highest_price": {
                "amount": 299.99,
                "currency": "USD"
            },
            "total_count": 1
        }

        mock_server.invoke_tool.return_value = mock_response

        # Get tomorrow's date
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=7)

        # Call method
        result = await flights_client.search_flights(
            origin="LAX",
            destination="JFK",
            departure_date=tomorrow,
            return_date=next_week
        )

        # Check result
        assert result == mock_response

        # Verify call parameters
        mock_server.invoke_tool.assert_called_once()
        args, kwargs = mock_server.invoke_tool.call_args
        assert args[0] == "search_flights"

        # Check proper conversion of parameters
        assert args[1]["origin"] == "LAX"
        assert args[1]["destination"] == "JFK"
        assert args[1]["departure_date"] == tomorrow.isoformat()
        assert args[1]["return_date"] == next_week.isoformat()

@pytest.mark.asyncio
async def test_get_offer_details(flights_client, mock_server):
    """Test get_offer_details method."""
    # Setup mock
    with patch.object(flights_client, 'get_server', return_value=mock_server):
        # Set up mock response
        mock_response = {
            "id": "off_00001",
            "airline": {
                "code": "AA",
                "name": "American Airlines"
            },
            "price": {
                "amount": 299.99,
                "currency": "USD"
            },
            "fare_rules": {
                "cancellation": "Non-refundable",
                "change": "Change fee applies"
            },
            "slices": [
                {
                    "origin": {
                        "code": "LAX"
                    },
                    "destination": {
                        "code": "JFK"
                    },
                    "departure_time": "2025-06-01T10:00:00",
                    "arrival_time": "2025-06-01T18:30:00"
                }
            ]
        }

        mock_server.invoke_tool.return_value = mock_response

        # Call method
        result = await flights_client.get_offer_details(
            offer_id="off_00001",
            currency="USD"
        )

        # Check result
        assert result == mock_response

        # Verify call parameters
        mock_server.invoke_tool.assert_called_once()
        args, kwargs = mock_server.invoke_tool.call_args
        assert args[0] == "get_offer_details"
        assert args[1]["offer_id"] == "off_00001"
        assert args[1]["currency"] == "USD"

@pytest.mark.asyncio
async def test_track_prices(flights_client, mock_server):
    """Test track_prices method."""
    # Setup mock
    with patch.object(flights_client, 'get_server', return_value=mock_server):
        # Set up mock response
        mock_response = {
            "tracking_id": "track_12345",
            "status": "active",
            "message": "Price tracking has been set up for flights from LAX to JFK."
        }

        mock_server.invoke_tool.return_value = mock_response

        # Get tomorrow's date
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=7)

        # Call method
        result = await flights_client.track_prices(
            origin="LAX",
            destination="JFK",
            departure_date=tomorrow,
            return_date=next_week,
            adults=2,
            notify_when="price_decrease",
            threshold_percentage=10.0
        )

        # Check result
        assert result == mock_response

        # Verify call parameters
        mock_server.invoke_tool.assert_called_once()
        args, kwargs = mock_server.invoke_tool.call_args
        assert args[0] == "track_prices"
        assert args[1]["origin"] == "LAX"
        assert args[1]["destination"] == "JFK"
        assert args[1]["departure_date"] == tomorrow.isoformat()
        assert args[1]["return_date"] == next_week.isoformat()
        assert args[1]["adults"] == 2
        assert args[1]["notify_when"] == "price_decrease"
        assert args[1]["threshold_percentage"] == 10.0
```

## 10. Docker Configuration

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Environment
ENV NODE_ENV=production
ENV PORT=3002

# Expose port
EXPOSE 3002

# Start MCP server
CMD ["node", "src/mcp/flights/server.js"]
```

```yaml
# docker-compose.yml (for Flights MCP Server)
version: "3.8"

services:
  flights-mcp:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3002:3002"
    environment:
      - DUFFEL_API_KEY=${DUFFEL_API_KEY}
      - DUFFEL_API_VERSION=${DUFFEL_API_VERSION}
      - REDIS_URL=${REDIS_URL}
      - NODE_ENV=production
      - PORT=3002
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - tripsage-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    networks:
      - tripsage-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 1m
      timeout: 10s
      retries: 3

volumes:
  redis-data:

networks:
  tripsage-network:
    driver: bridge
```

## 11. Integration with OpenAI Agents SDK

Add the Flights MCP Server configuration to the OpenAI Agents SDK configuration:

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

## 12. Integration with Claude Desktop

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "flights": {
      "command": "node",
      "args": ["./src/mcp/flights/server.js"],
      "env": {
        "DUFFEL_API_KEY": "${DUFFEL_API_KEY}",
        "DUFFEL_API_VERSION": "2023-06-02",
        "REDIS_URL": "${REDIS_URL}"
      }
    }
  }
}
```

## 13. Deployment and CI/CD

Add a GitHub Actions workflow for Flights MCP Server:

```yaml
# .github/workflows/flights-mcp.yml
name: Flights MCP CI/CD

on:
  push:
    branches: [main, dev]
    paths:
      - "src/mcp/flights/**"
      - ".github/workflows/flights-mcp.yml"
  pull_request:
    branches: [main, dev]
    paths:
      - "src/mcp/flights/**"

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: "18"
          cache: "npm"

      - name: Install dependencies
        run: npm ci
        working-directory: ./src/mcp/flights

      - name: Run linting
        run: npm run lint
        working-directory: ./src/mcp/flights

      - name: Run tests
        run: npm test
        working-directory: ./src/mcp/flights

  build:
    needs: test
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.repository_owner }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./Dockerfile.flights-mcp
          push: true
          tags: ghcr.io/${{ github.repository }}/flights-mcp:latest
```

## 14. Monitoring and Alerts

Implement a health check endpoint:

```javascript
// src/mcp/flights/server.js (add to existing file)
const express = require("express");
const app = express();

// Health check endpoint
app.get("/health", (req, res) => {
  res.status(200).json({
    status: "ok",
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
  });
});

// Start Express server alongside FastMCP
app.listen(config.PORT + 1, () => {
  logger.info(`Health check endpoint running on port ${config.PORT + 1}`);
});
```

## Conclusion

This detailed implementation guide provides a comprehensive approach to building the Flights MCP Server for TripSage. By following these steps, you'll create a robust, scalable service that integrates with the Duffel API while providing caching, error handling, and proper integration with the TripSage agent architecture. The implementation follows best practices for FastMCP 2.0 servers and includes all necessary components for deployment in both development and production environments.
