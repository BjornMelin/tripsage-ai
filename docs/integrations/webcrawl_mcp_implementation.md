# Web Crawling MCP Server Implementation

This document provides the detailed implementation specification for the Web Crawling MCP Server in TripSage.

## Overview

The Web Crawling MCP Server provides destination research capabilities, content extraction, and price monitoring for TripSage. It serves as a controlled interface to web content, enabling agents to gather rich travel information while respecting website terms of service and implementing best practices for web crawling.

## MCP Tools Exposed

```typescript
// MCP Tool Definitions
{
  "name": "mcp__webcrawl__extract_page_content",
  "parameters": {
    "url": {"type": "string", "description": "URL of the webpage to extract content from"},
    "selectors": {"type": "array", "items": {"type": "string"}, "description": "Optional CSS selectors to target specific content (e.g., 'div.main-content')"},
    "include_images": {"type": "boolean", "default": false, "description": "Whether to include image URLs in the extracted content"},
    "format": {"type": "string", "enum": ["markdown", "text", "html"], "default": "markdown", "description": "Format of the extracted content"}
  },
  "required": ["url"]
},
{
  "name": "mcp__webcrawl__search_destination_info",
  "parameters": {
    "destination": {"type": "string", "description": "Destination name (e.g., 'Paris, France')"},
    "topics": {"type": "array", "items": {"type": "string"}, "description": "Specific topics to search for (e.g., ['attractions', 'local cuisine', 'transportation'])"},
    "max_results": {"type": "integer", "default": 5, "description": "Maximum number of results to return per topic"}
  },
  "required": ["destination"]
},
{
  "name": "mcp__webcrawl__monitor_price_changes",
  "parameters": {
    "url": {"type": "string", "description": "URL of the webpage to monitor"},
    "price_selector": {"type": "string", "description": "CSS selector for the price element"},
    "frequency": {"type": "string", "enum": ["hourly", "daily", "weekly"], "default": "daily", "description": "How often to check for price changes"},
    "notification_threshold": {"type": "number", "default": 5, "description": "Percentage change to trigger a notification"}
  },
  "required": ["url", "price_selector"]
},
{
  "name": "mcp__webcrawl__get_latest_events",
  "parameters": {
    "destination": {"type": "string", "description": "Destination name (e.g., 'Paris, France')"},
    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
    "categories": {"type": "array", "items": {"type": "string"}, "description": "Event categories (e.g., ['music', 'festivals', 'sports'])"}
  },
  "required": ["destination", "start_date", "end_date"]
},
{
  "name": "mcp__webcrawl__crawl_travel_blog",
  "parameters": {
    "destination": {"type": "string", "description": "Destination name (e.g., 'Paris, France')"},
    "topics": {"type": "array", "items": {"type": "string"}, "description": "Specific topics to extract (e.g., ['hidden gems', 'local tips', 'safety'])"},
    "max_blogs": {"type": "integer", "default": 3, "description": "Maximum number of blogs to crawl"},
    "recent_only": {"type": "boolean", "default": true, "description": "Whether to only include blogs from the past year"}
  },
  "required": ["destination"]
}
```

## API Integrations

### Primary: Firecrawl API (existing MCP)

- **Key Endpoints**:

  - `firecrawl_scrape` - For single page extraction
  - `firecrawl_search` - For targeted information search
  - `firecrawl_map` - For discovering related content
  - `firecrawl_extract` - For structured data extraction
  - `firecrawl_deep_research` - For comprehensive topic research

- **Authentication**:
  - Uses existing MCP authentication

### Secondary: Playwright (existing MCP)

- **Key Functions**:

  - `playwright_navigate` - Browser navigation
  - `playwright_fill` - Form filling
  - `playwright_click` - Interaction
  - `playwright_screenshot` - Visual capture
  - `playwright_get_visible_text` - Content extraction

- **Authentication**:
  - Uses existing MCP authentication

### Tertiary: Puppeteer API

- **Key Functions**:

  - Page navigation
  - DOM manipulation
  - Content extraction
  - Interaction simulation

- **Authentication**:
  - Custom API key for direct Puppeteer service

## Connection Points to Existing Architecture

