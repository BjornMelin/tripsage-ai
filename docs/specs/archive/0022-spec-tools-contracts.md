# SPEC-0022: Tool Schemas and Execution Contracts

**Date:** 2025-11-11
**Version:** 1.0.0
**Status:** Superseded by [ADR-0044](../../architecture/decisions/adr-0044-ai-sdk-v6-tool-registry-and-mcp-integration.md) (AI SDK v6 Tool Registry and MCP Integration)

**Note:** This spec has been moved to `superseded/` as part of the 2025-01-XX specs audit. Tool contracts are now defined in [ADR-0044](../../architecture/decisions/adr-0044-ai-sdk-v6-tool-registry-and-mcp-integration.md) and implemented in `src/ai/tools/`.
**Category:** frontend
**Domain:** AI SDK v6

This spec documents the Zod schemas and expected outputs for the migrated tools.

## Web Search (Firecrawl)

- File: `src/ai/tools/server/web-search.ts`
- Input: `{ query: string (>=2), limit?: 1..10, fresh?: boolean }`
- Output: Firecrawl normalized JSON `{ results: Array<...> }`

## Web Crawl (Firecrawl)

- File: `src/ai/tools/server/web-crawl.ts`
- crawlUrl: `{ url: string, fresh?: boolean }` → extracted page JSON
- crawlSite: `{ url: string, maxPages?: 1..50, fresh?: boolean }` → crawl JSON

## Weather (OpenWeatherMap)

- File: `src/ai/tools/server/weather.ts`
- Input: `{ city: string, units?: 'metric'|'imperial' }`
- Output: `{ city, temp, description, humidity }`

## Flights (Duffel)

- File: `src/ai/tools/server/flights.ts`
- Input: `{ origin, destination, departureDate, returnDate?, passengers?, cabin?, currency? }`
- Output: `{ currency, offers: any[] }` (Duffel v2 offers)

## Maps (Google)

- File: `src/ai/tools/server/maps.ts`
- geocode: `{ address }` → geocoding results array
- distanceMatrix: `{ origins: string[], destinations: string[], units? }` →
  `{ origins, destinations, units, entries: [{ originIndex, destinationIndex, status, distanceMeters?, durationSeconds?, distanceText?, durationText? }] }`

## Accommodations (MCP/Proxy)

- File: `src/ai/tools/server/accommodations.ts`
- searchAccommodations: `{ location, checkin, checkout, guests, priceMin?, priceMax? }` → listing JSON via MCP/HTTP
- bookAccommodation: `{ listingId, checkin, checkout, guests, sessionId }` → `{ status, reference, ... }` with approval gate

## Memory (Supabase)

- File: `src/ai/tools/server/memory.ts`
- addConversationMemory: `{ content: string, category?: string }` → `{ id, createdAt }`
- searchUserMemories: `{ query: string, limit?: 1..20 }` → recent memory rows

## POI Lookup (Google Places)

- File: `src/ai/tools/server/google-places.ts`
- lookupPoiContext: `{ destination?: string, lat?: number, lon?: number, radiusMeters?: number, query?: string }` → `{ pois: Array<{placeId, name, lat, lon, types, rating, ...}>, provider: "googleplaces"|"stub" }`
- Uses Google Places API (New) Text Search with field masks for POI data
- Uses Google Maps Geocoding API for destination-based lookups with cached results (30-day max TTL per policy, key: `googleplaces:geocode:{normalizedDestination}`)
- Requires `GOOGLE_MAPS_SERVER_API_KEY` for Places and Geocoding APIs

## Planning (Redis)

- File: `src/ai/tools/server/planning.ts`
- createTravelPlan: `{ title, destinations, startDate, endDate, travelers, budget, preferences? }` → `{ planId, ... }`
- updateTravelPlan: `{ planId, ...partial }` → updated plan
- combineSearchResults: `{ planId, flights?, accommodations?, activities? }` → combined results
- saveTravelPlan: `{ planId }` → persisted plan
- deleteTravelPlan: `{ planId }` → deletion confirmation

## Execution Context & Approvals

- Types: `src/ai/tools/schemas/tools.ts`
- Approvals: `src/ai/tools/server/approvals.ts`
