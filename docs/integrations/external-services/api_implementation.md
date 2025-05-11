# API Implementation Guide

This document provides detailed implementation instructions for integrating various travel APIs with TripSage, including code examples, authentication flows, and best practices.

## Table of Contents

- [API Implementation Guide](#api-implementation-guide)
  - [Table of Contents](#table-of-contents)
  - [Environment Setup](#environment-setup)
    - [Required Environment Variables](#required-environment-variables)
    - [Project Structure](#project-structure)
  - [Flight API Implementation](#flight-api-implementation)
    - [Duffel API Integration](#duffel-api-integration)
      - [1. Installation](#1-installation)
      - [2. Service Implementation](#2-service-implementation)
      - [3. Exposed API Endpoints](#3-exposed-api-endpoints)
  - [Accommodation API Implementation](#accommodation-api-implementation)
    - [OpenBnB MCP Server Integration](#openbnb-mcp-server-integration)
      - [1. Installation](#1-installation-1)
      - [2. MCP Server Configuration](#2-mcp-server-configuration)
      - [3. Service Implementation](#3-service-implementation)
    - [Apify Booking.com Scraper Integration](#apify-bookingcom-scraper-integration)
      - [1. Installation](#1-installation-2)
      - [2. Service Implementation](#2-service-implementation-1)
  - [Maps API Implementation](#maps-api-implementation)
    - [Google Maps API Integration](#google-maps-api-integration)
      - [1. Installation](#1-installation-3)
      - [2. Service Implementation](#2-service-implementation-2)
  - [Search Integration](#search-integration)
    - [Linkup Search Implementation](#linkup-search-implementation)
      - [1. Service Implementation](#1-service-implementation)
  - [API Gateway Layer](#api-gateway-layer)
  - [Testing and Validation](#testing-and-validation)
  - [API Caching and Rate Limiting Implementation](#api-caching-and-rate-limiting-implementation)

## Environment Setup

Before implementing any API integrations, set up the environment variables and project structure:

### Required Environment Variables

Create a `.env` file in the project root with placeholders for all API credentials:

```plaintext
# Duffel API
DUFFEL_ACCESS_TOKEN=your_token_here

# Apify
APIFY_API_TOKEN=your_token_here

# Google Maps
GOOGLE_MAPS_API_KEY=your_key_here

# Other services
OPENAI_API_KEY=your_key_here
```

### Project Structure

```plaintext
src/
  api/              # API Gateway for client communication
  services/         # Service layer for external API integration
    flights/        # Flight-related services (Duffel)
    accommodations/ # Accommodation services (OpenBnB, Apify)
    maps/           # Location services (Google Maps)
    search/         # Search services (Linkup)
  utils/            # Shared utilities
    cache.js        # Caching utilities
    logger.js       # Logging utilities
    error.js        # Error handling utilities
  agents/           # Agent implementations
    travel_agent.js # Main travel planning agent
```

## Flight API Implementation

### Duffel API Integration

#### 1. Installation

```bash
npm install @duffel/api
```

#### 2. Service Implementation

Create a flight service module in `src/services/flights/duffel-service.js`:

```javascript
const { Duffel } = require("@duffel/api");
const { cacheWithTTL } = require("../../utils/cache");

class DuffelService {
  constructor() {
    this.duffel = new Duffel({
      token: process.env.DUFFEL_ACCESS_TOKEN,
    });
  }

  /**
   * Search for flight offers
   * @param {Object} params Search parameters
   * @returns {Promise<Array>} Flight offers
   */
  async searchFlights(params) {
    const {
      origin,
      destination,
      departureDate,
      returnDate = null,
      adults = 1,
      cabinClass = "economy",
    } = params;

    // Build slices array (one-way or round-trip)
    const slices = [
      {
        origin,
        destination,
        departure_date: departureDate,
      },
    ];

    if (returnDate) {
      slices.push({
        origin: destination,
        destination: origin,
        departure_date: returnDate,
      });
    }

    // Create the cache key
    const cacheKey = `flights:${origin}:${destination}:${departureDate}:${returnDate}:${adults}:${cabinClass}`;

    // Try to get from cache first
    const cachedResults = await cacheWithTTL.get(cacheKey);
    if (cachedResults) {
      return JSON.parse(cachedResults);
    }

    try {
      // Create offer request
      const offerRequest = await this.duffel.offerRequests.create({
        slices,
        passengers: Array(adults).fill({ type: "adult" }),
        cabin_class: cabinClass,
        return_offers: true,
      });

      // Get offers with more details
      const offers = await this.duffel.offers.list({
        offer_request_id: offerRequest.data.id,
        limit: 50,
      });

      // Cache results for 15 minutes
      await cacheWithTTL.set(cacheKey, JSON.stringify(offers.data), 900);

      return offers.data;
    } catch (error) {
      console.error("Error fetching flight offers:", error);
      throw new Error(`Failed to fetch flight offers: ${error.message}`);
    }
  }

  /**
   * Get detailed information about a specific offer
   * @param {string} offerId The Duffel offer ID
   * @returns {Promise<Object>} Detailed offer information
   */
  async getOfferDetails(offerId) {
    try {
      const offer = await this.duffel.offers.get(offerId);
      return offer.data;
    } catch (error) {
      console.error(`Error fetching offer ${offerId}:`, error);
      throw new Error(`Failed to fetch offer details: ${error.message}`);
    }
  }

  /**
   * Create an order (booking) from an offer
   * @param {Object} params Booking parameters
   * @returns {Promise<Object>} Order information
   */
  async createBooking(params) {
    const { offerId, passengers, paymentType = "balance" } = params;

    try {
      const order = await this.duffel.orders.create({
        selected_offers: [offerId],
        passengers,
        payments: [
          {
            type: paymentType,
            currency: "USD", // Should be dynamically set based on offer
            amount: "0", // Amount is calculated by Duffel
          },
        ],
      });

      return order.data;
    } catch (error) {
      console.error("Error creating booking:", error);
      throw new Error(`Failed to create booking: ${error.message}`);
    }
  }
}

module.exports = new DuffelService();
```

#### 3. Exposed API Endpoints

Create flight API endpoints in `src/api/routes/flights.js`:

```javascript
const express = require("express");
const router = express.Router();
const duffelService = require("../../services/flights/duffel-service");
const { asyncHandler } = require("../../utils/error");

/**
 * @route   GET /api/flights/search
 * @desc    Search for flights
 * @access  Public
 */
router.get(
  "/search",
  asyncHandler(async (req, res) => {
    const {
      origin,
      destination,
      departureDate,
      returnDate,
      adults = 1,
      cabinClass = "economy",
    } = req.query;

    // Validate required parameters
    if (!origin || !destination || !departureDate) {
      return res.status(400).json({
        error:
          "Missing required parameters: origin, destination, departureDate",
      });
    }

    const offers = await duffelService.searchFlights({
      origin,
      destination,
      departureDate,
      returnDate,
      adults: parseInt(adults, 10),
      cabinClass,
    });

    res.json(offers);
  })
);

/**
 * @route   GET /api/flights/offers/:id
 * @desc    Get details for a specific offer
 * @access  Public
 */
router.get(
  "/offers/:id",
  asyncHandler(async (req, res) => {
    const offerId = req.params.id;
    const offer = await duffelService.getOfferDetails(offerId);
    res.json(offer);
  })
);

/**
 * @route   POST /api/flights/booking
 * @desc    Create a flight booking
 * @access  Private
 */
router.post(
  "/booking",
  asyncHandler(async (req, res) => {
    const { offerId, passengers, paymentType } = req.body;

    // Validate required parameters
    if (!offerId || !passengers || !Array.isArray(passengers)) {
      return res.status(400).json({
        error: "Missing required parameters: offerId, passengers",
      });
    }

    const booking = await duffelService.createBooking({
      offerId,
      passengers,
      paymentType,
    });

    res.status(201).json(booking);
  })
);

module.exports = router;
```

## Accommodation API Implementation

### OpenBnB MCP Server Integration

#### 1. Installation

```bash
npm install -g @openbnb/mcp-server-airbnb
```

#### 2. MCP Server Configuration

Create an MCP client in `src/utils/mcp-client.js`:

```javascript
const { spawn } = require("child_process");
const axios = require("axios");

class MCPClient {
  constructor(config = {}) {
    this.serverProcesses = {};
    this.serverPorts = {};
    this.nextPort = 9000;
    this.config = config;
  }

  /**
   * Start an MCP server if not already running
   * @param {string} serverName The name of the MCP server
   * @returns {Promise<number>} The port number where the server is running
   */
  async startServer(serverName) {
    if (this.serverPorts[serverName]) {
      return this.serverPorts[serverName];
    }

    const serverConfig = this.config[serverName];
    if (!serverConfig) {
      throw new Error(`MCP server configuration not found for: ${serverName}`);
    }

    const port = this.nextPort++;
    const { command, args } = serverConfig;

    // Add port to the args
    const fullArgs = [...args, "--port", port.toString()];

    // Start the server process
    const serverProcess = spawn(command, fullArgs, {
      stdio: ["ignore", "pipe", "pipe"],
    });

    // Store the process reference
    this.serverProcesses[serverName] = serverProcess;
    this.serverPorts[serverName] = port;

    // Log server output for debugging
    serverProcess.stdout.on("data", (data) => {
      console.log(`[${serverName}] ${data.toString().trim()}`);
    });

    serverProcess.stderr.on("data", (data) => {
      console.error(`[${serverName}] ERROR: ${data.toString().trim()}`);
    });

    // Wait for server to start
    await new Promise((resolve) => setTimeout(resolve, 2000));

    return port;
  }

  /**
   * Call an MCP server tool
   * @param {string} serverName The MCP server name
   * @param {string} toolName The tool to call
   * @param {Object} params Tool parameters
   * @returns {Promise<any>} The tool result
   */
  async call(serverName, toolName, params) {
    const port = await this.startServer(serverName);

    try {
      const response = await axios.post(
        `http://localhost:${port}/mcp/${toolName}`,
        params
      );
      return response.data;
    } catch (error) {
      console.error(`Error calling MCP tool ${toolName}:`, error.message);
      throw new Error(`MCP tool call failed: ${error.message}`);
    }
  }

  /**
   * Shutdown all MCP servers
   */
  shutdown() {
    Object.entries(this.serverProcesses).forEach(([name, process]) => {
      process.kill();
      console.log(`MCP server ${name} shut down`);
    });
  }
}

// Create MCP client with server configurations
const mcpClient = new MCPClient({
  airbnb: {
    command: "npx",
    args: ["-y", "@openbnb/mcp-server-airbnb", "--ignore-robots-txt"],
  },
});

module.exports = mcpClient;
```

#### 3. Service Implementation

Create an OpenBnB service in `src/services/accommodations/airbnb-service.js`:

```javascript
const mcpClient = require("../../utils/mcp-client");
const { cacheWithTTL } = require("../../utils/cache");

class AirbnbService {
  /**
   * Search for Airbnb listings
   * @param {Object} params Search parameters
   * @returns {Promise<Array>} Airbnb listings
   */
  async searchListings(params) {
    const {
      location,
      checkin,
      checkout,
      adults = 2,
      children = 0,
      infants = 0,
      pets = 0,
      priceMin,
      priceMax,
      numResults = 20,
    } = params;

    // Create cache key
    const cacheKey = `airbnb:${location}:${checkin}:${checkout}:${adults}:${children}:${infants}:${pets}:${priceMin}:${priceMax}:${numResults}`;

    // Check cache first
    const cachedResults = await cacheWithTTL.get(cacheKey);
    if (cachedResults) {
      return JSON.parse(cachedResults);
    }

    try {
      // Call the MCP server
      const results = await mcpClient.call("airbnb", "airbnb_search", {
        location,
        checkin,
        checkout,
        adults,
        children,
        infants,
        pets,
        price_min: priceMin,
        price_max: priceMax,
        limit: numResults,
      });

      // Cache results for 15 minutes
      await cacheWithTTL.set(cacheKey, JSON.stringify(results), 900);

      return results;
    } catch (error) {
      console.error("Error searching Airbnb listings:", error);
      throw new Error(`Failed to search Airbnb listings: ${error.message}`);
    }
  }

  /**
   * Get details for a specific Airbnb listing
   * @param {string} listingId The Airbnb listing ID
   * @returns {Promise<Object>} Listing details
   */
  async getListingDetails(listingId) {
    // Create cache key
    const cacheKey = `airbnb:listing:${listingId}`;

    // Check cache first
    const cachedListing = await cacheWithTTL.get(cacheKey);
    if (cachedListing) {
      return JSON.parse(cachedListing);
    }

    try {
      // Call the MCP server
      const listing = await mcpClient.call("airbnb", "airbnb_listing_details", {
        listing_id: listingId,
      });

      // Cache listing details for 1 hour (less volatile than search results)
      await cacheWithTTL.set(cacheKey, JSON.stringify(listing), 3600);

      return listing;
    } catch (error) {
      console.error(`Error fetching Airbnb listing ${listingId}:`, error);
      throw new Error(`Failed to fetch Airbnb listing: ${error.message}`);
    }
  }
}

module.exports = new AirbnbService();
```

### Apify Booking.com Scraper Integration

#### 1. Installation

```bash
npm install apify-client
```

#### 2. Service Implementation

Create a Booking.com service in `src/services/accommodations/booking-service.js`:

```javascript
const { ApifyClient } = require("apify-client");
const { cacheWithTTL } = require("../../utils/cache");

class BookingService {
  constructor() {
    this.client = new ApifyClient({
      token: process.env.APIFY_API_TOKEN,
    });
  }

  /**
   * Search for hotels on Booking.com
   * @param {Object} params Search parameters
   * @returns {Promise<Array>} Hotel listings
   */
  async searchHotels(params) {
    const {
      location,
      checkIn,
      checkOut,
      adults = 2,
      rooms = 1,
      children = 0,
      currency = "USD",
      minPrice,
      maxPrice,
      minStars,
      maxStars,
      limit = 20,
    } = params;

    // Create cache key
    const cacheKey = `booking:${location}:${checkIn}:${checkOut}:${adults}:${rooms}:${children}:${currency}:${minPrice}:${maxPrice}:${minStars}:${maxStars}:${limit}`;

    // Check cache first
    const cachedResults = await cacheWithTTL.get(cacheKey);
    if (cachedResults) {
      return JSON.parse(cachedResults);
    }

    try {
      // Build input for Apify
      const input = {
        search: location,
        checkIn,
        checkOut,
        adults,
        rooms,
        children,
        currency,
        maxPrice: maxPrice || "999999",
        minPrice: minPrice || "0",
        maxResults: limit,
      };

      // Add star rating filter if provided
      if (minStars || maxStars) {
        input.starsFilter = [];

        for (let i = minStars || 1; i <= (maxStars || 5); i++) {
          input.starsFilter.push(i);
        }
      }

      // Start the Apify actor
      const run = await this.client
        .actor("voyager/booking-scraper")
        .call(input);

      // Get dataset items
      const { items } = await this.client
        .dataset(run.defaultDatasetId)
        .listItems();

      // Cache results for 15 minutes
      await cacheWithTTL.set(cacheKey, JSON.stringify(items), 900);

      return items;
    } catch (error) {
      console.error("Error searching Booking.com hotels:", error);
      throw new Error(`Failed to search Booking.com hotels: ${error.message}`);
    }
  }
}

module.exports = new BookingService();
```

## Maps API Implementation

### Google Maps API Integration

#### 1. Installation

```bash
npm install @googlemaps/google-maps-services-js
```

#### 2. Service Implementation

Create a Maps service in `src/services/maps/google-maps-service.js`:

```javascript
const { Client } = require("@googlemaps/google-maps-services-js");
const { cacheWithTTL } = require("../../utils/cache");

class GoogleMapsService {
  constructor() {
    this.client = new Client({});
    this.apiKey = process.env.GOOGLE_MAPS_API_KEY;
  }

  /**
   * Search for places by text query
   * @param {Object} params Search parameters
   * @returns {Promise<Array>} Place results
   */
  async searchPlaces(params) {
    const { query, location, radius, type } = params;

    // Create cache key
    const cacheKey = `places:${query}:${location}:${radius}:${type}`;

    // Check cache first
    const cachedResults = await cacheWithTTL.get(cacheKey);
    if (cachedResults) {
      return JSON.parse(cachedResults);
    }

    try {
      const response = await this.client.textSearch({
        params: {
          query,
          location,
          radius,
          type,
          key: this.apiKey,
        },
      });

      const places = response.data.results;

      // Cache results for 24 hours (place data is less volatile)
      await cacheWithTTL.set(cacheKey, JSON.stringify(places), 86400);

      return places;
    } catch (error) {
      console.error("Error searching places:", error);
      throw new Error(`Failed to search places: ${error.message}`);
    }
  }

  /**
   * Get details for a specific place
   * @param {string} placeId Google Maps place ID
   * @param {Array} fields Optional fields to include
   * @returns {Promise<Object>} Place details
   */
  async getPlaceDetails(placeId, fields = []) {
    // Default fields if none provided
    if (fields.length === 0) {
      fields = [
        "name",
        "formatted_address",
        "geometry",
        "photos",
        "rating",
        "formatted_phone_number",
        "website",
        "opening_hours",
        "price_level",
        "reviews",
      ];
    }

    // Create cache key
    const cacheKey = `place:${placeId}:${fields.join(",")}`;

    // Check cache first
    const cachedPlace = await cacheWithTTL.get(cacheKey);
    if (cachedPlace) {
      return JSON.parse(cachedPlace);
    }

    try {
      const response = await this.client.placeDetails({
        params: {
          place_id: placeId,
          fields: fields.join(","),
          key: this.apiKey,
        },
      });

      const placeDetails = response.data.result;

      // Cache place details for 24 hours
      await cacheWithTTL.set(cacheKey, JSON.stringify(placeDetails), 86400);

      return placeDetails;
    } catch (error) {
      console.error(`Error fetching place details for ${placeId}:`, error);
      throw new Error(`Failed to fetch place details: ${error.message}`);
    }
  }

  /**
   * Calculate distance between points
   * @param {Object} params Distance parameters
   * @returns {Promise<Object>} Distance and duration information
   */
  async calculateDistance(params) {
    const { origins, destinations, mode = "driving" } = params;

    // Create cache key
    const originsKey = Array.isArray(origins) ? origins.join("|") : origins;
    const destinationsKey = Array.isArray(destinations)
      ? destinations.join("|")
      : destinations;
    const cacheKey = `distance:${originsKey}:${destinationsKey}:${mode}`;

    // Check cache first
    const cachedDistance = await cacheWithTTL.get(cacheKey);
    if (cachedDistance) {
      return JSON.parse(cachedDistance);
    }

    try {
      const response = await this.client.distancematrix({
        params: {
          origins,
          destinations,
          mode,
          key: this.apiKey,
        },
      });

      const distanceData = response.data;

      // Cache distance data for 24 hours
      await cacheWithTTL.set(cacheKey, JSON.stringify(distanceData), 86400);

      return distanceData;
    } catch (error) {
      console.error("Error calculating distance:", error);
      throw new Error(`Failed to calculate distance: ${error.message}`);
    }
  }
}

module.exports = new GoogleMapsService();
```

## Search Integration

### Linkup Search Implementation

#### 1. Service Implementation

Create a Search service in `src/services/search/linkup-service.js`:

```javascript
const axios = require("axios");
const { cacheWithTTL } = require("../../utils/cache");

class LinkupSearchService {
  constructor() {
    // Here we're using the MCP version of Linkup
    this.apiUrl =
      process.env.LINKUP_API_URL || "http://localhost:3000/api/search";
    this.apiKey = process.env.LINKUP_API_KEY;
  }

  /**
   * Perform a web search using Linkup
   * @param {Object} params Search parameters
   * @returns {Promise<Object>} Search results
   */
  async searchWeb(params) {
    const { query, depth = "standard" } = params;

    if (!query) {
      throw new Error("Search query is required");
    }

    // Create cache key
    const cacheKey = `search:${query}:${depth}`;

    // Check cache first
    const cachedResults = await cacheWithTTL.get(cacheKey);
    if (cachedResults) {
      return JSON.parse(cachedResults);
    }

    try {
      // For MCP-based implementation
      const response = await axios.post(
        this.apiUrl,
        {
          query,
          depth,
        },
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.apiKey}`,
          },
        }
      );

      const searchResults = response.data;

      // Cache search results for 1 hour
      await cacheWithTTL.set(cacheKey, JSON.stringify(searchResults), 3600);

      return searchResults;
    } catch (error) {
      console.error(`Error performing Linkup search for "${query}":`, error);
      throw new Error(`Failed to perform search: ${error.message}`);
    }
  }

  /**
   * Perform a travel-specific search
   * @param {Object} params Search parameters
   * @returns {Promise<Object>} Travel search results
   */
  async searchTravel(params) {
    const { destination, travelType, dates } = params;

    // Construct a specialized travel query
    const query = `${travelType} in ${destination}${dates ? ` ${dates}` : ""}`;

    // Always use deep search for travel queries
    return this.searchWeb({
      query,
      depth: "deep",
    });
  }
}

module.exports = new LinkupSearchService();
```

## API Gateway Layer

Create a unified API gateway in `src/api/index.js`:

```javascript
const express = require("express");
const cors = require("cors");
const helmet = require("helmet");
const morgan = require("morgan");
const rateLimit = require("express-rate-limit");

// Import routes
const flightRoutes = require("./routes/flights");
const accommodationRoutes = require("./routes/accommodations");
const mapRoutes = require("./routes/maps");
const searchRoutes = require("./routes/search");

// Import error handling middleware
const { errorHandler } = require("../utils/error");

// Initialize express app
const app = express();

// Apply middleware
app.use(helmet()); // Security headers
app.use(cors()); // Enable CORS
app.use(express.json()); // Parse JSON bodies
app.use(morgan("combined")); // Logging

// Apply rate limiting
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  standardHeaders: true,
  legacyHeaders: false,
});
app.use(apiLimiter);

// Apply routes
app.use("/api/flights", flightRoutes);
app.use("/api/accommodations", accommodationRoutes);
app.use("/api/maps", mapRoutes);
app.use("/api/search", searchRoutes);

// Root route for health check
app.get("/", (req, res) => {
  res.json({ message: "TripSage API is running" });
});

// Error handling middleware
app.use(errorHandler);

module.exports = app;
```

## Testing and Validation

Create test scripts in `src/tests` to validate API integrations:

```javascript
// Example test for Duffel flight search
const duffelService = require("../services/flights/duffel-service");

async function testFlightSearch() {
  try {
    const results = await duffelService.searchFlights({
      origin: "JFK",
      destination: "LHR",
      departureDate: "2025-07-01",
    });

    console.log("Flight search successful!");
    console.log(`Found ${results.length} flights`);
    console.log("First result:", JSON.stringify(results[0], null, 2));

    return true;
  } catch (error) {
    console.error("Flight search test failed:", error);
    return false;
  }
}

// Run the test
testFlightSearch().then((success) => {
  if (success) {
    console.log("All tests passed!");
  } else {
    console.error("Tests failed");
    process.exit(1);
  }
});
```

## API Caching and Rate Limiting Implementation

Create a Redis-based caching utility in `src/utils/cache.js`:

```javascript
const Redis = require("ioredis");
const { promisify } = require("util");

// Initialize Redis client
const redisClient = new Redis({
  host: process.env.REDIS_HOST || "localhost",
  port: process.env.REDIS_PORT || 6379,
  password: process.env.REDIS_PASSWORD,
  keyPrefix: "tripsage:",
});

// Handle Redis connection events
redisClient.on("error", (err) => {
  console.error("Redis error:", err);
});

redisClient.on("connect", () => {
  console.log("Connected to Redis");
});

// Create a cache utility with TTL (time-to-live)
const cacheWithTTL = {
  /**
   * Get a value from cache
   * @param {string} key Cache key
   * @returns {Promise<string|null>} Cached value or null
   */
  async get(key) {
    try {
      return await redisClient.get(key);
    } catch (error) {
      console.error(`Cache get error for key ${key}:`, error);
      return null;
    }
  },

  /**
   * Set a value in cache with TTL
   * @param {string} key Cache key
   * @param {string} value Value to cache
   * @param {number} ttlSeconds Time-to-live in seconds
   * @returns {Promise<boolean>} Success status
   */
  async set(key, value, ttlSeconds = 300) {
    try {
      await redisClient.set(key, value, "EX", ttlSeconds);
      return true;
    } catch (error) {
      console.error(`Cache set error for key ${key}:`, error);
      return false;
    }
  },

  /**
   * Delete a value from cache
   * @param {string} key Cache key
   * @returns {Promise<boolean>} Success status
   */
  async del(key) {
    try {
      await redisClient.del(key);
      return true;
    } catch (error) {
      console.error(`Cache delete error for key ${key}:`, error);
      return false;
    }
  },

  /**
   * Clear all cache
   * @returns {Promise<boolean>} Success status
   */
  async clear() {
    try {
      // Note: This is using the keyPrefix, so it only clears TripSage keys
      const keys = await redisClient.keys("*");
      if (keys.length > 0) {
        await redisClient.del(keys);
      }
      return true;
    } catch (error) {
      console.error("Cache clear error:", error);
      return false;
    }
  },
};

module.exports = {
  redisClient,
  cacheWithTTL,
};
```

This implementation guide provides a comprehensive foundation for integrating travel APIs with TripSage. Follow these patterns for additional services as needed, and ensure thorough testing of each integration.
