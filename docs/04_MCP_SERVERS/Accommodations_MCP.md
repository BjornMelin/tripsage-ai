# Accommodations MCP Server Guide

This document provides the comprehensive implementation guide and specification for the Accommodations MCP Server within the TripSage AI Travel Planning System.

## 1. Overview

The Accommodations MCP Server is responsible for providing search, details, and potentially booking-related functionalities for various types of lodging, including hotels, vacation rentals, apartments, and hostels. It acts as an aggregator and standardized interface to multiple accommodation providers.

Given TripSage's strategy of leveraging existing MCPs where possible, this "server" is more accurately a **collection of client integrations with external, specialized accommodation MCPs and APIs**, all managed and exposed through TripSage's MCP Abstraction Layer.

## 2. Architecture and Provider Strategy

TripSage adopts a multi-provider approach:

1. **Airbnb (Vacation Rentals, Unique Stays)**
   - Integration: **OpenBnB MCP Server** (`@openbnb/mcp-server-airbnb`).
   - Provides listing search, property information. No direct booking.

2. **Booking.com (Hotels, Apartments, Guesthouses)**
   - Integration: **Apify Booking.com Scraper**.  
   - Provides hotel search, details, availability, pricing, reviews. No direct booking.

3. **Future Providers**:
   - Could include Duffel Stays, Amadeus Hotels, other APIs for booking capabilities.

## 3. OpenBnB Airbnb MCP Integration

- **Package**: `@openbnb/mcp-server-airbnb` (Node.js/TypeScript).
- **Tools**:
  - `airbnb_search` (listings)
  - `airbnb_listing_details`
- TripSage sets up config in `openai_agents_config.js`.

## 4. Apify Booking.com Scraper Integration

- **Actor**: e.g., `voyager/booking-scraper` on Apify.
- **TripSage** creates a custom wrapper that behaves like MCP tools:
  - `booking_search_hotels`
  - `booking_get_hotel_details`
- Uses `APIFY_API_TOKEN` from `.env`.

## 5. Exposed MCP Tools (Unified by TripSage)

### 5.1. `mcp__accommodations__search_accommodations`

- Searches across all providers (Airbnb, Booking.com).
- Parameters include location, check-in/out, guests, price range, property type, etc.
- Merges, normalizes, deduplicates results.

### 5.2. `mcp__accommodations__get_accommodation_details`

- Retrieves details from the specified provider (`airbnb`, `booking`) given an ID.

### 5.3. `mcp__accommodations__compare_accommodations`

- Fetches details for multiple accommodations for comparison.

### 5.4. `mcp__accommodations__get_reviews`

- Retrieves reviews for the specified accommodation.

### 5.5. `mcp__accommodations__track_prices`

- Sets up price tracking for specified dates, guests, threshold.

## 6. Data Transformation and Normalization

- `AirbnbTransformer` and `BookingTransformer` unify data into a common schema.

## 7. Caching Strategy

- **Search Results**: ~30min TTL
- **Accommodation Details**: ~1–6hr TTL
- **Reviews**: ~24hr TTL

## 8. Python Client (`src/mcp/accommodations/client.py`)

- Combines calls to OpenBnB MCP and Apify Booking.com scraper, returning unified results.

## 9. Agent Integration

- The Travel Planning Agent or an Accommodations Agent can invoke these tools to provide lodging options.

## 10. Deployment

- **OpenBnB MCP Server**: Node.js container for Airbnb data.
- **Apify**: Cloud-based, integrated via API token.
- All orchestrated by TripSage's Python backend and agent system.
