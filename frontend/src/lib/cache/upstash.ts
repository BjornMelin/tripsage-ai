/**
 * @fileoverview Upstash Redis caching utilities for JSON payloads.
 *
 * Provides type-safe helpers for caching JSON data in Upstash Redis.
 * All operations gracefully handle Redis unavailability (returns null/void).
 *
 * @example
 * ```ts
 * // Store data with 5-minute TTL
 * await setCachedJson("user:123:trips", trips, 300);
 *
 * // Retrieve cached data
 * const cached = await getCachedJson<Trip[]>("user:123:trips");
 * if (cached) return NextResponse.json(cached);
 *
 * // Invalidate on mutation
 * await deleteCachedJson("user:123:trips");
 * ```
 */

import { getRedis } from "@/lib/redis";

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
export async function getCachedJson<T>(key: string): Promise<T | null> {
  const redis = getRedis();
  if (!redis) return null;

  const raw = await redis.get<string>(key);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
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
export async function setCachedJson(
  key: string,
  value: unknown,
  ttlSeconds?: number
): Promise<void> {
  const redis = getRedis();
  if (!redis) return;

  const payload = JSON.stringify(value);
  if (ttlSeconds && ttlSeconds > 0) {
    await redis.set(key, payload, { ex: ttlSeconds });
    return;
  }
  await redis.set(key, payload);
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
export async function deleteCachedJson(key: string): Promise<void> {
  const redis = getRedis();
  if (!redis) return;
  await redis.del(key);
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
export async function deleteCachedJsonMany(keys: string[]): Promise<number> {
  const redis = getRedis();
  if (!redis) return 0;
  if (keys.length === 0) return 0;
  return await redis.del(...keys);
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
