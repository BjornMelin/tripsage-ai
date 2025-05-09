# Airbnb MCP Server Integration

This document outlines the implementation details for the Airbnb MCP Server, which provides accommodation search and listing details for the TripSage travel planning system.

## Overview

The Airbnb MCP Server enables TripSage to access accommodation information from Airbnb without requiring direct API access. This integration allows the system to search for listings based on location and travel criteria, retrieve detailed information about specific properties, and incorporate this data into the travel planning process. The server respects Airbnb's terms of service while providing structured access to publicly available information.

## Technology Selection

After evaluating multiple implementation approaches, we selected the following technology stack:

- **Node.js**: JavaScript runtime for the server implementation
- **TypeScript**: Type-safe language for robust code quality
- **Cheerio**: HTML parsing library for structured data extraction
- **Axios**: HTTP client for making web requests
- **FastMCP**: Framework for building MCP servers with minimal boilerplate

We chose this stack because:

- It provides a lightweight, efficient solution for extracting structured data
- TypeScript ensures type safety and improves maintainability
- The implementation respects website terms while providing necessary functionality
- FastMCP simplifies the MCP server implementation with minimal boilerplate

## MCP Tools

The Airbnb MCP Server exposes two primary tools:

### airbnb_search

Searches for Airbnb listings based on location and optional filters.

```typescript
@mcp.tool()
async function airbnb_search(
  {
    location,
    checkin,
    checkout,
    adults,
    children,
    infants,
    pets,
    price_min,
    price_max
  }: {
    location: string,
    checkin?: string,
    checkout?: string,
    adults?: number,
    children?: number,
    infants?: number,
    pets?: number,
    price_min?: number,
    price_max?: number
  }
): Promise<AirbnbSearchResult> {
  try {
    // Build search URL
    const searchParams = new URLSearchParams();
    searchParams.append('query', location);

    if (checkin) searchParams.append('checkin', checkin);
    if (checkout) searchParams.append('checkout', checkout);
    if (adults) searchParams.append('adults', adults.toString());
    if (children) searchParams.append('children', children.toString());
    if (infants) searchParams.append('infants', infants.toString());
    if (pets) searchParams.append('pets', pets.toString());
    if (price_min) searchParams.append('price_min', price_min.toString());
    if (price_max) searchParams.append('price_max', price_max.toString());

    const searchUrl = `https://www.airbnb.com/s/homes?${searchParams.toString()}`;

    // Fetch search results page
    const response = await axios.get(searchUrl, {
      headers: {
        'User-Agent': USER_AGENT,
        'Accept-Language': 'en-US,en;q=0.9'
      }
    });

    // Parse HTML and extract listing data
    const $ = cheerio.load(response.data);
    const listings = extractListingsFromHTML($);

    return {
      location,
      count: listings.length,
      listings: listings.map(listing => ({
        id: listing.id,
        name: listing.name,
        url: `https://www.airbnb.com${listing.url}`,
        image: listing.image,
        superhost: listing.superhost,
        price_string: listing.priceString,
        price_total: listing.priceTotal,
        rating: listing.rating,
        reviews_count: listing.reviewsCount,
        location_info: listing.locationInfo,
        property_type: listing.propertyType,
        beds: listing.beds,
        bedrooms: listing.bedrooms,
        bathrooms: listing.bathrooms
      }))
    };
  } catch (error) {
    throw new Error(`Airbnb search error: ${error.message}`);
  }
}
```

### airbnb_listing_details

Retrieves detailed information about a specific Airbnb listing by ID.

```typescript
@mcp.tool()
async function airbnb_listing_details(
  {
    id,
    checkin,
    checkout,
    adults,
    children,
    infants,
    pets
  }: {
    id: string,
    checkin?: string,
    checkout?: string,
    adults?: number,
    children?: number,
    infants?: number,
    pets?: number
  }
): Promise<AirbnbListingDetails> {
  try {
    // Build listing URL
    const listingUrl = `https://www.airbnb.com/rooms/${id}`;
    let fullUrl = listingUrl;

    if (checkin && checkout) {
      const searchParams = new URLSearchParams();
      searchParams.append('check_in', checkin);
      searchParams.append('check_out', checkout);
      if (adults) searchParams.append('adults', adults.toString());
      if (children) searchParams.append('children', children.toString());
      if (infants) searchParams.append('infants', infants.toString());
      if (pets) searchParams.append('pets', pets.toString());

      fullUrl = `${listingUrl}?${searchParams.toString()}`;
    }

    // Fetch listing page
    const response = await axios.get(fullUrl, {
      headers: {
        'User-Agent': USER_AGENT,
        'Accept-Language': 'en-US,en;q=0.9'
      }
    });

    // Parse HTML and extract listing details
    const $ = cheerio.load(response.data);
    const details = extractListingDetailsFromHTML($, id);

    return {
      id,
      url: listingUrl,
      name: details.name,
      description: details.description,
      host: details.host,
      property_type: details.propertyType,
      location: details.location,
      coordinates: details.coordinates,
      amenities: details.amenities,
      bedrooms: details.bedrooms,
      beds: details.beds,
      bathrooms: details.bathrooms,
      max_guests: details.maxGuests,
      rating: details.rating,
      reviews_count: details.reviewsCount,
      reviews_summary: details.reviewsSummary,
      price_per_night: details.pricePerNight,
      price_total: details.priceTotal,
      images: details.images.slice(0, 10) // Limit to 10 images
    };
  } catch (error) {
    throw new Error(`Airbnb listing details error: ${error.message}`);
  }
}
```

## Implementation Details

### Server Architecture

The Airbnb MCP Server follows a clean architecture with separation of concerns:

1. **Server**: MCP server setup and configuration
2. **Utils**: Helper functions for data extraction and HTML parsing
3. **Models**: Type definitions and interfaces
4. **Tools**: MCP tool implementations

### Core Components

#### Server Entry Point

```typescript
// index.ts
import { FastMCP } from "fastmcp";
import { airbnb_search, airbnb_listing_details } from "./tools";

