/**
 * @fileoverview Upstash Redis caching utilities for JSON payloads.
 */

import type { z } from "zod";
import { getRedis } from "@/lib/redis";
import { withTelemetrySpan } from "@/lib/telemetry/span";

type CacheTelemetryOptions = {
  namespace?: string;
};

/**
 * Derives a low-cardinality cache "namespace" from a Redis key.
 *
 * This intentionally avoids emitting full keys (which may include user IDs or
 * other high-cardinality data) into telemetry. We only emit the top-level
 * namespace segment (before the first `:`) because later segments may include
 * user-derived or high-cardinality identifiers.
 */
function deriveCacheNamespace(key: string): string {
  const separatorIndex = key.indexOf(":");
  if (separatorIndex <= 0) return "unknown";
  const candidate = key.slice(0, separatorIndex);
  // Only allow low-cardinality namespaces (avoid IDs, UUIDs, or user-provided prefixes).
  if (candidate.length > 32) return "unknown";
  if (!/^[a-z][a-z0-9_-]*$/i.test(candidate)) return "unknown";
  return candidate.toLowerCase();
}

/**
 * Result of a cache lookup with explicit status.
 * Allows callers to distinguish cache miss from corrupted data and unavailability.
 */
export type CacheResult<T> =
  | { status: "hit"; data: T }
  | { status: "miss" }
  | { status: "invalid"; raw: unknown }
  | { status: "unavailable" };

/**
 * Retrieves a cached JSON value from Upstash Redis.
 *
 * Deserializes the stored JSON string back to the specified type.
 * Returns `null` if Redis is unavailable, key doesn't exist, or
 * deserialization fails.
 *
 * @typeParam T - Expected type of the cached value.
 * @param key - Redis key to fetch.
 * @returns Deserialized value or `null` if not found/invalid.
 *
 * @example
 * ```ts
 * const trips = await getCachedJson<Trip[]>("user:123:trips");
 * ```
 */
export function getCachedJson<T>(
  key: string,
  options?: CacheTelemetryOptions
): Promise<T | null> {
  return withTelemetrySpan(
    "cache.get",
    {
      attributes: {
        "cache.key_length": key.length,
        "cache.namespace": options?.namespace ?? deriveCacheNamespace(key),
        "cache.operation": "get",
        "cache.system": "upstash",
      },
    },
    async (span) => {
      const redis = getRedis();
      if (!redis) {
        span.setAttribute("cache.status", "unavailable");
        return null;
      }

      // We store JSON strings via JSON.stringify(), so we need to parse them manually.
      // Upstash Redis only auto-deserializes when storing objects directly, not pre-stringified JSON.
      const raw = await redis.get<string>(key);
      if (raw === null) {
        span.setAttribute("cache.hit", false);
        return null;
      }

      try {
        span.setAttribute("cache.hit", true);
        return JSON.parse(raw) as T;
      } catch {
        // Invalid JSON - return null to indicate cache miss/invalid data
        span.setAttribute("cache.hit", false);
        span.setAttribute("cache.parse_error", true);
        return null;
      }
    }
  );
}

/**
 * Retrieves a cached JSON value with explicit status and optional schema validation.
 *
 * Unlike `getCachedJson`, this function returns a discriminated union that lets
 * callers distinguish between cache miss, valid hit, and corrupted/invalid data.
 * When a schema is provided, the cached data is validated against it.
 *
 * @typeParam T - Expected type of the cached value.
 * @param key - Redis key to fetch.
 * @param schema - Optional Zod schema to validate the cached data.
 * @returns CacheResult with status indicating hit, miss, or invalid.
 *
 * @example
 * ```ts
 * const result = await getCachedJsonSafe("config:123", configSchema);
 * if (result.status === "hit") {
 *   return result.data;
 * }
 * if (result.status === "invalid") {
 *   logger.warn("Invalid cached config", { raw: result.raw });
 * }
 * // Fetch fresh data...
 * ```
 */
export function getCachedJsonSafe<T>(
  key: string,
  schema?: z.ZodType<T>,
  options?: CacheTelemetryOptions
): Promise<CacheResult<T>> {
  return withTelemetrySpan(
    "cache.get_safe",
    {
      attributes: {
        "cache.has_schema": Boolean(schema),
        "cache.key_length": key.length,
        "cache.namespace": options?.namespace ?? deriveCacheNamespace(key),
        "cache.operation": "get",
        "cache.system": "upstash",
      },
    },
    async (span) => {
      const redis = getRedis();
      if (!redis) {
        span.setAttribute("cache.status", "unavailable");
        return { status: "unavailable" as const };
      }

      // We store JSON strings via JSON.stringify(), so we need to parse them manually.
      // Upstash Redis only auto-deserializes when storing objects directly, not pre-stringified JSON.
      const raw = await redis.get<string>(key);
      if (raw === null) {
        span.setAttribute("cache.status", "miss");
        return { status: "miss" as const };
      }

      let parsed: unknown;
      try {
        parsed = JSON.parse(raw);
      } catch {
        // Invalid JSON - return invalid status with raw string
        span.setAttribute("cache.status", "invalid");
        return { raw, status: "invalid" as const };
      }

      if (schema) {
        const result = schema.safeParse(parsed);
        if (!result.success) {
          span.setAttribute("cache.status", "invalid");
          span.setAttribute("cache.validation_failed", true);
          return { raw: parsed, status: "invalid" as const };
        }
        span.setAttribute("cache.status", "hit");
        return { data: result.data, status: "hit" as const };
      }

      span.setAttribute("cache.status", "hit");
      return { data: parsed as T, status: "hit" as const };
    }
  );
}

