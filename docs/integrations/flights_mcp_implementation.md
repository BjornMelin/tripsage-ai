# Flights MCP Server Implementation

This document provides the detailed implementation specification for the Flights MCP Server in TripSage.

## Overview

The Flights MCP Server provides comprehensive flight search, booking, and management capabilities for the TripSage platform. It integrates with the Duffel API to access content from more than 300 airlines through a single platform, including NDC, GDS, and LCC distribution channels.

## MCP Tools Exposed

```typescript
// MCP Tool Definitions
{
  "name": "mcp__flights__search_flights",
  "parameters": {
    "origin": {"type": "string", "description": "Origin airport code (e.g., 'LAX')"},
    "destination": {"type": "string", "description": "Destination airport code (e.g., 'JFK')"},
    "departure_date": {"type": "string", "description": "Departure date in YYYY-MM-DD format"},
    "return_date": {"type": "string", "description": "Return date in YYYY-MM-DD format for round trips", "required": false},
    "adults": {"type": "integer", "description": "Number of adult passengers", "default": 1},
    "children": {"type": "integer", "description": "Number of child passengers (2-11 years)", "default": 0},
    "infants": {"type": "integer", "description": "Number of infant passengers (<2 years)", "default": 0},
    "cabin_class": {"type": "string", "enum": ["economy", "premium_economy", "business", "first"], "default": "economy", "description": "Preferred cabin class"},
    "max_connections": {"type": "integer", "description": "Maximum number of connections per slice", "default": null},
    "airline_codes": {"type": "array", "items": {"type": "string"}, "description": "Limit results to specific airlines (IATA codes)", "default": []},
    "currency": {"type": "string", "description": "Currency for prices (ISO 4217 code)", "default": "USD"}
  },
  "required": ["origin", "destination", "departure_date"]
},
{
  "name": "mcp__flights__search_multi_city",
  "parameters": {
    "slices": {"type": "array", "items": {"type": "object", "properties": {
      "origin": {"type": "string", "description": "Origin airport code"},
      "destination": {"type": "string", "description": "Destination airport code"},
      "departure_date": {"type": "string", "description": "Departure date in YYYY-MM-DD format"}
    }, "required": ["origin", "destination", "departure_date"]}},
    "adults": {"type": "integer", "description": "Number of adult passengers", "default": 1},
    "children": {"type": "integer", "description": "Number of child passengers (2-11 years)", "default": 0},
    "infants": {"type": "integer", "description": "Number of infant passengers (<2 years)", "default": 0},
    "cabin_class": {"type": "string", "enum": ["economy", "premium_economy", "business", "first"], "default": "economy", "description": "Preferred cabin class"},
    "max_connections": {"type": "integer", "description": "Maximum number of connections per slice", "default": null},
    "currency": {"type": "string", "description": "Currency for prices (ISO 4217 code)", "default": "USD"}
  },
  "required": ["slices"]
},
{
  "name": "mcp__flights__get_offer_details",
  "parameters": {
    "offer_id": {"type": "string", "description": "ID of the flight offer to get details for"}
  },
  "required": ["offer_id"]
},
{
  "name": "mcp__flights__get_fare_rules",
  "parameters": {
    "offer_id": {"type": "string", "description": "ID of the flight offer to get fare rules for"}
  },
  "required": ["offer_id"]
},
{
  "name": "mcp__flights__create_order",
  "parameters": {
    "offer_id": {"type": "string", "description": "ID of the flight offer to book"},
    "passengers": {"type": "array", "items": {"type": "object"}, "description": "Passenger details including names, email, phone, etc."},
    "payment": {"type": "object", "description": "Payment details including type, amount, and currency"}
  },
  "required": ["offer_id", "passengers", "payment"]
},
{
  "name": "mcp__flights__get_order",
  "parameters": {
    "order_id": {"type": "string", "description": "ID of the flight booking to retrieve"}
  },
  "required": ["order_id"]
},
{
  "name": "mcp__flights__track_prices",
  "parameters": {
    "origin": {"type": "string", "description": "Origin airport code (e.g., 'LAX')"},
    "destination": {"type": "string", "description": "Destination airport code (e.g., 'JFK')"},
    "departure_date": {"type": "string", "description": "Departure date in YYYY-MM-DD format"},
    "return_date": {"type": "string", "description": "Return date in YYYY-MM-DD format", "required": false},
    "cabin_class": {"type": "string", "enum": ["economy", "premium_economy", "business", "first"], "default": "economy", "description": "Preferred cabin class"},
    "notify_when": {"type": "string", "enum": ["price_decrease", "any_change"], "default": "price_decrease", "description": "When to send notifications"},
    "notification_threshold": {"type": "number", "description": "Minimum percentage decrease to trigger notification", "default": 5}
  },
  "required": ["origin", "destination", "departure_date"]
}
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

## Connection Points to Existing Architecture

### Agent Integration

- **Travel Agent**:

  - Primary integration point for flight search and booking
  - Handles complex multi-city itineraries
  - Provides flight recommendations based on price and convenience

- **Budget Agent**:

  - Price tracking and alerting for preferred routes
  - Optimization for best value flights
  - Budget allocation across flight components

- **Itinerary Agent**:
  - Flight details for itinerary creation
  - Coordination with accommodation and activity timing
  - Trip optimization based on flight schedules

## File Structure

```plaintext
src/
  mcp/
    flights/
      __init__.py                  # Package initialization
      server.py                    # MCP server implementation
      config.py                    # Server configuration settings
      handlers/
        __init__.py                # Module initialization
        search_handler.py          # Flight search handler
        multi_city_handler.py      # Multi-city search handler
        offer_handler.py           # Offer details handler
        booking_handler.py         # Booking creation handler
        order_handler.py           # Order management handler
        price_tracker_handler.py   # Price tracking handler
      services/
        __init__.py                # Module initialization
        duffel_service.py          # Duffel API client
        cache_service.py           # Caching service
        price_tracking_service.py  # Price tracking service
      models/
        __init__.py                # Module initialization
        flight.py                  # Flight data models
        offer.py                   # Offer data models
        passenger.py               # Passenger data models
        order.py                   # Order data models
        price_alert.py             # Price alert models
      transformers/
        __init__.py                # Module initialization
        duffel_transformer.py      # Transforms Duffel API responses
        response_formatter.py      # Formats responses for agents
      storage/
        __init__.py                # Module initialization
        supabase.py                # Supabase database integration
        memory.py                  # Knowledge graph integration
      utils/
        __init__.py                # Module initialization
        validation.py              # Input validation utilities
        date_utils.py              # Date handling utilities
        error_handling.py          # Error handling utilities
        logging.py                 # Logging configuration
