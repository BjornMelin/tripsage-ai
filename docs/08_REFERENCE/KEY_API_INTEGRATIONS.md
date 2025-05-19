# TripSage Key External API Integrations Guide

This document outlines the strategy and implementation details for integrating key external third-party APIs that power various functionalities within the TripSage system. While TripSage primarily interacts with these services via its Model Context Protocol (MCP) servers or client wrappers, understanding the underlying APIs is crucial.

## 1. General API Integration Strategy

TripSage's approach to integrating external APIs involves:

1.  **Abstraction via MCPs/Clients**: Most direct API interactions are encapsulated within specific MCP servers (e.g., Flights MCP, Weather MCP) or dedicated Python client wrappers. This decouples the core application logic from the specifics of external APIs.
2.  **Centralized Configuration**: API keys and service endpoints are managed through the centralized Pydantic settings system.
3.  **Error Handling**: Standardized error handling and retry mechanisms are implemented in the client wrappers or MCP servers.
4.  **Caching**: Responses from external APIs are cached (using Redis) to improve performance and manage rate limits/costs.
5.  **Asynchronous Operations**: API calls are made asynchronously using libraries like `httpx` (Python) or `axios` (Node.js for MCPs).

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
*   **TripSage Integration**: Via the **Flights MCP Server**. The MCP server's `DuffelService` encapsulates all interactions with the Duffel API.
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

### 3.1. Airbnb Data (via OpenBnB MCP Server)

*   **Source**: Public Airbnb website data.
*   **Integration**: Via the `@openbnb/mcp-server-airbnb` (Node.js).
*   **Functionality**: Search listings, get listing details. No booking.
*   **Authentication**: None required for the OpenBnB MCP itself.
*   **Rationale**: Provides access to Airbnb's unique vacation rental inventory without needing a private API.
*   **TripSage Integration**: Via the **Accommodations MCP Server** (which internally uses a client for the OpenBnB MCP).

### 3.2. Booking.com Data (via Apify Booking.com Scraper)

*   **Source**: Public Booking.com website data.
*   **Integration**: Via an Apify actor (e.g., `voyager/booking-scraper`). TripSage uses the Apify API to run this actor and retrieve results.
*   **Functionality**: Hotel/accommodation search, property details, pricing, reviews. No direct booking.
*   **Authentication**: Apify API Token.
*   **Pricing**: Apify platform credits (pay-per-execution/usage).
*   **Rationale**: Access to Booking.com's extensive hotel inventory.
*   **TripSage Integration**: Via the **Accommodations MCP Server** (which has an internal `ApifyService` to call the Apify API).

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
*   **TripSage Integration**: Via the **Google Maps MCP Server** (`@modelcontextprotocol/server-google-maps`, Node.js based). TripSage's Python backend uses a client to communicate with this MCP server.
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

## 5. Web Search APIs (for General Information)

### 5.1. Primary Method: OpenAI WebSearchTool (via Agents SDK)

*   **Functionality**: Allows AI agents to perform web searches to answer general knowledge questions, find current events, or research topics not covered by specialized APIs.
*   **Integration**: Natively available as a tool within the OpenAI Agents SDK.
*   **Configuration**: TripSage enhances this by providing travel-optimized `allowed_domains` and `blocked_domains` lists to guide the agent towards reliable travel information sources.
*   **Cost**: Included as part of the OpenAI API usage (token consumption for search queries and processing results).
*   **Rationale**: Simplifies implementation as it's built into the agent framework. Agent can autonomously decide when and what to search. Travel-specific domain configuration helps improve relevance.

### 5.2. Specialized Web Crawling (via WebCrawl MCP)

*   **Functionality**: For deeper, structured data extraction from specific websites or topics, TripSage uses its **WebCrawl MCP**. This MCP, in turn, uses:
    *   **Crawl4AI (Self-Hosted)**: For efficient bulk crawling and extraction from informational sites.
    *   **Playwright (via BrowserAutomation MCP or embedded)**: For dynamic, JavaScript-heavy sites.
*   **Rationale**: Used when WebSearchTool is too general or cannot extract information in the required structured format.

### 5.3. Alternatives Considered for General Search:

*   **Bing Search API / Google Custom Search API**:
    *   Provide direct programmatic access to search engine results.
    *   **Pros**: More control over search parameters and results.
    *   **Cons**: Additional API key management, separate costs, and requires more logic to integrate effectively with AI agents compared to the native WebSearchTool.
*   **Linkup Search (MCP)**:
    *   An MCP server for web search.
    *   **Pros**: Standardized MCP interface.
    *   **Cons**: May add an extra layer if the underlying search is one of the above; WebSearchTool is more direct for OpenAI agents. Considered as a potential supplement if WebSearchTool has limitations.

## 6. Authentication Flow for External APIs

*   **API Keys**: For services like Duffel, Apify, Google Maps, API keys are stored securely in TripSage's centralized configuration (loaded from environment variables using Pydantic `SecretStr`). These keys are used by the respective MCP servers or client wrappers when making calls.
*   **OAuth 2.0 (e.g., Google Calendar, potentially Amadeus)**:
    1.  **Authorization Request**: TripSage (via the relevant MCP server like Calendar MCP) initiates the OAuth flow by redirecting the user to the provider's authorization server with requested scopes.
    2.  **User Consent**: User grants permission.
    3.  **Authorization Code**: Provider redirects back to TripSage's registered callback URI with an authorization code.
    4.  **Token Exchange**: TripSage's MCP server exchanges the code for an access token and a refresh token.
    5.  **Token Storage**: Access and refresh tokens are securely stored (e.g., encrypted in Supabase, associated with the TripSage user).
    6.  **API Access**: Access token is used for API calls. Refresh token is used to obtain new access tokens when they expire.

## 7. API Client Implementation in TripSage

For each external API integrated (usually via an MCP server), TripSage has a corresponding Python client class (e.g., `FlightsMCPClient`, `GoogleMapsMCPClient`). These clients typically:

*   Inherit from a `BaseMCPClient` (part of the MCP Abstraction Layer).
*   Handle request formatting, authentication, and response parsing.
*   Integrate with the Redis caching layer.
*   Implement standardized error handling.
*   Expose methods as `@function_tool` for easy use by AI agents.

(See specific MCP server documents in `docs/04_MCP_SERVERS/` for details on their underlying API usage and client implementations.)

This multi-API integration strategy allows TripSage to leverage best-in-class services for each specific travel domain, providing a rich and comprehensive dataset for its AI planning agents.