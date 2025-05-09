# Google Maps MCP Server Integration

This document outlines the implementation details for the Google Maps MCP Server, which provides location and mapping capabilities for the TripSage travel planning system.

## Overview

The Google Maps MCP Server acts as a bridge between AI agents and the Google Maps API, enabling access to a wide range of geospatial data and location-based services. This integration is crucial for TripSage to provide accurate location information, distance calculations, place search, and visual mapping capabilities to enhance the travel planning experience.

## Technology Selection

After evaluating various mapping APIs and server implementation frameworks, we selected the following technology stack:

- **Google Maps Platform API**: Comprehensive set of mapping services with global coverage
- **Node.js**: JavaScript runtime for building the MCP server
- **TypeScript**: Strongly-typed language for robust code
- **FastMCP**: High-level framework for building MCP servers with minimal boilerplate
- **Docker**: For containerized deployment

The Google Maps Platform was chosen for its comprehensive API offerings, global data coverage, and reliability. The Node.js/TypeScript implementation provides a good balance of performance and developer productivity.

## API Features

The Google Maps MCP Server exposes the following core API features:

### Geocoding Services

- **Forward Geocoding**: Convert addresses to geographic coordinates (latitude/longitude)
- **Reverse Geocoding**: Convert coordinates to human-readable addresses

### Place Services

- **Place Search**: Find places by text query, location proximity, or category
- **Place Details**: Get comprehensive information about a specific place
- **Place Photos**: Retrieve photos associated with places
- **Autocomplete**: Suggest place completions based on partial text input

### Distance and Directions

- **Distance Matrix**: Calculate travel distance and time between multiple origins and destinations
- **Directions**: Get step-by-step directions between locations with various transportation modes
- **Route Optimization**: Find optimal routes for multi-stop itineraries

### Maps Visualization

- **Static Maps**: Generate map images with custom markers and styling
- **Street View**: Access street-level imagery for destinations

## MCP Tools

The Google Maps MCP Server implements the following tools:

### Geocoding Tools

```typescript
@mcp.tool()
async function geocode_address(
  { address }: { address: string }
): Promise<GeocodingResult> {
  try {
    const response = await mapsClient.geocode({
      address: address
    });

    return {
      status: response.data.status,
      results: response.data.results.map(result => ({
        formatted_address: result.formatted_address,
        place_id: result.place_id,
        location: {
          lat: result.geometry.location.lat,
          lng: result.geometry.location.lng
        }
      }))
    };
  } catch (error) {
    throw new Error(`Geocoding error: ${error.message}`);
  }
}

@mcp.tool()
async function reverse_geocode(
  { lat, lng }: { lat: number, lng: number }
): Promise<GeocodingResult> {
  try {
    const response = await mapsClient.geocode({
      location: { lat, lng }
    });

    return {
      status: response.data.status,
      results: response.data.results.map(result => ({
        formatted_address: result.formatted_address,
        place_id: result.place_id,
        location: {
          lat: result.geometry.location.lat,
          lng: result.geometry.location.lng
        }
      }))
    };
  } catch (error) {
    throw new Error(`Reverse geocoding error: ${error.message}`);
  }
}
```

### Place Tools

```typescript
@mcp.tool()
async function search_places(
  {
    query,
    location,
    radius,
    type
  }: {
    query?: string,
    location?: { lat: number, lng: number },
    radius?: number,
    type?: string
  }
): Promise<PlaceSearchResult> {
  try {
    const response = await mapsClient.places({
      query,
      location: location ? `${location.lat},${location.lng}` : undefined,
      radius,
      type
    });

    return {
      status: response.data.status,
      results: response.data.results.map(result => ({
        name: result.name,
        place_id: result.place_id,
        formatted_address: result.formatted_address,
        location: {
          lat: result.geometry.location.lat,
          lng: result.geometry.location.lng
        },
        rating: result.rating,
        types: result.types
      }))
    };
  } catch (error) {
    throw new Error(`Place search error: ${error.message}`);
  }
}

@mcp.tool()
async function get_place_details(
  { place_id }: { place_id: string }
): Promise<PlaceDetailsResult> {
  try {
    const response = await mapsClient.place({
      place_id: place_id,
      fields: [
        'name', 'formatted_address', 'formatted_phone_number',
        'website', 'opening_hours', 'rating', 'reviews',
        'price_level', 'photos', 'geometry'
      ]
    });

    return {
      status: response.data.status,
      result: {
        name: response.data.result.name,
        formatted_address: response.data.result.formatted_address,
        formatted_phone_number: response.data.result.formatted_phone_number,
        website: response.data.result.website,
        opening_hours: response.data.result.opening_hours,
        rating: response.data.result.rating,
        reviews: response.data.result.reviews,
        price_level: response.data.result.price_level,
        photos: response.data.result.photos,
        location: {
          lat: response.data.result.geometry.location.lat,
          lng: response.data.result.geometry.location.lng
        }
      }
    };
  } catch (error) {
    throw new Error(`Place details error: ${error.message}`);
  }
}
```

### Distance and Directions Tools