### Agent Integration

- **Travel Agent**:

  - Destination research during trip planning
  - Local insights and recommendations
  - Travel blog information extraction

- **Budget Agent**:

  - Price tracking and comparison
  - Historical price trend analysis
  - Deal finding for flights and accommodations

- **Itinerary Agent**:
  - Local event discovery
  - Attraction details and recommendations
  - Activity planning based on blog insights

## File Structure

```plaintext
src/
  mcp/
    webcrawl/
      __init__.py                  # Package initialization
      server.py                    # MCP server implementation
      config.py                    # Server configuration settings
      handlers/
        __init__.py                # Module initialization
        extract_handler.py         # Page content extraction
        search_handler.py          # Destination search
        monitor_handler.py         # Price monitoring
        events_handler.py          # Event discovery
        blog_handler.py            # Travel blog crawling
      extractors/
        __init__.py                # Module initialization
        content_extractor.py       # General content extraction
        price_extractor.py         # Price extraction
        event_extractor.py         # Event extraction
        blog_extractor.py          # Blog content extraction
      sources/
        __init__.py                # Module initialization
        firecrawl_source.py        # Firecrawl API integration
        playwright_source.py       # Playwright integration
        puppeteer_source.py        # Puppeteer API integration
        source_interface.py        # Common interface for all sources
      processors/
        __init__.py                # Module initialization
        markdown_processor.py      # Markdown conversion
        content_cleaner.py         # Content cleaning and formatting
        sentiment_analyzer.py      # Text sentiment analysis
        entity_extractor.py        # Named entity extraction
      storage/
        __init__.py                # Module initialization
        cache.py                   # Response caching implementation
        supabase.py                # Supabase database integration
        memory.py                  # Knowledge graph integration
      utils/
        __init__.py                # Module initialization
        url_validator.py           # URL validation and normalization
        rate_limiter.py            # Rate limiting implementation
        response_formatter.py      # Response formatting utilities
        html_parser.py             # HTML parsing utilities
        logging.py                 # Logging configuration
```

## Key Functions and Interfaces

### Source Interface

```typescript
// source_interface.ts
interface CrawlSource {
  extractPageContent(
    url: string,
    options: ExtractionOptions
  ): Promise<ExtractedContent>;
  searchDestinationInfo(
    destination: string,
    topics: string[],
    maxResults: number
  ): Promise<DestinationInfo>;
  monitorPriceChanges(
    url: string,
    selector: string,
    options: MonitorOptions
  ): Promise<PriceMonitorResult>;
  getLatestEvents(
    destination: string,
    startDate: string,
    endDate: string,
    categories: string[]
  ): Promise<EventList>;
  crawlTravelBlog(
    destination: string,
    topics: string[],
    maxBlogs: number,
    recentOnly: boolean
  ): Promise<BlogInsights>;
}

interface ExtractionOptions {
  selectors?: string[];
  includeImages?: boolean;
  format?: "markdown" | "text" | "html";
  timeout?: number;
  wait?: number;
}

interface ExtractedContent {
  url: string;
  title: string;
  content: string;
  images?: string[];
  metadata?: {
    author?: string;
    publishDate?: string;
    lastModified?: string;
    siteName?: string;
  };
  format: string;
}

interface DestinationInfo {
  destination: string;
  topics: {
    [topic: string]: TopicResult[];
  };
  sources: string[];
}

interface TopicResult {
  title: string;
  content: string;
  source: string;
  url: string;
  confidence: number;
}

interface MonitorOptions {
  frequency: "hourly" | "daily" | "weekly";
  notificationThreshold: number;
  startDate?: string;
  endDate?: string;
}

interface PriceMonitorResult {
  url: string;
  initial_price?: {
    amount: number;
    currency: string;
    timestamp: string;
  };
  current_price?: {
    amount: number;
    currency: string;
    timestamp: string;
  };
  monitoring_id: string;
  status: "scheduled" | "monitoring" | "completed" | "error";
  history?: PriceEntry[];
  next_check?: string;
}

interface PriceEntry {
  timestamp: string;
  amount: number;
  currency: string;
  change_percent?: number;
}

interface EventList {
  destination: string;
  date_range: {
    start_date: string;
    end_date: string;
  };
  events: Event[];
  sources: string[];
}

interface Event {
  name: string;
  description: string;
  category: string;
  date: string;
  time?: string;
  venue?: string;
  address?: string;
  url?: string;
  price_range?: string;
  image_url?: string;
  source: string;
}

interface BlogInsights {
  destination: string;
  topics: {
    [topic: string]: BlogTopic[];
  };
  sources: BlogSource[];
  extraction_date: string;
}

interface BlogTopic {
  title: string;
  summary: string;
  key_points: string[];
  sentiment: "positive" | "neutral" | "negative";
  source_index: number;
}

interface BlogSource {
  url: string;
  title: string;
  author?: string;
  publish_date?: string;
  reputation_score?: number;
}
```