/**
 * Stores a JSON value in Upstash Redis with optional TTL.
 *
 * Serializes the value to JSON before storage. If `ttlSeconds` is
 * provided and positive, sets an expiration on the key.
 *
 * @param key - Redis key to store the value under.
 * @param value - Value to serialize and cache (must be JSON-serializable).
 * @param ttlSeconds - Optional TTL in seconds. Ignored if <= 0.
 *
 * @example
 * ```ts
 * // Cache for 5 minutes
 * await setCachedJson("user:123:trips", trips, 300);
 *
 * // Cache indefinitely
 * await setCachedJson("config:features", features);
 * ```
 */
export function setCachedJson(
  key: string,
  value: unknown,
  ttlSeconds?: number,
  options?: CacheTelemetryOptions
): Promise<void> {
  return withTelemetrySpan(
    "cache.set",
    {
      attributes: {
        "cache.key_length": key.length,
        "cache.namespace": options?.namespace ?? deriveCacheNamespace(key),
        "cache.operation": "set",
        "cache.system": "upstash",
        "cache.ttl_seconds": ttlSeconds ?? 0,
      },
    },
    async (span) => {
      const redis = getRedis();
      if (!redis) {
        span.setAttribute("cache.status", "unavailable");
        return;
      }

      const payload = JSON.stringify(value);
      span.setAttribute("cache.value_bytes", payload.length);
      if (ttlSeconds && ttlSeconds > 0) {
        await redis.set(key, payload, { ex: ttlSeconds });
        return;
      }
      await redis.set(key, payload);
    }
  );
}

/**
 * Deletes a cached JSON value from Upstash Redis.
 *
 * Use for cache invalidation when underlying data changes.
 * No-op if Redis is unavailable.
 *
 * @param key - Redis key to delete.
 *
 * @example
 * ```ts
 * // Invalidate after trip creation
 * await deleteCachedJson("user:123:trips");
 * ```
 */
export function deleteCachedJson(
  key: string,
  options?: CacheTelemetryOptions
): Promise<void> {
  return withTelemetrySpan(
    "cache.delete",
    {
      attributes: {
        "cache.key_length": key.length,
        "cache.namespace": options?.namespace ?? deriveCacheNamespace(key),
        "cache.operation": "delete",
        "cache.system": "upstash",
      },
    },
    async (span) => {
      const redis = getRedis();
      if (!redis) {
        span.setAttribute("cache.status", "unavailable");
        return;
      }
      const deleted = await redis.del(key);
      span.setAttribute("cache.deleted_count", deleted);
    }
  );
}

/**
 * Deletes multiple cached JSON values from Upstash Redis.
 *
 * Efficient batch deletion for invalidating related cache entries.
 * No-op if Redis is unavailable or keys array is empty.
 *
 * @param keys - Array of Redis keys to delete.
 * @returns Number of keys actually deleted, or 0 if Redis unavailable.
 *
 * @example
 * ```ts
 * // Invalidate all user caches on logout
 * const deleted = await deleteCachedJsonMany([
 *   "user:123:trips",
 *   "user:123:suggestions",
 *   "user:123:attachments"
 * ]);
 * ```
 */
export function deleteCachedJsonMany(
  keys: string[],
  options?: CacheTelemetryOptions
): Promise<number> {
  return withTelemetrySpan(
    "cache.delete_many",
    {
      attributes: {
        "cache.key_count": keys.length,
        "cache.namespace":
          options?.namespace ??
          (keys.length > 0 ? deriveCacheNamespace(keys[0]) : "unknown"),
        "cache.operation": "delete",
        "cache.system": "upstash",
      },
    },
    async (span) => {
      const redis = getRedis();
      if (!redis) {
        span.setAttribute("cache.status", "unavailable");
        return 0;
      }
      if (keys.length === 0) return 0;
      const deleted = await redis.del(...keys);
      span.setAttribute("cache.deleted_count", deleted);
      return deleted;
    }
  );
}

/**
 * Invalidates cache entries matching a user prefix pattern.
 *
 * Deletes the specified cache types for a user. Uses explicit key
 * construction rather than SCAN for predictability and safety.
 *
 * @param userId - User ID whose cache entries should be invalidated.
 * @param cacheTypes - Cache type prefixes to invalidate (e.g., ["trips", "suggestions"]).
 *
 * @example
 * ```ts
 * // Invalidate all trip-related caches for user
 * await invalidateUserCache("user-123", ["trips:list", "trips:suggestions"]);
 * ```
 */
export async function invalidateUserCache(
  userId: string,
  cacheTypes: string[]
): Promise<void> {
  const keys = cacheTypes.map((type) => `${type}:${userId}:all`);
  await deleteCachedJsonMany(keys);
}