// Create MCP server
const server = new FastMCP({
  name: "airbnb-mcp",
  version: "1.0.0",
  description: "Airbnb MCP Server for TripSage",
});

// Register tools
server.registerTool(airbnb_search);
server.registerTool(airbnb_listing_details);

// Start the server
const port = parseInt(process.env.PORT || "3000");
server.start({
  transportType: process.env.TRANSPORT_TYPE || "stdio",
  http: {
    port: port,
  },
});

console.log(`Airbnb MCP Server started`);
```

#### HTML Extraction Utilities

```typescript
// utils/extractors.ts
import * as cheerio from "cheerio";

export function extractListingsFromHTML(
  $: cheerio.CheerioAPI
): AirbnbListing[] {
  const listings: AirbnbListing[] = [];

  // Find all listing cards in the search results
  $("._8ssblpx").each((i, el) => {
    try {
      const $el = $(el);

      // Extract listing ID
      const idMatch = $el
        .find("a")
        .attr("href")
        ?.match(/\/rooms\/(\d+)/);
      if (!idMatch) return;

      const id = idMatch[1];
      const url = $el.find("a").attr("href") || "";

      // Extract other listing data
      const name = $el.find("._bzh5lkq").text().trim();
      const image = $el.find("img").attr("src") || "";
      const superhost = $el.find("._1mhorg9").length > 0;

      const priceString = $el.find("._1jo4hgw").text().trim();
      const priceMatch = priceString.match(/\$(\d+)/);
      const priceTotal = priceMatch ? parseInt(priceMatch[1]) : null;

      const ratingText = $el.find("._10fy1f8").text().trim();
      const ratingMatch = ratingText.match(/(\d+\.\d+)/);
      const rating = ratingMatch ? parseFloat(ratingMatch[1]) : null;

      const reviewsText = $el.find("._a7a5sx").text().trim();
      const reviewsMatch = reviewsText.match(/(\d+)/);
      const reviewsCount = reviewsMatch ? parseInt(reviewsMatch[1]) : 0;

      const locationInfo = $el.find("._kqh46o").text().trim();
      const propertyType = $el.find("._b14dlit").first().text().trim();

      const details = $el.find("._kqh46o").last().text().trim();
      const bedsMatch = details.match(/(\d+) bed/);
      const beds = bedsMatch ? parseInt(bedsMatch[1]) : null;

      const bedroomsMatch = details.match(/(\d+) bedroom/);
      const bedrooms = bedroomsMatch ? parseInt(bedroomsMatch[1]) : null;

      const bathroomsMatch = details.match(/(\d+) bathroom/);
      const bathrooms = bathroomsMatch ? parseInt(bathroomsMatch[1]) : null;

      listings.push({
        id,
        name,
        url,
        image,
        superhost,
        priceString,
        priceTotal,
        rating,
        reviewsCount,
        locationInfo,
        propertyType,
        beds,
        bedrooms,
        bathrooms,
      });
    } catch (error) {
      // Skip listings that fail to parse
      console.error(`Error parsing listing: ${error.message}`);
    }
  });

  return listings;
}

