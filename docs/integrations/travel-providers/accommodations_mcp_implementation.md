# Accommodations MCP Server Implementation

This document provides the detailed implementation specification for the Accommodations MCP Server in TripSage.

## Overview

The Accommodations MCP Server provides comprehensive accommodation search, booking, and management capabilities for the TripSage platform. It integrates with multiple providers (primarily Airbnb via OpenBnB and Booking.com via Apify) to offer a wide range of accommodation options from hotels and resorts to vacation rentals and apartments.

## MCP Tools Exposed

```typescript
// MCP Tool Definitions
{
  "name": "mcp__accommodations__search_accommodations",
  "parameters": {
    "location": {"type": "string", "description": "City or specific location"},
    "check_in_date": {"type": "string", "description": "Check-in date in YYYY-MM-DD format"},
    "check_out_date": {"type": "string", "description": "Check-out date in YYYY-MM-DD format"},
    "adults": {"type": "integer", "description": "Number of adults", "default": 2},
    "children": {"type": "integer", "description": "Number of children (2-11 years)", "default": 0},
    "infants": {"type": "integer", "description": "Number of infants (<2 years)", "default": 0},
    "pets": {"type": "integer", "description": "Number of pets", "default": 0},
    "rooms": {"type": "integer", "description": "Number of rooms (for hotels)", "default": 1},
    "property_type": {"type": "string", "enum": ["hotel", "apartment", "hostel", "resort", "guesthouse", "any"], "default": "any", "description": "Type of accommodation to search for"},
    "min_rating": {"type": "number", "description": "Minimum star/guest rating (1-5)", "default": 0},
    "max_price": {"type": "number", "description": "Maximum price per night in USD", "default": null},
    "min_price": {"type": "number", "description": "Minimum price per night in USD", "default": null},
    "amenities": {"type": "array", "items": {"type": "string"}, "description": "Desired amenities (e.g., wifi, pool, etc.)", "default": []},
    "providers": {"type": "array", "items": {"type": "string", "enum": ["airbnb", "booking", "all"]}, "default": ["all"], "description": "Accommodation providers to search"}
  },
  "required": ["location", "check_in_date", "check_out_date"]
},
{
  "name": "mcp__accommodations__get_accommodation_details",
  "parameters": {
    "accommodation_id": {"type": "string", "description": "ID of the accommodation to get details for"},
    "provider": {"type": "string", "enum": ["airbnb", "booking"], "description": "Provider of the accommodation"},
    "check_in_date": {"type": "string", "description": "Check-in date in YYYY-MM-DD format", "required": false},
    "check_out_date": {"type": "string", "description": "Check-out date in YYYY-MM-DD format", "required": false},
    "adults": {"type": "integer", "description": "Number of adults", "default": 2},
    "children": {"type": "integer", "description": "Number of children", "default": 0},
    "infants": {"type": "integer", "description": "Number of infants", "default": 0},
    "pets": {"type": "integer", "description": "Number of pets", "default": 0}
  },
  "required": ["accommodation_id", "provider"]
},
{
  "name": "mcp__accommodations__compare_accommodations",
  "parameters": {
    "accommodation_ids": {"type": "array", "items": {"type": "object", "properties": {
      "id": {"type": "string", "description": "ID of the accommodation"},
      "provider": {"type": "string", "enum": ["airbnb", "booking"], "description": "Provider of the accommodation"}
    }, "required": ["id", "provider"]}},
    "check_in_date": {"type": "string", "description": "Check-in date in YYYY-MM-DD format"},
    "check_out_date": {"type": "string", "description": "Check-out date in YYYY-MM-DD format"},
    "adults": {"type": "integer", "description": "Number of adults", "default": 2},
    "children": {"type": "integer", "description": "Number of children", "default": 0}
  },
  "required": ["accommodation_ids", "check_in_date", "check_out_date"]
},
{
  "name": "mcp__accommodations__get_reviews",
  "parameters": {
    "accommodation_id": {"type": "string", "description": "ID of the accommodation"},
    "provider": {"type": "string", "enum": ["airbnb", "booking"], "description": "Provider of the accommodation"},
    "limit": {"type": "integer", "description": "Maximum number of reviews", "default": 10},
    "sort": {"type": "string", "enum": ["recent", "positive", "negative", "relevant"], "default": "recent", "description": "Sorting criteria for reviews"},
    "min_rating": {"type": "integer", "description": "Minimum rating to filter reviews", "default": 0, "minimum": 0, "maximum": 5}
  },
  "required": ["accommodation_id", "provider"]
},
{
  "name": "mcp__accommodations__track_prices",
  "parameters": {
    "accommodation_id": {"type": "string", "description": "ID of the accommodation"},
    "provider": {"type": "string", "enum": ["airbnb", "booking"], "description": "Provider of the accommodation"},
    "check_in_date": {"type": "string", "description": "Check-in date in YYYY-MM-DD format"},
    "check_out_date": {"type": "string", "description": "Check-out date in YYYY-MM-DD format"},
    "adults": {"type": "integer", "description": "Number of adults", "default": 2},
    "children": {"type": "integer", "description": "Number of children", "default": 0},
    "notify_when": {"type": "string", "enum": ["price_decrease", "any_change"], "default": "price_decrease", "description": "When to send notifications"},
    "notification_threshold": {"type": "number", "description": "Minimum percentage decrease to trigger notification", "default": 5}
  },
  "required": ["accommodation_id", "provider", "check_in_date", "check_out_date"]
}
```

