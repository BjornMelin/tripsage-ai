/**
 * @fileoverview Upstash Redis client helper.
 * Uses the HTTP/REST client so it can run on Edge and Node runtimes.
 * Reads credentials from environment (Vercel integration recommended).
 */
import { Redis } from "@upstash/redis";
import { getServerEnvVarWithFallback } from "@/lib/env/server";

let redisSingleton: Redis | undefined;

// Test injection point (follows factory.ts pattern)
let testRedisFactory: (() => Redis | undefined) | null = null;

/**
 * Override Redis client factory for tests.
 * Pass null to reset to production behavior.
 *
 * Also clears the cached singleton to force fresh client creation on the next
 * getRedis() call. This ensures test isolation—setting a new factory or null
 * will result in a fresh client from the new factory or production code.
 *
 * @example
 * ```ts
 * import { setRedisFactoryForTests } from "@/lib/redis";
 * import { RedisMockClient } from "@/test/upstash/redis-mock";
 *
 * setRedisFactoryForTests(() => new RedisMockClient() as unknown as Redis);
 *
 * // After tests
 * setRedisFactoryForTests(null);
 * ```
 */
export function setRedisFactoryForTests(
  factory: (() => Redis | undefined) | null
): void {
  testRedisFactory = factory;
  redisSingleton = undefined; // Clear cache to force factory usage
}

/**
 * Returns the Redis client for server code.
 * - Production path: returns a cached singleton (constructed once per process).
 * - Test path: if setRedisFactoryForTests() is configured, returns the factory
 *   result per call (may or may not be singleton depending on the factory).
 *
 * setRedisFactoryForTests() clears the cached singleton so the next call uses
 * the test factory or recreates the production client with fresh credentials.
 * @returns The Redis client or undefined if env is missing.
 */
export function getRedis(): Redis | undefined {
  // Test override takes precedence
  if (testRedisFactory) return testRedisFactory();

  if (redisSingleton) return redisSingleton;
  const url = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_URL", undefined);
  const token = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_TOKEN", undefined);
  if (!url || !token) return undefined;
  redisSingleton = new Redis({ token, url });
  return redisSingleton;
}

/**
 * Increment a counter by key with an optional TTL (seconds).
 * @param key Counter key
 * @param [ttlSeconds] Optional TTL in seconds to set after increment
 * @returns New counter value or null if redis unavailable
 */
export async function incrCounter(
  key: string,
  ttlSeconds?: number
): Promise<number | null> {
  const redis = getRedis();
  if (!redis) return null;
  const value = await redis.incr(key);
  if (ttlSeconds && ttlSeconds > 0) {
    await redis.expire(key, ttlSeconds);
  }
  return value;
}
