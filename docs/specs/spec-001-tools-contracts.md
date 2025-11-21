# Spec-001: Tool Schemas and Execution Contracts

**Date:** 2025-11-11
**Version:** 1.0.0
**Status:** Superseded by ADR-0044 (AI SDK v6 Tool Registry and MCP Integration)
**Category:** frontend
**Domain:** AI SDK v6

This spec documents the Zod schemas and expected outputs for the migrated tools.

## Web Search (Firecrawl)

- File: `frontend/src/lib/tools/web-search.ts`
- Input: `{ query: string (>=2), limit?: 1..10, fresh?: boolean }`
- Output: Firecrawl normalized JSON `{ results: Array<...> }`

## Web Crawl (Firecrawl)

- File: `frontend/src/lib/tools/web-crawl.ts`
- crawlUrl: `{ url: string, fresh?: boolean }` → extracted page JSON
- crawlSite: `{ url: string, maxPages?: 1..50, fresh?: boolean }` → crawl JSON

## Weather (OpenWeatherMap)

- File: `frontend/src/lib/tools/weather.ts`
- Input: `{ city: string, units?: 'metric'|'imperial' }`
- Output: `{ city, temp, description, humidity }`

## Flights (Duffel)

- File: `frontend/src/lib/tools/flights.ts`
- Input: `{ origin, destination, departureDate, returnDate?, passengers?, cabin?, currency? }`
- Output: `{ currency, offers: any[] }` (Duffel v2 offers)

## Maps (Google)

- File: `frontend/src/lib/tools/maps.ts`
- geocode: `{ address }` → Places array
- distanceMatrix: `{ origins: string[], destinations: string[], units? }` → Distance Matrix JSON

## Accommodations (MCP/Proxy)

- File: `frontend/src/lib/tools/accommodations.ts`
- searchAccommodations: `{ location, checkin, checkout, guests, priceMin?, priceMax? }` → listing JSON via MCP/HTTP
- bookAccommodation: `{ listingId, checkin, checkout, guests, sessionId }` → `{ status, reference, ... }` with approval gate

## Memory (Supabase)

- File: `frontend/src/lib/tools/memory.ts`
- addConversationMemory: `{ content: string, category?: string }` → `{ id, createdAt }`
- searchUserMemories: `{ query: string, limit?: 1..20 }` → recent memory rows

## POI Lookup (Google Places)

- File: `frontend/src/lib/tools/google-places.ts`
- lookupPoiContext: `{ destination?: string, lat?: number, lon?: number, radiusMeters?: number, query?: string }` → `{ pois: Array<{placeId, name, lat, lon, types, rating, ...}>, provider: "googleplaces"|"stub" }`
- Uses Google Places API (New) Text Search with field masks for POI data
- Uses Google Maps Geocoding API for destination-based lookups with cached results (30-day max TTL per policy, key: `googleplaces:geocode:{normalizedDestination}`)
- Requires `GOOGLE_MAPS_SERVER_API_KEY` for Places and Geocoding APIs

## Planning (Redis)

- File: `frontend/src/lib/tools/planning.ts`
- createTravelPlan: `{ title, destinations, startDate, endDate, travelers, budget, preferences? }` → `{ planId, ... }`
- updateTravelPlan: `{ planId, ...partial }` → updated plan
- combineSearchResults: `{ planId, flights?, accommodations?, activities? }` → combined results
- saveTravelPlan: `{ planId }` → persisted plan
- deleteTravelPlan: `{ planId }` → deletion confirmation

## Execution Context & Approvals

- Types: `frontend/src/lib/tools/types.ts`
- Approvals: `frontend/src/lib/tools/approvals.ts`