```

## Key Functions and Interfaces

### Duffel Service Interface

```typescript
// duffel_service.ts
import { OfferRequest, Offer, Order, SeatMap, PaymentIntent } from "../models";
import axios from "axios";
import { config } from "../config";

export class DuffelService {
  private api: any;
  private baseUrl: string = "https://api.duffel.com/air";
  private headers: any;

  constructor() {
    this.headers = {
      Authorization: `Bearer ${config.DUFFEL_API_KEY}`,
      "Duffel-Version": "2023-06-02",
      "Content-Type": "application/json",
      Accept: "application/json",
      "Accept-Encoding": "gzip",
    };
  }

  async createOfferRequest(params: any): Promise<OfferRequest> {
    try {
      // Construct slices from parameters
      const slices = [];

      // If it's a simple one-way or round trip
      if (params.origin && params.destination) {
        slices.push({
          origin: params.origin,
          destination: params.destination,
          departure_date: params.departure_date,
        });

        if (params.return_date) {
          slices.push({
            origin: params.destination,
            destination: params.origin,
            departure_date: params.return_date,
          });
        }
      }
      // If it's a multi-city trip
      else if (params.slices && Array.isArray(params.slices)) {
        params.slices.forEach((slice: any) => {
          slices.push({
            origin: slice.origin,
            destination: slice.destination,
            departure_date: slice.departure_date,
          });
        });
      }

      // Construct passengers
      const passengers = [];
      for (let i = 0; i < (params.adults || 1); i++) {
        passengers.push({ type: "adult" });
      }

      for (let i = 0; i < (params.children || 0); i++) {
        passengers.push({ type: "child" });
      }

      for (let i = 0; i < (params.infants || 0); i++) {
        passengers.push({ type: "infant_without_seat" });
      }

      // Create offer request payload
      const payload = {
        slices,
        passengers,
        cabin_class: params.cabin_class || "economy",
        return_offers: true,
      };

      // Add optional parameters if provided
      if (
        params.max_connections !== null &&
        params.max_connections !== undefined
      ) {
        payload["max_connections"] = params.max_connections;
      }

      // Make API request
      const response = await axios.post(
        `${this.baseUrl}/offer_requests`,
        { data: payload },
        { headers: this.headers }
      );

      return response.data.data;
    } catch (error) {
      console.error("Error creating offer request:", error);
      throw new Error(`Failed to create offer request: ${error.message}`);
    }
  }

