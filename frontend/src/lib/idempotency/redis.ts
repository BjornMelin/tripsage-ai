/**
 * @fileoverview Simple Redis-based idempotency helpers using Upstash REST.
 */

import "server-only";

import { getRedis } from "@/lib/redis";
import { warnRedisUnavailable } from "@/lib/telemetry/redis";

const REDIS_FEATURE = "idempotency.keys";

/**
 * Attempt to reserve an idempotency key for ttl seconds.
 * Returns true if reserved (first occurrence), false if duplicate.
 */
export async function tryReserveKey(key: string, ttlSeconds = 300): Promise<boolean> {
  const redis = getRedis();
  if (!redis) {
    warnRedisUnavailable(REDIS_FEATURE);
    return true; // If Redis is unavailable, do not block processing.
  }
  const namespaced = `idemp:${key}`;
  const result = await redis.set(namespaced, "1", { ex: ttlSeconds, nx: true });
  return result === "OK";
}
