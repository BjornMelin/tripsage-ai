/**
 * @fileoverview Simple Redis-based idempotency helpers using Upstash REST.
 *
 * Implements configurable fail mode to control behavior when Redis
 * is unavailable:
 * - Fail open (default): Allow processing, may cause duplicates
 * - Fail closed: Throw error to prevent potential duplicate processing
 */

import "server-only";

import { getRedis } from "@/lib/redis";
import { warnRedisUnavailable } from "@/lib/telemetry/redis";

const REDIS_FEATURE = "idempotency.keys";

/**
 * Default fail mode from environment variable.
 * Set IDEMPOTENCY_FAIL_OPEN=false to fail closed (throw on Redis unavailable).
 */
const DEFAULT_FAIL_OPEN = process.env.IDEMPOTENCY_FAIL_OPEN !== "false";

/**
 * Error thrown when idempotency check fails due to Redis unavailability
 * and fail mode is "closed".
 */
export class IdempotencyServiceUnavailableError extends Error {
  constructor() {
    super("Idempotency service unavailable: Redis not configured");
    this.name = "IdempotencyServiceUnavailableError";
  }
}

/**
 * Options for reserving an idempotency key.
 */
export interface ReserveKeyOptions {
  /**
   * TTL for the idempotency key in seconds.
   * @default 300 (5 minutes)
   */
  ttlSeconds?: number;

  /**
   * Whether to fail open when Redis is unavailable.
   * - true (default): Return true (allow processing), log warning
   * - false: Throw IdempotencyServiceUnavailableError
   *
   * Can also be set globally via IDEMPOTENCY_FAIL_OPEN env var.
   */
  failOpen?: boolean;
}

/**
 * Attempt to reserve an idempotency key for a specified TTL.
 *
 * @param key - Unique key for this idempotent operation
 * @param ttlSecondsOrOptions - TTL in seconds (number) or options object
 * @returns true if reserved (first occurrence), false if duplicate
 * @throws IdempotencyServiceUnavailableError if Redis unavailable and failOpen=false
 *
 * @example
 * ```ts
 * // Basic usage (fail open by default)
 * const isUnique = await tryReserveKey("event:123", 300);
 *
 * // Fail closed for critical operations
 * const isUnique = await tryReserveKey("payment:456", { ttlSeconds: 600, failOpen: false });
 * ```
 */
export async function tryReserveKey(
  key: string,
  ttlSecondsOrOptions: number | ReserveKeyOptions = 300
): Promise<boolean> {
  // Parse options (backwards compatible with number-only signature)
  const options: ReserveKeyOptions =
    typeof ttlSecondsOrOptions === "number"
      ? { ttlSeconds: ttlSecondsOrOptions }
      : ttlSecondsOrOptions;

  const ttlSeconds = options.ttlSeconds ?? 300;
  const failOpen = options.failOpen ?? DEFAULT_FAIL_OPEN;

  const redis = getRedis();
  if (!redis) {
    warnRedisUnavailable(REDIS_FEATURE);

    if (!failOpen) {
      throw new IdempotencyServiceUnavailableError();
    }

    // Fail open: allow processing (may cause duplicates during Redis outage)
    return true;
  }

  const namespaced = `idemp:${key}`;
  const result = await redis.set(namespaced, "1", { ex: ttlSeconds, nx: true });
  return result === "OK";
}

/**
 * Check if an idempotency key exists without reserving it.
 *
 * @param key - Unique key to check
 * @returns true if key exists (is a duplicate), false if new
 */
export async function hasKey(key: string): Promise<boolean> {
  const redis = getRedis();
  if (!redis) {
    warnRedisUnavailable(REDIS_FEATURE);
    return false;
  }

  const namespaced = `idemp:${key}`;
  const result = await redis.exists(namespaced);
  return result > 0;
}

/**
 * Release an idempotency key (for rollback scenarios).
 *
 * @param key - Unique key to release
 * @returns true if key was released, false if not found or Redis unavailable
 */
export async function releaseKey(key: string): Promise<boolean> {
  const redis = getRedis();
  if (!redis) {
    warnRedisUnavailable(REDIS_FEATURE);
    return false;
  }

  const namespaced = `idemp:${key}`;
  const result = await redis.del(namespaced);
  return result > 0;
}