```typescript
@mcp.tool()
async function calculate_distance(
  {
    origins,
    destinations,
    mode
  }: {
    origins: Array<{ lat: number, lng: number } | string>,
    destinations: Array<{ lat: number, lng: number } | string>,
    mode?: 'driving' | 'walking' | 'bicycling' | 'transit'
  }
): Promise<DistanceMatrixResult> {
  try {
    const originsStr = origins.map(o =>
      typeof o === 'string' ? o : `${o.lat},${o.lng}`
    );

    const destinationsStr = destinations.map(d =>
      typeof d === 'string' ? d : `${d.lat},${d.lng}`
    );

    const response = await mapsClient.distanceMatrix({
      origins: originsStr,
      destinations: destinationsStr,
      mode: mode || 'driving'
    });

    return {
      status: response.data.status,
      origin_addresses: response.data.origin_addresses,
      destination_addresses: response.data.destination_addresses,
      rows: response.data.rows
    };
  } catch (error) {
    throw new Error(`Distance calculation error: ${error.message}`);
  }
}

@mcp.tool()
async function get_directions(
  {
    origin,
    destination,
    waypoints,
    mode,
    alternatives
  }: {
    origin: { lat: number, lng: number } | string,
    destination: { lat: number, lng: number } | string,
    waypoints?: Array<{ lat: number, lng: number } | string>,
    mode?: 'driving' | 'walking' | 'bicycling' | 'transit',
    alternatives?: boolean
  }
): Promise<DirectionsResult> {
  try {
    const originStr = typeof origin === 'string' ?
      origin : `${origin.lat},${origin.lng}`;

    const destinationStr = typeof destination === 'string' ?
      destination : `${destination.lat},${destination.lng}`;

    const waypointsStr = waypoints?.map(wp =>
      typeof wp === 'string' ? wp : `${wp.lat},${wp.lng}`
    );

    const response = await mapsClient.directions({
      origin: originStr,
      destination: destinationStr,
      waypoints: waypointsStr,
      mode: mode || 'driving',
      alternatives: alternatives || false
    });

    return {
      status: response.data.status,
      routes: response.data.routes.map(route => ({
        summary: route.summary,
        legs: route.legs.map(leg => ({
          distance: leg.distance,
          duration: leg.duration,
          start_address: leg.start_address,
          end_address: leg.end_address,
          steps: leg.steps.map(step => ({
            distance: step.distance,
            duration: step.duration,
            instructions: step.html_instructions,
            travel_mode: step.travel_mode
          }))
        }))
      }))
    };
  } catch (error) {
    throw new Error(`Directions error: ${error.message}`);
  }
}
```

### Maps Visualization Tools

```typescript
@mcp.tool()
async function generate_static_map(
  {
    center,
    zoom,
    size,
    markers
  }: {
    center?: { lat: number, lng: number } | string,
    zoom?: number,
    size?: { width: number, height: number },
    markers?: Array<{
      location: { lat: number, lng: number } | string,
      label?: string,
      color?: string
    }>
  }
): Promise<StaticMapResult> {
  try {
    const centerStr = center ?
      (typeof center === 'string' ? center : `${center.lat},${center.lng}`) :
      undefined;

    const markersParams = markers?.map(marker => {
      const locationStr = typeof marker.location === 'string' ?
        marker.location : `${marker.location.lat},${marker.location.lng}`;

      return `color:${marker.color || 'red'}|label:${marker.label || ''}|${locationStr}`;
    });

    const params = {
      center: centerStr,
      zoom: zoom || 14,
      size: `${size?.width || 600}x${size?.height || 400}`,
      markers: markersParams,
      key: GOOGLE_MAPS_API_KEY
    };

    const url = `https://maps.googleapis.com/maps/api/staticmap?${new URLSearchParams(params)}`;

    return {
      map_url: url
    };
  } catch (error) {
    throw new Error(`Static map generation error: ${error.message}`);
  }
}
```

## Implementation Details

### Server Architecture

The Google Maps MCP Server follows a clean architecture with separation of concerns:

1. **Core**: MCP server setup and configuration
2. **Services**: Wrappers around Google Maps API client
3. **Models**: Type definitions and interfaces
4. **Tools**: MCP tool implementations
5. **Resources**: MCP resource implementations

### Key Components

#### Server Initialization

```typescript
// index.ts
import { FastMCP } from "fastmcp";
import { registerGoogleMapsTools } from "./tools";
import { configureGoogleMapsClient } from "./services";

// Initialize Google Maps client
const mapsClient = configureGoogleMapsClient({
  apiKey: process.env.GOOGLE_MAPS_API_KEY,
});

// Create MCP server
const server = new FastMCP({
  name: "google-maps-mcp",
  version: "1.0.0",
  description: "Google Maps MCP Server for TripSage",
});

// Register tools with MCP server
registerGoogleMapsTools(server, mapsClient);

// Start the server
const port = parseInt(process.env.PORT || "3000");
server.start({
  transportType: process.env.TRANSPORT_TYPE || "stdio",
  http: {
    port: port,
  },
});