## API Integrations

### Primary: OpenBnB MCP Server (Airbnb)

- **Key Tools**:

  - `airbnb_search` - Search for Airbnb listings
  - `airbnb_listing_details` - Get detailed information about a listing

- **Features**:
  - No API key required
  - Returns structured JSON data
  - Reduces context load by flattening data

### Secondary: Apify Booking.com Scraper

- **Key Functionality**:

  - Hotel/accommodation search
  - Detailed property information
  - Room availability and pricing
  - Review extraction

- **Authentication**:
  - Apify API key required
  - Usage-based pricing

## Connection Points to Existing Architecture

### Agent Integration

- **Travel Agent**:

  - Main integration point for accommodation search and booking
  - Provides accommodation recommendations based on budget and preferences
  - Coordinates with flight bookings for comprehensive travel planning

- **Budget Agent**:

  - Price tracking and alerting for accommodations
  - Budget allocation across travel components
  - Cost comparison between accommodation options

- **Itinerary Agent**:
  - Accommodation details for itinerary creation
  - Coordination with flight schedules and activities
  - Location-based planning for activities near accommodations

## File Structure

```plaintext
src/
  mcp/
    accommodations/
      __init__.py                  # Package initialization
      server.py                    # MCP server implementation
      config.py                    # Server configuration settings
      handlers/
        __init__.py                # Module initialization
        search_handler.py          # Accommodation search handler
        details_handler.py         # Accommodation details handler
        compare_handler.py         # Accommodation comparison handler
        reviews_handler.py         # Reviews retrieval handler
        price_tracker_handler.py   # Price tracking handler
      providers/
        __init__.py                # Module initialization
        airbnb_provider.py         # Airbnb integration via OpenBnB
        booking_provider.py        # Booking.com integration via Apify
        provider_interface.py      # Common interface for all providers
      services/
        __init__.py                # Module initialization
        cache_service.py           # Caching service
        price_tracking_service.py  # Price tracking service
        normalization_service.py   # Data normalization across providers
      models/
        __init__.py                # Module initialization
        accommodation.py           # Accommodation data models
        room.py                    # Room data models
        review.py                  # Review data models
        price_alert.py             # Price alert models
      transformers/
        __init__.py                # Module initialization
        airbnb_transformer.py      # Transforms Airbnb data to internal format
        booking_transformer.py     # Transforms Booking.com data to internal format
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

### Provider Interface

```typescript
// provider_interface.ts
export interface AccommodationProvider {
  searchAccommodations(params: SearchParams): Promise<SearchResult>;
  getAccommodationDetails(
    id: string,
    params: DetailsParams
  ): Promise<AccommodationDetails>;
  getReviews(id: string, params: ReviewParams): Promise<ReviewResult>;
  trackPrices(id: string, params: TrackPriceParams): Promise<TrackPriceResult>;
}

export interface SearchParams {
  location: string;
  checkInDate: string;
  checkOutDate: string;
  adults: number;
  children: number;
  infants: number;
  pets: number;
  propertyType?: string;
  minRating?: number;
  maxPrice?: number;
  minPrice?: number;
  amenities?: string[];
}

export interface DetailsParams {
  checkInDate?: string;
  checkOutDate?: string;
  adults: number;
  children: number;
  infants: number;
  pets: number;
}

export interface ReviewParams {
  limit: number;
  sort: string;
  minRating: number;
}

export interface TrackPriceParams {
  checkInDate: string;
  checkOutDate: string;
  adults: number;
  children: number;
  notifyWhen: string;
  notificationThreshold: number;
}

export interface SearchResult {
  accommodations: Accommodation[];
  totalCount: number;
  searchParams: SearchParams;
  provider: string;
}

export interface Accommodation {
  id: string;
  provider: string;
  name: string;
  type: string;
  url: string;
  location: Location;
  price: Price;
  rating?: number;
  reviewCount?: number;
  images?: string[];
  description?: string;
  amenities?: string[];
  roomOptions?: RoomOption[];
}

export interface AccommodationDetails extends Accommodation {
  host?: Host;
  checkIn?: string;
  checkOut?: string;
  cancellationPolicy?: string;
  roomOptions: RoomOption[];
  amenities: string[];
  houseRules?: string[];
  coordinates: Coordinates;
  nearbyAttractions?: Attraction[];
}

export interface ReviewResult {
  reviews: Review[];
  totalCount: number;
  accommodation: {
    id: string;
    name: string;
    provider: string;
  };
}

export interface TrackPriceResult {
  trackingId: string;
  accommodation: {
    id: string;
    name: string;
    provider: string;
  };
  currentPrice: Price;
  trackingParams: TrackPriceParams;
}

// Additional interfaces for common data structures
export interface Location {
  address: string;
  city: string;
  region?: string;
  country: string;
  zipCode?: string;
}