### Firecrawl Source Implementation

```typescript
// firecrawl_source.ts
import {
  CrawlSource,
  ExtractionOptions,
  ExtractedContent,
  DestinationInfo,
  MonitorOptions,
  PriceMonitorResult,
  EventList,
  BlogInsights,
} from "./source_interface";
import { logError, logInfo } from "../utils/logging";
import { validateUrl } from "../utils/url_validator";
import { formatResponse } from "../utils/response_formatter";

export class FirecrawlSource implements CrawlSource {
  async extractPageContent(
    url: string,
    options: ExtractionOptions
  ): Promise<ExtractedContent> {
    try {
      // Validate URL
      validateUrl(url);

      // Prepare Firecrawl options
      const scrapeOptions = {
        url: url,
        formats: [options.format === "html" ? "html" : "markdown"],
        onlyMainContent: true,
        waitFor: options.wait || 0,
      };

      if (options.selectors && options.selectors.length > 0) {
        scrapeOptions["includeTags"] = options.selectors;
      }

      // Call Firecrawl MCP
      const result = await callMCP(
        "mcp__firecrawl__firecrawl_scrape",
        scrapeOptions
      );

      // Process result
      const content = options.format === "html" ? result.html : result.markdown;

      // Extract title and metadata
      const title = extractTitle(content);
      const metadata = extractMetadata(content, result);

      // Extract images if requested
      const images = options.includeImages ? extractImages(content) : undefined;

      return {
        url: url,
        title: title,
        content: content,
        images: images,
        metadata: metadata,
        format: options.format || "markdown",
      };
    } catch (error) {
      logError(`Error extracting content from ${url}: ${error.message}`);
      throw new Error(`Failed to extract page content: ${error.message}`);
    }
  }

  async searchDestinationInfo(
    destination: string,
    topics: string[] = [],
    maxResults: number = 5
  ): Promise<DestinationInfo> {
    try {
      // Prepare topics if not provided
      const searchTopics =
        topics.length > 0
          ? topics
          : [
              "attractions",
              "things to do",
              "best time to visit",
              "local cuisine",
              "transportation",
            ];

      // Initialize result structure
      const result: DestinationInfo = {
        destination: destination,
        topics: {},
        sources: [],
      };

      // Search for each topic
      for (const topic of searchTopics) {
        const query = `${destination} ${topic}`;

        // Call Firecrawl search with scrape options
        const searchResult = await callMCP("mcp__firecrawl__firecrawl_search", {
          query: query,
          limit: maxResults,
          scrapeOptions: {
            formats: ["markdown"],
            onlyMainContent: true,
          },
        });

        // Process search results
        result.topics[topic] = [];

        for (const item of searchResult.results) {
          // Extract relevant information
          const topicResult = {
            title: item.title,
            content: item.content,
            source: item.source || extractDomain(item.url),
            url: item.url,
            confidence: calculateConfidence(item, query),
          };

          result.topics[topic].push(topicResult);

          // Add source to sources list if not already there
          if (!result.sources.includes(topicResult.source)) {
            result.sources.push(topicResult.source);
          }
        }
      }

      return result;
    } catch (error) {
      logError(
        `Error searching destination info for ${destination}: ${error.message}`
      );
      throw new Error(
        `Failed to search destination information: ${error.message}`
      );
    }
  }

  async monitorPriceChanges(
    url: string,
    selector: string,
    options: MonitorOptions
  ): Promise<PriceMonitorResult> {
    try {
      // Validate URL
      validateUrl(url);

      // First, extract current price
      const currentPrice = await this.extractPrice(url, selector);

      // Create monitoring record in database
      const monitoringId = await createPriceMonitor(
        url,
        selector,
        currentPrice,
        options
      );

      // Schedule monitoring job
      await schedulePriceMonitoring(monitoringId, options.frequency);

      return {
        url: url,
        initial_price: currentPrice
          ? {
              amount: currentPrice.amount,
              currency: currentPrice.currency,
              timestamp: new Date().toISOString(),
            }
          : undefined,
        current_price: currentPrice
          ? {
              amount: currentPrice.amount,
              currency: currentPrice.currency,
              timestamp: new Date().toISOString(),
            }
          : undefined,
        monitoring_id: monitoringId,
        status: "scheduled",
        next_check: calculateNextCheck(options.frequency),
      };
    } catch (error) {
      logError(
        `Error setting up price monitoring for ${url}: ${error.message}`
      );
      throw new Error(`Failed to monitor price changes: ${error.message}`);
    }
  }

  private async extractPrice(
    url: string,
    selector: string
  ): Promise<{ amount: number; currency: string } | undefined> {
    try {
      // Extract price element using Firecrawl's scrape function
      const result = await callMCP("mcp__firecrawl__firecrawl_scrape", {
        url: url,
        actions: [
          { type: "wait", milliseconds: 2000 }, // Wait for dynamic content
        ],
        formats: ["html"],
        includeTags: [selector],
      });

      // Process result to extract price
      const priceText = extractTextFromHTML(result.html);
      return parsePriceText(priceText);
    } catch (error) {
      logError(`Error extracting price from ${url}: ${error.message}`);
      return undefined;
    }
  }

  async getLatestEvents(
    destination: string,
    startDate: string,
    endDate: string,
    categories: string[] = []
  ): Promise<EventList> {
    try {
      // Build search queries based on destination and dates
      const queries = [];
      queries.push(
        `${destination} events ${formatDateRange(startDate, endDate)}`
      );

      for (const category of categories) {
        queries.push(
          `${destination} ${category} events ${formatDateRange(
            startDate,
            endDate
          )}`
        );
      }

      // Initialize result
      const result: EventList = {
        destination: destination,
        date_range: {
          start_date: startDate,
          end_date: endDate,
        },
        events: [],
        sources: [],
      };

      // Search for each query
      for (const query of queries) {
        // Use Firecrawl's deep research for comprehensive results
        const searchResult = await callMCP(
          "mcp__firecrawl__firecrawl_deep_research",
          {
            query: query,
            maxDepth: 3,
            maxUrls: 10,
          }
        );

        // Extract events from research results
        const extractedEvents = extractEventsFromResearch(
          searchResult,
          startDate,
          endDate,
          categories
        );

        // Add to result
        for (const event of extractedEvents) {
          // Check if event already exists (deduplicate)
          const exists = result.events.some(
            (e) =>
              e.name === event.name &&
              e.date === event.date &&
              (e.venue === event.venue || (!e.venue && !event.venue))
          );

          if (!exists) {
            result.events.push(event);
          }

          // Add source if not already in sources
          if (!result.sources.includes(event.source)) {
            result.sources.push(event.source);
          }
        }
      }

      // Sort events by date
      result.events.sort(
        (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
      );

      return result;
    } catch (error) {
      logError(`Error getting events for ${destination}: ${error.message}`);
      throw new Error(`Failed to get latest events: ${error.message}`);
    }
  }

  async crawlTravelBlog(
    destination: string,
    topics: string[] = [],
    maxBlogs: number = 3,
    recentOnly: boolean = true
  ): Promise<BlogInsights> {
    try {
      // First, search for relevant travel blogs
      const query = `${destination} travel blog`;
      const additionalQuery = topics.length > 0 ? ` ${topics.join(" ")}` : "";

      const searchResult = await callMCP("mcp__firecrawl__firecrawl_search", {
        query: query + additionalQuery,
        limit: maxBlogs * 2, // Search for more than needed to filter later
      });

      // Filter to actual blog posts
      const blogUrls = filterToBlogPosts(searchResult.results, recentOnly);

      // Initialize result
      const result: BlogInsights = {
        destination: destination,
        topics: {},
        sources: [],
        extraction_date: new Date().toISOString(),
      };

      // Initialize topic structure
      for (const topic of topics.length > 0 ? topics : ["general"]) {
        result.topics[topic] = [];
      }

      // Process each blog
      for (let i = 0; i < Math.min(blogUrls.length, maxBlogs); i++) {
        const blogUrl = blogUrls[i];

        // Scrape the blog content
        const blogContent = await this.extractPageContent(blogUrl, {
          format: "markdown",
          includeImages: false,
        });

        // Add to sources
        result.sources.push({
          url: blogUrl,
          title: blogContent.title,
          author: blogContent.metadata?.author,
          publish_date: blogContent.metadata?.publishDate,
          reputation_score: calculateBlogReputationScore(blogContent),
        });

        // Extract insights for each topic
        for (const topic of topics.length > 0 ? topics : ["general"]) {
          const insights = extractBlogInsights(blogContent, topic);

          if (insights) {
            insights.source_index = i;
            result.topics[topic].push(insights);
          }
        }
      }

      return result;
    } catch (error) {
      logError(
        `Error crawling travel blogs for ${destination}: ${error.message}`
      );
      throw new Error(`Failed to crawl travel blogs: ${error.message}`);
    }
  }
}

// Helper functions
function extractTitle(content: string): string {
  // Implementation
}

function extractMetadata(content: string, result: any): any {
  // Implementation
}

function extractImages(content: string): string[] {
  // Implementation
}

function extractDomain(url: string): string {
  // Implementation
}

function calculateConfidence(item: any, query: string): number {
  // Implementation
}

async function createPriceMonitor(
  url: string,
  selector: string,
  currentPrice: any,
  options: MonitorOptions
): Promise<string> {
  // Implementation
}

async function schedulePriceMonitoring(
  monitoringId: string,
  frequency: string
): Promise<void> {
  // Implementation
}

function calculateNextCheck(frequency: string): string {
  // Implementation
}

function extractTextFromHTML(html: string): string {
  // Implementation
}

function parsePriceText(
  text: string
): { amount: number; currency: string } | undefined {
  // Implementation
}

function formatDateRange(startDate: string, endDate: string): string {
  // Implementation
}

function extractEventsFromResearch(
  research: any,
  startDate: string,
  endDate: string,
  categories: string[]
): any[] {
  // Implementation
}

function filterToBlogPosts(results: any[], recentOnly: boolean): string[] {
  // Implementation
}

function calculateBlogReputationScore(blog: ExtractedContent): number {
  // Implementation
}

function extractBlogInsights(blog: ExtractedContent, topic: string): any {
  // Implementation
}
```