console.log(`Google Maps MCP Server started`);
```

#### Google Maps Client Configuration

```typescript
// services/maps-client.ts
import { Client } from "@googlemaps/google-maps-services-js";

export interface GoogleMapsClientConfig {
  apiKey: string;
  timeout?: number;
}

export function configureGoogleMapsClient(config: GoogleMapsClientConfig) {
  const client = new Client({
    timeout: config.timeout || 10000,
  });

  return {
    geocode: (params: any) =>
      client.geocode({
        params: {
          ...params,
          key: config.apiKey,
        },
      }),

    places: (params: any) =>
      client.placesNearby({
        params: {
          ...params,
          key: config.apiKey,
        },
      }),

    place: (params: any) =>
      client.placeDetails({
        params: {
          ...params,
          key: config.apiKey,
        },
      }),

    distanceMatrix: (params: any) =>
      client.distancematrix({
        params: {
          ...params,
          key: config.apiKey,
        },
      }),

    directions: (params: any) =>
      client.directions({
        params: {
          ...params,
          key: config.apiKey,
        },
      }),
  };
}
```

## Integration with TripSage

The Google Maps MCP Server integrates with TripSage in the following ways:

### Agent Integration

TripSage leverages the Google Maps MCP Server for several key tasks in the travel planning process:

1. **Destination Information**: Retrieve detailed information about travel destinations.
2. **Distance Calculations**: Determine travel time and distance between locations.
3. **Itinerary Planning**: Map out multi-stop routes with optimized waypoints.
4. **Point of Interest Search**: Find attractions, restaurants, and accommodations near destinations.
5. **Visual Elements**: Generate maps and visual aids for the travel plan.

### Data Flow

1. **Input**: Travel agent receives location queries and geospatial data requirements.
2. **Processing**: The agent translates these requirements into appropriate MCP tool calls.
3. **API Interaction**: The MCP server calls the Google Maps API with the appropriate parameters.
4. **Response Processing**: Results are processed and formatted for agent consumption.
5. **Dual Storage**: Relevant location data is stored in both Supabase (for structured data) and the knowledge graph (for semantic relationships).

### Example Workflow

A typical workflow for planning a multi-city trip might involve:

1. Geocoding destinations to get precise coordinates
2. Calculating distances between cities to estimate travel time
3. Searching for points of interest in each destination
4. Generating an optimized route with appropriate stops
5. Creating static maps to visualize the journey

## Deployment and Configuration

### Environment Variables

| Variable            | Description                        | Default         |
| ------------------- | ---------------------------------- | --------------- |
| GOOGLE_MAPS_API_KEY | API key for Google Maps Platform   | None (Required) |
| PORT                | Port for the MCP server            | 3000            |
| TRANSPORT_TYPE      | MCP transport type (stdio or http) | stdio           |
| TIMEOUT             | Timeout for API requests (ms)      | 10000           |

### Deployment Options

1. **Docker Container**: The recommended deployment method

   ```bash
   docker build -t google-maps-mcp .
   docker run -e GOOGLE_MAPS_API_KEY=your_api_key google-maps-mcp
   ```

2. **Serverless Functions**: For dynamic scaling based on demand

   ```bash
   serverless deploy
   ```

3. **Node.js Process**: For direct integration with other services

   ```bash
   npm install
   npm start
   ```

### Cost Management

Google Maps Platform operates on a pay-as-you-go model with a free tier that includes:

- 28,500 free geocoding requests per month
- 40,000 free Places API calls per month
- 100,000 free static map loads per month

To manage costs effectively:

- Implement caching for frequent location requests
- Batch geocoding operations when possible
- Monitor API usage with Google Cloud Console

## Best Practices

1. **Error Handling**: Implement comprehensive error handling for API failures
2. **Rate Limiting**: Respect Google Maps API usage limits
3. **Caching**: Cache responses for frequently accessed locations
4. **Query Optimization**: Use the most specific search parameters available
5. **Sensitive Data**: Be cautious with location data that might reveal personal information
6. **Alternative Routes**: Generate multiple route options when appropriate
7. **Regional Formatting**: Account for international address formats and conventions

## Limitations and Future Enhancements

### Current Limitations

- Limited support for public transportation in some regions
- No built-in travel time predictions with traffic considerations
- Static maps lack interactive elements

### Planned Enhancements

1. **Predictive Travel Times**: Incorporate time-of-day traffic predictions
2. **Custom Map Styling**: Enhanced visualization options for maps
3. **Local Transit Integration**: Better support for public transportation routing
4. **Location Awareness**: Contextual awareness of location sensitivities (e.g., seasonal closures)
5. **Offline Data**: Support for basic functionality without constant API access
6. **3D Visualization**: Integration with Street View and 3D mapping capabilities

## Conclusion

The Google Maps MCP Server provides essential geospatial and location-based capabilities for the TripSage travel planning system. By integrating with Google's comprehensive mapping platform, TripSage can offer accurate, detailed, and visually rich travel planning features. The implementation follows best practices for MCP server design with proper error handling, optimization, and security considerations.

This integration forms a critical component of the TripSage ecosystem, enhancing the system's ability to provide intelligent, location-aware travel recommendations and visualizations.