export interface Price {
  amount: number;
  currency: string;
  period: string; // per_night, total, etc.
  originalAmount?: number; // For discounted prices
}

export interface RoomOption {
  id: string;
  name: string;
  maxOccupancy: number;
  price: Price;
  bedConfiguration: string;
  amenities: string[];
  available: boolean;
}

export interface Host {
  id: string;
  name: string;
  rating?: number;
  isSuperhost?: boolean;
  responseRate?: number;
  joinedDate?: string;
}

export interface Review {
  id: string;
  author: string;
  date: string;
  rating: number;
  content: string;
  stayDate?: string;
  stayDuration?: number;
  travelerType?: string;
  helpful?: number;
  roomType?: string;
}

export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface Attraction {
  name: string;
  distance: number;
  type: string;
}
```

### Airbnb Provider Implementation

```typescript
// airbnb_provider.ts
import { exec } from "child_process";
import { promisify } from "util";
import {
  AccommodationProvider,
  SearchParams,
  DetailsParams,
  ReviewParams,
  TrackPriceParams,
  SearchResult,
  AccommodationDetails,
  ReviewResult,
  TrackPriceResult,
} from "./provider_interface";
import { AirbnbTransformer } from "../transformers/airbnb_transformer";
import { ValidationError } from "../utils/error_handling";
import {
  validateSearchParams,
  validateDetailsParams,
} from "../utils/validation";

const execAsync = promisify(exec);

export class AirbnbProvider implements AccommodationProvider {
  private transformer: AirbnbTransformer;

  constructor() {
    this.transformer = new AirbnbTransformer();
  }

  async searchAccommodations(params: SearchParams): Promise<SearchResult> {
    try {
      // Validate params
      validateSearchParams(params);

      // Prepare parameters for OpenBnB MCP server
      const mpcParams = {
        location: params.location,
        checkin: params.checkInDate,
        checkout: params.checkOutDate,
        adults: params.adults,
        children: params.children,
        infants: params.infants,
        pets: params.pets,
        minPrice: params.minPrice,
        maxPrice: params.maxPrice,
      };

      // Call OpenBnB MCP server
      const { stdout, stderr } = await execAsync(
        `airbnb_search '${JSON.stringify(mpcParams)}'`
      );

      if (stderr) {
        throw new Error(`OpenBnB search error: ${stderr}`);
      }

      // Parse results
      const searchResults = JSON.parse(stdout);

      // Transform to our format
      return this.transformer.transformSearchResults(searchResults, params);
    } catch (error) {
      if (error instanceof ValidationError) {
        throw error;
      }
      throw new Error(
        `Failed to search Airbnb accommodations: ${error.message}`
      );
    }
  }

  async getAccommodationDetails(
    id: string,
    params: DetailsParams
  ): Promise<AccommodationDetails> {
    try {
      // Validate params
      validateDetailsParams(params);

      // Prepare parameters for OpenBnB MCP server
      const mpcParams = {
        id: id,
        checkin: params.checkInDate,
        checkout: params.checkOutDate,
        adults: params.adults,
        children: params.children,
        infants: params.infants,
        pets: params.pets,
      };

      // Call OpenBnB MCP server
      const { stdout, stderr } = await execAsync(
        `airbnb_listing_details '${JSON.stringify(mpcParams)}'`
      );

      if (stderr) {
        throw new Error(`OpenBnB details error: ${stderr}`);
      }

      // Parse results
      const detailsResult = JSON.parse(stdout);

      // Transform to our format
      return this.transformer.transformListingDetails(detailsResult);
    } catch (error) {
      if (error instanceof ValidationError) {
        throw error;
      }
      throw new Error(
        `Failed to get Airbnb accommodation details: ${error.message}`
      );
    }
  }

  async getReviews(id: string, params: ReviewParams): Promise<ReviewResult> {
    try {
      // For Airbnb, reviews are included in listing details
      // So we'll get the listing details and extract reviews
      const detailsParams: DetailsParams = {
        adults: 2,
        children: 0,
        infants: 0,
        pets: 0,
      };

      const details = await this.getAccommodationDetails(id, detailsParams);

      // Transform to reviews result format
      return this.transformer.transformReviews(details, params);
    } catch (error) {
      throw new Error(`Failed to get Airbnb reviews: ${error.message}`);
    }
  }

  async trackPrices(
    id: string,
    params: TrackPriceParams
  ): Promise<TrackPriceResult> {
    try {
      // Get current price to establish baseline
      const detailsParams: DetailsParams = {
        checkInDate: params.checkInDate,
        checkOutDate: params.checkOutDate,
        adults: params.adults,
        children: params.children,
        infants: 0,
        pets: 0,
      };

      const details = await this.getAccommodationDetails(id, detailsParams);

      // Create price tracking record in database
      const trackingId = await this.createPriceTrackingRecord(
        id,
        details,
        params
      );

      return {
        trackingId,
        accommodation: {
          id,
          name: details.name,
          provider: "airbnb",
        },
        currentPrice: details.price,
        trackingParams: params,
      };
    } catch (error) {
      throw new Error(
        `Failed to set up Airbnb price tracking: ${error.message}`
      );
    }
  }

