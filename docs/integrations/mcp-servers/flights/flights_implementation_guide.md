# Flights MCP Server Implementation Guide

This document provides a comprehensive step-by-step guide for implementing the Flights MCP Server for TripSage, building on the existing documentation in `flights_mcp_implementation.md`.

## Prerequisites

Before implementing the Flights MCP Server, ensure you have:

1. Python and Node.js development environments set up
2. FastMCP 2.0 installed and configured
3. Duffel API credentials obtained (see [Duffel API documentation](https://duffel.com/docs))
4. Redis instance running for caching (local or remote)
5. Access to TripSage repository with proper permissions

## Implementation Workflow

### Step 1: Set Up Project Structure

Create the necessary directory structure for the Flights MCP Server:

```bash
# From the TripSage project root
mkdir -p src/mcp/flights/{tools,services,transformers,utils,tests}
touch src/mcp/flights/__init__.py
touch src/mcp/flights/server.js
touch src/mcp/flights/client.py
touch src/mcp/flights/config.py

# Create tool files
touch src/mcp/flights/tools/index.ts
touch src/mcp/flights/tools/search_flights.ts
touch src/mcp/flights/tools/search_multi_city.ts
touch src/mcp/flights/tools/get_offer_details.ts
touch src/mcp/flights/tools/get_fare_rules.ts
touch src/mcp/flights/tools/create_order.ts
touch src/mcp/flights/tools/get_order.ts
touch src/mcp/flights/tools/track_prices.ts

# Create service files
touch src/mcp/flights/services/duffel_service.ts

# Create transformer files
touch src/mcp/flights/transformers/duffel_transformer.ts

# Create utility files
touch src/mcp/flights/utils/cache.ts
touch src/mcp/flights/utils/error_handling.ts
touch src/mcp/flights/utils/validation.ts

# Create test files
touch src/mcp/flights/tests/__init__.py
touch src/mcp/flights/tests/test_client.py
mkdir -p src/mcp/flights/tests/fixtures
```

### Step 2: Set Up Environment Configuration

Create the configuration module for the Flights MCP Server:

```python
# src/mcp/flights/config.py
from typing import Dict, Any, Optional
import os
from src.utils.config import get_config

class FlightsMCPConfig:
    """Configuration for the Flights MCP Server."""

    def __init__(self):
        """Initialize the configuration from environment variables and config file."""
        # Get base configuration
        config = get_config()

        # Duffel API settings
        self.duffel_api_key = config.get("DUFFEL_API_KEY")
        self.duffel_api_version = config.get("DUFFEL_API_VERSION", "2023-06-02")
        self.duffel_api_url = config.get("DUFFEL_API_URL", "https://api.duffel.com")

        # Cache settings
        self.cache_enabled = config.get("FLIGHTS_CACHE_ENABLED", True)
        self.cache_ttl_default = int(config.get("FLIGHTS_CACHE_TTL_DEFAULT", 300))  # 5 minutes
        self.cache_ttl_offers = int(config.get("FLIGHTS_CACHE_TTL_OFFERS", 300))    # 5 minutes
        self.cache_ttl_schedules = int(config.get("FLIGHTS_CACHE_TTL_SCHEDULES", 3600))  # 1 hour

        # Request settings
        self.request_timeout = int(config.get("FLIGHTS_REQUEST_TIMEOUT", 30))  # 30 seconds
        self.max_retries = int(config.get("FLIGHTS_MAX_RETRIES", 3))
        self.retry_delay = int(config.get("FLIGHTS_RETRY_DELAY", 1))  # 1 second

    def validate(self) -> None:
        """Validate the configuration.

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        if not self.duffel_api_key:
            raise ValueError("DUFFEL_API_KEY is required")

        if not self.duffel_api_version:
            raise ValueError("DUFFEL_API_VERSION is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary with configuration values
        """
        return {
            "duffel_api_key": "****" if self.duffel_api_key else None,
            "duffel_api_version": self.duffel_api_version,
            "duffel_api_url": self.duffel_api_url,
            "cache_enabled": self.cache_enabled,
            "cache_ttl_default": self.cache_ttl_default,
            "cache_ttl_offers": self.cache_ttl_offers,
            "cache_ttl_schedules": self.cache_ttl_schedules,
            "request_timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay
        }

# Create a singleton instance
flights_config = FlightsMCPConfig()
```

### Step 3: Implement Duffel API Service

Create the Duffel API service:

```typescript
// src/mcp/flights/services/duffel_service.ts
import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import { retryAxios } from "../utils/error_handling";

interface DuffelServiceConfig {
  apiKey: string;
  apiVersion: string;
  apiUrl: string;
  timeout: number;
  maxRetries: number;
  retryDelay: number;
}

/**
 * Service for interacting with the Duffel API.
 */
export class DuffelService {
  private client: AxiosInstance;
  private config: DuffelServiceConfig;

  /**
   * Create a new DuffelService instance.
   *
   * @param config - Optional configuration override
   */
  constructor(config?: Partial<DuffelServiceConfig>) {
    // Load configuration from environment variables
    this.config = {
      apiKey: process.env.DUFFEL_API_KEY || "",
      apiVersion: process.env.DUFFEL_API_VERSION || "2023-06-02",
      apiUrl: process.env.DUFFEL_API_URL || "https://api.duffel.com",
      timeout: Number(process.env.FLIGHTS_REQUEST_TIMEOUT || 30) * 1000,
      maxRetries: Number(process.env.FLIGHTS_MAX_RETRIES || 3),
      retryDelay: Number(process.env.FLIGHTS_RETRY_DELAY || 1) * 1000,
      ...config,
    };

    // Validate configuration
    if (!this.config.apiKey) {
      throw new Error("Duffel API key is required");
    }

    // Create axios client
    this.client = axios.create({
      baseURL: this.config.apiUrl,
      headers: {
        Authorization: `Bearer ${this.config.apiKey}`,
        Accept: "application/json",
        "Content-Type": "application/json",
        "Duffel-Version": this.config.apiVersion,
      },
      timeout: this.config.timeout,
    });
  }

  /**
   * Create an offer request to search for flights.
   *
   * @param payload - The offer request payload
   * @returns The created offer request
   */
  async createOfferRequest(payload: any): Promise<any> {
    try {
      const response = await retryAxios(
        () => this.client.post("/air/offer_requests", { data: payload }),
        this.config.maxRetries,
        this.config.retryDelay
      );
      return response.data.data;
    } catch (error) {
      console.error("Error creating offer request:", error);
      throw this.formatError(error, "Failed to create offer request");
    }
  }

  /**
   * Get offers for an offer request.
   *
   * @param offerId - The offer request ID
   * @returns The offers
   */
  async getOffers(offerId: string): Promise<any> {
    try {
      const response = await retryAxios(
        () => this.client.get(`/air/offers?offer_request_id=${offerId}`),
        this.config.maxRetries,
        this.config.retryDelay
      );
      return response.data.data;
    } catch (error) {
      console.error("Error getting offers:", error);
      throw this.formatError(error, "Failed to get offers");
    }
  }

  /**
   * Get offer details.
   *
   * @param offerId - The offer ID
   * @returns The offer details
   */
  async getOfferDetails(offerId: string): Promise<any> {
    try {
      const response = await retryAxios(
        () => this.client.get(`/air/offers/${offerId}`),
        this.config.maxRetries,
        this.config.retryDelay
      );
      return response.data.data;
    } catch (error) {
      console.error("Error getting offer details:", error);
      throw this.formatError(error, "Failed to get offer details");
    }
  }

  /**
   * Get seat maps for an offer.
   *
   * @param offerId - The offer ID
   * @returns The seat maps
   */
  async getSeatMaps(offerId: string): Promise<any> {
    try {
      const response = await retryAxios(
        () => this.client.get(`/air/seat_maps?offer_id=${offerId}`),
        this.config.maxRetries,
        this.config.retryDelay
      );
      return response.data.data;
    } catch (error) {
      console.error("Error getting seat maps:", error);
      throw this.formatError(error, "Failed to get seat maps");
    }
  }

  /**
   * Create an order to book a flight.
   *
   * @param payload - The order creation payload
   * @returns The created order
   */
  async createOrder(payload: any): Promise<any> {
    try {
      const response = await retryAxios(
        () => this.client.post("/air/orders", { data: payload }),
        this.config.maxRetries,
        this.config.retryDelay
      );
      return response.data.data;
    } catch (error) {
      console.error("Error creating order:", error);
      throw this.formatError(error, "Failed to create order");
    }
  }

  /**
   * Get order details.
   *
   * @param orderId - The order ID
   * @returns The order details
   */
  async getOrder(orderId: string): Promise<any> {
    try {
      const response = await retryAxios(
        () => this.client.get(`/air/orders/${orderId}`),
        this.config.maxRetries,
        this.config.retryDelay
      );
      return response.data.data;
    } catch (error) {
      console.error("Error getting order:", error);
      throw this.formatError(error, "Failed to get order");
    }
  }

  /**
   * Format an error response.
   *
   * @param error - The error object
   * @param defaultMessage - The default error message
   * @returns A formatted error
   */
  private formatError(error: any, defaultMessage: string): Error {
    if (error.response && error.response.data && error.response.data.errors) {
      const errors = error.response.data.errors;
      const messages = errors.map((e: any) => e.message || e.title).join("; ");
      return new Error(messages || defaultMessage);
    }
    return new Error(error.message || defaultMessage);
  }
}
```

### Step 4: Implement Error Handling Utilities

Create error handling utilities for the Flights MCP Server:

```typescript
// src/mcp/flights/utils/error_handling.ts
import axios, { AxiosError } from "axios";

/**
 * Retry an axios request with exponential backoff.
 *
 * @param requestFn - Function that returns an axios request promise
 * @param maxRetries - Maximum number of retries
 * @param retryDelay - Base delay between retries in milliseconds
 * @returns The axios response
 */
export async function retryAxios(
  requestFn: () => Promise<any>,
  maxRetries: number = 3,
  retryDelay: number = 1000
): Promise<any> {
  let lastError: any;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await requestFn();
    } catch (error) {
      lastError = error;

      // Check if we should retry
      if (attempt < maxRetries && shouldRetryRequest(error)) {
        // Calculate delay with exponential backoff and jitter
        const delay = calculateRetryDelay(attempt, retryDelay);
        console.log(
          `Retrying request in ${delay}ms (attempt ${
            attempt + 1
          }/${maxRetries})`
        );
        await sleep(delay);
      } else {
        // No more retries or error is not retryable
        break;
      }
    }
  }

  throw lastError;
}

/**
 * Determine if a request should be retried based on the error.
 *
 * @param error - The error object
 * @returns True if the request should be retried
 */
function shouldRetryRequest(error: any): boolean {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError;

    // Retry on network errors
    if (!axiosError.response) {
      return true;
    }

    // Retry on rate limiting (429) and server errors (5xx)
    const status = axiosError.response.status;
    return status === 429 || (status >= 500 && status < 600);
  }

  return false;
}

/**
 * Calculate retry delay with exponential backoff and jitter.
 *
 * @param attempt - The current attempt number (0-based)
 * @param baseDelay - The base delay in milliseconds
 * @returns The delay in milliseconds
 */
function calculateRetryDelay(attempt: number, baseDelay: number): number {
  // Exponential backoff: baseDelay * 2^attempt
  const exponentialDelay = baseDelay * Math.pow(2, attempt);

  // Add jitter (random 0-30% of delay)
  const jitter = Math.random() * 0.3 * exponentialDelay;

  return exponentialDelay + jitter;
}

/**
 * Sleep for a specified duration.
 *
 * @param ms - The duration in milliseconds
 * @returns A promise that resolves after the duration
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
```

### Step 5: Implement Caching Utilities

Create caching utilities for the Flights MCP Server:

```typescript
// src/mcp/flights/utils/cache.ts
import { createClient, RedisClientType } from "redis";

// Redis client singleton
let redisClient: RedisClientType | null = null;

/**
 * Get the Redis client instance.
 *
 * @returns The Redis client
 */
async function getRedisClient(): Promise<RedisClientType> {
  if (!redisClient) {
    const url = process.env.REDIS_URL || "redis://localhost:6379";
    redisClient = createClient({ url });
    await redisClient.connect();
  }

  return redisClient;
}

/**
 * Cache results with TTL.
 *
 * @param key - The cache key
 * @param data - The data to cache
 * @param ttl - Time-to-live in seconds
 * @returns True if successful, false otherwise
 */
export async function cacheResults(
  key: string,
  data: any,
  ttl: number = 300
): Promise<boolean> {
  try {
    // Skip caching if not enabled
    if (process.env.FLIGHTS_CACHE_ENABLED === "false") {
      return false;
    }

    const redis = await getRedisClient();
    await redis.set(key, JSON.stringify(data), { EX: ttl });
    return true;
  } catch (error) {
    console.error("Error caching results:", error);
    return false;
  }
}

/**
 * Get cached results.
 *
 * @param key - The cache key
 * @returns The cached data or null if not found
 */
export async function getCachedResults(key: string): Promise<any | null> {
  try {
    // Skip cache if not enabled
    if (process.env.FLIGHTS_CACHE_ENABLED === "false") {
      return null;
    }

    const redis = await getRedisClient();
    const data = await redis.get(key);

    if (data) {
      return JSON.parse(data);
    }

    return null;
  } catch (error) {
    console.error("Error getting cached results:", error);
    return null;
  }
}

/**
 * Invalidate cached results.
 *
 * @param key - The cache key
 * @returns True if successful, false otherwise
 */
export async function invalidateCache(key: string): Promise<boolean> {
  try {
    const redis = await getRedisClient();
    await redis.del(key);
    return true;
  } catch (error) {
    console.error("Error invalidating cache:", error);
    return false;
  }
}

/**
 * Generate a cache key based on search parameters.
 *
 * @param prefix - The cache key prefix
 * @param params - The search parameters
 * @returns The cache key
 */
export function generateCacheKey(prefix: string, params: any): string {
  // Create a stable JSON string (sorted keys)
  const stableParams = JSON.stringify(params, Object.keys(params).sort());

  // Generate a simple hash
  let hash = 0;
  for (let i = 0; i < stableParams.length; i++) {
    const char = stableParams.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32-bit integer
  }

  return `${prefix}:${hash}`;
}
```

### Step 6: Implement Data Transformers

Create data transformers for the Flights MCP Server:

```typescript
// src/mcp/flights/transformers/duffel_transformer.ts
/**
 * Format search results for client consumption.
 *
 * @param offers - The raw offers from Duffel API
 * @param currency - The currency to display prices in
 * @returns Formatted search results
 */
export function formatSearchResults(
  offers: any[],
  currency: string = "USD"
): any {
  // Extract airlines for reference
  const airlines = extractAirlines(offers);

  // Format each offer
  const formattedOffers = offers.map((offer) =>
    formatOffer(offer, airlines, currency)
  );

  return {
    offers: formattedOffers,
    airlines: Object.values(airlines),
    meta: {
      currency,
      count: formattedOffers.length,
      lowest_price: findLowestPrice(formattedOffers),
    },
  };
}

/**
 * Format a single offer.
 *
 * @param offer - The raw offer
 * @param airlines - The airlines reference object
 * @param currency - The currency to display prices in
 * @returns Formatted offer
 */
function formatOffer(offer: any, airlines: any, currency: string): any {
  // Extract slices (flight segments)
  const slices = offer.slices.map((slice: any) => formatSlice(slice, airlines));

  // Extract passengers
  const passengers = {
    adults: countPassengersByType(offer.passengers, "adult"),
    children: countPassengersByType(offer.passengers, "child"),
    infants: countPassengersByType(offer.passengers, "infant_without_seat"),
  };

  // Format offer
  return {
    id: offer.id,
    price: {
      amount: parseFloat(offer.total_amount),
      currency: offer.total_currency || currency,
      base_amount: parseFloat(offer.base_amount),
      tax_amount: parseFloat(offer.tax_amount),
    },
    slices,
    passengers,
    total_duration: calculateTotalDuration(offer.slices),
    created_at: offer.created_at,
    expires_at: offer.expires_at,
    live_mode: offer.live_mode,
    private_fares: offer.private_fares,
    conditions: {
      refundable: offer.conditions?.refundable || false,
      exchangeable: offer.conditions?.exchangeable || false,
      change_fee: offer.conditions?.change_before_departure?.penalty_amount
        ? {
            amount: parseFloat(
              offer.conditions.change_before_departure.penalty_amount
            ),
            currency: offer.conditions.change_before_departure.penalty_currency,
          }
        : null,
    },
  };
}

/**
 * Format a slice (flight segment).
 *
 * @param slice - The raw slice
 * @param airlines - The airlines reference object
 * @returns Formatted slice
 */
function formatSlice(slice: any, airlines: any): any {
  // Extract segments (individual flights)
  const segments = slice.segments.map((segment: any) =>
    formatSegment(segment, airlines)
  );

  return {
    id: slice.id,
    origin: {
      airport: slice.origin.iata_code,
      terminal: slice.origin.terminal,
      city: slice.origin.city_name,
      country: slice.origin.country_name,
    },
    destination: {
      airport: slice.destination.iata_code,
      terminal: slice.destination.terminal,
      city: slice.destination.city_name,
      country: slice.destination.country_name,
    },
    departure_time: slice.departure_time,
    arrival_time: slice.arrival_time,
    duration: slice.duration,
    segments,
    stops: segments.length - 1,
    overnight: isOvernight(slice.departure_time, slice.arrival_time),
    long_layover: hasLongLayover(segments),
    short_layover: hasShortLayover(segments),
  };
}

/**
 * Format a segment (individual flight).
 *
 * @param segment - The raw segment
 * @param airlines - The airlines reference object
 * @returns Formatted segment
 */
function formatSegment(segment: any, airlines: any): any {
  const airlineCode = segment.operating_carrier.iata_code;

  return {
    id: segment.id,
    origin: {
      airport: segment.origin.iata_code,
      terminal: segment.origin.terminal,
      city: segment.origin.city_name,
      country: segment.origin.country_name,
    },
    destination: {
      airport: segment.destination.iata_code,
      terminal: segment.destination.terminal,
      city: segment.destination.city_name,
      country: segment.destination.country_name,
    },
    departure_time: segment.departure_time,
    arrival_time: segment.arrival_time,
    duration: segment.duration,
    aircraft: {
      code: segment.aircraft?.iata_code,
      name: segment.aircraft?.name,
    },
    airline: {
      code: airlineCode,
      name: airlines[airlineCode]?.name || airlineCode,
    },
    flight_number: segment.flight_number,
    distance: segment.distance,
    cabin_class: segment.cabin_class,
    amenities: extractAmenities(segment.amenities || []),
  };
}

/**
 * Extract airlines from offers.
 *
 * @param offers - The raw offers
 * @returns Object with airline data keyed by IATA code
 */
function extractAirlines(offers: any[]): any {
  const airlines: any = {};

  // Iterate through all offers and segments
  for (const offer of offers) {
    for (const slice of offer.slices) {
      for (const segment of slice.segments) {
        const marketingCarrier = segment.marketing_carrier;
        const operatingCarrier = segment.operating_carrier;

        if (marketingCarrier && marketingCarrier.iata_code) {
          airlines[marketingCarrier.iata_code] = {
            code: marketingCarrier.iata_code,
            name: marketingCarrier.name,
          };
        }

        if (operatingCarrier && operatingCarrier.iata_code) {
          airlines[operatingCarrier.iata_code] = {
            code: operatingCarrier.iata_code,
            name: operatingCarrier.name,
          };
        }
      }
    }
  }

  return airlines;
}

/**
 * Count passengers by type.
 *
 * @param passengers - The passengers array
 * @param type - The passenger type to count
 * @returns The count
 */
function countPassengersByType(passengers: any[], type: string): number {
  return passengers.filter((p) => p.type === type).length;
}

/**
 * Calculate the total duration of all slices.
 *
 * @param slices - The slices array
 * @returns The total duration in minutes
 */
function calculateTotalDuration(slices: any[]): number {
  return slices.reduce((total, slice) => total + slice.duration, 0);
}

/**
 * Check if a flight is overnight.
 *
 * @param departureTime - The departure time
 * @param arrivalTime - The arrival time
 * @returns True if overnight
 */
function isOvernight(departureTime: string, arrivalTime: string): boolean {
  const departureDate = new Date(departureTime).getDate();
  const arrivalDate = new Date(arrivalTime).getDate();

  return departureDate !== arrivalDate;
}

/**
 * Check if there are any long layovers (>4 hours).
 *
 * @param segments - The segments array
 * @returns True if there are long layovers
 */
function hasLongLayover(segments: any[]): boolean {
  if (segments.length <= 1) {
    return false;
  }

  for (let i = 0; i < segments.length - 1; i++) {
    const currentArrival = new Date(segments[i].arrival_time).getTime();
    const nextDeparture = new Date(segments[i + 1].departure_time).getTime();

    // Calculate layover in hours
    const layoverHours = (nextDeparture - currentArrival) / (1000 * 60 * 60);

    if (layoverHours > 4) {
      return true;
    }
  }

  return false;
}

/**
 * Check if there are any short layovers (<1 hour).
 *
 * @param segments - The segments array
 * @returns True if there are short layovers
 */
function hasShortLayover(segments: any[]): boolean {
  if (segments.length <= 1) {
    return false;
  }

  for (let i = 0; i < segments.length - 1; i++) {
    const currentArrival = new Date(segments[i].arrival_time).getTime();
    const nextDeparture = new Date(segments[i + 1].departure_time).getTime();

    // Calculate layover in minutes
    const layoverMinutes = (nextDeparture - currentArrival) / (1000 * 60);

    if (layoverMinutes < 60) {
      return true;
    }
  }

  return false;
}

/**
 * Extract and format amenities.
 *
 * @param amenities - The raw amenities array
 * @returns Formatted amenities
 */
function extractAmenities(amenities: any[]): any {
  const result: any = {
    wifi: false,
    power: false,
    entertainment: false,
  };

  for (const amenity of amenities) {
    switch (amenity.type) {
      case "wifi":
        result.wifi = true;
        break;
      case "power":
        result.power = true;
        break;
      case "entertainment":
        result.entertainment = true;
        break;
    }
  }

  return result;
}

/**
 * Find the lowest price among offers.
 *
 * @param offers - The formatted offers
 * @returns The lowest price
 */
function findLowestPrice(offers: any[]): number {
  if (offers.length === 0) {
    return 0;
  }

  return Math.min(...offers.map((offer) => offer.price.amount));
}
```

### Step 7: Implement Search Flights Tool

Create the search_flights tool:

```typescript
// src/mcp/flights/tools/search_flights.ts
import { z } from "zod";
import { createTool } from "fastmcp";
import { DuffelService } from "../services/duffel_service";
import { formatSearchResults } from "../transformers/duffel_transformer";
import {
  cacheResults,
  getCachedResults,
  generateCacheKey,
} from "../utils/cache";

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
      const cacheKey = generateCacheKey("flights_search", input);

      // Check cache first
      const cachedResults = await getCachedResults(cacheKey);
      if (cachedResults) {
        context.info("Cache hit for flight search");
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

      // Log the search parameters
      context.info("Searching flights", input);

      // Make API request
      context.info("Creating offer request");
      const offerRequest = await duffelService.createOfferRequest(payload);

      context.info("Getting offers", { offer_request_id: offerRequest.id });
      const offers = await duffelService.getOffers(offerRequest.id);

      // Transform and format results
      context.info("Transforming results", { offers_count: offers.length });
      const results = formatSearchResults(offers, input.currency);

      // Cache results
      const cacheTtl = Number(process.env.FLIGHTS_CACHE_TTL_OFFERS || 300); // 5 minutes
      await cacheResults(cacheKey, results, cacheTtl);

      return results;
    } catch (error) {
      // Log the error
      context.error("Error searching flights", { error: error.message });

      // Return structured error response
      return {
        error: error.message || "Failed to search flights",
        input: {
          origin: input.origin,
          destination: input.destination,
          departure_date: input.departure_date,
          return_date: input.return_date,
        },
      };
    }
  },
});
```

### Step 8: Implement Server Entry Point

Create the FastMCP server:

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

// Log server information
console.log(`Flights MCP Server started`);
console.log(`- Version: ${server.version}`);
console.log(`- Description: ${server.description}`);
console.log(`- Registered tools: ${server.getTools().length}`);
```

### Step 9: Implement Python Client

Create the Python client for the Flights MCP Server:

```python
# src/mcp/flights/client.py
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

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
        return_date: Optional[str] = None,
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
            cabin_class: Preferred cabin class (economy, premium_economy, business, first)
            max_connections: Maximum number of connections per slice
            airline_codes: Limit results to specific airlines (IATA codes)
            currency: Currency for prices (ISO 4217 code)

        Returns:
            Dictionary with search results
        """
        try:
            # Validate inputs
            self._validate_airport_code(origin)
            self._validate_airport_code(destination)
            self._validate_date(departure_date)
            if return_date:
                self._validate_date(return_date)

            # Call the MCP server
            server = await self.get_server()
            result = await server.invoke_tool(
                "search_flights",
                {
                    "origin": origin.upper(),  # Standardize to uppercase
                    "destination": destination.upper(),  # Standardize to uppercase
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "adults": adults,
                    "children": children,
                    "infants": infants,
                    "cabin_class": cabin_class,
                    "max_connections": max_connections,
                    "airline_codes": airline_codes or [],
                    "currency": currency.upper()  # Standardize to uppercase
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error searching flights: {str(e)}")
            return {
                "error": f"Failed to search flights: {str(e)}",
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date
            }

    @function_tool
    async def search_multi_city(
        self,
        slices: List[Dict[str, str]],
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "economy",
        max_connections: Optional[int] = None,
        airline_codes: Optional[List[str]] = None,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """Search for multi-city flights.

        Args:
            slices: List of flight slices, each with origin, destination, and departure_date
            adults: Number of adult passengers
            children: Number of child passengers (2-11 years)
            infants: Number of infant passengers (<2 years)
            cabin_class: Preferred cabin class (economy, premium_economy, business, first)
            max_connections: Maximum number of connections per slice
            airline_codes: Limit results to specific airlines (IATA codes)
            currency: Currency for prices (ISO 4217 code)

        Returns:
            Dictionary with search results
        """
        try:
            # Validate slices
            for slice in slices:
                self._validate_airport_code(slice.get("origin"))
                self._validate_airport_code(slice.get("destination"))
                self._validate_date(slice.get("departure_date"))

            # Call the MCP server
            server = await self.get_server()
            result = await server.invoke_tool(
                "search_multi_city",
                {
                    "slices": [
                        {
                            "origin": s["origin"].upper(),
                            "destination": s["destination"].upper(),
                            "departure_date": s["departure_date"]
                        }
                        for s in slices
                    ],
                    "adults": adults,
                    "children": children,
                    "infants": infants,
                    "cabin_class": cabin_class,
                    "max_connections": max_connections,
                    "airline_codes": airline_codes or [],
                    "currency": currency.upper()
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error searching multi-city flights: {str(e)}")
            return {
                "error": f"Failed to search multi-city flights: {str(e)}",
                "slices": slices
            }

    @function_tool
    async def get_offer_details(
        self,
        offer_id: str
    ) -> Dict[str, Any]:
        """Get detailed information about a flight offer.

        Args:
            offer_id: The unique identifier for the offer

        Returns:
            Dictionary with offer details
        """
        try:
            server = await self.get_server()
            result = await server.invoke_tool(
                "get_offer_details",
                {"offer_id": offer_id}
            )
            return result
        except Exception as e:
            logger.error(f"Error getting offer details: {str(e)}")
            return {
                "error": f"Failed to get offer details: {str(e)}",
                "offer_id": offer_id
            }

    # Helper validation methods
    def _validate_airport_code(self, code: str) -> None:
        """Validate airport IATA code format.

        Args:
            code: The airport code to validate

        Raises:
            ValueError: If the code is invalid
        """
        if not code or not isinstance(code, str):
            raise ValueError("Airport code is required")

        if len(code) != 3:
            raise ValueError(f"Invalid airport code: {code} (must be 3 characters)")

    def _validate_date(self, date_str: str) -> None:
        """Validate date format.

        Args:
            date_str: The date string to validate

        Raises:
            ValueError: If the date is invalid
        """
        if not date_str or not isinstance(date_str, str):
            raise ValueError("Date is required")

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")

            # Check if date is in the past
            if date.date() < datetime.now().date():
                raise ValueError(f"Date cannot be in the past: {date_str}")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str} (must be YYYY-MM-DD)")
```

### Step 10: Implement Tests

Create tests for the Flights MCP client:

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

@pytest.mark.asyncio
async def test_search_flights_validation(flight_client):
    """Test search_flights validation."""
    # Get tomorrow's date
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Test invalid airport code
    with pytest.raises(ValueError, match="Invalid airport code"):
        await flight_client.search_flights(
            origin="INVALID",
            destination="JFK",
            departure_date=tomorrow
        )

    # Test invalid date format
    with pytest.raises(ValueError, match="Invalid date format"):
        await flight_client.search_flights(
            origin="LAX",
            destination="JFK",
            departure_date="01-01-2023"  # Wrong format
        )

    # Test date in the past
    past_date = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    with pytest.raises(ValueError, match="Date cannot be in the past"):
        await flight_client.search_flights(
            origin="LAX",
            destination="JFK",
            departure_date=past_date
        )
```

### Step 11: Update MCP Server Configuration

Update the MCP server configuration files:

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
        FLIGHTS_CACHE_ENABLED: "true",
        FLIGHTS_CACHE_TTL_OFFERS: "300",
        FLIGHTS_CACHE_TTL_SCHEDULES: "3600",
      },
    },
  },
};
```

```json
// claude_desktop_config.json
{
  "mcpServers": {
    // Existing MCP servers...

    "flights": {
      "command": "node",
      "args": ["./src/mcp/flights/server.js"],
      "env": {
        "DUFFEL_API_KEY": "${DUFFEL_API_KEY}",
        "DUFFEL_API_VERSION": "2023-06-02",
        "REDIS_URL": "${REDIS_URL}",
        "FLIGHTS_CACHE_ENABLED": "true",
        "FLIGHTS_CACHE_TTL_OFFERS": "300",
        "FLIGHTS_CACHE_TTL_SCHEDULES": "3600"
      }
    }
  }
}
```

### Step 12: Create Environment Variables Example

Create an `.env.example` file with required environment variables:

```bash
# .env.example
# Duffel API credentials
DUFFEL_API_KEY=duffel_test_yourkey
DUFFEL_API_VERSION=2023-06-02

# Redis configuration
REDIS_URL=redis://localhost:6379

# Cache settings
FLIGHTS_CACHE_ENABLED=true
FLIGHTS_CACHE_TTL_DEFAULT=300
FLIGHTS_CACHE_TTL_OFFERS=300
FLIGHTS_CACHE_TTL_SCHEDULES=3600

# Request settings
FLIGHTS_REQUEST_TIMEOUT=30
FLIGHTS_MAX_RETRIES=3
FLIGHTS_RETRY_DELAY=1
```

### Step 13: Create Docker Configuration

Create a Dockerfile for the Flights MCP Server:

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

## Testing the Implementation

### Manual Testing

Run these commands to test the Flights MCP Server:

```bash
# Start the server
node src/mcp/flights/server.js

# In another terminal, run the test script
python -m src.mcp.flights.tests.test_client
```

### Integration Testing

Test the Flights MCP Server with the TripSage travel agent:

```python
# tests/integration/test_flights_integration.py
import pytest
import asyncio
from datetime import date, timedelta

from src.agents.travel_agent import TravelAgent
from src.mcp.flights.client import FlightsMCPClient

@pytest.mark.asyncio
async def test_flight_search_integration():
    """Test flight search integration with the travel agent."""
    # Create the travel agent
    agent = TravelAgent()

    # Create the flights client
    flights_client = FlightsMCPClient()

    # Get tomorrow's date
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    next_week = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")

    # Search for flights
    result = await flights_client.search_flights(
        origin="LAX",
        destination="JFK",
        departure_date=tomorrow,
        return_date=next_week
    )

    # Check result
    assert "offers" in result
    assert isinstance(result["offers"], list)

    # Test interaction with the agent
    response = await agent.agent.run(f"I want to fly from LAX to JFK tomorrow")

    # Check that the response contains flight information
    assert "LAX" in response
    assert "JFK" in response
```

## Performance Optimization

### Performance Testing

Create a script to test performance of the Flights MCP Server:

```python
# src/mcp/flights/tests/test_performance.py
import asyncio
import time
from datetime import date, timedelta
import statistics

from src.mcp.flights.client import FlightsMCPClient

async def test_search_performance(iterations=10):
    """Test search performance."""
    client = FlightsMCPClient()

    # Get tomorrow's date
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    next_week = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")

    # Test parameters
    airports = [
        ("LAX", "JFK"),  # Los Angeles to New York
        ("SFO", "LHR"),  # San Francisco to London
        ("ORD", "CDG"),  # Chicago to Paris
        ("ATL", "NRT"),  # Atlanta to Tokyo
        ("DFW", "SYD")   # Dallas to Sydney
    ]

    results = []

    for origin, destination in airports:
        print(f"Testing {origin} to {destination}...")
        durations = []

        for i in range(iterations):
            start_time = time.time()

            result = await client.search_flights(
                origin=origin,
                destination=destination,
                departure_date=tomorrow,
                return_date=next_week
            )

            end_time = time.time()
            duration = end_time - start_time
            durations.append(duration)

            print(f"  Iteration {i+1}: {duration:.2f}s")

            # Short delay between requests to avoid rate limiting
            await asyncio.sleep(1)

        avg_duration = statistics.mean(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        print(f"  Results for {origin} to {destination}:")
        print(f"    Average: {avg_duration:.2f}s")
        print(f"    Min: {min_duration:.2f}s")
        print(f"    Max: {max_duration:.2f}s")

        results.append({
            "route": f"{origin}-{destination}",
            "average": avg_duration,
            "min": min_duration,
            "max": max_duration
        })

    print("\nSummary:")
    for result in results:
        print(f"{result['route']}: Avg {result['average']:.2f}s (Min: {result['min']:.2f}s, Max: {result['max']:.2f}s)")

if __name__ == "__main__":
    asyncio.run(test_search_performance())
```

## Security Considerations

### Add Security Validation

Update the client to include additional security validation:

```python
# Add to src/mcp/flights/client.py
def _validate_security(self):
    """Validate security configuration.

    Raises:
        ValueError: If security configuration is invalid
    """
    if not self._config.duffel_api_key:
        raise ValueError("DUFFEL_API_KEY environment variable is required")
```

## Conclusion

This implementation guide provides a comprehensive approach to setting up the Flights MCP Server for TripSage, including:

1. **Project Structure**: Clear organization of files and directories
2. **Configuration**: Environment-based configuration with proper validation
3. **API Integration**: Robust Duffel API integration with error handling
4. **Caching**: Redis-based caching for improved performance
5. **Testing**: Unit and integration tests for verification
6. **Performance**: Performance testing and optimization
7. **Security**: Security validation and best practices

Follow this guide step-by-step to implement a scalable, maintainable, and efficient Flights MCP Server for the TripSage travel planning system.
