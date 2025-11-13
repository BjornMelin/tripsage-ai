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
import { Redis } from "@upstash/redis";
import { versionedKey, bumpTag } from "@/lib/cache/tags";

const redis = Redis.fromEnv();

// Write a value under the current trip namespace version
async function writeTripCache(tripId: string, data: unknown) {
  const key = await versionedKey("trip", `by-id:${tripId}`);
  await redis.set(key, JSON.stringify(data), { ex: 3600 });
}

// Read the current value
async function readTripCache(tripId: string) {
  const key = await versionedKey("trip", `by-id:${tripId}`);
  const val = await redis.get<string>(key);
  return val ? JSON.parse(val) : null;
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

## Gotchas

- Tag storms: if a single request bumps many tags, consider batching via `bumpTags()`.
- Version drift: versions are small integers; monitor increments and ensure you don’t bump excessively.
- Multi-tenant: include tenant identifiers in either the tag or the per-key suffix if isolation is needed.