  private async createPriceTrackingRecord(
    id: string,
    details: AccommodationDetails,
    params: TrackPriceParams
  ): Promise<string> {
    // Implementation to create a record in the database
    // This would be replaced with actual database code
    return `airbnb_price_track_${id}_${Date.now()}`;
  }
}
```

### Booking Provider Implementation

```typescript
// booking_provider.ts
import axios from "axios";
import {
  AccommodationProvider,
  SearchParams,
  DetailsParams,
  ReviewParams,
  TrackPriceParams,
  SearchResult,
  AccommodationDetails,
  ReviewResult,
  TrackPriceResult,
} from "./provider_interface";
import { BookingTransformer } from "../transformers/booking_transformer";
import { ValidationError } from "../utils/error_handling";
import {
  validateSearchParams,
  validateDetailsParams,
} from "../utils/validation";
import { config } from "../config";

export class BookingProvider implements AccommodationProvider {
  private transformer: BookingTransformer;
  private apifyClient: any;

  constructor() {
    this.transformer = new BookingTransformer();
    this.apifyClient = axios.create({
      baseURL: "https://api.apify.com/v2",
      headers: {
        Authorization: `Bearer ${config.APIFY_API_KEY}`,
      },
    });
  }

  async searchAccommodations(params: SearchParams): Promise<SearchResult> {
    try {
      // Validate params
      validateSearchParams(params);

      // Prepare parameters for Apify Booking.com Scraper
      const apifyParams = {
        search: params.location,
        checkIn: params.checkInDate,
        checkOut: params.checkOutDate,
        adults: params.adults,
        children: params.children,
        rooms: 1, // Default to 1 room
        currency: "USD",
        language: "en-us",
        minPrice: params.minPrice,
        maxPrice: params.maxPrice,
        minScore: params.minRating ? params.minRating * 2 : undefined, // Booking uses 1-10 scale
        propertyType:
          params.propertyType === "any" ? undefined : params.propertyType,
      };

      // Call Apify Booking.com Scraper
      const response = await this.apifyClient.post(
        "/acts/voyager~booking-scraper/runs",
        {
          json: apifyParams,
        }
      );

      const runId = response.data.data.id;

      // Wait for the run to finish
      let finished = false;
      let results = null;

      while (!finished) {
        await new Promise((resolve) => setTimeout(resolve, 5000)); // Wait 5 seconds

        const runStatus = await this.apifyClient.get(
          `/acts/voyager~booking-scraper/runs/${runId}`
        );

        if (runStatus.data.data.status === "SUCCEEDED") {
          // Get the results
          const resultData = await this.apifyClient.get(
            `/datasets/${runStatus.data.data.defaultDatasetId}/items`
          );
          results = resultData.data;
          finished = true;
        } else if (
          runStatus.data.data.status === "FAILED" ||
          runStatus.data.data.status === "TIMED-OUT"
        ) {
          throw new Error(
            `Apify run failed: ${runStatus.data.data.statusMessage}`
          );
        }
      }

      // Transform to our format
      return this.transformer.transformSearchResults(results, params);
    } catch (error) {
      if (error instanceof ValidationError) {
        throw error;
      }
      throw new Error(
        `Failed to search Booking.com accommodations: ${error.message}`
      );
    }
  }

  async getAccommodationDetails(
    id: string,
    params: DetailsParams
  ): Promise<AccommodationDetails> {
    try {
      // Validate params
      validateDetailsParams(params);

      // For Booking.com, the ID is typically a URL path
      // Construct the full URL
      const url = `https://www.booking.com/hotel/${id}.html`;

      // Prepare parameters for Apify
      const apifyParams = {
        url: url,
        checkIn: params.checkInDate,
        checkOut: params.checkOutDate,
        adults: params.adults,
        children: params.children,
      };

      // Call Apify Booking.com Scraper in detail mode
      const response = await this.apifyClient.post(
        "/acts/voyager~booking-scraper/runs",
        {
          json: {
            ...apifyParams,
            maxPages: 1,
            extendOutputFunction: `
            async ({ page, item, customData }) => {
              // Extract additional details not captured by default
              const details = {};
              // Add custom extraction logic here
              return details;
            }
          `,
          },
        }
      );

      const runId = response.data.data.id;

      // Wait for the run to finish
      let finished = false;
      let result = null;

      while (!finished) {
        await new Promise((resolve) => setTimeout(resolve, 5000)); // Wait 5 seconds

        const runStatus = await this.apifyClient.get(
          `/acts/voyager~booking-scraper/runs/${runId}`
        );

        if (runStatus.data.data.status === "SUCCEEDED") {
          // Get the results
          const resultData = await this.apifyClient.get(
            `/datasets/${runStatus.data.data.defaultDatasetId}/items`
          );
          result = resultData.data[0]; // Get the first (and should be only) result
          finished = true;
        } else if (
          runStatus.data.data.status === "FAILED" ||
          runStatus.data.data.status === "TIMED-OUT"
        ) {
          throw new Error(
            `Apify run failed: ${runStatus.data.data.statusMessage}`
          );
        }
      }

      // Transform to our format
      return this.transformer.transformAccommodationDetails(result);
    } catch (error) {
      if (error instanceof ValidationError) {
        throw error;
      }
      throw new Error(
        `Failed to get Booking.com accommodation details: ${error.message}`
      );
    }
  }