### Main Server Implementation

```typescript
// server.ts
import express from "express";
import bodyParser from "body-parser";
import { FirecrawlSource } from "./sources/firecrawl_source";
import { PlaywrightSource } from "./sources/playwright_source";
import { PuppeteerSource } from "./sources/puppeteer_source";
import { CacheService } from "./storage/cache";
import { logRequest, logError, logInfo } from "./utils/logging";
import { validateInput } from "./utils/validation";
import { formatResponse } from "./utils/response_formatter";
import { Config } from "./config";

const app = express();
app.use(bodyParser.json());

// Initialize sources
const firecrawlSource = new FirecrawlSource();
const playwrightSource = new PlaywrightSource();
const puppeteerSource = new PuppeteerSource();

// Initialize services
const cache = new CacheService();

// Source selection logic
function selectSource(operation: string, params: any) {
  // Default to Firecrawl for most operations
  if (operation.startsWith("search") || operation === "crawl_travel_blog") {
    return firecrawlSource;
  }

  // For price monitoring, decide based on the URL pattern
  if (operation === "monitor_price_changes") {
    if (params.url.includes("booking.com")) {
      return puppeteerSource;
    }
    return playwrightSource;
  }

  // For content extraction, decide based on site complexity
  if (operation === "extract_page_content") {
    if (isSpaOrDynamicSite(params.url)) {
      return playwrightSource;
    }
    return firecrawlSource;
  }

  // Default fallback
  return firecrawlSource;
}

// Handle MCP tool requests
app.post("/api/mcp/webcrawl/extract_page_content", async (req, res) => {
  try {
    logRequest("extract_page_content", req.body);

    // Validate input
    const { url, selectors, include_images, format } = validateInput(req.body, [
      "url",
    ]);

    // Check cache
    const cacheKey = `content:${url}:${
      selectors?.join(",") || "none"
    }:${include_images}:${format || "markdown"}`;
    const cachedData = await cache.get(cacheKey);
    if (cachedData) {
      return res.json(cachedData);
    }

    // Select appropriate source
    const source = selectSource("extract_page_content", { url });

    // Call source
    const options = {
      selectors: selectors,
      includeImages: include_images,
      format: format || "markdown",
    };

    const data = await source.extractPageContent(url, options);

    // Cache result (expires in 1 day for most sites, 1 hour for news/dynamic sites)
    const ttl = isNewsOrFrequentlyUpdatedSite(url) ? 60 * 60 : 24 * 60 * 60;
    await cache.set(cacheKey, data, ttl);

    // Return formatted response
    return res.json(formatResponse(data));
  } catch (error) {
    logError(`Error in extract_page_content: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

