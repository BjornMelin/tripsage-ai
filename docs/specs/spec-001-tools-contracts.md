# Spec-001: Tool Schemas and Execution Contracts

**Date:** 2025-11-11
**Version:** 1.0.0
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

## Execution Context & Approvals

- Types: `frontend/src/lib/tools/types.ts`
- Approvals: `frontend/src/lib/tools/approvals.ts`
