# Cache Versioned Keys – Developer Recipe

This project uses versioned-tag cache keys to achieve O(1) invalidation.

## Key idea

- Every logical cache namespace (e.g. `trip`, `search`, `flight`) has a monotonically increasing version stored in Redis.
- Readers and writers compose keys as `namespace:v<version>:<key>`.
- Invalidation just bumps the namespace version; no key scans required.

## APIs

Use the helper in `frontend/src/lib/cache/tags.ts`:

- `getTagVersion(tag: string): Promise<number>` – read current version
- `versionedKey(tag: string, key: string): Promise<string>` – compose a versioned key
- `bumpTag(tag: string): Promise<number>` – increment a single tag version
- `bumpTags(tags: string[]): Promise<Record<string, number>>` – increment multiple

## Example

```ts
import { versionedKey, bumpTag } from "@/lib/cache/tags";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";

// Write a value under the current trip namespace version
async function writeTripCache(tripId: string, data: unknown) {
  const key = await versionedKey("trip", `by-id:${tripId}`);
  await setCachedJson(key, data, 3600); // 1 hour TTL
}

// Read the current value
async function readTripCache<T>(tripId: string): Promise<T | null> {
  const key = await versionedKey("trip", `by-id:${tripId}`);
  return await getCachedJson<T>(key);
}

// Invalidate all trip cache for writes to trips (DB triggers will also call the webhook)
async function invalidateTrips() {
  await bumpTag("trip");
}
```

## Where to invalidate

- DB changes → the `/api/hooks/cache` route bumps the relevant tags (via pg_net triggers).
- Application changes → call `bumpTag(s)` in write paths that modify derived views but do not trigger DB changes.

## Migration/rollout guidance

- Readers: adopt `versionedKey()` first. Old keys will naturally expire.
- Writers: dual-write (old + new) if you can’t afford cache misses during rollout. Remove old writes once readers ship.
- TTL: keep TTLs on values so legacy keys disappear even if not explicitly deleted.

## Tag Naming Conventions

Cache tags follow a hierarchical naming pattern: `<domain>:<resource>` or `<domain>:<operation>`.

### Current Tags

- `accommodations:search` - Accommodation search results
- `accommodations:booking` - Booking price checks
- `trip` - Trip data
- `user_trips` - User trip associations
- `trip_search` - Trip search results
- `search` - Generic search results
- `search_cache` - Search cache entries
- `flight` - Flight data
- `flight_search` - Flight search results
- `accommodation` - Accommodation details
- `hotel_search` - Hotel search results
- `memory` - Chat memory data
- `conversation` - Conversation data
- `chat_memory` - Chat memory cache
- `configuration` - Agent configuration cache

### Naming Guidelines

- Use lowercase with colons as separators
- Format: `<domain>:<resource>` or `<domain>:<operation>`
- Be specific: prefer `accommodations:search` over `search`
- Group related tags: use prefixes like `accommodations:*` for domain grouping

## Cache Dependency Graph

### Accommodations Domain

```text
accommodations:search
  └─ Invalidated by: booking creation (bumpTag in service.ts:421)
  └─ Used by: AccommodationSearchResult cache reads/writes

accommodations:booking
  └─ Invalidated by: booking price changes
  └─ Used by: CachedBookingPrice cache reads/writes
```

### Database-Driven Invalidation

The `/api/hooks/cache` route automatically invalidates tags based on database table changes:

- `trips` table → `["trip", "user_trips", "trip_search", "search", "search_cache"]`
- `flights` table → `["flight", "flight_search", "search", "search_cache"]`
- `accommodations` table → `["accommodation", "hotel_search", "search", "search_cache"]`
- `search_*` tables → `["search", "search_cache"]`
- `chat_messages` / `chat_sessions` → `["memory", "conversation", "chat_memory"]`

### Application-Level Invalidation

Some cache invalidation happens in application code:

- **Accommodations booking** (`accommodations/service.ts:421`): Bumps `accommodations:search` when a booking is created
- **Agent configuration** (`api/config/agents/*/route.ts`): Bumps `configuration` tag on config updates

## Real-World Example: Accommodations Service

The accommodations service demonstrates proper tag-based caching:

```ts
import { versionedKey, bumpTag } from "@/lib/cache/tags";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";

const CACHE_TAG_SEARCH = "accommodations:search";

// Read with versioned key
const versionedCacheKey = await versionedKey(CACHE_TAG_SEARCH, baseCacheKey);
const cached = await getCachedJson<AccommodationSearchResult>(versionedCacheKey);

// Write with versioned key
const cacheKey = await versionedKey(CACHE_TAG_SEARCH, baseCacheKey);
await setCachedJson(cacheKey, result, cacheTtlSeconds);

// Invalidate on write (e.g., after booking creation)
await bumpTag(CACHE_TAG_SEARCH);
```

## Gotchas

- Tag storms: if a single request bumps many tags, consider batching via `bumpTags()`.
- Version drift: versions are small integers; monitor increments and ensure you don't bump excessively.
- Multi-tenant: include tenant identifiers in either the tag or the per-key suffix if isolation is needed.
- Always use `versionedKey()` for reads and writes - never construct keys manually.
- When invalidating, bump tags instead of manually deleting keys for O(1) invalidation.