  async getOffers(offerRequestId: string): Promise<Offer[]> {
    try {
      const response = await axios.get(
        `${this.baseUrl}/offers?offer_request_id=${offerRequestId}`,
        { headers: this.headers }
      );

      return response.data.data;
    } catch (error) {
      console.error("Error getting offers:", error);
      throw new Error(`Failed to get offers: ${error.message}`);
    }
  }

  async getOffer(offerId: string): Promise<Offer> {
    try {
      const response = await axios.get(`${this.baseUrl}/offers/${offerId}`, {
        headers: this.headers,
      });

      return response.data.data;
    } catch (error) {
      console.error("Error getting offer details:", error);
      throw new Error(`Failed to get offer details: ${error.message}`);
    }
  }

  async createOrder(
    offerId: string,
    passengers: any[],
    payment: any
  ): Promise<Order> {
    try {
      const payload = {
        selected_offers: [offerId],
        passengers,
        payments: [payment],
      };

      const response = await axios.post(
        `${this.baseUrl}/orders`,
        { data: payload },
        { headers: this.headers }
      );

      return response.data.data;
    } catch (error) {
      console.error("Error creating order:", error);
      throw new Error(`Failed to create order: ${error.message}`);
    }
  }

  async getOrder(orderId: string): Promise<Order> {
    try {
      const response = await axios.get(`${this.baseUrl}/orders/${orderId}`, {
        headers: this.headers,
      });

      return response.data.data;
    } catch (error) {
      console.error("Error getting order:", error);
      throw new Error(`Failed to get order: ${error.message}`);
    }
  }

  // Additional methods for other endpoints...
}
```

### Search Handler

```typescript
// search_handler.ts
import { DuffelService } from "../services/duffel_service";
import { CacheService } from "../services/cache_service";
import { DuffelTransformer } from "../transformers/duffel_transformer";
import { validateSearchParams } from "../utils/validation";
import { getOfferPriceStatistics } from "../utils/price_utils";

export class SearchHandler {
  private duffelService: DuffelService;
  private cacheService: CacheService;
  private transformer: DuffelTransformer;

  constructor() {
    this.duffelService = new DuffelService();
    this.cacheService = new CacheService();
    this.transformer = new DuffelTransformer();
  }

  async handleSearch(params: any): Promise<any> {
    try {
      // Validate search parameters
      validateSearchParams(params);

      // Create cache key
      const cacheKey = this.createCacheKey(params);

      // Check cache
      const cachedResult = await this.cacheService.get(cacheKey);
      if (cachedResult) {
        return cachedResult;
      }

      // Create offer request
      const offerRequest = await this.duffelService.createOfferRequest(params);

      // Get offers
      const offers = await this.duffelService.getOffers(offerRequest.id);

      // Transform offers to a more user-friendly format
      const transformedOffers = this.transformer.transformOffers(
        offers,
        params.currency || "USD"
      );

      // Calculate price statistics
      const priceStats = getOfferPriceStatistics(transformedOffers);

      // Prepare result
      const result = {
        offers: transformedOffers,
        request_id: offerRequest.id,
        price_statistics: priceStats,
        search_params: params,
      };

      // Cache result for 5 minutes
      await this.cacheService.set(cacheKey, result, 300);

      return result;
    } catch (error) {
      console.error("Error handling search:", error);
      throw new Error(`Failed to handle search: ${error.message}`);
    }
  }