app.post("/api/mcp/webcrawl/search_destination_info", async (req, res) => {
  try {
    logRequest("search_destination_info", req.body);

    // Validate input
    const { destination, topics, max_results } = validateInput(req.body, [
      "destination",
    ]);

    // Check cache
    const topicsKey = topics ? topics.sort().join(",") : "default";
    const cacheKey = `destination:${destination}:${topicsKey}:${
      max_results || 5
    }`;
    const cachedData = await cache.get(cacheKey);
    if (cachedData) {
      return res.json(cachedData);
    }

    // Call source (always use Firecrawl for search)
    const data = await firecrawlSource.searchDestinationInfo(
      destination,
      topics,
      max_results || 5
    );

    // Cache result (expires in 1 week)
    await cache.set(cacheKey, data, 7 * 24 * 60 * 60);

    // Return formatted response
    return res.json(formatResponse(data));
  } catch (error) {
    logError(`Error in search_destination_info: ${error.message}`);
    return res.status(500).json({
      error: true,
      message: error.message,
    });
  }
});

// Additional endpoints for other MCP tools...

// Utility functions
function isSpaOrDynamicSite(url: string): boolean {
  // Check if the site likely requires JavaScript execution
  const dynamicSiteDomains = [
    "tripadvisor.com",
    "airbnb.com",
    "booking.com",
    "expedia.com",
    "hotels.com",
    "kayak.com",
    "orbitz.com",
    "hotwire.com",
  ];

  return dynamicSiteDomains.some((domain) => url.includes(domain));
}

