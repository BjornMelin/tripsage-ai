# Hotel Search Integration Strategy

This document outlines the strategy for integrating hotel search capabilities into TripSage, beyond the current Airbnb integration.

## Current Status

TripSage currently integrates with:
- **Airbnb** via OpenBnB MCP server - For vacation rentals and unique stays

## Hotel Search Strategy

After researching available options, we've identified the following approach for adding hotel search capabilities:

### Primary Approach: Apify Booking.com MCP Integration

Rather than building a custom MCP server for hotel search, TripSage will leverage existing Apify Booking.com MCP servers:

1. **Apify Booking.com Scraper MCP**:
   - Comprehensive hotel search and information retrieval
   - Structured data for prices, amenities, and availability
   - Well-maintained and reliable API
   - Handles pagination and result formatting

2. **Integration Implementation**:
   - Extend `create_accommodation_client` in `src/mcp/accommodations/factory.py` to support a "booking" source
   - Create a `BookingMCPClient` class in a new file `src/mcp/accommodations/booking_client.py`
   - Follow the same interface pattern as `AirbnbMCPClient` for consistency
   - Add appropriate Pydantic models for request/response validation

3. **Configuration**:
   - Add Booking.com configuration to `settings.py` under `AccommodationsMCPConfig`
   - Store Apify API key in environment variables
   - Configure rate limiting appropriately

### Data Storage & Persistence

Hotel search results will use the same dual storage approach as other accommodation data:

1. **Supabase Storage**:
   - Store structured hotel data in database
   - Use the same schema with appropriate metadata

2. **Knowledge Graph Storage**:
   - Add hotels to memory graph with appropriate entity type
   - Create relations to destinations and amenities
   - Store observations about pricing, ratings, etc.

## Implementation Timeline

1. **Phase 1: Direct Integration (Current)**
   - Use Airbnb MCP integration for vacation rentals
   - Document hotel search strategy

2. **Phase 2: Booking.com MCP Integration**
   - Implement BookingMCPClient
   - Add Apify Booking.com MCP integration
   - Update agent tools to support both sources

3. **Phase 3: Enhanced Hotel Features**
   - Add hotel-specific filters (star rating, facilities)
   - Improve hotel review analysis
   - Add price trend monitoring

## Alternative Approaches Considered

1. **Custom Hotel MCP Server**
   - **Pros**: More control over functionality, potentially better performance
   - **Cons**: Significant development and maintenance overhead
   - **Decision**: Rejected in favor of using existing MCP servers

2. **Multiple Hotel Data Sources**
   - **Pros**: More comprehensive coverage, ability to compare prices
   - **Cons**: Additional complexity, higher API costs
   - **Decision**: Consider for future expansion after initial Booking.com integration

3. **Browser Automation**
   - **Pros**: Access to any hotel site
   - **Cons**: Brittle, higher maintenance, slower performance
   - **Decision**: Use only as fallback if API integrations fail

## Conclusion

The hotel search strategy focuses on leveraging existing MCP servers rather than building custom solutions. This approach balances speed of implementation with quality of results, while maintaining the extensibility to add more sources in the future.

We will initially integrate with the Apify Booking.com MCP server while maintaining our existing Airbnb integration, providing TripSage users with a comprehensive set of accommodation options.