  private createCacheKey(params: any): string {
    // Create a deterministic cache key based on search parameters
    const key = {
      origin: params.origin,
      destination: params.destination,
      departure_date: params.departure_date,
      return_date: params.return_date,
      adults: params.adults || 1,
      children: params.children || 0,
      infants: params.infants || 0,
      cabin_class: params.cabin_class || "economy",
      max_connections: params.max_connections,
    };

    return `flights_search:${JSON.stringify(key)}`;
  }
}
```

### Price Tracking Service

```typescript
// price_tracking_service.ts
import { DuffelService } from "./duffel_service";
import { supabase } from "../storage/supabase";
import { config } from "../config";
import { createNotification } from "../utils/notification_utils";

export class PriceTrackingService {
  private duffelService: DuffelService;

  constructor() {
    this.duffelService = new DuffelService();
  }

  async trackPrices(params: any): Promise<any> {
    try {
      // Create initial search to get baseline prices
      const offerRequest = await this.duffelService.createOfferRequest(params);
      const offers = await this.duffelService.getOffers(offerRequest.id);

      // Find the best price
      let bestPrice = null;
      let bestOffer = null;

      for (const offer of offers) {
        const price = offer.total_amount;
        if (bestPrice === null || price < bestPrice) {
          bestPrice = price;
          bestOffer = offer;
        }
      }

      if (!bestPrice || !bestOffer) {
        throw new Error("No valid offers found for price tracking");
      }

      // Create price tracking record
      const trackingRecord = {
        route: {
          origin: params.origin,
          destination: params.destination,
          departure_date: params.departure_date,
          return_date: params.return_date,
          cabin_class: params.cabin_class || "economy",
        },
        initial_price: {
          amount: bestPrice,
          currency: bestOffer.total_currency,
          timestamp: new Date().toISOString(),
        },
        user_id: params.user_id,
        notification_threshold: params.notification_threshold || 5,
        notify_when: params.notify_when || "price_decrease",
        status: "active",
        last_checked: new Date().toISOString(),
        price_history: [
          {
            amount: bestPrice,
            currency: bestOffer.total_currency,
            timestamp: new Date().toISOString(),
            offer_id: bestOffer.id,
          },
        ],
      };

      // Save to database
      const { data, error } = await supabase
        .from("price_tracking")
        .insert(trackingRecord)
        .select();

      if (error) {
        throw new Error(`Database error: ${error.message}`);
      }

      return {
        tracking_id: data[0].id,
        message: "Price tracking has been set up successfully",
        initial_price: trackingRecord.initial_price,
        parameters: trackingRecord.route,
      };
    } catch (error) {
      console.error("Error setting up price tracking:", error);
      throw new Error(`Failed to set up price tracking: ${error.message}`);
    }
  }

  async checkPriceUpdates(): Promise<void> {
    try {
      // Get all active price tracking records
      const { data: trackingRecords, error } = await supabase
        .from("price_tracking")
        .select("*")
        .eq("status", "active");

      if (error) {
        throw new Error(`Database error: ${error.message}`);
      }

      for (const record of trackingRecords) {
        await this.checkSinglePriceUpdate(record);
      }
    } catch (error) {
      console.error("Error checking price updates:", error);
    }
  }

