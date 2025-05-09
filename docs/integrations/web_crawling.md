# Web Crawling Integration Guide

This guide provides comprehensive instructions for integrating web crawling capabilities into TripSage using Firecrawl. This integration enhances travel planning by providing access to current travel information, destination details, and travel advisories.

## Table of Contents

- [Selected Solution](#selected-solution)
- [Setup and Configuration](#setup-and-configuration)
- [Integration with TripSage](#integration-with-tripsage)
- [Implementation Guide](#implementation-guide)
- [Usage Patterns](#usage-patterns)
- [Testing and Verification](#testing-and-verification)
- [Cost Optimization](#cost-optimization)

## Selected Solution

After evaluating web crawling solutions, **Firecrawl** has been selected as the optimal solution for TripSage.

### Why Firecrawl?

1. **Native MCP Integration**:

   - Built-in Model Context Protocol support
   - Seamless integration with OpenAI agents
   - Consistent tool definition format

2. **Feature Completeness**:

   - Full web crawling capabilities
   - Targeted page scraping
   - Structured data extraction
   - Search functionality

3. **Developer Experience**:

   - Excellent documentation
   - Simple API structure
   - Robust error handling
   - Configurable crawl settings

4. **Cost Efficiency for Personal Use**:
   - Free tier available for limited usage
   - Pay-per-use pricing model
   - Fine-grained control over crawl depth and scope

### Compared to Alternatives

Firecrawl outperforms alternatives like Crawl4AI for TripSage's specific needs:

| Feature                      | Firecrawl                 | Crawl4AI                |
| ---------------------------- | ------------------------- | ----------------------- |
| **MCP Integration**          | Native                    | Requires custom wrapper |
| **Personal Usage Free Tier** | Limited credits           | Limited pages/month     |
| **Customization**            | High                      | Medium                  |
| **Travel-Specific Features** | Better content extraction | More limited            |
| **Documentation**            | Excellent                 | Good                    |
| **Ease of Implementation**   | Very high                 | Medium                  |

## Setup and Configuration

Follow these steps to set up Firecrawl for personal use with TripSage:

### 1. Create a Firecrawl Account

1. Visit [Firecrawl Sign Up](https://firecrawl.dev/signup)
2. Create a free account using your email
3. Verify your email address through the confirmation link

### 2. Generate API Key

1. Log in to your Firecrawl account
2. Navigate to the "API Keys" section in dashboard
3. Create a new API key with a descriptive name (e.g., "TripSage Personal")
4. Copy your API key for configuration

### 3. Configure TripSage

1. Create or edit the `.env` file in your TripSage project root
2. Add your Firecrawl API key:

```
FIRECRAWL_API_KEY=your_api_key_here
```

3. Save the file and restart your TripSage application

### 4. Test the Connection

Use the following code to verify your Firecrawl connection:

```javascript
const axios = require("axios");

async function testFirecrawlConnection() {
  try {
    const response = await axios.post(
      "https://api.firecrawl.dev/health",
      {},
      {
        headers: {
          Authorization: `Bearer ${process.env.FIRECRAWL_API_KEY}`,
          "Content-Type": "application/json",
        },
      }
    );

    console.log("Firecrawl connection successful:", response.data);
    return true;
  } catch (error) {
    console.error("Firecrawl connection failed:", error.message);
    return false;
  }
}

testFirecrawlConnection();
```

## Integration with TripSage

Web crawling enhances TripSage in several key areas:

### 1. Travel Advisories and Entry Requirements

Use Firecrawl to gather current information about:

- Government travel advisories for destinations
- Visa and entry requirements
- Health and safety information
- COVID-19 restrictions and requirements

### 2. Destination Research Enhancement

Enrich destination information with:

- Current local events and festivals
- Seasonal information
- Operating hours for attractions
- Recent traveler experiences and reviews

### 3. Price and Availability Verification

Validate pricing and availability information:

- Check for special offers directly from provider websites
- Verify operating hours and availability for attractions
- Monitor for price changes on travel services

### 4. Itinerary Enrichment

Enhance travel itineraries with:

- Detailed attraction information
- Local transportation options
- Restaurant menus and reviews
- Event schedules and ticket availability

## Implementation Guide

This section provides a detailed guide for implementing web crawling with Firecrawl.

### 1. Create Firecrawl Service

Create a file `src/services/crawling/firecrawl-service.js`:

```javascript
const mcpClient = require("../../utils/mcp-client");
const { cacheWithTTL } = require("../../utils/cache");

class FirecrawlService {
  /**
   * Crawl a specific travel advisory
   * @param {string} country Country code or name
   * @returns {Promise<Object>} Travel advisory data
   */
  async crawlTravelAdvisory(country) {
    // Create cache key
    const cacheKey = `crawl:advisory:${country.toLowerCase()}`;

    // Check cache first (longer TTL for advisories - 24 hours)
    const cachedData = await cacheWithTTL.get(cacheKey);
    if (cachedData) {
      return JSON.parse(cachedData);
    }

    try {
      // Government travel advisory URLs by country
      const advisoryUrls = {
        us: (country) =>
          `https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories/${country.toLowerCase()}-travel-advisory.html`,
        uk: (country) =>
          `https://www.gov.uk/foreign-travel-advice/${country.toLowerCase()}`,
        au: (country) =>
          `https://www.smartraveller.gov.au/destinations/${country.toLowerCase()}`,
        ca: (country) =>
          `https://travel.gc.ca/destinations/${country.toLowerCase()}`,
      };

      // Call Firecrawl MCP to crawl US travel advisory (default)
      const result = await mcpClient.call("firecrawl", "firecrawl_scrape", {
        url: advisoryUrls.us(country),
        formats: ["markdown"],
        onlyMainContent: true,
      });

      // Extract relevant advisory information
      const advisoryData = {
        country,
        source: "US Department of State",
        content: result.markdown,
        timestamp: new Date().toISOString(),
        url: advisoryUrls.us(country),
      };

      // Add additional data from other sources when available
      try {
        const ukAdvisory = await mcpClient.call(
          "firecrawl",
          "firecrawl_scrape",
          {
            url: advisoryUrls.uk(country),
            formats: ["markdown"],
            onlyMainContent: true,
          }
        );

        advisoryData.additional_sources = [
          {
            name: "UK Foreign Office",
            content: ukAdvisory.markdown,
            url: advisoryUrls.uk(country),
          },
        ];
      } catch (err) {
        // Non-critical error, just log and continue
        console.log(
          `Could not fetch UK advisory for ${country}: ${err.message}`
        );
      }

      // Parse advisory level
      advisoryData.advisory_level = this.parseAdvisoryLevel(result.markdown);

      // Extract key information
      advisoryData.key_info = this.extractKeyAdvisoryInfo(result.markdown);

      // Cache for 24 hours
      await cacheWithTTL.set(cacheKey, JSON.stringify(advisoryData), 86400);

      return advisoryData;
    } catch (error) {
      console.error(`Error crawling travel advisory for ${country}:`, error);
      throw new Error(`Failed to crawl travel advisory: ${error.message}`);
    }
  }

  /**
   * Search and crawl destination information
   * @param {string} destination Destination name
   * @returns {Promise<Object>} Destination information
   */
  async searchDestinationInfo(destination) {
    // Create cache key
    const cacheKey = `crawl:destination:${destination
      .toLowerCase()
      .replace(/\s+/g, "_")}`;

    // Check cache first (6 hours TTL)
    const cachedData = await cacheWithTTL.get(cacheKey);
    if (cachedData) {
      return JSON.parse(cachedData);
    }

    try {
      // Search for destination information
      const searchResults = await mcpClient.call(
        "firecrawl",
        "firecrawl_search",
        {
          query: `${destination} travel guide`,
          limit: 5,
          scrapeOptions: {
            formats: ["markdown"],
            onlyMainContent: true,
          },
        }
      );

      // Process search results
      const processedResults = [];

      for (const result of searchResults) {
        // Only process results that have been scraped
        if (result.content && result.content.markdown) {
          processedResults.push({
            title: result.title,
            url: result.url,
            content: result.content.markdown,
            source: new URL(result.url).hostname,
          });
        }
      }

      // Extract structured information if possible
      let structuredInfo = {};

      try {
        // Try to extract structured destination information
        const extractResult = await mcpClient.call(
          "firecrawl",
          "firecrawl_extract",
          {
            urls: [searchResults[0].url],
            schema: {
              destination: "string",
              bestTimeToVisit: "string",
              topAttractions: "array",
              localCuisine: "array",
              transportOptions: "array",
              safetyTips: "array",
            },
            prompt: `Extract key travel information about ${destination}`,
          }
        );

        if (extractResult && extractResult.length > 0) {
          structuredInfo = extractResult[0];
        }
      } catch (extractError) {
        console.log(
          `Structured data extraction failed for ${destination}: ${extractError.message}`
        );
        // Non-critical error, continue without structured data
      }

      // Combine results
      const destinationInfo = {
        destination,
        timestamp: new Date().toISOString(),
        sources: processedResults,
        structured_info: structuredInfo,
      };

      // Cache for 6 hours
      await cacheWithTTL.set(cacheKey, JSON.stringify(destinationInfo), 21600);

      return destinationInfo;
    } catch (error) {
      console.error(
        `Error searching destination info for ${destination}:`,
        error
      );
      throw new Error(`Failed to search destination info: ${error.message}`);
    }
  }

  /**
   * Crawl for attraction details
   * @param {string} attraction Attraction name
   * @param {string} location Location of the attraction
   * @returns {Promise<Object>} Attraction details
   */
  async getAttractionDetails(attraction, location) {
    // Create cache key
    const cacheKey = `crawl:attraction:${attraction
      .toLowerCase()
      .replace(/\s+/g, "_")}:${location.toLowerCase().replace(/\s+/g, "_")}`;

    // Check cache first (12 hours TTL)
    const cachedData = await cacheWithTTL.get(cacheKey);
    if (cachedData) {
      return JSON.parse(cachedData);
    }

    try {
      // Search for specific attraction
      const searchResults = await mcpClient.call(
        "firecrawl",
        "firecrawl_search",
        {
          query: `${attraction} ${location} hours tickets information`,
          limit: 3,
          scrapeOptions: {
            formats: ["markdown"],
            onlyMainContent: true,
          },
        }
      );

      // Extract structured attraction information
      const extractResult = await mcpClient.call(
        "firecrawl",
        "firecrawl_extract",
        {
          urls: searchResults.map((r) => r.url),
          schema: {
            attractionName: "string",
            description: "string",
            openingHours: "object",
            ticketPrices: "object",
            address: "string",
            contactInfo: "object",
            visitDuration: "string",
            bestTimeToVisit: "string",
            tips: "array",
          },
          prompt: `Extract detailed visitor information about "${attraction}" in ${location}`,
        }
      );

      // Process and merge results
      let attractionInfo = {};

      if (extractResult && extractResult.length > 0) {
        // Merge all extracted data
        attractionInfo = extractResult.reduce((merged, current) => {
          Object.entries(current).forEach(([key, value]) => {
            // If the merged result doesn't have this property yet, add it
            if (!merged[key] && value) {
              merged[key] = value;
            }
            // If the property exists but the new value is more complete, use it
            else if (
              (merged[key] &&
                value &&
                typeof value === "string" &&
                value.length > merged[key].length) ||
              (Array.isArray(value) && value.length > merged[key].length)
            ) {
              merged[key] = value;
            }
          });
          return merged;
        }, {});
      }

      // Add raw content
      attractionInfo.sources = searchResults.map((r) => ({
        title: r.title,
        url: r.url,
        snippet:
          r.content?.markdown?.substring(0, 300) + "..." || r.snippet || "",
      }));

      attractionInfo.location = location;
      attractionInfo.timestamp = new Date().toISOString();

      // Cache for 12 hours
      await cacheWithTTL.set(cacheKey, JSON.stringify(attractionInfo), 43200);

      return attractionInfo;
    } catch (error) {
      console.error(
        `Error getting attraction details for ${attraction} in ${location}:`,
        error
      );
      throw new Error(`Failed to get attraction details: ${error.message}`);
    }
  }

  /**
   * Deep research on a travel topic
   * @param {string} topic Travel topic to research
   * @returns {Promise<Object>} Research results
   */
  async conductTravelResearch(topic) {
    // Create cache key
    const cacheKey = `crawl:research:${topic
      .toLowerCase()
      .replace(/\s+/g, "_")}`;

    // Check cache first (3 days TTL for research topics)
    const cachedData = await cacheWithTTL.get(cacheKey);
    if (cachedData) {
      return JSON.parse(cachedData);
    }

    try {
      // Use deep research for comprehensive analysis
      const researchResult = await mcpClient.call(
        "firecrawl",
        "firecrawl_deep_research",
        {
          query: topic,
          maxUrls: 15, // Limit to 15 URLs to control costs
          maxDepth: 3, // Moderate depth of analysis
          timeLimit: 60, // 60 second time limit
        }
      );

      // Process research result
      const researchData = {
        topic,
        timestamp: new Date().toISOString(),
        summary: researchResult.summary,
        key_points: researchResult.keyPoints || [],
        sources: researchResult.sources || [],
      };

      // Cache for 3 days (research topics change slowly)
      await cacheWithTTL.set(cacheKey, JSON.stringify(researchData), 259200);

      return researchData;
    } catch (error) {
      console.error(`Error conducting travel research on ${topic}:`, error);
      throw new Error(`Failed to conduct travel research: ${error.message}`);
    }
  }

  /**
   * Parse advisory level from advisory text
   * @private
   */
  parseAdvisoryLevel(advisoryText) {
    // Implementation depends on the format of the advisory
    // This is a simplified example for US advisories
    if (advisoryText.includes("Level 4: Do Not Travel")) {
      return {
        level: 4,
        description: "Do Not Travel",
      };
    } else if (advisoryText.includes("Level 3: Reconsider Travel")) {
      return {
        level: 3,
        description: "Reconsider Travel",
      };
    } else if (advisoryText.includes("Level 2: Exercise Increased Caution")) {
      return {
        level: 2,
        description: "Exercise Increased Caution",
      };
    } else if (advisoryText.includes("Level 1: Exercise Normal Precautions")) {
      return {
        level: 1,
        description: "Exercise Normal Precautions",
      };
    } else {
      return {
        level: null,
        description: "Advisory level not found",
      };
    }
  }

  /**
   * Extract key information from advisory text
   * @private
   */
  extractKeyAdvisoryInfo(advisoryText) {
    // This is a simplified example
    const keyInfo = {
      safety: [],
      health: [],
      entry_requirements: [],
    };

    // Extract safety information
    if (advisoryText.includes("Crime:")) {
      const crimeMatch = advisoryText.match(/Crime:([^.\n]+)/);
      if (crimeMatch && crimeMatch[1]) {
        keyInfo.safety.push("Crime: " + crimeMatch[1].trim());
      }
    }

    if (advisoryText.includes("Terrorism:")) {
      const terrorismMatch = advisoryText.match(/Terrorism:([^.\n]+)/);
      if (terrorismMatch && terrorismMatch[1]) {
        keyInfo.safety.push("Terrorism: " + terrorismMatch[1].trim());
      }
    }

    // Extract health information
    if (advisoryText.includes("Health:")) {
      const healthMatch = advisoryText.match(/Health:([^.\n]+)/);
      if (healthMatch && healthMatch[1]) {
        keyInfo.health.push("Health: " + healthMatch[1].trim());
      }
    }

    // Extract entry requirements
    if (
      advisoryText.includes("Entry requirements:") ||
      advisoryText.includes("Visa requirements:")
    ) {
      const entryMatch = advisoryText.match(
        /(?:Entry|Visa) requirements:([^.\n]+)/
      );
      if (entryMatch && entryMatch[1]) {
        keyInfo.entry_requirements.push(entryMatch[1].trim());
      }
    }

    return keyInfo;
  }
}

module.exports = new FirecrawlService();
```

### 2. Create API Endpoints

Create a file `src/api/routes/crawling.js`:

```javascript
const express = require("express");
const router = express.Router();
const firecrawlService = require("../../services/crawling/firecrawl-service");
const { asyncHandler } = require("../../utils/error");

/**
 * @route   GET /api/crawl/advisory/:country
 * @desc    Get travel advisory for a country
 * @access  Public
 */
router.get(
  "/advisory/:country",
  asyncHandler(async (req, res) => {
    const country = req.params.country;
    const advisory = await firecrawlService.crawlTravelAdvisory(country);
    res.json(advisory);
  })
);

/**
 * @route   GET /api/crawl/destination/:name
 * @desc    Get information about a destination
 * @access  Public
 */
router.get(
  "/destination/:name",
  asyncHandler(async (req, res) => {
    const destination = req.params.name;
    const info = await firecrawlService.searchDestinationInfo(destination);
    res.json(info);
  })
);

/**
 * @route   GET /api/crawl/attraction
 * @desc    Get details about a specific attraction
 * @access  Public
 */
router.get(
  "/attraction",
  asyncHandler(async (req, res) => {
    const { name, location } = req.query;

    if (!name || !location) {
      return res.status(400).json({
        error: "Missing required parameters: name, location",
      });
    }

    const details = await firecrawlService.getAttractionDetails(name, location);
    res.json(details);
  })
);

/**
 * @route   POST /api/crawl/research
 * @desc    Conduct deep research on a travel topic
 * @access  Public
 */
router.post(
  "/research",
  asyncHandler(async (req, res) => {
    const { topic } = req.body;

    if (!topic) {
      return res
        .status(400)
        .json({ error: "Missing required parameter: topic" });
    }

    const research = await firecrawlService.conductTravelResearch(topic);
    res.json(research);
  })
);

module.exports = router;
```

### 3. Add to API Gateway

Update `src/api/index.js` to include the crawling routes:

```javascript
// Add this line with the other route imports
const crawlingRoutes = require("./routes/crawling");

// Add this line with the other app.use statements
app.use("/api/crawl", crawlingRoutes);
```

### 4. Agent Prompt Enhancement

Update the travel agent prompt in `prompts/agent_development_prompt.md` to include web crawling capabilities:

```
You are TripSage, an AI travel assistant specializing in comprehensive trip planning.

CAPABILITIES:
- Search and book flights using Duffel API
- Find accommodations through OpenBnB (Airbnb data) and Apify (Booking.com)
- Locate attractions and restaurants via Google Maps Platform
- Access real-time travel information through web search
- Get current weather data and forecasts for destinations
- Retrieve up-to-date travel advisories and destination information through web crawling

INTERACTION GUIDELINES:
1. Always gather key trip parameters first (dates, destination, budget, preferences)
2. Use appropriate API calls based on the user's query stage:
   - Initial planning: Use lightweight search APIs first
   - Specific requests: Use specialized booking APIs
3. Present options clearly with price, ratings, and key features
4. Maintain state between interactions to avoid repeating information
5. Offer recommendations based on user preferences and constraints

WEB CRAWLING INTEGRATION:
- Check current travel advisories when users ask about specific destinations
- Retrieve up-to-date destination information for richer recommendations
- Get current attraction details (hours, prices, special events)
- Conduct deep research on specialized travel topics when needed

When calling web crawling tools:
- For travel advisories: Include country code or name for accurate results
- For destination information: Use specific destination names
- For attraction details: Include both attraction name and location
- For deep research: Formulate specific topics for more targeted results

Remember to use web crawling selectively and efficiently to control costs.

IMPORTANT: Handle API errors gracefully. If data is unavailable, explain why and suggest alternatives.
```

## Usage Patterns

To maximize the value of web crawling while controlling costs, follow these usage patterns:

### 1. Selective Crawling

Only crawl when necessary, prioritizing:

- High-value information (travel advisories, entry requirements)
- Time-sensitive data (operating hours, current events)
- User-requested details (specific attraction information)

### 2. Comprehensive Caching

Implement aggressive caching based on data volatility:

- Travel advisories: 24-hour cache
- Destination information: 6-hour cache
- Attraction details: 12-hour cache
- Research topics: 3-day cache

### 3. Prioritized Information Sources

Focus crawling on authoritative sources:

- Government websites for travel advisories
- Official tourism websites for destination information
- Attraction official websites for details
- Reputable travel publications for general information

### 4. Depth Control

Adjust crawl depth based on information needs:

- Level 1: Basic advisory information
- Level 2: Standard destination information
- Level 3: Comprehensive research (use sparingly)

## Testing and Verification

### Unit Tests

Create a file `src/tests/firecrawl-service.test.js`:

```javascript
const firecrawlService = require("../services/crawling/firecrawl-service");

async function testFirecrawlService() {
  try {
    console.log("Testing travel advisory crawling...");
    const advisory = await firecrawlService.crawlTravelAdvisory("france");
    console.log("Travel advisory:", JSON.stringify(advisory, null, 2));
    console.log("Test passed: Travel advisory retrieved");

    console.log("\nTesting destination information search...");
    const destinationInfo = await firecrawlService.searchDestinationInfo(
      "Kyoto"
    );
    console.log("Destination info:", JSON.stringify(destinationInfo, null, 2));
    console.log("Test passed: Destination information retrieved");

    console.log("\nTesting attraction details...");
    const attractionDetails = await firecrawlService.getAttractionDetails(
      "Eiffel Tower",
      "Paris"
    );
    console.log(
      "Attraction details:",
      JSON.stringify(attractionDetails, null, 2)
    );
    console.log("Test passed: Attraction details retrieved");

    console.log("\nTesting travel research...");
    const research = await firecrawlService.conductTravelResearch(
      "Best time to visit Bali"
    );
    console.log("Research results:", JSON.stringify(research, null, 2));
    console.log("Test passed: Travel research conducted");

    return true;
  } catch (error) {
    console.error("Test failed:", error);
    return false;
  }
}

// Run test
testFirecrawlService().then((success) => {
  if (success) {
    console.log("\nAll Firecrawl service tests passed!");
  } else {
    console.error("\nFirecrawl service tests failed");
    process.exit(1);
  }
});
```

### Integration Testing

Test the following scenarios:

1. **Travel Advisory Retrieval**:

   - Test with valid country codes and names
   - Verify proper parsing of advisory levels
   - Check extraction of key information
   - Test error handling with invalid countries

2. **Destination Information**:

   - Test with popular and lesser-known destinations
   - Verify structured information extraction
   - Check source attribution
   - Test information quality and relevance

3. **Attraction Details**:

   - Test with specific attractions in various cities
   - Verify extraction of hours, prices, and recommendations
   - Check for accurate contact information
   - Test handling of non-existent attractions

4. **Research Capabilities**:
   - Test with specific travel research questions
   - Verify depth and quality of research
   - Check source attribution
   - Test with complex multi-faceted topics

## Cost Optimization

To minimize costs when using Firecrawl in a personal deployment, implement these strategies:

### 1. Request Throttling

Create a request throttling mechanism in `src/utils/throttling.js`:

```javascript
class RequestThrottler {
  constructor(options = {}) {
    this.dailyLimit = options.dailyLimit || 100;
    this.requestCounts = {};
    this.resetTime = options.resetTime || "00:00:00"; // UTC time to reset counters

    // Set up daily reset
    this.setupDailyReset();
  }

  setupDailyReset() {
    // Calculate time until next reset
    const now = new Date();
    const resetParts = this.resetTime.split(":").map(Number);
    const nextReset = new Date(now);
    nextReset.setUTCHours(resetParts[0], resetParts[1], resetParts[2], 0);

    if (nextReset <= now) {
      // If reset time has already passed today, schedule for tomorrow
      nextReset.setUTCDate(nextReset.getUTCDate() + 1);
    }

    const timeUntilReset = nextReset - now;

    // Schedule reset
    setTimeout(() => {
      this.resetCounts();
      this.setupDailyReset(); // Set up next day's reset
    }, timeUntilReset);
  }

  resetCounts() {
    this.requestCounts = {};
    console.log("Request counts reset at", new Date().toISOString());
  }

  async throttle(serviceName, callback) {
    // Initialize count if not exists
    if (!this.requestCounts[serviceName]) {
      this.requestCounts[serviceName] = 0;
    }

    // Check if over limit
    if (this.requestCounts[serviceName] >= this.dailyLimit) {
      throw new Error(
        `Daily limit of ${this.dailyLimit} requests exceeded for ${serviceName}`
      );
    }

    // Increment counter
    this.requestCounts[serviceName]++;

    // Log usage
    console.log(
      `${serviceName} request: ${this.requestCounts[serviceName]}/${this.dailyLimit}`
    );

    // Execute callback
    return callback();
  }
}

// Create throttler instance
const throttler = new RequestThrottler({
  dailyLimit: process.env.FIRECRAWL_DAILY_LIMIT || 100,
});

module.exports = throttler;
```

### 2. Implement Usage in Service

Update the Firecrawl service to use throttling:

```javascript
// Add this import to firecrawl-service.js
const throttler = require('../../utils/throttling');

// Then modify each method to use throttling
async crawlTravelAdvisory(country) {
  // Check cache first...

  // Use throttling
  return throttler.throttle('firecrawl', async () => {
    // Original implementation goes here
  });
}
```

### 3. Usage Dashboard

Create a simple dashboard to monitor Firecrawl usage:

```javascript
// src/api/routes/admin.js
router.get(
  "/crawl-usage",
  asyncHandler(async (req, res) => {
    res.json({
      daily_limits: {
        firecrawl: process.env.FIRECRAWL_DAILY_LIMIT || 100,
      },
      current_usage: req.app.get("throttler").requestCounts,
      reset_time: req.app.get("throttler").resetTime,
      recommendation: getUsageRecommendation(
        req.app.get("throttler").requestCounts
      ),
    });
  })
);

function getUsageRecommendation(requestCounts) {
  const firecrawlCount = requestCounts.firecrawl || 0;
  const limit = process.env.FIRECRAWL_DAILY_LIMIT || 100;
  const usagePercentage = (firecrawlCount / limit) * 100;

  if (usagePercentage > 90) {
    return "Critical: Usage nearing limit. Disable non-essential crawling.";
  } else if (usagePercentage > 75) {
    return "Warning: High usage. Consider increasing cache TTLs.";
  } else if (usagePercentage > 50) {
    return "Moderate usage. Monitor for sharp increases.";
  } else {
    return "Low usage. Current settings are appropriate.";
  }
}
```

### 4. Automated Cost Control

Implement automatic throttling adjustment based on usage patterns:

```javascript
// Add to throttler.js
adjustThrottling() {
  // Get current hour
  const currentHour = new Date().getUTCHours();

  // Calculate usage percentage
  const firecrawlCount = this.requestCounts.firecrawl || 0;
  const limit = this.dailyLimit;
  const usagePercentage = (firecrawlCount / limit) * 100;

  // Adjust based on time of day and usage
  if (currentHour < 12) {
    // Morning hours - keep standard limit
    return;
  } else if (currentHour < 18) {
    // Afternoon - adjust if usage is high
    if (usagePercentage > 60) {
      // Temporarily reduce limits
      console.log('Reducing firecrawl priority due to high usage');
      return 'medium';
    }
  } else {
    // Evening - be more conservative
    if (usagePercentage > 80) {
      console.log('Restricting firecrawl to essential requests only');
      return 'low';
    } else if (usagePercentage > 50) {
      console.log('Reducing firecrawl priority due to day-end approaching');
      return 'medium';
    }
  }

  return 'high';
}
```

By following this implementation guide, you'll have a fully functional web crawling integration for TripSage that enhances the travel planning experience with up-to-date information while carefully managing usage costs for personal deployment.