  async getReviews(id: string, params: ReviewParams): Promise<ReviewResult> {
    try {
      // For Booking.com, we need to use the Booking.com Reviews Scraper
      // Construct the full URL
      const url = `https://www.booking.com/hotel/${id}.html`;

      // Prepare parameters for Apify
      const apifyParams = {
        url: url,
        maxReviews: params.limit,
        sortBy: this.mapReviewSortParam(params.sort),
        minScore: params.minRating ? params.minRating * 2 : undefined, // Booking uses 1-10 scale
      };

      // Call Apify Booking.com Reviews Scraper
      const response = await this.apifyClient.post(
        "/acts/voyager~booking-reviews-scraper/runs",
        {
          json: apifyParams,
        }
      );

      const runId = response.data.data.id;

      // Wait for the run to finish
      let finished = false;
      let results = null;

      while (!finished) {
        await new Promise((resolve) => setTimeout(resolve, 5000)); // Wait 5 seconds

        const runStatus = await this.apifyClient.get(
          `/acts/voyager~booking-reviews-scraper/runs/${runId}`
        );

        if (runStatus.data.data.status === "SUCCEEDED") {
          // Get the results
          const resultData = await this.apifyClient.get(
            `/datasets/${runStatus.data.data.defaultDatasetId}/items`
          );
          results = resultData.data;
          finished = true;
        } else if (
          runStatus.data.data.status === "FAILED" ||
          runStatus.data.data.status === "TIMED-OUT"
        ) {
          throw new Error(
            `Apify run failed: ${runStatus.data.data.statusMessage}`
          );
        }
      }

      // Get basic accommodation info to include in the response
      // This is just a shallow call to get the name and other basic details
      const detailsParams: DetailsParams = {
        adults: 2,
        children: 0,
        infants: 0,
        pets: 0,
      };

      const hotelInfo = await this.getAccommodationDetails(id, detailsParams);

      // Transform to our format
      return this.transformer.transformReviews(results, hotelInfo, params);
    } catch (error) {
      throw new Error(`Failed to get Booking.com reviews: ${error.message}`);
    }
  }

  async trackPrices(
    id: string,
    params: TrackPriceParams
  ): Promise<TrackPriceResult> {
    try {
      // Get current price to establish baseline
      const detailsParams: DetailsParams = {
        checkInDate: params.checkInDate,
        checkOutDate: params.checkOutDate,
        adults: params.adults,
        children: params.children,
        infants: 0,
        pets: 0,
      };

      const details = await this.getAccommodationDetails(id, detailsParams);

      // Create price tracking record in database
      const trackingId = await this.createPriceTrackingRecord(
        id,
        details,
        params
      );

      return {
        trackingId,
        accommodation: {
          id,
          name: details.name,
          provider: "booking",
        },
        currentPrice: details.price,
        trackingParams: params,
      };
    } catch (error) {
      throw new Error(
        `Failed to set up Booking.com price tracking: ${error.message}`
      );
    }
  }

  private async createPriceTrackingRecord(
    id: string,
    details: AccommodationDetails,
    params: TrackPriceParams
  ): Promise<string> {
    // Implementation to create a record in the database
    // This would be replaced with actual database code
    return `booking_price_track_${id}_${Date.now()}`;
  }

  private mapReviewSortParam(sort: string): string {
    // Map our sort parameter to Booking.com's sort parameter
    switch (sort) {
      case "recent":
        return "newest_first";
      case "positive":
        return "top_scores";
      case "negative":
        return "low_scores";
      case "relevant":
        return "most_relevant";
      default:
        return "newest_first";
    }
  }
}
```

### Search Handler

```typescript
// search_handler.ts
import { AccommodationProvider } from "../providers/provider_interface";
import { AirbnbProvider } from "../providers/airbnb_provider";
import { BookingProvider } from "../providers/booking_provider";
import { CacheService } from "../services/cache_service";
import { validateSearchParams } from "../utils/validation";
import { normalizeSearchResults } from "../services/normalization_service";

export class SearchHandler {
  private airbnbProvider: AccommodationProvider;
  private bookingProvider: AccommodationProvider;
  private cacheService: CacheService;

  constructor() {
    this.airbnbProvider = new AirbnbProvider();
    this.bookingProvider = new BookingProvider();
    this.cacheService = new CacheService();
  }