function isNewsOrFrequentlyUpdatedSite(url: string): boolean {
  // Check if the site is likely to update content frequently
  const frequentUpdateDomains = [
    "cnn.com",
    "bbc.com",
    "nytimes.com",
    "theguardian.com",
    "weather.com",
    "accuweather.com",
  ];

  return frequentUpdateDomains.some((domain) => url.includes(domain));
}

// Start server
const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  logInfo(`Web Crawling MCP Server running on port ${PORT}`);
});
```

## Data Formats

### Input Format Examples

```json
// extract_page_content input
{
  "url": "https://www.example.com/paris-travel-guide",
  "selectors": ["article.main-content", "div.attractions-list"],
  "include_images": true,
  "format": "markdown"
}

// search_destination_info input
{
  "destination": "Kyoto, Japan",
  "topics": ["historical sites", "traditional cuisine", "cherry blossom season"],
  "max_results": 3
}

// monitor_price_changes input
{
  "url": "https://www.booking.com/hotel/fr/grand-hotel-du-palais-royal-paris.html",
  "price_selector": "div.prco-wrapper span.prco-valign-middle-helper",
  "frequency": "daily",
  "notification_threshold": 10
}
```

### Output Format Examples

```json
// extract_page_content output
{
  "url": "https://www.example.com/paris-travel-guide",
  "title": "Paris Travel Guide: Everything You Need to Know",
  "content": "# Paris Travel Guide\n\nParis, the capital of France, is known for its stunning architecture, art museums, historical landmarks, and its influence on fashion, culture, and food.\n\n## Top Attractions\n\n- **Eiffel Tower**: Iconic iron tower that's one of the most recognizable structures in the world.\n- **Louvre Museum**: World's largest art museum and home to the Mona Lisa.\n- **Notre-Dame Cathedral**: Medieval Catholic cathedral known for its French Gothic architecture.\n\n...",
  "images": [
    "https://www.example.com/images/eiffel-tower.jpg",
    "https://www.example.com/images/louvre-museum.jpg",
    "https://www.example.com/images/notre-dame.jpg"
  ],
  "metadata": {
    "author": "Travel Expert Magazine",
    "publishDate": "2024-12-10",
    "lastModified": "2025-03-15",
    "siteName": "Example Travel Guides"
  },
  "format": "markdown"
}

