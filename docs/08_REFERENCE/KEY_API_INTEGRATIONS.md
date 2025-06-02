# TripSage Key External API Integrations Guide

This document outlines the strategy and implementation details for integrating key external third-party APIs that power various functionalities within the TripSage system. TripSage uses **7 direct SDK integrations** and **1 MCP server** (Airbnb) for optimal performance and simplified architecture.

## 1. General API Integration Strategy

TripSage's unified architecture approach to integrating external APIs involves:

1.  **Direct SDK Integration**: 7 primary services use official SDKs for optimal performance and native Python integration
2.  **Single MCP Server**: Only Airbnb integration uses MCP server due to lack of official API access
3.  **BYOK (Bring Your Own Key)**: Centralized user-provided API key management with secure encryption
4.  **Unified Configuration**: All API keys and service endpoints managed through Pydantic settings with validation
5.  **Advanced Error Handling**: Standardized retry mechanisms, circuit breakers, and graceful degradation
6.  **DragonflyDB Caching**: High-performance caching with multi-tier TTL strategy (25x faster than Redis)
7.  **Asynchronous Operations**: All API calls use `httpx` with connection pooling and timeout management

## 2. Flight Data and Booking APIs

### 2.1. Primary Provider: Duffel API

*   **Website**: [Duffel.com](https://duffel.com/)
*   **Functionality**: Flight search (Offer Requests, Offers), seat selection, ancillary services, booking (Order creation), order management (changes, cancellations).
*   **Coverage**: 300+ airlines, including NDC, GDS, and LCCs.
*   **API Model**: RESTful JSON API.
*   **Authentication**: Bearer token (API key). `Authorization: Bearer <your_duffel_api_key>`.
*   **Versioning**: Via `Duffel-Version` header (e.g., `2023-06-02`).
*   **SDKs**: Official SDKs available (e.g., `@duffel/api` for Node.js, `duffel_api` for Python). TripSage's Flights MCP (Node.js based) uses the official Node.js SDK.
*   **Pricing**: Transaction-based fees.
*   **TripSage Integration**: **Direct SDK Integration** via `DuffelFlightsService` using the official Duffel Python SDK.
    *   Key Endpoints Used (by Flights MCP):
        *   `POST /air/offer_requests`: To initiate a flight search.
        *   `GET /air/offers?offer_request_id={id}`: To retrieve flight offers.
        *   `GET /air/offers/{id}`: To get details of a specific offer.
        *   `GET /air/seat_maps?offer_id={id}`: For seat selection.
        *   `POST /air/orders`: To create a booking.
        *   `GET /air/orders/{id}`: To retrieve booking details.
*   **Rationale for Choice**: Modern API design, comprehensive features, good developer experience, suitable pricing model for TripSage.

### 2.2. Alternatives Considered for Flights:

*   **Amadeus API**:
    *   Broader coverage (400+ airlines) and more established.
    *   More complex API and authentication (OAuth 2.0). Pricing can be less transparent.
    *   Considered as a potential future addition for expanded coverage if Duffel proves insufficient for certain routes/airlines.
*   **Skyscanner API**:
    *   Extensive coverage (1200+ airlines).
    *   Primarily for search and price comparison; booking is usually a redirect.
    *   Pay-per-click model less suitable for deep integration.
*   **Kiwi.com API**:
    *   Good coverage (750+ airlines), strong in LCCs and virtual interlining.
    *   Commission-based model.
    *   A viable alternative or supplement to Duffel.

## 3. Accommodation Data APIs

TripSage uses a hybrid approach, primarily relying on MCP servers that scrape public data, and potentially direct API integrations in the future.

### 3.1. Airbnb Data (via Airbnb MCP Server)

*   **Source**: Public Airbnb website data.
*   **Integration**: Via the `@openbnb/mcp-server-airbnb` (Node.js) - **Only remaining MCP integration**.
*   **Functionality**: Search listings, get listing details, pricing information. No booking capability.
*   **Authentication**: None required for the MCP server itself.
*   **Rationale**: No official Airbnb API available; MCP provides structured access to vacation rental inventory.
*   **TripSage Integration**: Via dedicated `AirbnbMCPClient` with caching and error handling.

### 3.2. Alternative Hotel Data Sources

*   **Note**: Direct hotel booking integrations are planned for future releases.
*   **Current Focus**: Airbnb vacation rentals provide unique inventory not available through other channels.
*   **Future Integrations**: Considering direct partnerships with hotel chains and OTA APIs for comprehensive accommodation coverage.

### 3.3. Alternatives Considered for Accommodations:

*   **RapidAPI Hotels / Other Aggregators**: Offer licensed data from multiple platforms and direct booking.
    *   **Pros**: Licensed data, booking capability.
    *   **Cons**: Subscription costs, potentially less comprehensive than targeted scraping for specific platforms.
*   **Amadeus Hotel API**: Licensed GDS content.
    *   **Pros**: Integrated with flight GDS, booking capability.
    *   **Cons**: Can have limited coverage for non-traditional lodging.

## 4. Maps and Location APIs

### 4.1. Primary Provider: Google Maps Platform

*   **Website**: [cloud.google.com/maps-platform](https://cloud.google.com/maps-platform/)
*   **Functionality**: Geocoding, reverse geocoding, place search, place details, directions, distance matrix, static maps, Street View.
*   **API Model**: RESTful JSON APIs.
*   **Authentication**: API Key.
*   **SDKs**: Official SDKs for various languages (e.g., `@googlemaps/google-maps-services-js` for Node.js, `google-maps-services-python`).
*   **Pricing**: Pay-as-you-go with a significant monthly free tier ($200 credit).
*   **TripSage Integration**: **Direct SDK Integration** via `GoogleMapsService` using the official Google Maps Python SDK with BYOK support.
*   **Rationale for Choice**: Highest quality and most comprehensive mapping, place, and routing data globally. Excellent documentation and SDKs. Free tier is usually sufficient for development and personal/small-scale use.

### 4.2. Alternatives Considered for Maps:

*   **Mapbox**:
    *   Very good map quality and developer tools.
    *   Competitive pricing, also with a free tier.
    *   A strong alternative, but Google Maps often has slightly better POI data coverage.
*   **OpenStreetMap (OSM)**:
    *   Free and open data.
    *   Requires self-hosting for services like geocoding (e.g., Nominatim) and routing (e.g., OSRM, GraphHopper), or using third-party services built on OSM.
    *   Data quality can vary by region.
*   **HERE Maps**:
    *   Strong enterprise offering, particularly good for automotive and logistics.
    *   Good global coverage.

## 5. Web Crawling and Search APIs

### 5.1. Primary Method: Crawl4AI (Direct Integration)

*   **Functionality**: High-performance web crawling and content extraction optimized for travel information gathering.
*   **Integration**: **Direct SDK Integration** via `Crawl4AIService` with async HTTP client.
*   **Configuration**: Self-hosted Crawl4AI instance with travel-specific extraction rules and content filtering.
*   **Performance**: Async processing with connection pooling, 5 concurrent requests max.
*   **Cost**: Self-hosted infrastructure costs only, no per-request fees.
*   **Rationale**: Superior performance and control compared to external search APIs. Optimized for structured travel data extraction.

### 5.2. Dynamic Content Handling

*   **Playwright Integration**: Embedded within Crawl4AI for JavaScript-heavy sites and dynamic content.
*   **Browser Automation**: Headless Chrome instances for complex interactions and SPA rendering.
*   **Intelligent Routing**: Automatic selection between static crawling and browser automation based on site requirements.

### 5.3. Alternatives Considered for General Search:

*   **Bing Search API / Google Custom Search API**:
    *   Provide direct programmatic access to search engine results.
    *   **Pros**: More control over search parameters and results.
    *   **Cons**: Additional API key management, separate costs, and requires more logic to integrate effectively with AI agents compared to the native WebSearchTool.
*   **Linkup Search (MCP)**:
    *   An MCP server for web search.
    *   **Pros**: Standardized MCP interface.
    *   **Cons**: May add an extra layer if the underlying search is one of the above; WebSearchTool is more direct for OpenAI agents. Considered as a potential supplement if WebSearchTool has limitations.

## 6. BYOK (Bring Your Own Key) Authentication System

*   **User-Provided API Keys**: Users provide their own API keys for external services, ensuring cost control and compliance.
*   **Secure Storage**: API keys encrypted using AES-256 with user-specific salt and master secret.
*   **Key Validation**: Automatic validation of API keys before storage and periodic health checks.
*   **Service Mapping**: Each user can configure keys for specific services (Duffel, Google Maps, etc.).
*   **Fallback Handling**: Graceful degradation when user keys are invalid or quota exceeded.
*   **OAuth 2.0 (Google Calendar)**: 
    1.  **Authorization Request**: TripSage initiates OAuth flow via `GoogleCalendarService` 
    2.  **User Consent**: User grants calendar access permissions
    3.  **Token Exchange**: Service exchanges authorization code for access/refresh tokens
    4.  **Secure Storage**: Tokens encrypted and stored in Supabase with user association
    5.  **Automatic Refresh**: Background token refresh with fallback error handling
    6.  **Scoped Access**: Minimal required permissions for calendar read/write operations

## 7. Current External Service Integrations

### Direct SDK Integrations (7 services):

1. **Duffel** - Flight search and booking (`DuffelFlightsService`)
2. **Google Maps** - Geocoding, places, directions (`GoogleMapsService`)
3. **Google Calendar** - Calendar integration (`GoogleCalendarService`)
4. **OpenWeatherMap** - Weather data (`WeatherService`)
5. **Visual Crossing** - Extended weather forecasts (`WeatherService`)
6. **Crawl4AI** - Web crawling and content extraction (`Crawl4AIService`)
7. **Mem0** - Memory and embedding operations (`Mem0Service`)

### MCP Integration (1 service):

8. **Airbnb** - Vacation rental listings (`AirbnbMCPClient`)

### Service Architecture:

*   **Unified Service Pattern**: All services inherit from `BaseService` with standardized error handling
*   **DragonflyDB Integration**: High-performance caching across all services
*   **BYOK Support**: User-provided API keys for cost control and compliance
*   **Agent Tool Integration**: Services exposed as `@function_tool` for AI agent use
*   **Performance Monitoring**: Request tracking, error rates, and latency monitoring

This streamlined integration strategy provides optimal performance while maintaining flexibility and user control over API costs.