  async handleSearch(params: any): Promise<any> {
    try {
      // Validate the parameters
      validateSearchParams(params);

      // Create cache key
      const cacheKey = this.createCacheKey(params);

      // Check cache
      const cachedResult = await this.cacheService.get(cacheKey);
      if (cachedResult) {
        return cachedResult;
      }

      // Determine which providers to search
      const providers = params.providers || ["all"];
      const shouldSearchAirbnb =
        providers.includes("all") || providers.includes("airbnb");
      const shouldSearchBooking =
        providers.includes("all") || providers.includes("booking");

      // Execute searches in parallel
      const searches = [];

      if (shouldSearchAirbnb) {
        searches.push(this.airbnbProvider.searchAccommodations(params));
      }

      if (shouldSearchBooking) {
        searches.push(this.bookingProvider.searchAccommodations(params));
      }

      // Wait for all searches to complete
      const searchResults = await Promise.all(searches);

      // Normalize and combine results
      const combinedResults = normalizeSearchResults(searchResults);

      // Add search metadata
      const result = {
        accommodations: combinedResults,
        total_count: combinedResults.length,
        search_params: params,
        price_stats: this.calculatePriceStats(combinedResults),
      };

      // Cache the results
      await this.cacheService.set(cacheKey, result, 1800); // 30 minutes

      return result;
    } catch (error) {
      console.error("Error in search handler:", error);
      throw new Error(`Failed to search accommodations: ${error.message}`);
    }
  }

  private createCacheKey(params: any): string {
    // Create a deterministic cache key based on search parameters
    const key = {
      location: params.location,
      check_in_date: params.check_in_date,
      check_out_date: params.check_out_date,
      adults: params.adults || 2,
      children: params.children || 0,
      infants: params.infants || 0,
      pets: params.pets || 0,
      rooms: params.rooms || 1,
      property_type: params.property_type || "any",
      min_rating: params.min_rating || 0,
      max_price: params.max_price,
      min_price: params.min_price,
      amenities: params.amenities || [],
      providers: params.providers || ["all"],
    };

    return `accommodations_search:${JSON.stringify(key)}`;
  }

  private calculatePriceStats(accommodations: any[]): any {
    if (accommodations.length === 0) {
      return {
        min: null,
        max: null,
        avg: null,
        median: null,
      };
    }

    // Extract prices
    const prices = accommodations
      .map((a) => a.price.amount)
      .filter((p) => p !== null && p !== undefined);

    if (prices.length === 0) {
      return {
        min: null,
        max: null,
        avg: null,
        median: null,
      };
    }

    // Calculate statistics
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const sum = prices.reduce((a, b) => a + b, 0);
    const avg = sum / prices.length;

    // Calculate median
    const sortedPrices = [...prices].sort((a, b) => a - b);
    const middle = Math.floor(sortedPrices.length / 2);
    const median =
      sortedPrices.length % 2 === 0
        ? (sortedPrices[middle - 1] + sortedPrices[middle]) / 2
        : sortedPrices[middle];

    return {
      min,
      max,
      avg,
      median,
    };
  }
}
```

### Main Server Implementation

```typescript
// server.ts
import express from "express";
import bodyParser from "body-parser";
import { SearchHandler } from "./handlers/search_handler";
import { DetailsHandler } from "./handlers/details_handler";
import { CompareHandler } from "./handlers/compare_handler";
import { ReviewsHandler } from "./handlers/reviews_handler";
import { PriceTrackerHandler } from "./handlers/price_tracker_handler";
import { setupScheduledTasks } from "./utils/scheduler";
import { logRequest, logError, logInfo } from "./utils/logging";
import { config } from "./config";

const app = express();
app.use(bodyParser.json());

// Initialize handlers
const searchHandler = new SearchHandler();
const detailsHandler = new DetailsHandler();
const compareHandler = new CompareHandler();
const reviewsHandler = new ReviewsHandler();
const priceTrackerHandler = new PriceTrackerHandler();

// Set up scheduled tasks (e.g., price update checks)
setupScheduledTasks();