// search_destination_info output
{
  "destination": "Kyoto, Japan",
  "topics": {
    "historical sites": [
      {
        "title": "Top 10 Historical Sites in Kyoto You Can't Miss",
        "content": "Kyoto, once the capital of Japan, is home to countless temples, shrines, and other historically priceless structures. Here are the top 10 historical sites you must visit in Kyoto:\n\n1. **Kinkaku-ji (Golden Pavilion)** - A Zen temple covered in gold leaf, set in a beautiful garden with a reflective pond.\n\n2. **Fushimi Inari Shrine** - Famous for its thousands of vermilion torii gates.\n\n...",
        "source": "japan-guide.com",
        "url": "https://www.japan-guide.com/e/e3950.html",
        "confidence": 0.92
      },
      {
        "title": "Exploring Kyoto's UNESCO World Heritage Sites",
        "content": "Kyoto is home to an impressive 17 UNESCO World Heritage Sites, more than any other city in Japan. These sites represent the cultural heritage of Japan's ancient capital from the 8th to the 17th centuries.\n\n...",
        "source": "unesco.org",
        "url": "https://whc.unesco.org/en/list/688",
        "confidence": 0.87
      },
      {
        "title": "Historical Walking Tour of Eastern Kyoto",
        "content": "This self-guided walking tour takes you through the historic district of Higashiyama, including visits to Kiyomizu-dera Temple, Ninenzaka and Sannenzaka slopes, and Yasaka Shrine.\n\n...",
        "source": "insidekyoto.com",
        "url": "https://www.insidekyoto.com/eastern-kyoto-walking-tour",
        "confidence": 0.85
      }
    ],
    "traditional cuisine": [
      // Similar structure for cuisine results...
    ],
    "cherry blossom season": [
      // Similar structure for cherry blossom results...
    ]
  },
  "sources": [
    "japan-guide.com",
    "unesco.org",
    "insidekyoto.com",
    "kyotofoodie.com",
    "visitkyoto.org",
    "japan.travel"
  ]
}

