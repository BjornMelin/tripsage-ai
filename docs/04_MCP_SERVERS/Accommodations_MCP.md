# Accommodations MCP Server Guide

This document provides the comprehensive implementation guide and specification for the Accommodations MCP Server within the TripSage AI Travel Planning System.

## 1. Overview

The Accommodations MCP Server is responsible for providing search, details, and potentially booking-related functionalities for various types of lodging, including hotels, vacation rentals, apartments, and hostels. It acts as an aggregator and standardized interface to multiple accommodation providers.

Given TripSage's strategy of leveraging existing MCPs where possible, this "server" is more accurately a **collection of client integrations with external, specialized accommodation MCPs and APIs**, all managed and exposed through TripSage's MCP Abstraction Layer.

## 2. Architecture and Provider Strategy

TripSage adopts a multi-provider strategy for accommodation data to ensure comprehensive coverage:

1. **Airbnb (Vacation Rentals, Unique Stays)**:

    - **Integration Method**: Via the official **OpenBnB MCP Server (`@openbnb/mcp-server-airbnb`)**.
    - **Rationale**: OpenBnB provides a ready-to-use, maintained MCP server specifically for Airbnb data. It handles the complexities of interacting with Airbnb's public data. This aligns with TripSage's "external first" MCP strategy.
    - **Key Features**: Listing search, detailed property information. Does not support direct booking.

2. **Booking.com (Hotels, Apartments, Guesthouses)**:

    - **Integration Method**: Via the **Apify Booking.com Scraper Actor**, exposed as an MCP-like interface or wrapped by a thin custom TripSage tool/service.
    - **Rationale**: Apify provides robust scraping capabilities for Booking.com, which has extensive hotel inventory. While not a traditional MCP server, its API can be treated as such by a TripSage client wrapper.
    - **Key Features**: Hotel search, property details, room availability, pricing, review extraction. Does not support direct booking through this method.

3. **Future Providers (Post-MVP)**:
    - Direct hotel supplier APIs (e.g., via Duffel Stays, Amadeus Hotels) could be considered for booking capabilities and wider inventory.
    - Other vacation rental platforms.

This dual (initially) provider approach allows TripSage to offer a wide variety of lodging options to users.

## 3. OpenBnB Airbnb MCP Server Integration

### 3.1. Overview of OpenBnB MCP

- **Package**: `@openbnb/mcp-server-airbnb` (Node.js/TypeScript).
- **Functionality**: Provides access to Airbnb listing data without requiring an official Airbnb API key (which is not generally available).
- **Data Source**: Interacts with Airbnb's publicly accessible website data.
- **Ethical Considerations**: The OpenBnB server is designed to respect website terms where possible. TripSage's usage includes caching and rate limiting to be a responsible consumer.

### 3.2. Exposed Tools by OpenBnB MCP

- **`airbnb_search`**: Searches for Airbnb listings.
  - **Parameters**: `location` (string), `placeId` (string, optional), `checkin` (string YYYY-MM-DD, optional), `checkout` (string YYYY-MM-DD, optional), `adults` (int, optional), `children` (int, optional), `infants` (int, optional), `pets` (int, optional), `minPrice` (int, optional), `maxPrice` (int, optional), `cursor` (string, optional for pagination), `ignoreRobotsText` (bool, optional).
  - **Output**: Array of listing summaries (name, price, location, rating, type, ID, URL, photos).
- **`airbnb_listing_details`**: Retrieves detailed information for a specific Airbnb listing.
  - **Parameters**: `id` (string, listing ID), `checkin`, `checkout`, `adults`, etc. (optional, for price accuracy).
  - **Output**: Detailed listing information (description, host details, amenities, full pricing, reviews, house rules).

### 3.3. TripSage Configuration for OpenBnB MCP

In Claude Desktop or `openai_agents_config.js`:

```javascript
// openai_agents_config.js or similar
// ...
"airbnb": {
  "command": "npx",
  "args": ["-y", "@openbnb/mcp-server-airbnb"], // Add "--ignore-robots-txt" for dev if needed and understood
  "env": {} // Typically no API key needed for OpenBnB
}
// ...
```

TripSage's Python client for this MCP will then connect to the endpoint where this server is running.

## 4. Apify Booking.com Scraper Integration

### 4.1. Overview of Apify Actor

- **Actor**: `voyager/booking-scraper` (or a similar well-maintained Booking.com scraper on Apify).
- **Functionality**: Scrapes Booking.com for hotel data.
- **Authentication**: Requires an Apify API token.

