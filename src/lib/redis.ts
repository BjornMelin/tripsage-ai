/**
 * @fileoverview Upstash Redis REST client helper.
 */

import "server-only";

import { Redis } from "@upstash/redis";
import { getServerEnvVarWithFallback } from "@/lib/env/server";

let redisSingleton: Redis | undefined;

/**
 * Returns the Redis client for server code.
 *
 * Uses a cached singleton constructed once per process.
 * @returns The Redis client or undefined if env is missing.
 */
export function getRedis(): Redis | undefined {
  if (redisSingleton) return redisSingleton;
  const url = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_URL", undefined);
  const token = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_TOKEN", undefined);
  if (!url || !token) return undefined;
  redisSingleton = new Redis({ token, url });
  return redisSingleton;
}

/**
 * Increment a counter by key with an optional TTL (seconds).
 *
 * @param key - Counter key.
 * @param ttlSeconds - Optional TTL in seconds to set after increment.
 * @returns New counter value or null if redis unavailable.
 */
export async function incrCounter(
  key: string,
  ttlSeconds?: number
): Promise<number | null> {
  const redis = getRedis();
  if (!redis) return null;
  // Pipeline to reduce round trips on Redis REST (INCR + optional EXPIRE).
  if (ttlSeconds && ttlSeconds > 0) {
    const [value] = await redis
      .pipeline()
      .incr(key)
      .expire(key, ttlSeconds)
      .exec<[number, number]>();
    return value ?? null;
  }

  return await redis.incr(key);
}