// monitor_price_changes output
{
  "url": "https://www.booking.com/hotel/fr/grand-hotel-du-palais-royal-paris.html",
  "initial_price": {
    "amount": 350.00,
    "currency": "EUR",
    "timestamp": "2025-05-10T15:30:45Z"
  },
  "current_price": {
    "amount": 350.00,
    "currency": "EUR",
    "timestamp": "2025-05-10T15:30:45Z"
  },
  "monitoring_id": "mon_12345",
  "status": "scheduled",
  "next_check": "2025-05-11T15:30:45Z"
}
```

## Implementation Considerations

### Caching Strategy

- **Page Content**: Cache for 24 hours (1 hour for news/dynamic sites)
- **Destination Info**: Cache for 1 week
- **Event Listings**: Cache for 1 day
- **Blog Insights**: Cache for 1 week
- **Redis or in-memory cache** for quick access
- **Cache invalidation** based on TTL (Time-To-Live)

### Rate Limiting and Ethical Crawling

- **Respect robots.txt**: Implement a robots.txt parser and respect directives
- **Rate limiting**: Implement per-domain rate limiting (e.g., max 1 request per 5 seconds)
- **Crawl-delay**: Honor site-specific crawl-delay directives
- **User-agent identification**: Use appropriate user-agent strings
- **Conditional requests**: Use If-Modified-Since headers to reduce bandwidth
- **Domain diversity**: Alternate between different domains to reduce load on any single site

### Error Handling

- **Site Accessibility Issues**: Implement fallbacks when sites block crawlers
- **Parsing Failures**: Return partial results with warning messages
- **Timeout Handling**: Set appropriate timeouts for external requests
- **Circuit Breaker Pattern**: Temporarily disable crawling for problematic domains

### Performance Optimization

- **Parallel Crawling**: Process multiple URLs concurrently with rate limiting
- **Content Sanitization**: Remove irrelevant content and scripts before processing
- **Response Compression**: Use gzip/brotli for improved transfer speeds
- **Selective Crawling**: Only fetch necessary resources

### Security

- **URL Validation**: Prevent crawling of internal or sensitive domains
- **Input Sanitization**: Validate and sanitize all user inputs
- **Content Filtering**: Scan for and remove potentially malicious content
- **Access Control**: Implement role-based permissions for sensitive operations

## Integration with Agent Architecture

The Web Crawling MCP Server will be exposed to the TripSage agents through a client library that handles the MCP communication protocol. This integration will be implemented in the `src/agents/mcp_integration.py` file:

```python
# src/agents/mcp_integration.py

class WebCrawlMCPClient:
    """Client for interacting with the Web Crawling MCP Server"""

    def __init__(self, server_url):
        self.server_url = server_url

    async def extract_page_content(self, url, selectors=None, include_images=False, format='markdown'):
        """Extract content from a webpage"""
        try:
            # Implement MCP call to web crawl server
            result = await call_mcp_tool(
                "mcp__webcrawl__extract_page_content",
                {
                    "url": url,
                    "selectors": selectors,
                    "include_images": include_images,
                    "format": format
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error extracting page content: {str(e)}")
            raise

    async def search_destination_info(self, destination, topics=None, max_results=5):
        """Search for information about a travel destination"""
        try:
            topics = topics or []
            # Implement MCP call to web crawl server
            result = await call_mcp_tool(
                "mcp__webcrawl__search_destination_info",
                {
                    "destination": destination,
                    "topics": topics,
                    "max_results": max_results
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error searching destination info: {str(e)}")
            raise

    async def monitor_price_changes(self, url, price_selector, frequency="daily", notification_threshold=5):
        """Monitor price changes on a webpage"""
        try:
            # Implement MCP call to web crawl server
            result = await call_mcp_tool(
                "mcp__webcrawl__monitor_price_changes",
                {
                    "url": url,
                    "price_selector": price_selector,
                    "frequency": frequency,
                    "notification_threshold": notification_threshold
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error monitoring price changes: {str(e)}")
            raise

    # Additional methods for other MCP tools...
```

## Deployment Strategy

The Web Crawling MCP Server will be containerized using Docker and deployed as a standalone service. This allows for independent scaling and updates:

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

ENV NODE_ENV=production
ENV PORT=3001

EXPOSE 3001

CMD ["node", "server.js"]
```

### Resource Requirements

- **CPU**: Moderate (1-2 vCPU recommended, scales with traffic)
- **Memory**: 1GB minimum, 2GB recommended
- **Storage**: Minimal (primarily for code and logs)
- **Network**: High (frequent external API calls and web requests)

### Monitoring

- **Health Endpoint**: `/health` endpoint for monitoring
- **Metrics**: Request count, response time, error rate, cache hit rate
- **Logging**: Structured logs with request/response details
- **Alerts**: Set up for high error rates or slow responses

### Compliance Considerations

- **Terms of Service**: Maintain a list of site-specific crawling policies
- **Fair Use**: Implement proper attribution for content sources
- **Privacy**: Do not store personal information from crawled sites
- **Legal**: Adhere to copyright laws and fair use policies