  private async checkSinglePriceUpdate(record: any): Promise<void> {
    try {
      // Create search to get current prices
      const params = {
        origin: record.route.origin,
        destination: record.route.destination,
        departure_date: record.route.departure_date,
        return_date: record.route.return_date,
        cabin_class: record.route.cabin_class,
        adults: 1,
      };

      const offerRequest = await this.duffelService.createOfferRequest(params);
      const offers = await this.duffelService.getOffers(offerRequest.id);

      // Find the best current price
      let bestPrice = null;
      let bestOffer = null;

      for (const offer of offers) {
        const price = offer.total_amount;
        if (bestPrice === null || price < bestPrice) {
          bestPrice = price;
          bestOffer = offer;
        }
      }

      if (!bestPrice || !bestOffer) {
        console.log(
          `No valid offers found for route ${params.origin}-${params.destination}`
        );
        return;
      }

      // Add to price history
      const priceHistoryEntry = {
        amount: bestPrice,
        currency: bestOffer.total_currency,
        timestamp: new Date().toISOString(),
        offer_id: bestOffer.id,
      };

      const newPriceHistory = [...record.price_history, priceHistoryEntry];

      // Update last checked timestamp
      const updates = {
        last_checked: new Date().toISOString(),
        price_history: newPriceHistory,
      };

      // Check if we need to send a notification
      const initialPrice = record.initial_price.amount;
      const priceDecreasePercentage =
        ((initialPrice - bestPrice) / initialPrice) * 100;

      if (
        (record.notify_when === "price_decrease" &&
          priceDecreasePercentage >= record.notification_threshold) ||
        record.notify_when === "any_change"
      ) {
        // Create notification
        await createNotification({
          user_id: record.user_id,
          type: "price_alert",
          content: {
            route: `${params.origin} to ${params.destination}`,
            departure_date: params.departure_date,
            initial_price: {
              amount: initialPrice,
              currency: record.initial_price.currency,
            },
            current_price: {
              amount: bestPrice,
              currency: bestOffer.total_currency,
            },
            price_change: {
              amount: initialPrice - bestPrice,
              percentage: priceDecreasePercentage,
            },
            offer_id: bestOffer.id,
          },
        });

        // Update notification sent status
        updates["last_notification"] = new Date().toISOString();
      }

      // Update record in database
      await supabase.from("price_tracking").update(updates).eq("id", record.id);
    } catch (error) {
      console.error(
        `Error checking price update for record ${record.id}:`,
        error
      );
    }
  }
}
```

### Main Server Implementation

```typescript
// server.ts
import express from "express";
import bodyParser from "body-parser";
import { SearchHandler } from "./handlers/search_handler";
import { MultiCityHandler } from "./handlers/multi_city_handler";
import { OfferHandler } from "./handlers/offer_handler";
import { BookingHandler } from "./handlers/booking_handler";
import { OrderHandler } from "./handlers/order_handler";
import { PriceTrackerHandler } from "./handlers/price_tracker_handler";
import { setupScheduledTasks } from "./utils/scheduler";
import { logRequest, logError, logInfo } from "./utils/logging";
import { config } from "./config";

const app = express();
app.use(bodyParser.json());

// Initialize handlers
const searchHandler = new SearchHandler();
const multiCityHandler = new MultiCityHandler();
const offerHandler = new OfferHandler();
const bookingHandler = new BookingHandler();
const orderHandler = new OrderHandler();
const priceTrackerHandler = new PriceTrackerHandler();

// Set up scheduled tasks (e.g., price update checks)
setupScheduledTasks();

