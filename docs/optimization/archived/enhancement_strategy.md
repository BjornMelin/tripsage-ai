# TripSage Enhancement Strategy

This document outlines a comprehensive strategy for enhancing the TripSage travel planning application with additional integrations for weather data, web crawling, browser automation, calendar services, and custom MCP servers. The recommendations focus on personal usage scenarios where individual API keys are employed, prioritizing cost-effectiveness and ease of integration.

## Table of Contents

- [Overview](#overview)
- [Weather Integration](#weather-integration)
- [Web Crawling Integration](#web-crawling-integration)
- [Browser Automation Integration](#browser-automation-integration)
- [Calendar Integration](#calendar-integration)
- [Custom MCP Development Assessment](#custom-mcp-development-assessment)
- [Integration Architecture](#integration-architecture)
- [Implementation Priorities](#implementation-priorities)
- [Personal API Key Management](#personal-api-key-management)

## Overview

TripSage currently uses Duffel API for flights, OpenBnB MCP for Airbnb listings, Apify for Booking.com data, Google Maps Platform for location services, and a hybrid Linkup/OpenAI approach for search. This enhancement strategy expands capabilities while maintaining the personal-use focus, ensuring easy deployment for individual users with their own API keys.

Based on comprehensive research, we recommend the following enhancements:

1. **Weather Integration**: OpenWeatherMap API with a custom MCP server wrapper
2. **Web Crawling**: Firecrawl with selective usage patterns
3. **Browser Automation**: Browser-use for personal travel booking tasks
4. **Calendar Integration**: Google Calendar API with OAuth 2.0 personal authentication flow
5. **Custom MCP Development**: Targeted implementation using FastMCP for weather data integration

These recommendations provide optimal balance between functionality, cost, and ease of implementation for personal use cases.

## Weather Integration

### Solution Comparison

| Feature                 | OpenWeatherMap               | WeatherAPI          | Weatherbit        | Tomorrow.io       |
| ----------------------- | ---------------------------- | ------------------- | ----------------- | ----------------- |
| **Free Tier**           | 60 calls/min, 1M calls/month | 1M calls/month      | 50 calls/day      | 1K calls/day      |
| **Historical Data**     | 5 days (free)                | 7 days (free)       | Limited free      | Limited free      |
| **Forecast Length**     | 16 days                      | 14 days             | 16 days           | 15 days           |
| **Data Granularity**    | 3-hour intervals             | Hourly              | 3-hour intervals  | Hourly            |
| **API Simplicity**      | High                         | High                | Medium            | Medium            |
| **Documentation**       | Excellent                    | Very Good           | Good              | Good              |
| **Personal Usage Cost** | Free for most users          | Free for most users | Limited free tier | Limited free tier |

### Recommended Approach: OpenWeatherMap with Custom MCP Wrapper

We recommend using **OpenWeatherMap API** for weather integration due to its generous free tier, comprehensive data, and simple REST API design that is ideal for personal use. A custom MCP wrapper using FastMCP will streamline integration with the TripSage agent system.

**Key implementation components:**

1. **Data Collection**:

   - Current weather conditions for travel destinations
   - 5-day forecast with 3-hour step data
   - Historical weather patterns for travel planning

2. **Integration Touchpoints**:

   - Weather data displayed alongside destination information
   - Weather-aware travel recommendations
   - Weather-based activity suggestions
   - Packing recommendations based on expected conditions

3. **Implementation Code Example**:

```javascript
class WeatherService {
  constructor() {
    this.apiKey = process.env.OPENWEATHERMAP_API_KEY;
    this.baseUrl = "https://api.openweathermap.org/data/2.5";
  }

  async getCurrentWeather(location) {
    const url = `${this.baseUrl}/weather?q=${encodeURIComponent(
      location
    )}&units=metric&appid=${this.apiKey}`;
    const response = await axios.get(url);
    return this.formatWeatherData(response.data);
  }

  async getForecast(location, days = 5) {
    const url = `${this.baseUrl}/forecast?q=${encodeURIComponent(
      location
    )}&units=metric&appid=${this.apiKey}`;
    const response = await axios.get(url);
    return this.formatForecastData(response.data, days);
  }

  formatWeatherData(data) {
    return {
      location: {
        name: data.name,
        country: data.sys.country,
        coordinates: {
          lat: data.coord.lat,
          lon: data.coord.lon,
        },
      },
      current: {
        temperature: data.main.temp,
        feels_like: data.main.feels_like,
        humidity: data.main.humidity,
        wind_speed: data.wind.speed,
        condition: {
          main: data.weather[0].main,
          description: data.weather[0].description,
          icon: data.weather[0].icon,
        },
      },
      timestamp: data.dt,
    };
  }

  formatForecastData(data, days) {
    // Process 5-day forecast data (3-hour intervals)
    // Limit to requested number of days
    const forecastItems = data.list.filter(
      (item, index) => index < days * 8 // 8 measurements per day (3-hour intervals)
    );

    return {
      location: {
        name: data.city.name,
        country: data.city.country,
        coordinates: {
          lat: data.city.coord.lat,
          lon: data.city.coord.lon,
        },
      },
      forecast: forecastItems.map((item) => ({
        timestamp: item.dt,
        temperature: item.main.temp,
        feels_like: item.main.feels_like,
        humidity: item.main.humidity,
        wind_speed: item.wind.speed,
        condition: {
          main: item.weather[0].main,
          description: item.weather[0].description,
          icon: item.weather[0].icon,
        },
      })),
    };
  }
}
```

4. **Custom MCP Implementation**:

```javascript
// weather-mcp.js - FastMCP implementation for weather data
import { FastMCP } from "fastmcp";
import { WeatherService } from "./weather-service.js";

const weatherService = new WeatherService();

const mcp = new FastMCP();

// Register tools
mcp.registerTool({
  name: "get_current_weather",
  description: "Get current weather for a location",
  parameters: {
    location: {
      type: "string",
      description: "Location name or coordinates",
    },
  },
  execute: async ({ location }) => {
    try {
      const result = await weatherService.getCurrentWeather(location);
      return result;
    } catch (error) {
      return { error: error.message };
    }
  },
});

mcp.registerTool({
  name: "get_weather_forecast",
  description: "Get weather forecast for a location",
  parameters: {
    location: {
      type: "string",
      description: "Location name or coordinates",
    },
    days: {
      type: "number",
      description: "Number of days for forecast (1-5)",
      default: 5,
    },
  },
  execute: async ({ location, days }) => {
    try {
      const result = await weatherService.getForecast(location, days);
      return result;
    } catch (error) {
      return { error: error.message };
    }
  },
});

// Start the server
mcp.serve({
  port: process.env.WEATHER_MCP_PORT || 3100,
});
```

### Personal API Key Considerations

OpenWeatherMap offers a free API key with generous limits suitable for personal usage:

- 60 calls per minute
- 1,000,000 calls per month
- Simple registration at [OpenWeatherMap API](https://openweathermap.org/api)

## Web Crawling Integration

### Solution Comparison

| Feature                      | Firecrawl                 | Crawl4AI                |
| ---------------------------- | ------------------------- | ----------------------- |
| **MCP Integration**          | Native                    | Requires custom wrapper |
| **Personal Usage Free Tier** | Limited credits           | Limited pages/month     |
| **Customization**            | High                      | Medium                  |
| **Ease of Integration**      | Very high                 | Medium                  |
| **Documentation**            | Excellent                 | Good                    |
| **Scheduling**               | Supports scheduled crawls | Limited                 |
| **Content Extraction**       | Multiple formats          | Limited formats         |

### Recommended Approach: Firecrawl

We recommend **Firecrawl** for web crawling integration due to its native MCP interface, excellent documentation, and flexible crawling capabilities that are ideal for personal travel research use cases.

**Key implementation components:**

1. **Use Cases**:

   - Crawling travel blogs for destination insights
   - Gathering current travel advisories and entry requirements
   - Collecting attraction details and operating hours
   - Researching local events during travel dates

2. **Implementation Strategy**:

   - Implement targeted, on-demand crawling rather than bulk data collection
   - Cache crawl results to minimize API usage
   - Prioritize high-value travel information sources
   - Implement structured data extraction for consistent processing

3. **Implementation Code Example**:

```javascript
class FirecrawlService {
  constructor() {
    this.mcpClient = mcpClient; // From MCP client implementation
  }

  async crawlTravelAdvisories(country) {
    try {
      const result = await this.mcpClient.call("firecrawl", "firecrawl_crawl", {
        url: `https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories/${country.toLowerCase()}-travel-advisory.html`,
        maxDepth: 0, // Just crawl the specific page
        scrapeOptions: {
          formats: ["markdown"],
          onlyMainContent: true,
        },
      });

      return {
        crawlId: result.id,
        status: result.status,
      };
    } catch (error) {
      console.error("Error crawling travel advisories:", error);
      throw error;
    }
  }

  async crawlAttractions(destination) {
    try {
      const result = await this.mcpClient.call(
        "firecrawl",
        "firecrawl_search",
        {
          query: `top attractions in ${destination}`,
          limit: 5, // Limit results to control costs
          scrapeOptions: {
            formats: ["markdown"],
            onlyMainContent: true,
          },
        }
      );

      return result;
    } catch (error) {
      console.error("Error crawling attractions:", error);
      throw error;
    }
  }

  async extractStructuredData(url, schema) {
    try {
      const result = await this.mcpClient.call(
        "firecrawl",
        "firecrawl_extract",
        {
          urls: [url],
          schema: schema,
        }
      );

      return result;
    } catch (error) {
      console.error("Error extracting structured data:", error);
      throw error;
    }
  }

  async checkCrawlStatus(crawlId) {
    try {
      const result = await this.mcpClient.call(
        "firecrawl",
        "firecrawl_check_crawl_status",
        {
          id: crawlId,
        }
      );

      return result;
    } catch (error) {
      console.error("Error checking crawl status:", error);
      throw error;
    }
  }
}
```

4. **Cost Control Mechanisms**:
   - Implement request throttling
   - Use targeted searches rather than broad crawls
   - Cache results aggressively (7-14 day TTL for travel information)
   - Implement a daily crawl quota system

### Personal Usage Considerations

For personal usage, we recommend:

- Setting up a free Firecrawl account
- Using the selective crawling approach outlined above
- Implementing a local caching layer to minimize API calls
- Setting weekly quotas to prevent unexpected charges

## Browser Automation Integration

### Solution Comparison

| Feature                      | Browser-use | Browserbase+Stagehand | Stagehand Standalone |
| ---------------------------- | ----------- | --------------------- | -------------------- |
| **Personal Usage Free Tier** | Generous    | Limited               | Limited              |
| **MCP Integration**          | Native      | Requires wrapper      | Requires wrapper     |
| **Installation Complexity**  | Low         | Medium                | Medium               |
| **Developer Experience**     | Excellent   | Good                  | Good                 |
| **Authentication Handling**  | Built-in    | Limited               | Limited              |
| **Headless Mode**            | Supported   | Supported             | Supported            |
| **Visual Debugging**         | Excellent   | Good                  | Limited              |

### Recommended Approach: Browser-use

We recommend **Browser-use** for browser automation due to its native MCP integration, excellent developer experience, and generous free tier that makes it ideal for personal usage. It excels at automating travel booking workflows while minimizing implementation complexity.

**Key implementation components:**

1. **Use Cases**:

   - Automating flight booking confirmations
   - Checking in for flights
   - Scraping detailed hotel information
   - Capturing screenshots of travel itineraries

2. **Implementation Strategy**:

   - Create reusable automation workflows for common travel tasks
   - Implement secure credential management for travel sites
   - Add mechanisms to handle website changes gracefully
   - Include screenshot capabilities for verification

3. **Implementation Code Example**:

```javascript
class BrowserAutomationService {
  constructor() {
    this.mcpClient = mcpClient; // From MCP client implementation
  }

  async checkFlightStatus(airline, flightNumber, date) {
    try {
      // Navigate to airline status page
      await this.mcpClient.call("browser", "browser_navigate", {
        url: this.getAirlineStatusUrl(airline),
      });

      // Get page snapshot for analysis
      const snapshot = await this.mcpClient.call(
        "browser",
        "browser_snapshot",
        {}
      );

      // Fill flight details form
      await this.mcpClient.call("browser", "browser_type", {
        element: "Flight number input field",
        ref: this.findElementRef(snapshot, "input", "flight"),
        text: flightNumber,
        submit: false,
      });

      await this.mcpClient.call("browser", "browser_type", {
        element: "Flight date input field",
        ref: this.findElementRef(snapshot, "input", "date"),
        text: date,
        submit: false,
      });

      // Click submit button
      await this.mcpClient.call("browser", "browser_click", {
        element: "Search button",
        ref: this.findElementRef(snapshot, "button", "search"),
      });

      // Wait for results to load
      await this.mcpClient.call("browser", "browser_wait", {
        time: 3,
      });

      // Take screenshot of results
      const screenshot = await this.mcpClient.call(
        "browser",
        "browser_screenshot",
        {
          name: `flight_status_${airline}_${flightNumber}`,
        }
      );

      // Get visible text content
      const content = await this.mcpClient.call(
        "browser",
        "browser_get_visible_text",
        {}
      );

      return {
        text: content,
        screenshot: screenshot,
      };
    } catch (error) {
      console.error("Error checking flight status:", error);
      throw error;
    }
  }

  async checkInForFlight(airline, confirmationCode, lastName, options = {}) {
    // Implement airline-specific check-in workflow
    // Similar pattern to above but with airline-specific logic
  }

  findElementRef(snapshot, elementType, nameHint) {
    // Helper to find element references in page snapshot
    // Implementation depends on snapshot structure
    // This is a simplified example
    const elements = snapshot.elements.filter(
      (el) =>
        el.tagName.toLowerCase() === elementType &&
        (el.name?.includes(nameHint) ||
          el.id?.includes(nameHint) ||
          el.className?.includes(nameHint))
    );

    return elements[0]?.ref;
  }

  getAirlineStatusUrl(airline) {
    // Map airline code to status URL
    const airlineUrls = {
      AA: "https://www.aa.com/travelInformation/flights/status",
      DL: "https://www.delta.com/flight-status-lookup",
      UA: "https://www.united.com/en/us/flightstatus",
      // Add more airlines as needed
    };

    return airlineUrls[airline] || "https://www.flightstats.com";
  }
}
```

4. **Security Considerations**:
   - Never hardcode credentials
   - Implement secure credential storage
   - Use headless mode for background operations
   - Implement timeout handling to prevent hanging processes

### Personal Usage Considerations

Browser-use offers an excellent free tier for personal projects:

- No setup cost
- 100 automation minutes free per month
- Simple MCP interface
- Works well with personal travel booking needs

## Calendar Integration

### Solution Comparison

| Feature                    | Google Calendar | Microsoft Calendar | Nylas Calendar  |
| -------------------------- | --------------- | ------------------ | --------------- |
| **Free Tier**              | Generous        | Limited            | Very limited    |
| **Personal Auth Flow**     | OAuth 2.0       | OAuth 2.0          | OAuth + API key |
| **Integration Complexity** | Medium          | High               | Medium          |
| **Documentation**          | Excellent       | Good               | Good            |
| **Personal Usage Cost**    | Free            | Free               | Paid plans      |
| **API Limits**             | 1M requests/day | More restricted    | Limited         |

### Recommended Approach: Google Calendar API

We recommend **Google Calendar API** for calendar integration due to its generous free tier, robust OAuth 2.0 flow that works well for personal usage, and comprehensive documentation. It provides the best balance of functionality and simplicity for travel itinerary integration.

**Key implementation components:**

1. **Use Cases**:

   - Adding flight bookings to calendar
   - Creating travel itinerary events
   - Setting reminders for check-in times
   - Sharing trip details with travel companions

2. **Integration Approach**:

   - Implement OAuth 2.0 with personal Google accounts
   - Create structured travel events with rich metadata
   - Add smart notifications for travel-related activities
   - Support importing/exporting in standard formats (iCal)

3. **Implementation Code Example**:

```javascript
class GoogleCalendarService {
  constructor() {
    this.clientId = process.env.GOOGLE_CLIENT_ID;
    this.clientSecret = process.env.GOOGLE_CLIENT_SECRET;
    this.redirectUri = process.env.GOOGLE_REDIRECT_URI;
  }

  /**
   * Get OAuth URL for user authentication
   */
  getAuthUrl() {
    const oauth2Client = new google.auth.OAuth2(
      this.clientId,
      this.clientSecret,
      this.redirectUri
    );

    const scopes = [
      "https://www.googleapis.com/auth/calendar",
      "https://www.googleapis.com/auth/calendar.events",
    ];

    return oauth2Client.generateAuthUrl({
      access_type: "offline",
      scope: scopes,
      prompt: "consent", // Force to get refresh token
    });
  }

  /**
   * Exchange authorization code for tokens
   */
  async getTokens(code) {
    const oauth2Client = new google.auth.OAuth2(
      this.clientId,
      this.clientSecret,
      this.redirectUri
    );

    const { tokens } = await oauth2Client.getToken(code);
    return tokens;
  }

  /**
   * Create authenticated client
   */
  getAuthenticatedClient(tokens) {
    const oauth2Client = new google.auth.OAuth2(
      this.clientId,
      this.clientSecret,
      this.redirectUri
    );

    oauth2Client.setCredentials(tokens);

    return google.calendar({
      version: "v3",
      auth: oauth2Client,
    });
  }

  /**
   * Add flight to calendar
   */
  async addFlightToCalendar(tokens, flightDetails) {
    const calendar = this.getAuthenticatedClient(tokens);

    const event = {
      summary: `Flight: ${flightDetails.airline} ${flightDetails.flightNumber}`,
      location: `${flightDetails.departureAirport} to ${flightDetails.arrivalAirport}`,
      description: `
        Confirmation: ${flightDetails.confirmationCode}
        Departure: ${flightDetails.departureAirport} Terminal ${
        flightDetails.departureTerminal
      }
        Arrival: ${flightDetails.arrivalAirport} Terminal ${
        flightDetails.arrivalTerminal
      }
        Seat: ${flightDetails.seat || "Not assigned"}
      `,
      start: {
        dateTime: flightDetails.departureTime,
        timeZone: flightDetails.departureTimezone,
      },
      end: {
        dateTime: flightDetails.arrivalTime,
        timeZone: flightDetails.arrivalTimezone,
      },
      reminders: {
        useDefault: false,
        overrides: [
          { method: "email", minutes: 24 * 60 }, // 1 day before
          { method: "popup", minutes: 3 * 60 }, // 3 hours before
        ],
      },
    };

    try {
      const response = await calendar.events.insert({
        calendarId: "primary",
        resource: event,
      });

      return response.data;
    } catch (error) {
      console.error("Error adding flight to calendar:", error);
      throw error;
    }
  }

  /**
   * Create travel itinerary
   */
  async createTravelItinerary(tokens, tripDetails) {
    const calendar = this.getAuthenticatedClient(tokens);
    const events = [];

    // Create events for each itinerary item
    for (const item of tripDetails.itinerary) {
      const event = {
        summary: item.title,
        location: item.location,
        description: item.description,
        start: {
          dateTime: item.startTime,
          timeZone: item.timezone,
        },
        end: {
          dateTime: item.endTime,
          timeZone: item.timezone,
        },
      };

      try {
        const response = await calendar.events.insert({
          calendarId: "primary",
          resource: event,
        });

        events.push(response.data);
      } catch (error) {
        console.error(`Error adding itinerary item "${item.title}":`, error);
      }
    }

    return events;
  }
}
```

4. **Authentication Flow**:
   - User authorizes the application once with their Google account
   - Store refresh token securely for future access
   - Implement token refresh logic to maintain access
   - Add clear authorization revocation process

### Personal Usage Considerations

Google Calendar API is highly suitable for personal usage:

- No cost for individual users
- 1,000,000 requests per day limit (far exceeds personal needs)
- OAuth 2.0 allows using personal Google account
- No commercial licensing needed for personal use

## Custom MCP Development Assessment

### FastMCP Evaluation

| Criterion              | Assessment                                          | Score (1-5) |
| ---------------------- | --------------------------------------------------- | ----------- |
| **Learning Curve**     | Moderate - requires JavaScript/TypeScript knowledge | 3           |
| **Documentation**      | Good, with examples                                 | 4           |
| **Maintenance Burden** | Low - simple wrappers can be stable                 | 4           |
| **Performance**        | Excellent for single-user scenarios                 | 5           |
| **Development Time**   | 1-2 days per MCP server                             | 4           |
| **Overall Value**      | High for custom needs                               | 4           |

### Recommendation: Selective FastMCP Implementation

We recommend a **selective approach to FastMCP development**, focusing on creating custom MCP servers only for specific high-value use cases rather than wrapping all external APIs. This balanced approach provides customization where needed while minimizing development and maintenance burden.

**Recommended Custom MCP implementations:**

1. **Weather MCP Server**:

   - Create a FastMCP wrapper for OpenWeatherMap
   - Add travel-specific weather interpretation
   - Implement intelligent caching for weather data

2. **Calendar MCP Server**:
   - Create a FastMCP wrapper for Google Calendar API
   - Add travel-specific event templates
   - Handle OAuth flow for personal accounts

**NOT recommended for custom MCP implementation:**

1. Browser Automation: Use native Browser-use MCP instead
2. Web Crawling: Use native Firecrawl MCP instead
3. Flight/Accommodation APIs: Use existing implementations

### FastMCP Implementation Strategy

1. **Development Approach**:

   - Create slim wrappers around external APIs
   - Focus on mapping API responses to standardized formats
   - Add travel-specific interpretation of data where valuable

2. **Deployment Strategy**:

   - Package MCP servers as independent modules
   - Implement automatic startup/shutdown to minimize resource usage
   - Add health checks and automatic restarts

3. **Sample FastMCP Server Implementation**:

```javascript
// weather-mcp-server.js
import { FastMCP } from "fastmcp";
import axios from "axios";

// Create MCP server
const mcp = new FastMCP();

// Weather service implementation
class WeatherService {
  constructor() {
    this.apiKey = process.env.OPENWEATHERMAP_API_KEY;
    this.baseUrl = "https://api.openweathermap.org/data/2.5";
    this.cache = new Map();
    this.cacheTTL = 30 * 60 * 1000; // 30 minutes
  }

  async getCurrentWeather(location) {
    const cacheKey = `current:${location}`;

    // Check cache
    if (this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey);
      if (Date.now() - cached.timestamp < this.cacheTTL) {
        return cached.data;
      }
    }

    // Make API request
    const url = `${this.baseUrl}/weather?q=${encodeURIComponent(
      location
    )}&units=metric&appid=${this.apiKey}`;
    const response = await axios.get(url);

    // Format and cache response
    const formattedData = this.formatWeatherData(response.data);
    this.cache.set(cacheKey, {
      timestamp: Date.now(),
      data: formattedData,
    });

    return formattedData;
  }

  formatWeatherData(data) {
    return {
      location: {
        name: data.name,
        country: data.sys.country,
      },
      current: {
        temperature: {
          celsius: data.main.temp,
          fahrenheit: (data.main.temp * 9) / 5 + 32,
        },
        feels_like: {
          celsius: data.main.feels_like,
          fahrenheit: (data.main.feels_like * 9) / 5 + 32,
        },
        humidity: data.main.humidity,
        wind: {
          speed: data.wind.speed,
          direction: this.getWindDirection(data.wind.deg),
        },
        condition: {
          main: data.weather[0].main,
          description: data.weather[0].description,
          icon: `https://openweathermap.org/img/wn/${data.weather[0].icon}@2x.png`,
        },
      },
      travel_advice: this.getTravelAdvice(data),
    };
  }

  getWindDirection(degrees) {
    const directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
    return directions[Math.round(degrees / 45) % 8];
  }

  getTravelAdvice(data) {
    // Generate travel-specific advice based on weather conditions
    const temp = data.main.temp;
    const condition = data.weather[0].main.toLowerCase();

    let advice = [];

    // Temperature-based advice
    if (temp < 0) {
      advice.push("Pack heavy winter clothing and insulated footwear");
    } else if (temp < 10) {
      advice.push("Pack warm layers and a good jacket");
    } else if (temp < 20) {
      advice.push("Pack light jacket and layers for varied temperatures");
    } else if (temp < 30) {
      advice.push("Pack light clothing with sun protection");
    } else {
      advice.push(
        "Pack very light clothing, sun protection, and stay hydrated"
      );
    }

    // Condition-based advice
    if (condition.includes("rain")) {
      advice.push("Pack waterproof clothing and umbrella");
    } else if (condition.includes("snow")) {
      advice.push("Pack waterproof boots and snow-appropriate gear");
    } else if (condition.includes("clear")) {
      advice.push("Bring sunglasses and sunscreen");
    }

    return advice;
  }
}

// Create service instance
const weatherService = new WeatherService();

// Register MCP tools
mcp.registerTool({
  name: "get_current_weather",
  description: "Get current weather for a location with travel advice",
  parameters: {
    location: {
      type: "string",
      description: "City name or location",
    },
  },
  execute: async ({ location }) => {
    try {
      return await weatherService.getCurrentWeather(location);
    } catch (error) {
      return { error: error.message };
    }
  },
});

// Start MCP server
const port = process.env.PORT || 3000;
mcp.serve({ port });
console.log(`Weather MCP server running on port ${port}`);
```

### Maintenance Considerations

For custom MCP servers, implement:

- Automated tests for each tool
- Version pinning for external dependencies
- Centralized logging and error reporting
- Graceful handling of API rate limits and outages

## Integration Architecture

The enhanced architecture integrates new components with the existing TripSage system while maintaining a modular approach that allows for personal deployment.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                       TripSage Enhanced Architecture                │
│                                                                     │
├─────────────┬─────────────────────────────────────────┬─────────────┤
│             │                                         │             │
│  CLIENT     │              API GATEWAY                │  AGENT      │
│  LAYER      │              LAYER                      │  LAYER      │
│             │                                         │             │
├─────────────┼─────────────────────────────────────────┼─────────────┤
│             │                                         │             │
│             │            SERVICE LAYER                │             │
│             │                                         │             │
├─────────────┼─────────────┬───────────┬───────────────┼─────────────┤
│             │             │           │               │             │
│  FLIGHTS    │  ACCOMMO-   │  MAPS &   │  SEARCH       │  WEATHER    │
│  SERVICE    │  DATIONS    │  LOCATION │  SERVICE      │  SERVICE    │
│  Duffel     │  OpenBnB    │  Google   │  Linkup/      │  OpenWeather│
│             │  Apify      │  Maps     │  OpenAI       │  Map        │
│             │             │           │               │             │
├─────────────┼─────────────┼───────────┼───────────────┼─────────────┤
│             │             │           │               │             │
│  BROWSER    │  WEB        │  CALENDAR │  CACHING      │  ERROR      │
│  AUTOMATION │  CRAWLING   │  SERVICE  │  LAYER        │  HANDLING   │
│  Browser-use│  Firecrawl  │  Google   │  Redis        │             │
│             │             │  Calendar │               │             │
│             │             │           │               │             │
├─────────────┴─────────────┴───────────┴───────────────┴─────────────┤
│                                                                     │
│                          MCP SERVER LAYER                           │
│                                                                     │
├─────────────┬─────────────┬───────────┬───────────────┬─────────────┤
│             │             │           │               │             │
│  DUFFEL     │  OPENBNB    │  BROWSER  │  FIRECRAWL   │  WEATHER    │
│  MCP        │  MCP        │  MCP      │  MCP         │  MCP        │
│             │             │           │               │  (Custom)   │
│             │             │           │               │             │
├─────────────┼─────────────┼───────────┼───────────────┼─────────────┤
│             │             │           │               │             │
│  CALENDAR   │  LINKUP     │  OPENAI   │  GOOGLE MAPS │  API        │
│  MCP        │  MCP        │  TOOLS    │  MCP         │  CLIENTS    │
│  (Custom)   │             │           │               │             │
│             │             │           │               │             │
└─────────────┴─────────────┴───────────┴───────────────┴─────────────┘
```

### Key Integration Points

1. **Centralized MCP Orchestration**:

   - Implement an MCP Orchestrator class to manage all MCP servers
   - Standardize error handling and response normalization
   - Add centralized logging and monitoring

2. **Service Discovery and Health Checks**:

   - Add service discovery for MCP servers
   - Implement health checks for all services
   - Enable automatic restart of failed MCP servers

3. **Data Flow Standardization**:
   - Standardize data models across all services
   - Implement consistent error response formats
   - Create unified logging pattern for debugging

### Integration Implementation Example

```javascript
// mcp-orchestrator.js
class MCPOrchestrator {
  constructor() {
    this.servers = {};
    this.serverConfig = {
      weather: {
        port: 3100,
        command: "node",
        args: ["weather-mcp-server.js"],
        healthEndpoint: "/health",
      },
      browser: {
        port: 3101,
        external: true, // Not managed by this orchestrator
        healthEndpoint: "/health",
      },
      firecrawl: {
        port: 3102,
        external: true,
        healthEndpoint: "/health",
      },
      calendar: {
        port: 3103,
        command: "node",
        args: ["calendar-mcp-server.js"],
        healthEndpoint: "/health",
      },
      // Add more server configs as needed
    };
  }

  async startAllServers() {
    for (const [name, config] of Object.entries(this.serverConfig)) {
      if (!config.external) {
        await this.startServer(name);
      }
    }
  }

  async startServer(name) {
    const config = this.serverConfig[name];
    if (!config) {
      throw new Error(`No configuration found for MCP server: ${name}`);
    }

    if (config.external) {
      console.log(`MCP server ${name} is externally managed`);
      return;
    }

    if (this.servers[name]) {
      console.log(`MCP server ${name} is already running`);
      return;
    }

    console.log(`Starting MCP server: ${name}`);

    // Start the server process
    const process = spawn(config.command, config.args, {
      env: { ...process.env, PORT: config.port },
      stdio: "pipe",
    });

    this.servers[name] = {
      process,
      port: config.port,
      status: "starting",
    };

    // Monitor the server
    process.stdout.on("data", (data) => {
      console.log(`[${name}] ${data.toString().trim()}`);
    });

    process.stderr.on("data", (data) => {
      console.error(`[${name}] ERROR: ${data.toString().trim()}`);
    });

    process.on("close", (code) => {
      console.log(`MCP server ${name} exited with code ${code}`);
      delete this.servers[name];

      // Auto-restart if unexpected exit
      if (code !== 0) {
        console.log(`Restarting MCP server ${name}...`);
        setTimeout(() => this.startServer(name), 5000);
      }
    });

    // Wait for server to start
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Check server health
    try {
      await this.checkServerHealth(name);
      this.servers[name].status = "running";
      console.log(`MCP server ${name} is running on port ${config.port}`);
    } catch (error) {
      console.error(`MCP server ${name} health check failed:`, error);
      this.servers[name].status = "unhealthy";
    }
  }

  async checkServerHealth(name) {
    const config = this.serverConfig[name];
    const url = `http://localhost:${config.port}${config.healthEndpoint}`;

    try {
      const response = await axios.get(url, { timeout: 5000 });
      return response.status === 200;
    } catch (error) {
      console.error(`Health check failed for ${name}:`, error.message);
      return false;
    }
  }

  async callTool(serverName, toolName, params) {
    const config = this.serverConfig[serverName];
    if (!config) {
      throw new Error(`Unknown MCP server: ${serverName}`);
    }

    // Ensure server is running if managed internally
    if (
      !config.external &&
      (!this.servers[serverName] ||
        this.servers[serverName].status !== "running")
    ) {
      await this.startServer(serverName);
    }

    const port = config.port;
    const url = `http://localhost:${port}/mcp/${toolName}`;

    try {
      const response = await axios.post(url, params, {
        headers: { "Content-Type": "application/json" },
        timeout: 30000,
      });

      return response.data;
    } catch (error) {
      console.error(
        `MCP tool call failed: ${serverName}.${toolName}`,
        error.message
      );
      throw new Error(`MCP tool call failed: ${error.message}`);
    }
  }

  shutdown() {
    for (const [name, server] of Object.entries(this.servers)) {
      if (server.process) {
        console.log(`Shutting down MCP server: ${name}`);
        server.process.kill();
      }
    }
  }
}

// Usage
const orchestrator = new MCPOrchestrator();
orchestrator.startAllServers();

// Handle process exit
process.on("SIGINT", () => {
  console.log("Shutting down all MCP servers...");
  orchestrator.shutdown();
  process.exit(0);
});
```

## Implementation Priorities

Based on the value provided and implementation complexity, we recommend the following phased approach:

### Phase 1: Weather Integration and Web Crawling (1-2 weeks)

1. **Weather Integration**:

   - Implement OpenWeatherMap service
   - Create custom Weather MCP server
   - Add weather data to destination information

2. **Web Crawling with Firecrawl**:
   - Set up Firecrawl integration
   - Implement travel advisory crawling
   - Add destination information enhancement

**Success metrics**:

- Weather information displayed for all destinations
- Current travel advisories available for major destinations
- Enhanced destination details from web crawling

### Phase 2: Browser Automation and Calendar Integration (2-3 weeks)

1. **Browser Automation with Browser-use**:

   - Implement flight status checking
   - Create flight check-in workflows
   - Add screenshot capabilities for verification

2. **Calendar Integration**:
   - Create Google Calendar OAuth flow
   - Implement flight-to-calendar functionality
   - Add travel itinerary creation

**Success metrics**:

- Successful automation of flight status checks
- Working flight check-in assistance
- Calendar events created for bookings
- Complete travel itineraries in calendar

### Phase 3: Custom MCP Development and Integration Refinement (1-2 weeks)

1. **Custom MCP Servers**:

   - Develop Weather MCP server
   - Develop Calendar MCP server
   - Create MCP orchestration layer

2. **Integration Refinement**:
   - Implement caching strategy
   - Add error handling and recovery
   - Create comprehensive logging

**Success metrics**:

- All MCP servers running stably
- Reduced API calls through caching
- Graceful error handling throughout the system

### Phase 4: Final Polish and Optimization (1 week)

1. **Performance Optimization**:

   - Optimize data flow between services
   - Implement request batching where possible
   - Add response compression

2. **Documentation and Deployment**:
   - Create comprehensive setup guide
   - Document API key requirements
   - Create example configurations

**Success metrics**:

- Response times under 1 second for most operations
- Complete documentation for personal deployment
- Simplified setup process for new users

## Personal API Key Management

To facilitate easy deployment by individual users with their own API keys, we recommend implementing a structured API key management system:

### Environment Configuration

Create a `.env.example` file with placeholders for all required API keys:

```plaintext
# Core APIs
DUFFEL_ACCESS_TOKEN=your_token_here
GOOGLE_MAPS_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Enhancement APIs
OPENWEATHERMAP_API_KEY=your_key_here
FIRECRAWL_API_KEY=your_key_here
BROWSER_USE_API_KEY=your_key_here

# OAuth Configuration
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback
```

### Documentation for Personal Setup

Include a detailed setup guide in the project README:

1. **API Key Acquisition Guide**:

   - Step-by-step instructions for obtaining each API key
   - Links to registration pages
   - Notes on free tier limitations

2. **Local Configuration**:

   - Instructions for copying `.env.example` to `.env`
   - Guidelines for setting redirect URIs for OAuth
   - Security recommendations for key storage

3. **Testing Configuration**:
   - Commands to verify all API keys are working
   - Troubleshooting tips for common issues
   - Fallback options for unavailable services

### API Key Security Guidelines

Include security best practices in the documentation:

1. **Never commit `.env` files** to repositories
2. **Set restrictive permissions** on `.env` files
3. **Use environment variables** rather than hardcoded keys
4. **Implement key rotation** procedures
5. **Set API key restrictions** where supported (IP, referrer, etc.)

By following these recommendations, TripSage will provide a robust, flexible travel planning experience enhanced with weather data, web crawling, browser automation, and calendar integration, all optimized for personal usage with individual API keys.