### 4.2. Simulating MCP Tools with Apify

TripSage will create a Python client that wraps Apify API calls to make them behave like MCP tool invocations.

- **`booking_search_hotels` (Custom Tool in TripSage Client)**:
  - **Parameters**: Similar to `airbnb_search` (location, check-in/out, guests, price range, star rating).
  - **Internal Logic**: Constructs the input object for the Apify Booking.com scraper actor, runs the actor, waits for completion, and retrieves results from the actor's dataset.
  - **Output**: Transformed list of hotel summaries.
- **`booking_get_hotel_details` (Custom Tool in TripSage Client)**:
  - **Parameters**: `hotel_url` or `hotel_id` (Booking.com specific).
  - **Internal Logic**: Runs the Apify scraper actor for a single hotel URL.
  - **Output**: Transformed detailed hotel information.

### Environment Variable for Apify

```plaintext
# .env
APIFY_API_TOKEN=your_apify_api_token
```

## 5. Exposed MCP Tools by TripSage's Accommodation Abstraction

TripSage's own `AccommodationsMCPClient` (Python) will abstract the provider-specific tools and expose a unified set of tools to the agents.

### 5.1. `mcp__accommodations__search_accommodations`

- **Description**: Searches for accommodations across all configured providers (Airbnb, Booking.com).
- **Parameters**:
  - `location` (string, required)
  - `check_in_date` (string, YYYY-MM-DD, required)
  - `check_out_date` (string, YYYY-MM-DD, required)
  - `adults` (int, default: 2)
  - `children` (int, default: 0)
  - `infants` (int, default: 0)
  - `pets` (int, default: 0)
  - `rooms` (int, default: 1, primarily for hotels)
  - `property_type` (string enum: "hotel", "apartment", "hostel", "any", etc., default: "any")
  - `min_rating` (float, 0-5, optional)
  - `max_price` (float, optional, per night in USD)
  - `min_price` (float, optional, per night in USD)
  - `amenities` (List[str], optional, e.g., ["wifi", "pool"])
  - `providers` (List[str] enum: ["airbnb", "booking", "all"], default: ["all"])
- **Output**: A list of standardized `Accommodation` objects, each with a `provider` field.
- **Handler Logic (in Python Client)**:
  1. Validates input.
  2. Based on `providers` parameter, calls `airbnb_search` (via OpenBnB MCP client) and/or `booking_search_hotels` (via Apify client wrapper) in parallel.
  3. Collects results from all sources.
  4. Normalizes results from each provider into a common TripSage `Accommodation` schema using provider-specific transformers (`AirbnbTransformer`, `BookingTransformer`).
  5. Merges, de-duplicates (if possible), and ranks/sorts the combined results.
  6. Caches and returns the unified list.

### 5.2. `mcp__accommodations__get_accommodation_details`

- **Description**: Retrieves detailed information for a specific accommodation.
- **Parameters**:
  - `accommodation_id` (string, required): The provider-specific ID.
  - `provider` (string enum: ["airbnb", "booking"], required).
  - `check_in_date`, `check_out_date`, `adults`, etc. (optional, for price accuracy).
- **Output**: A standardized `AccommodationDetails` object.
- **Handler Logic (in Python Client)**:
  1. Validates input.
  2. Routes the request to the appropriate client method (`airbnb_listing_details` or `booking_get_hotel_details`).
  3. Normalizes the provider's detailed response.
  4. Caches and returns.

### 5.3. `mcp__accommodations__compare_accommodations`

- **Description**: Fetches details for multiple accommodations to facilitate comparison.
- **Parameters**:
  - `accommodation_ids` (List[object with `id` and `provider`], required).
  - `check_in_date`, `check_out_date`, `adults` (for context).
- **Output**: A list of `AccommodationDetails` objects.
- **Handler Logic**: Calls `mcp__accommodations__get_accommodation_details` for each item in parallel.

### 5.4. `mcp__accommodations__get_reviews`

- **Description**: Retrieves reviews for a specific accommodation.
- **Parameters**:
  - `accommodation_id` (string, required).
  - `provider` (string enum: ["airbnb", "booking"], required).
  - `limit` (int, default: 10).
  - `sort` (string enum: "recent", "positive", "negative", "relevant", default: "recent").
  - `min_rating` (int, 0-5, optional).