// Handle MCP tool requests
app.post("/api/mcp/flights/search_flights", async (req, res) => {
  try {
    logRequest("search_flights", req.body);
    const result = await searchHandler.handleSearch(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in search_flights: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/flights/search_multi_city", async (req, res) => {
  try {
    logRequest("search_multi_city", req.body);
    const result = await multiCityHandler.handleSearch(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in search_multi_city: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/flights/get_offer_details", async (req, res) => {
  try {
    logRequest("get_offer_details", req.body);
    const result = await offerHandler.handleGetOffer(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in get_offer_details: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/flights/get_fare_rules", async (req, res) => {
  try {
    logRequest("get_fare_rules", req.body);
    const result = await offerHandler.handleGetFareRules(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in get_fare_rules: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/flights/create_order", async (req, res) => {
  try {
    logRequest("create_order", req.body);
    const result = await bookingHandler.handleCreateOrder(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in create_order: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/flights/get_order", async (req, res) => {
  try {
    logRequest("get_order", req.body);
    const result = await orderHandler.handleGetOrder(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in get_order: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/flights/track_prices", async (req, res) => {
  try {
    logRequest("track_prices", req.body);
    const result = await priceTrackerHandler.handleTrackPrices(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in track_prices: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

// Start server
const PORT = process.env.PORT || 3002;
app.listen(PORT, () => {
  logInfo(`Flights MCP Server running on port ${PORT}`);
});
```

## Data Formats

### Input Format Examples

```json
// search_flights input
{
  "origin": "LAX",
  "destination": "JFK",
  "departure_date": "2025-06-15",
  "return_date": "2025-06-22",
  "adults": 2,
  "children": 1,
  "infants": 0,
  "cabin_class": "economy",
  "max_connections": 1,
  "currency": "USD"
}

// search_multi_city input
{
  "slices": [
    {
      "origin": "LAX",
      "destination": "JFK",
      "departure_date": "2025-06-15"
    },
    {
      "origin": "JFK",
      "destination": "MIA",
      "departure_date": "2025-06-20"
    },
    {
      "origin": "MIA",
      "destination": "LAX",
      "departure_date": "2025-06-25"
    }
  ],
  "adults": 2,
  "cabin_class": "economy",
  "currency": "USD"
}

// create_order input
{
  "offer_id": "off_0000AEdEKsHY9Kk6aK6fEO",
  "passengers": [
    {
      "id": "pas_0000AEdEKsHY9Kk6aK6fEP",
      "title": "mr",
      "given_name": "John",
      "family_name": "Doe",
      "gender": "m",
      "born_on": "1980-01-01",
      "email": "john.doe@example.com",
      "phone_number": "+1234567890"
    },
    {
      "id": "pas_0000AEdEKsHY9Kk6aK6fEQ",
      "title": "ms",
      "given_name": "Jane",
      "family_name": "Doe",
      "gender": "f",
      "born_on": "1985-01-01",
      "email": "jane.doe@example.com",
      "phone_number": "+1234567891"
    }
  ],
  "payment": {
    "type": "balance",
    "currency": "USD",
    "amount": 1234.56
  }
}
```

### Output Format Examples

```json
// search_flights output
{
  "offers": [
    {
      "id": "off_0000AEdEKsHY9Kk6aK6fEO",
      "price": {
        "amount": 567.89,
        "currency": "USD",
        "base_amount": 450.00,
        "taxes_amount": 117.89,
        "fees_amount": 0.00
      },
      "airline": {
        "code": "UA",
        "name": "United Airlines"
      },
      "slices": [
        {
          "origin": {
            "code": "LAX",
            "name": "Los Angeles International Airport",
            "city": "Los Angeles",
            "country": "US"
          },
          "destination": {
            "code": "JFK",
            "name": "John F. Kennedy International Airport",
            "city": "New York",
            "country": "US"
          },
          "departure": {
            "date": "2025-06-15",
            "time": "08:00",
            "datetime": "2025-06-15T08:00:00-07:00"
          },
          "arrival": {
            "date": "2025-06-15",
            "time": "16:30",
            "datetime": "2025-06-15T16:30:00-04:00"
          },
          "duration_minutes": 330,
          "segments": [
            {
              "origin": "LAX",
              "destination": "JFK",
              "departure": "2025-06-15T08:00:00-07:00",
              "arrival": "2025-06-15T16:30:00-04:00",
              "flight_number": "UA123",
              "aircraft": {
                "code": "B777",
                "name": "Boeing 777"
              },
              "duration_minutes": 330
            }
          ],
          "stops": [],
          "is_return": false
        },
        {
          "origin": {
            "code": "JFK",
            "name": "John F. Kennedy International Airport",
            "city": "New York",
            "country": "US"
          },
          "destination": {
            "code": "LAX",
            "name": "Los Angeles International Airport",
            "city": "Los Angeles",
            "country": "US"
          },
          "departure": {
            "date": "2025-06-22",
            "time": "10:30",
            "datetime": "2025-06-22T10:30:00-04:00"
          },
          "arrival": {
            "date": "2025-06-22",
            "time": "13:45",
            "datetime": "2025-06-22T13:45:00-07:00"
          },
          "duration_minutes": 375,
          "segments": [
            {
              "origin": "JFK",
              "destination": "LAX",
              "departure": "2025-06-22T10:30:00-04:00",
              "arrival": "2025-06-22T13:45:00-07:00",
              "flight_number": "UA456",
              "aircraft": {
                "code": "B777",
                "name": "Boeing 777"
              },
              "duration_minutes": 375
            }
          ],
          "stops": [],
          "is_return": true
        }
      ],
      "passengers": {
        "adults": 2,
        "children": 1,
        "infants": 0
      },
      "cabin_class": "economy",
      "baggage_allowance": {
        "checked": [
          {
            "quantity": 1,
            "weight": {
              "value": 23,
              "unit": "kg"
            },
            "dimensions": null,
            "passenger_type": "adult"
          },
          {
            "quantity": 1,
            "weight": {
              "value": 23,
              "unit": "kg"
            },
            "dimensions": null,
            "passenger_type": "child"
          }
        ],
        "carry_on": [
          {
            "quantity": 1,
            "weight": {
              "value": 7,
              "unit": "kg"
            },
            "dimensions": null,
            "passenger_type": "all"
          }
        ]
      },
      "total_duration_minutes": 705,
      "departure_date": "2025-06-15",
      "return_date": "2025-06-22"
    }
    // Additional offer objects...
  ],
  "request_id": "offreq_0000AEdEKsHY9Kk6aK6fEN",
  "price_statistics": {
    "minimum": 567.89,
    "maximum": 987.65,
    "average": 778.23,
    "median": 789.45
  },
  "search_params": {
    "origin": "LAX",
    "destination": "JFK",
    "departure_date": "2025-06-15",
    "return_date": "2025-06-22",
    "adults": 2,
    "children": 1,
    "infants": 0,
    "cabin_class": "economy",
    "max_connections": 1,
    "currency": "USD"
  }
}

// get_offer_details output
{
  "id": "off_0000AEdEKsHY9Kk6aK6fEO",
  "price": {
    "amount": 567.89,
    "currency": "USD",
    "base_amount": 450.00,
    "taxes_amount": 117.89,
    "fees_amount": 0.00,
    "breakdown": {
      "base": {
        "amount": 450.00,
        "currency": "USD"
      },
      "taxes": [
        {
          "code": "YQ",
          "name": "Fuel Surcharge",
          "amount": 75.00,
          "currency": "USD"
        },
        {
          "code": "XF",
          "name": "Passenger Facility Charge",
          "amount": 42.89,
          "currency": "USD"
        }
      ],
      "fees": []
    }
  },
  "airline": {
    "code": "UA",
    "name": "United Airlines",
    "logo_url": "https://example.com/airlines/ua.png"
  },
  "slices": [
    // Same structure as in search_flights response, but with more details
  ],
  "passengers": {
    "adult": {
      "count": 2,
      "fare_basis": "Y1BASIC",
      "cabin_class": "economy",
      "booking_class": "Y"
    },
    "child": {
      "count": 1,
      "fare_basis": "Y1BASIC",
      "cabin_class": "economy",
      "booking_class": "Y"
    }
  },
  "fare_brand": {
    "name": "Basic Economy",
    "conditions": {
      "changeable": false,
      "refundable": false,
      "upgradeable": false
    }
  },
  "baggage_allowance": {
    // Same structure as in search_flights response, but with more details
  },
  "conditions": {
    "change_before_departure": {
      "allowed": false,
      "penalty_amount": null,
      "penalty_currency": null
    },
    "refund_before_departure": {
      "allowed": false,
      "penalty_amount": null,
      "penalty_currency": null
    }
  },
  "passenger_identity_documents_required": true,
  "payment_requirements": {
    "payment_required_by": "2025-06-10T23:59:59Z",
    "price_guarantee_expires_at": "2025-06-08T23:59:59Z"
  }
}

// create_order output
{
  "id": "ord_0000AEdEKsHY9Kk6aK6fER",
  "booking_reference": "ABC123",
  "airline_booking_reference": "DEFGHI",
  "status": "confirmed",
  "price": {
    "amount": 1234.56,
    "currency": "USD"
  },
  "passengers": [
    {
      "id": "pas_0000AEdEKsHY9Kk6aK6fEP",
      "title": "mr",
      "given_name": "John",
      "family_name": "Doe",
      "ticket_number": "0162345678901",
      "documents": []
    },
    {
      "id": "pas_0000AEdEKsHY9Kk6aK6fEQ",
      "title": "ms",
      "given_name": "Jane",
      "family_name": "Doe",
      "ticket_number": "0162345678902",
      "documents": []
    }
  ],
  "slices": [
    // Same structure as in search_flights response
  ],
  "created_at": "2025-06-01T12:34:56Z",
  "payment_status": "paid",
  "checkable_bags": true,
  "unbundled_baggage": false,
  "additional_services": []
}

// track_prices output
{
  "tracking_id": "pt_0000AEdEKsHY9Kk6aK6fES",
  "message": "Price tracking has been set up successfully",
  "initial_price": {
    "amount": 567.89,
    "currency": "USD",
    "timestamp": "2025-06-01T12:34:56Z"
  },
  "parameters": {
    "origin": "LAX",
    "destination": "JFK",
    "departure_date": "2025-06-15",
    "return_date": "2025-06-22",
    "cabin_class": "economy"
  }
}
```

## Implementation Considerations

### Caching Strategy

- **Search Results**: Cache for 5-15 minutes depending on search popularity
- **Offer Details**: Cache for 2 minutes due to potential price changes
- **Flight Schedules**: Cache for longer periods (4-24 hours)
- **Price Tracking Data**: Store in database for long-term analysis
- **Use Redis** for distributed caching in production environments

### Error Handling

- **Rate Limiting**: Implement exponential backoff for API rate limit errors
- **Offer Staleness**: Special handling for stale offers with clear user feedback
- **Payment Failures**: Detailed error handling for payment issues
- **Network Timeouts**: Retry logic for network failures

### Performance Optimization

- **Parallel Processing**: Fetch offers from multiple airlines simultaneously
- **Batch Updates**: Group price tracking checks for efficiency
- **Response Compression**: Use gzip/brotli for network efficiency
- **Selective Fields**: Only request needed fields from Duffel API

### Security

- **API Key Management**: Secure storage and rotation of Duffel API keys
- **Payment Information**: Proper handling of sensitive payment data
- **User Data**: Secure storage of passenger information
- **Input Validation**: Thorough validation of all user inputs

## Integration with Agent Architecture

The Flights MCP Server will be exposed to the TripSage agents through a client library that handles the MCP communication protocol. This integration will be implemented in the `src/agents/mcp_integration.py` file:

```python
# src/agents/mcp_integration.py

class FlightsMCPClient:
    """Client for interacting with the Flights MCP Server"""

    def __init__(self, server_url):
        self.server_url = server_url

    async def search_flights(self, origin, destination, departure_date, return_date=None,
                           adults=1, children=0, infants=0, cabin_class="economy",
                           max_connections=None, currency="USD"):
        """Search for flights between origin and destination"""
        try:
            # Implement MCP call to flights server
            result = await call_mcp_tool(
                "mcp__flights__search_flights",
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
                    "currency": currency
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error searching flights: {str(e)}")
            raise

    async def search_multi_city(self, slices, adults=1, children=0, infants=0,
                              cabin_class="economy", currency="USD"):
        """Search for multi-city flight itineraries"""
        try:
            # Implement MCP call to flights server
            result = await call_mcp_tool(
                "mcp__flights__search_multi_city",
                {
                    "slices": slices,
                    "adults": adults,
                    "children": children,
                    "infants": infants,
                    "cabin_class": cabin_class,
                    "currency": currency
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error searching multi-city flights: {str(e)}")
            raise

    async def get_offer_details(self, offer_id):
        """Get detailed information about a flight offer"""
        try:
            # Implement MCP call to flights server
            result = await call_mcp_tool(
                "mcp__flights__get_offer_details",
                {
                    "offer_id": offer_id
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error getting offer details: {str(e)}")
            raise

    # Additional methods for other MCP tools...
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

CMD ["node", "dist/server.js"]
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
