/**
 * @fileoverview Upstash Redis client helper.
 * Uses the HTTP/REST client so it can run on Edge and Node runtimes.
 * Reads credentials from environment (Vercel integration recommended).
 */
import { Redis } from "@upstash/redis";
import { getServerEnvVarWithFallback } from "@/lib/env/server";

let redisSingleton: Redis | undefined;

/**
 * Returns a singleton Upstash Redis client if credentials are present.
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