- **Output**: `ReviewResult` object with a list of standardized `Review` objects.
- **Handler Logic**: Routes to provider-specific review fetching logic. Normalizes review data.

### 5.5. `mcp__accommodations__track_prices`

- **Description**: Sets up price tracking for a specific accommodation for given dates/guests.
- **Parameters**:
  - `accommodation_id`, `provider`, `check_in_date`, `check_out_date`, `adults`, etc.
  - `notify_when` (string enum: "price_decrease", "any_change").
  - `notification_threshold` (float, percentage).
- **Output**: Confirmation of tracking setup.
- **Handler Logic**: Stores tracking request in Supabase. A separate worker would perform checks.

(Refer to `docs/integrations/travel-providers/accommodations_mcp_implementation.md` for detailed Pydantic/Zod schemas for these tools and their outputs.)

## 6. Data Transformation and Normalization

- **`AirbnbTransformer`**: Converts OpenBnB MCP responses to TripSage's canonical `Accommodation` and `AccommodationDetails` models.
- **`BookingTransformer`**: Converts Apify Booking.com scraper results to TripSage's canonical models.
- **`NormalizationService`**: Contains shared logic for cleaning data, standardizing amenity lists, parsing ratings, etc.

## 7. Caching Strategy

- **Search Results**: TTL of 30 minutes. Cache key includes all significant search parameters.
- **Accommodation Details**: TTL of 1-6 hours (as details change less frequently than availability/pricing for a specific search).
- **Reviews**: TTL of 24 hours.
- **Cache Implementation**: Redis, accessed via TripSage's `CacheService`.

## 8. Python Client (`src/mcp/accommodations/client.py`)

This client, part of TripSage's Python backend, interacts with the (external) OpenBnB MCP and the Apify API (wrapped to act like an MCP). It implements the unified tools described in section 5.

```python
# src/mcp/accommodations/client.py (Conceptual Snippet)
from typing import Dict, Any, List, Optional
from ..base_mcp_client import BaseMCPClient # For OpenBnB
from ...utils.config import settings
from ...services.apify_service import ApifyService # Custom service to call Apify actors
# from .transformers import AirbnbTransformer, BookingTransformer # Pydantic models for transformation

class AccommodationsMCPClient: # This is TripSage's client, not an MCP server itself
    def __init__(self):
        self.openbnb_client = BaseMCPClient(
            server_name="airbnb", # From settings, points to OpenBnB MCP
            endpoint=settings.mcp_servers.airbnb.endpoint
        )
        self.apify_service = ApifyService(api_token=settings.apify_api_token.get_secret_value())
        # self.airbnb_transformer = AirbnbTransformer()
        # self.booking_transformer = BookingTransformer()
        # self.logger = get_module_logger(__name__)

    async def search_accommodations(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        providers = params.get("providers", ["all"])

        async def search_airbnb():
            # ... call self.openbnb_client.invoke_tool("airbnb_search", airbnb_params) ...
            # ... raw_airbnb_results = ...
            # ... transformed_results = self.airbnb_transformer.transform_search_results(raw_airbnb_results) ...
            # results.extend(transformed_results)
            pass # Placeholder

        async def search_booking():
            # ... call self.apify_service.run_booking_scraper(booking_params) ...
            # ... raw_booking_results = ...
            # ... transformed_results = self.booking_transformer.transform_search_results(raw_booking_results) ...
            # results.extend(transformed_results)
            pass # Placeholder

        tasks = []
        if "all" in providers or "airbnb" in providers:
            tasks.append(search_airbnb())
        if "all" in providers or "booking" in providers:
            tasks.append(search_booking())

        await asyncio.gather(*tasks)

        # Further sort/rank/deduplicate results
        return results

    # ... other unified methods like get_accommodation_details ...
```

## 9. Agent Integration

The `AccommodationsMCPClient`'s unified tools are registered with the Travel Planning Agent and Accommodation Agent. This allows agents to search for various lodging types without needing to know the underlying provider details.

## 10. Deployment

- **OpenBnB MCP Server**: Deployed as a separate Node.js process/container. Managed by TripSage's startup scripts.
- **Apify**: Cloud-based service; interaction is via API calls from TripSage backend.
- **TripSage Accommodations Logic**: Part of the main TripSage Python backend (client and transformers).

This multi-faceted approach ensures TripSage can offer a broad range of accommodation options by integrating specialized external services under a unified MCP abstraction.