export function extractListingDetailsFromHTML(
  $: cheerio.CheerioAPI,
  id: string
): AirbnbListingDetails {
  // Extract listing title
  const name = $("h1").text().trim();

  // Extract listing description
  const description = $('div[data-section-id="DESCRIPTION_DEFAULT"] span')
    .text()
    .trim();

  // Extract host information
  const host = {
    name: $('div[data-section-id="HOST_PROFILE_DEFAULT"] h2').text().trim(),
    image:
      $('div[data-section-id="HOST_PROFILE_DEFAULT"] img').attr("src") || "",
    superhost: $('div[data-section-id="HOST_PROFILE_DEFAULT"]')
      .text()
      .includes("Superhost"),
  };

  // Extract location information
  const location = $('div[data-section-id="LOCATION_DEFAULT"] h2')
    .next()
    .text()
    .trim();

  // Extract coordinates from the embedded map
  let coordinates = null;
  const scriptTags = $("script");
  scriptTags.each((i, el) => {
    const scriptContent = $(el).html() || "";
    const coordsMatch = scriptContent.match(
      /"lat":(-?\d+\.\d+),"lng":(-?\d+\.\d+)/
    );
    if (coordsMatch) {
      coordinates = {
        lat: parseFloat(coordsMatch[1]),
        lng: parseFloat(coordsMatch[2]),
      };
    }
  });

  // Extract amenities
  const amenities: string[] = [];
  $('div[data-section-id="AMENITIES_DEFAULT"] div._1qsawv5').each((i, el) => {
    amenities.push($(el).text().trim());
  });

  // Extract property details
  const propertyInfo = $('div[data-section-id="OVERVIEW_DEFAULT"] h2').next();

  const propertyType = propertyInfo.find("div").first().text().trim();

  const guestsText = propertyInfo.find("div").eq(1).text().trim();
  const guestsMatch = guestsText.match(/(\d+) guest/);
  const maxGuests = guestsMatch ? parseInt(guestsMatch[1]) : null;

  const bedroomsMatch = propertyInfo.text().match(/(\d+) bedroom/);
  const bedrooms = bedroomsMatch ? parseInt(bedroomsMatch[1]) : null;

  const bedsMatch = propertyInfo.text().match(/(\d+) bed/);
  const beds = bedsMatch ? parseInt(bedsMatch[1]) : null;

  const bathroomsMatch = propertyInfo.text().match(/(\d+) bathroom/);
  const bathrooms = bathroomsMatch ? parseInt(bathroomsMatch[1]) : null;

  // Extract price information
  const priceElement = $("._1k4xcdh");
  const priceString = priceElement.text().trim();
  const priceMatch = priceString.match(/\$(\d+)/);
  const pricePerNight = priceMatch ? parseInt(priceMatch[1]) : null;

  const totalPriceElement = $("._1k4xcdh").next();
  const totalPriceString = totalPriceElement.text().trim();
  const totalPriceMatch = totalPriceString.match(/\$(\d+)/);
  const priceTotal = totalPriceMatch ? parseInt(totalPriceMatch[1]) : null;

  // Extract rating information
  const ratingText = $("span._1ne5r4rt").text().trim();
  const ratingMatch = ratingText.match(/(\d+\.\d+)/);
  const rating = ratingMatch ? parseFloat(ratingMatch[1]) : null;

  const reviewsText = $("span._s65ijh7").text().trim();
  const reviewsMatch = reviewsText.match(/(\d+)/);
  const reviewsCount = reviewsMatch ? parseInt(reviewsMatch[1]) : 0;

  // Extract review summaries
  const reviewsSummary: { category: string; rating: number }[] = [];
  $("div._1s11ltsf").each((i, el) => {
    const category = $(el).find("div._y1ba89").text().trim();
    const ratingText = $(el).find("span._4oybiu").text().trim();
    const ratingValue = parseFloat(ratingText);

    if (category && !isNaN(ratingValue)) {
      reviewsSummary.push({
        category,
        rating: ratingValue,
      });
    }
  });

  // Extract images
  const images: string[] = [];
  $('div[data-testid="photo-viewer"] img').each((i, el) => {
    const src = $(el).attr("src");
    if (src) images.push(src);
  });

  return {
    name,
    description,
    host,
    propertyType,
    location,
    coordinates,
    amenities,
    bedrooms,
    beds,
    bathrooms,
    maxGuests,
    rating,
    reviewsCount,
    reviewsSummary,
    pricePerNight,
    priceTotal,
    images,
  };
}
```

## Integration with TripSage

The Airbnb MCP Server integrates with TripSage in the following ways:

### Agent Integration

The Travel Agent uses the Airbnb MCP Server for several key tasks in the accommodation planning process:

1. **Accommodation Search**: Find suitable lodging options based on the traveler's destination and criteria.
2. **Property Evaluation**: Gather detailed information about specific properties to assess suitability.
3. **Price Comparison**: Compare prices across different properties and with other accommodation providers.
4. **Feature Analysis**: Evaluate property amenities and features to match traveler preferences.
5. **Location Assessment**: Analyze property location relative to planned activities and attractions.

### Data Flow

1. **Input**: Travel agent receives accommodation requirements (location, dates, guests, etc.).
2. **Processing**: The agent translates these requirements into appropriate MCP tool calls.
3. **API Interaction**: The MCP server retrieves and parses accommodation data from Airbnb.
4. **Response Processing**: Results are processed and formatted for agent consumption.
5. **Dual Storage**: Relevant accommodation data is stored in both Supabase (for structured queries) and the knowledge graph (for semantic relationships).

### Example Workflow

A typical workflow for planning accommodations might involve:

1. Searching for properties in the destination area within the travel dates
2. Filtering results based on price range, number of guests, and other criteria
3. Retrieving detailed information about promising properties
4. Comparing options based on price, amenities, location, and reviews
5. Storing selected options in the dual storage architecture for later reference

## Deployment and Configuration

### Environment Variables

| Variable           | Description                         | Default                                                      |
| ------------------ | ----------------------------------- | ------------------------------------------------------------ |
| PORT               | Port for the MCP server             | 3000                                                         |
| TRANSPORT_TYPE     | MCP transport type (stdio or http)  | stdio                                                        |
| RESPECT_ROBOTS_TXT | Whether to respect robots.txt rules | true                                                         |
| USER_AGENT         | User agent string for HTTP requests | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 |
| REQUEST_TIMEOUT    | Timeout for HTTP requests (ms)      | 30000                                                        |

### Deployment Options

1. **Docker Container**: The recommended deployment method

   ```bash
   docker build -t airbnb-mcp .
   docker run airbnb-mcp
   ```

2. **NPM Package**: For direct integration with other Node.js services

   ```bash
   npm install @openbnb/mcp-server-airbnb
   npx @openbnb/mcp-server-airbnb
   ```

3. **Local Development**: For testing and development

   ```bash
   npm install
   npm start
   ```

### Error Handling

The Airbnb MCP Server implements comprehensive error handling to manage:

- Network failures and timeouts
- HTML parsing errors when website structure changes
- Rate limiting and temporary blocks
- Malformed input parameters
- Edge cases in data extraction

Each error is logged and returns a structured error response to the client.

## Best Practices and Ethical Considerations

### Web Scraping Guidelines

1. **Respect Terms of Service**: The server is configured to respect Airbnb's robots.txt by default.
2. **Rate Limiting**: Implement reasonable delays between requests to avoid overloading the service.
3. **Caching**: Cache search results and listing details to reduce redundant requests.
4. **User Agent**: Use a consistent, identifiable user agent string for transparency.
5. **Minimal Data**: Extract only the necessary information, avoiding sensitive or private data.

### Data Privacy

1. **Personal Information**: Never extract or store personal information about hosts or guests.
2. **Location Privacy**: Handle exact location coordinates with appropriate security measures.
3. **Data Retention**: Implement appropriate retention policies for cached accommodation data.

## Limitations and Future Enhancements

### Current Limitations

- Limited to publicly available information on Airbnb's website
- No access to real-time availability information
- No ability to make bookings or transactions
- Susceptible to website structure changes

### Planned Enhancements

1. **Smart Caching**: Implement intelligent caching with time-based invalidation
2. **Structure Resilience**: Improve HTML parsing to handle minor website changes
3. **Enhanced Filtering**: Support more advanced filtering options for searches
4. **Alternative Sources**: Integration with multiple accommodation providers
5. **Result Normalization**: Standardize data format across different providers
6. **Review Analysis**: Extract and analyze review sentiment for better recommendations

## Conclusion

The Airbnb MCP Server provides TripSage with access to accommodation information from Airbnb in a structured, ethical manner. By leveraging HTML parsing techniques, the server extracts essential property information that can be incorporated into the travel planning process. This integration enables TripSage to offer comprehensive accommodation options to users without requiring API access or direct integration with Airbnb's systems.

The server implementation respects Airbnb's terms of service while providing the functionality needed for effective travel planning. Future enhancements will focus on improving resilience, expanding data coverage, and integrating with additional accommodation providers.