// Handle MCP tool requests
app.post("/api/mcp/accommodations/search_accommodations", async (req, res) => {
  try {
    logRequest("search_accommodations", req.body);
    const result = await searchHandler.handleSearch(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in search_accommodations: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post(
  "/api/mcp/accommodations/get_accommodation_details",
  async (req, res) => {
    try {
      logRequest("get_accommodation_details", req.body);
      const result = await detailsHandler.handleGetDetails(req.body);
      return res.json(result);
    } catch (error) {
      logError(`Error in get_accommodation_details: ${error.message}`);
      return res.status(500).json({
        error: true,
        message: error.message,
      });
    }
  }
);

app.post("/api/mcp/accommodations/compare_accommodations", async (req, res) => {
  try {
    logRequest("compare_accommodations", req.body);
    const result = await compareHandler.handleCompare(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in compare_accommodations: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/accommodations/get_reviews", async (req, res) => {
  try {
    logRequest("get_reviews", req.body);
    const result = await reviewsHandler.handleGetReviews(req.body);
    return res.json(result);
  } catch (error) {
    logError(`Error in get_reviews: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/accommodations/track_prices", async (req, res) => {
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
const PORT = process.env.PORT || 3003;
app.listen(PORT, () => {
  logInfo(`Accommodations MCP Server running on port ${PORT}`);
});
```

## Data Formats

### Input Format Examples

```json
// search_accommodations input
{
  "location": "Paris, France",
  "check_in_date": "2025-06-15",
  "check_out_date": "2025-06-22",
  "adults": 2,
  "children": 1,
  "property_type": "any",
  "min_rating": 4,
  "max_price": 200,
  "amenities": ["wifi", "air_conditioning"],
  "providers": ["airbnb", "booking"]
}

// get_accommodation_details input
{
  "accommodation_id": "123456",
  "provider": "airbnb",
  "check_in_date": "2025-06-15",
  "check_out_date": "2025-06-22",
  "adults": 2,
  "children": 1
}

// compare_accommodations input
{
  "accommodation_ids": [
    {
      "id": "123456",
      "provider": "airbnb"
    },
    {
      "id": "789012",
      "provider": "booking"
    }
  ],
  "check_in_date": "2025-06-15",
  "check_out_date": "2025-06-22",
  "adults": 2
}
```

### Output Format Examples

```json
// search_accommodations output
{
  "accommodations": [
    {
      "id": "123456",
      "provider": "airbnb",
      "name": "Charming Parisian Apartment",
      "type": "apartment",
      "url": "https://www.airbnb.com/rooms/123456",
      "location": {
        "address": "123 Rue Saint-Denis, Paris, France",
        "city": "Paris",
        "country": "France"
      },
      "price": {
        "amount": 150,
        "currency": "USD",
        "period": "per_night"
      },
      "rating": 4.8,
      "reviewCount": 245,
      "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
      "description": "Charming apartment in the heart of Le Marais...",
      "amenities": ["wifi", "air_conditioning", "kitchen", "washing_machine"]
    },
    {
      "id": "789012",
      "provider": "booking",
      "name": "Hotel de Paris",
      "type": "hotel",
      "url": "https://www.booking.com/hotel/fr/789012.html",
      "location": {
        "address": "456 Avenue des Champs-Élysées, Paris, France",
        "city": "Paris",
        "country": "France"
      },
      "price": {
        "amount": 180,
        "currency": "USD",
        "period": "per_night"
      },
      "rating": 4.5,
      "reviewCount": 1250,
      "images": ["https://example.com/image3.jpg", "https://example.com/image4.jpg"],
      "description": "Elegant hotel near the Champs-Élysées...",
      "amenities": ["wifi", "air_conditioning", "restaurant", "fitness_center"]
    }
  ],
  "total_count": 2,
  "search_params": {
    "location": "Paris, France",
    "check_in_date": "2025-06-15",
    "check_out_date": "2025-06-22",
    "adults": 2,
    "children": 1,
    "property_type": "any",
    "min_rating": 4,
    "max_price": 200,
    "amenities": ["wifi", "air_conditioning"],
    "providers": ["airbnb", "booking"]
  },
  "price_stats": {
    "min": 150,
    "max": 180,
    "avg": 165,
    "median": 165
  }
}

// get_accommodation_details output
{
  "id": "123456",
  "provider": "airbnb",
  "name": "Charming Parisian Apartment",
  "type": "apartment",
  "url": "https://www.airbnb.com/rooms/123456",
  "location": {
    "address": "123 Rue Saint-Denis, Paris, France",
    "city": "Paris",
    "region": "Île-de-France",
    "country": "France",
    "zipCode": "75003"
  },
  "price": {
    "amount": 150,
    "currency": "USD",
    "period": "per_night",
    "originalAmount": 165
  },
  "rating": 4.8,
  "reviewCount": 245,
  "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg", "https://example.com/image3.jpg"],
  "description": "Charming apartment in the heart of Le Marais with a beautiful view of the city. Recently renovated with modern amenities while maintaining its classic Parisian charm.",
  "host": {
    "id": "host123",
    "name": "Marie",
    "rating": 4.9,
    "isSuperhost": true,
    "responseRate": 98,
    "joinedDate": "2018-01-15"
  },
  "checkIn": "Anytime after 3:00 PM",
  "checkOut": "11:00 AM",
  "cancellationPolicy": "Moderate - Full refund 5 days prior to arrival",
  "roomOptions": [
    {
      "id": "room1",
      "name": "Entire apartment",
      "maxOccupancy": 4,
      "price": {
        "amount": 150,
        "currency": "USD",
        "period": "per_night"
      },
      "bedConfiguration": "1 queen bed, 1 sofa bed",
      "amenities": ["wifi", "air_conditioning", "kitchen", "washing_machine"],
      "available": true
    }
  ],
  "amenities": [
    "wifi",
    "air_conditioning",
    "kitchen",
    "washing_machine",
    "tv",
    "heating",
    "elevator",
    "workspace",
    "hangers",
    "iron",
    "hairdryer"
  ],
  "houseRules": [
    "No smoking",
    "No pets",
    "No parties or events",
    "Quiet hours after 10:00 PM"
  ],
  "coordinates": {
    "latitude": 48.8647,
    "longitude": 2.3609
  },
  "nearbyAttractions": [
    {
      "name": "Centre Pompidou",
      "distance": 0.5,
      "type": "museum"
    },
    {
      "name": "Notre-Dame Cathedral",
      "distance": 1.2,
      "type": "landmark"
    }
  ]
}

// get_reviews output
{
  "reviews": [
    {
      "id": "rev123",
      "author": "John",
      "date": "2025-04-20",
      "rating": 5,
      "content": "Amazing apartment in a perfect location. Marie was a wonderful host. Everything was clean and exactly as described.",
      "stayDate": "2025-04-10",
      "stayDuration": 3,
      "travelerType": "couple",
      "helpful": 12,
      "roomType": "Entire apartment"
    },
    {
      "id": "rev124",
      "author": "Sarah",
      "date": "2025-03-15",
      "rating": 4,
      "content": "Great location and beautiful apartment. The bed was a bit uncomfortable, but everything else was perfect.",
      "stayDate": "2025-03-05",
      "stayDuration": 7,
      "travelerType": "family",
      "helpful": 5,
      "roomType": "Entire apartment"
    }
  ],
  "totalCount": 245,
  "accommodation": {
    "id": "123456",
    "name": "Charming Parisian Apartment",
    "provider": "airbnb"
  }
}

// track_prices output
{
  "trackingId": "airbnb_price_track_123456_1621234567890",
  "accommodation": {
    "id": "123456",
    "name": "Charming Parisian Apartment",
    "provider": "airbnb"
  },
  "currentPrice": {
    "amount": 150,
    "currency": "USD",
    "period": "per_night"
  },
  "trackingParams": {
    "checkInDate": "2025-06-15",
    "checkOutDate": "2025-06-22",
    "adults": 2,
    "children": 1,
    "notifyWhen": "price_decrease",
    "notificationThreshold": 5
  },
  "message": "Price tracking has been set up successfully. You will be notified if the price decreases by 5% or more."
}
```

## Implementation Considerations

### Caching Strategy

- **Search Results**: Cache for 30 minutes
- **Accommodation Details**: Cache for 6 hours
- **Reviews**: Cache for 24 hours
- **Use Redis** for distributed caching in production environments
- **Invalidate Cache** when prices are known to change (e.g., after checking price changes)

### Error Handling

- **Provider Fallbacks**: If one provider fails, still return results from others
- **Rate Limiting**: Implement backoff strategies for API calls
- **Timeout Handling**: Set appropriate timeouts for external API calls
- **Validation**: Thorough validation of all user inputs

### Performance Optimization

- **Parallel Requests**: Execute multi-provider searches in parallel
- **Selective Fields**: Only request needed fields from provider APIs
- **Response Compression**: Use gzip/brotli for network efficiency
- **Pagination**: Implement proper pagination for large result sets

### Security

- **API Key Management**: Secure storage and rotation of API keys
- **Input Validation**: Sanitize and validate all user inputs
- **Rate Limiting**: Prevent abuse through appropriate request limits
- **Logging**: No sensitive information in logs

## Integration with Agent Architecture

The Accommodations MCP Server will be exposed to the TripSage agents through a client library that handles the MCP communication protocol. This integration will be implemented in the `src/agents/mcp_integration.py` file:

```python
# src/agents/mcp_integration.py

class AccommodationsMCPClient:
    """Client for interacting with the Accommodations MCP Server"""

    def __init__(self, server_url):
        self.server_url = server_url

    async def search_accommodations(self, location, check_in_date, check_out_date, adults=2,
                                  children=0, infants=0, pets=0, property_type="any",
                                  min_rating=0, max_price=None, amenities=None, providers=None):
        """Search for accommodations based on criteria"""
        try:
            amenities = amenities or []
            providers = providers or ["all"]

            # Implement MCP call to accommodations server
            result = await call_mcp_tool(
                "mcp__accommodations__search_accommodations",
                {
                    "location": location,
                    "check_in_date": check_in_date,
                    "check_out_date": check_out_date,
                    "adults": adults,
                    "children": children,
                    "infants": infants,
                    "pets": pets,
                    "property_type": property_type,
                    "min_rating": min_rating,
                    "max_price": max_price,
                    "amenities": amenities,
                    "providers": providers
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error searching accommodations: {str(e)}")
            raise

    async def get_accommodation_details(self, accommodation_id, provider,
                                      check_in_date=None, check_out_date=None,
                                      adults=2, children=0, infants=0, pets=0):
        """Get detailed information about an accommodation"""
        try:
            # Implement MCP call to accommodations server
            result = await call_mcp_tool(
                "mcp__accommodations__get_accommodation_details",
                {
                    "accommodation_id": accommodation_id,
                    "provider": provider,
                    "check_in_date": check_in_date,
                    "check_out_date": check_out_date,
                    "adults": adults,
                    "children": children,
                    "infants": infants,
                    "pets": pets
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error getting accommodation details: {str(e)}")
            raise

    # Additional methods for other MCP tools...
```

## Deployment Strategy

The Accommodations MCP Server will be containerized using Docker and deployed as a standalone service. This allows for independent scaling and updates:

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

ENV NODE_ENV=production
ENV PORT=3003

EXPOSE 3003

CMD ["node", "dist/server.js"]
```

### Resource Requirements

- **CPU**: Moderate (1-2 vCPU recommended, scales with traffic)
- **Memory**: 1GB minimum, 2GB recommended
- **Storage**: Minimal (primarily for code and logs)
- **Network**: Moderate to high (API calls to providers)

### Monitoring

- **Health Endpoint**: `/health` endpoint for monitoring
- **Metrics**: Request count, response time, error rate, cache hit rate
- **Logging**: Structured logs with request/response details
- **Alerts**: Set up for high error rates or slow responses
