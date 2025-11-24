/**
 * @fileoverview Upstash Redis caching utilities for JSON payloads.
 *
 * Returns null when Redis is unavailable or keys are missing.
 */

import { getRedis } from "@/lib/redis";

/**
 * Fetch a cached JSON payload from Upstash Redis.
 *
 * Retrieves and deserializes a JSON value from Redis. Returns null if Redis
 * is not configured, the key is missing, or deserialization fails.
 *
 * @param key - Redis key to fetch.
 * @returns Promise resolving to deserialized JSON value or null if not found/invalid.
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
 * Store a JSON payload in Upstash Redis with an optional TTL.
 *
 * Serializes the value to JSON and stores it in Redis. If TTL is provided
 * and positive, sets expiration. Skips if Redis is unavailable.
 *
 * @param key - Redis key to store the value under.
 * @param value - Value to serialize and cache (must be JSON-serializable).
 * @param ttlSeconds - Optional TTL in seconds (ignored if <= 0).
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
 * Delete a cached JSON payload from Upstash Redis.
 *
 * Removes the key from Redis cache. Skips if Redis is unavailable.
 *
 * @param key - Redis key to delete.
 */
export async function deleteCachedJson(key: string): Promise<void> {
  const redis = getRedis();
  if (!redis) return;
  await redis.del(key);
}

/**
 * Delete multiple cached JSON payloads from Upstash Redis.
 *
 * Removes multiple keys from Redis cache. Skips if Redis is unavailable.
 *
 * @param keys - Array of Redis keys to delete.
 * @returns Number of keys deleted.
 */
export async function deleteCachedJsonMany(keys: string[]): Promise<number> {
  const redis = getRedis();
  if (!redis) return 0;
  if (keys.length === 0) return 0;
  return await redis.del(...keys);
}
