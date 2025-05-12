# Travel APIs Integration Guide

This document provides detailed information on integrating various travel APIs into the TripSage application for flight, accommodation, and other travel-related data.

## Table of Contents

- [Flight APIs](#flight-apis)
  - [Duffel API](#duffel-api)
  - [Amadeus API](#amadeus-api)
- [Accommodation APIs](#accommodation-apis)
  - [OpenBnB MCP Server for Airbnb](#openbnb-mcp-server-for-airbnb)
  - [Booking.com API Alternatives](#bookingcom-api-alternatives)
- [Maps and Location APIs](#maps-and-location-apis)
  - [Google Maps Platform](#google-maps-platform)
- [Search Integration](#search-integration)
  - [Linkup Search](#linkup-search)
  - [OpenAI Search](#openai-search)
- [Implementation Recommendations](#implementation-recommendations)

## Flight APIs

### Duffel API

Duffel provides a modern travel API for flight search, booking, and management through a single RESTful API interface.

#### Key Features

- Real-time flight search and pricing
- Flight booking and management
- Seat selection and ancillary services
- Multi-carrier support

#### Integration with Node.js

Duffel offers an official JavaScript client that simplifies API interactions:

```javascript
import { Duffel } from "@duffel/api";

const duffel = new Duffel({
  token: process.env.DUFFEL_ACCESS_TOKEN,
});

// Example: Search for flights
const offerRequestResponse = await duffel.offerRequests.create({
  slices: [
    {
      origin: "NYC",
      destination: "LHR",
      departure_date: "2025-06-21",
    },
  ],
  passengers: [{ type: "adult" }],
  cabin_class: "economy",
});

console.log(offerRequestResponse.data.id);
```

#### Implementation in TripSage

For TripSage, we recommend implementing the following Duffel API workflow:

1. **Flight Search**: Create offer requests with parameters from user input
2. **Display Options**: Show pricing, airline, and flight details from returned offers
3. **Booking**: Create orders with passenger information and payment details
4. **Order Management**: Allow users to view bookings and make changes

#### Resources

- [Duffel API Documentation](https://duffel.com/docs/api/overview/welcome)
- [Duffel JavaScript Client GitHub](https://github.com/duffelhq/duffel-api-javascript)

### Amadeus API

Amadeus offers a comprehensive set of travel APIs with extensive flight data and partner integrations.

#### Key Features

- Global distribution system with numerous airline partnerships
- Flight offers search with extensive filtering options
- Price analysis and calendar search
- Integration with loyalty programs

#### Integration with Node.js

Amadeus provides an official Node.js SDK:

```javascript
const Amadeus = require("amadeus");

const amadeus = new Amadeus({
  clientId: process.env.AMADEUS_CLIENT_ID,
  clientSecret: process.env.AMADEUS_CLIENT_SECRET,
});

// Example: Search for flights
amadeus.shopping.flightOffersSearch
  .get({
    originLocationCode: "SYD",
    destinationLocationCode: "BKK",
    departureDate: "2025-06-01",
    adults: "2",
  })
  .then(function (response) {
    console.log(response.data);
  })
  .catch(function (error) {
    console.error(error);
  });
```

#### OAuth Authentication

Amadeus uses OAuth 2.0 with Client Credentials Grant:

1. Get API credentials from the Amadeus Developer Portal
2. Authenticate using client ID and secret to receive an access token
3. The SDK automatically handles token management and renewal

#### Resources

- [Amadeus Self-Service APIs Documentation](https://developers.amadeus.com/self-service/category/air)
- [Amadeus Node.js SDK GitHub](https://github.com/amadeus4dev/amadeus-node)

## Accommodation APIs

### OpenBnB MCP Server for Airbnb

The OpenBnB MCP server provides access to Airbnb listings without requiring an official API key through the Model Context Protocol (MCP).

#### Key Features

- Search for Airbnb listings with filters
- Retrieve detailed listing information
- No API key required
- Compatible with AI agents through MCP

#### Integration with Node.js

To use the OpenBnB MCP server in a Node.js application:

```javascript
// Example configuration for using the MCP server
const config = {
  mcpServers: {
    airbnb: {
      command: "npx",
      args: ["-y", "@openbnb/mcp-server-airbnb", "--ignore-robots-txt"],
    },
  },
};

// Usage in a Node.js application through an MCP client
// (Implementation will depend on your MCP client library)
const result = await mcpClient.call("airbnb", "airbnb_search", {
  location: "Miami, FL",
  checkin: "2025-07-01",
  checkout: "2025-07-08",
  adults: 2,
});
```

#### Resources

- [OpenBnB MCP Server GitHub](https://github.com/openbnb-org/mcp-server-airbnb)

### Booking.com API Alternatives

Since Booking.com's official API has limited availability, several alternatives exist for accessing accommodation data.

#### Options

1. **Apify Booking.com Scraper**:

   - Extracts hotel data from Booking.com
   - Available as a Node.js library
   - Requires Apify API token

   ```javascript
   import { ApifyClient } from "apify-client";

   const client = new ApifyClient({ token: process.env.APIFY_TOKEN });

   const run = await client.actor("voyager/booking-scraper").call({
     search: "New York",
     checkIn: "2025-07-01",
     checkOut: "2025-07-08",
     adults: 2,
     rooms: 1,
     currency: "USD",
     language: "en-gb",
   });

   const items = await client.dataset(run.defaultDatasetId).listItems();
   console.log(items);
   ```

2. **RapidAPI Hotel API**:
   - Provides access to multiple booking platforms
   - REST API with detailed search parameters
   - Requires RapidAPI subscription

#### Implementation Recommendation

For TripSage, we recommend using a dual approach:

1. Use OpenBnB MCP server for Airbnb listings
2. Use Apify's Booking.com scraper for hotel listings

This combination provides comprehensive accommodation options while minimizing integration complexity.

## Maps and Location APIs

### Google Maps Platform

Google Maps provides comprehensive location services for travel applications.

#### Key Features

- Places API for location search
- Maps JavaScript API for interactive maps
- Distance Matrix API for travel time calculations
- Geocoding API for address lookups

#### Integration with Node.js

Using the Google Maps JavaScript API with Node.js/Express:

```javascript
// Server-side (Express.js)
app.get("/api/places", async (req, res) => {
  const { query } = req.query;

  try {
    const response = await axios.get(
      `https://maps.googleapis.com/maps/api/place/textsearch/json?query=${encodeURIComponent(
        query
      )}&key=${process.env.GOOGLE_MAPS_API_KEY}`
    );

    res.json(response.data.results);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Client-side (JavaScript)
function initMap() {
  const map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: -34.397, lng: 150.644 },
    zoom: 8,
  });
}
```

#### Resources

- [Google Maps Platform Documentation](https://developers.google.com/maps/documentation)
- [Google Maps Node.js Client](https://github.com/googlemaps/google-maps-services-js)

## Search Integration

### Linkup Search

Linkup provides real-time web search capabilities that can be integrated into applications.

#### Key Features

- Real-time web search integration
- Targeted search across travel sites
- Rich result formatting options
- Simple API structure

#### Integration with Node.js

Using the Linkup MCP server in a Node.js application:

```javascript
// Example search using Linkup MCP
const results = await linkupClient.searchWeb({
  query: "best hotels in barcelona",
  depth: "deep", // Use "deep" for comprehensive travel research
});

// Process and display results
console.log(results);
```

#### Implementation Recommendation

Linkup search is ideal for enhancing travel recommendations with real-time information about destinations, accommodations, and activities. However, use strategically to avoid excessive API calls.

### OpenAI Search

OpenAI's search functionality is built into the OpenAI Assistants API.

#### Key Features

- Built directly into the OpenAI API
- Search managed by OpenAI's infrastructure
- Simple integration with agent tools

#### Implementation Recommendation

For TripSage, consider the following search strategy:

1. Use Linkup for detailed, travel-specific searches
2. Use OpenAI's built-in search for general information
3. Implement caching to reduce redundant searches

## Implementation Recommendations

Based on our research, we recommend the following approach for TripSage:

### API Selection

- **Flights**: Use Duffel as the primary flight search and booking API
- **Accommodations**: Use OpenBnB MCP for Airbnb listings and Apify for Booking.com data
- **Maps**: Implement Google Maps Platform for location services
- **Search**: Use Linkup for travel-specific searches with OpenAI's built-in search as backup

### Architecture Design

1. **Service-Oriented Architecture**:

   - Create separate services for each travel component (flights, accommodations, etc.)
   - Implement a central API gateway to route requests
   - Use microservices for scalability

2. **MCP Integration Strategy**:

   - Create a unified MCP client that can work with multiple MCP servers
   - Handle authentication and error management centrally
   - Implement caching to reduce duplicate requests

3. **Data Flow**:
   - User requests → API Gateway → Appropriate Service → External API → Response
   - Cache frequent searches and results
   - Implement retry logic for API failures

### Security Considerations

- Store all API keys in environment variables
- Implement rate limiting for external API calls
- Use HTTPS for all requests
- Validate and sanitize user inputs

### Performance Optimization

- Cache search results to reduce API calls
- Implement background polling for price updates
- Use asynchronous processing for non-blocking operations
- Consider serverless functions for scaling during peak demand

This implementation strategy provides a comprehensive, scalable solution for the TripSage travel planning system while minimizing integration complexity and maximizing performance.
