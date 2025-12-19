/**
 * @fileoverview Simple Redis-based idempotency helpers using Upstash REST.
 *
 * Implements configurable fail mode to control behavior when Redis
 * is unavailable:
 * - Fail open (default): Allow processing, may cause duplicates
 * - Fail closed: Throw error to prevent potential duplicate processing
 */

import "server-only";

import { z } from "zod";

import { getRedis } from "@/lib/redis";
import { emitOperationalAlertOncePerWindow } from "@/lib/telemetry/degraded-mode";
import { warnRedisUnavailable } from "@/lib/telemetry/redis";

const REDIS_FEATURE = "idempotency.keys";

const idempotencyConfigSchema = z.strictObject({
  // biome-ignore lint/style/useNamingConvention: Env var casing is uppercase by convention
  IDEMPOTENCY_FAIL_OPEN: z.string().optional().default("true"),
});

/**
 * Default fail mode from environment variable.
 * Set IDEMPOTENCY_FAIL_OPEN=false to fail closed (throw on Redis unavailable).
 * Evaluated once at module load; pass `failOpen` option per call to override at runtime.
 */
const { IDEMPOTENCY_FAIL_OPEN } = idempotencyConfigSchema.parse({
  // biome-ignore lint/style/useNamingConvention: Env var casing is uppercase by convention
  IDEMPOTENCY_FAIL_OPEN: process.env.IDEMPOTENCY_FAIL_OPEN,
});
const DEFAULT_FAIL_OPEN = IDEMPOTENCY_FAIL_OPEN !== "false";

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
   * Can also be set globally via IDEMPOTENCY_FAIL_OPEN env var (read at module load).
   */
  failOpen?: boolean;

  /**
   * Alias for fail-open behavior with explicit naming.
   * When set, overrides failOpen.
   */
  degradedMode?: "fail_closed" | "fail_open";
}

function resolveDegradedMode(options: {
  degradedMode?: "fail_closed" | "fail_open";
  failOpen?: boolean;
}): "fail_closed" | "fail_open" {
  if (options.degradedMode) return options.degradedMode;
  if (options.failOpen === true) return "fail_open";
  if (options.failOpen === false) return "fail_closed";
  return DEFAULT_FAIL_OPEN ? "fail_open" : "fail_closed";
}

function getIdempotencyNamespace(key: string): string {
  const idx = key.indexOf(":");
  const namespace = idx === -1 ? key : key.slice(0, idx);
  return namespace.trim().slice(0, 64) || "unknown";
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
  const degradedMode = resolveDegradedMode(options);
  const failOpen = degradedMode === "fail_open";

  const redis = getRedis();
  if (!redis) {
    warnRedisUnavailable(REDIS_FEATURE);

    if (!failOpen) {
      throw new IdempotencyServiceUnavailableError();
    }

    emitOperationalAlertOncePerWindow({
      attributes: {
        degradedMode: "fail_open",
        namespace: getIdempotencyNamespace(key),
        reason: "redis_unavailable",
      },
      event: "idempotency.degraded",
      windowMs: 60_000,
    });

    // Fail open: allow processing (may cause duplicates during Redis outage)
    return true;
  }

  const namespaced = `idemp:${key}`;
  try {
    const result = await redis.set(namespaced, "1", { ex: ttlSeconds, nx: true });
    return result === "OK";
  } catch (error) {
    const errorName = error instanceof Error ? error.name : "UnknownError";
    const errorMessage = error instanceof Error ? error.message : String(error);
    warnRedisUnavailable(REDIS_FEATURE, { errorMessage, errorName });
    if (!failOpen) {
      throw new IdempotencyServiceUnavailableError();
    }
    emitOperationalAlertOncePerWindow({
      attributes: {
        degradedMode: "fail_open",
        errorMessage,
        errorName,
        namespace: getIdempotencyNamespace(key),
        reason: "redis_error",
      },
      event: "idempotency.degraded",
      windowMs: 60_000,
    });
    return true;
  }
}

/**
 * Check if an idempotency key exists without reserving it.
 *
 * Unlike `tryReserveKey`, this function returns a boolean even on Redis errors
 * rather than throwing `IdempotencyServiceUnavailableError`. This asymmetry
 * is intentional:
 *
 * - **hasKey** is for read-only duplicate detection where callers need a simple
 *   boolean answer. Return values map to fail modes:
 *   - `fail_closed` → returns `true` (treat as duplicate, deny processing)
 *   - `fail_open` → returns `false` (treat as new, allow processing)
 *
 * - **tryReserveKey** must atomically reserve the key or fail explicitly for
 *   strict lock-acquisition semantics. Throwing on `fail_closed` forces callers
 *   to handle the outage scenario rather than silently proceeding.
 *
 * Operational alerts are emitted on Redis errors, so callers can rely on
 * centralized logging/monitoring rather than catching exceptions.
 *
 * @param key - Unique key to check
 * @param options - Optional overrides for fail mode
 * @returns true if key exists (is a duplicate), false if new
 */
export async function hasKey(
  key: string,
  options?: Pick<ReserveKeyOptions, "degradedMode" | "failOpen">
): Promise<boolean> {
  const degradedMode = resolveDegradedMode(options ?? {});
  const failOpen = degradedMode === "fail_open";

  const redis = getRedis();
  if (!redis) {
    warnRedisUnavailable(REDIS_FEATURE);
    // Fail-open: allow processing (treat as not found)
    // Fail-closed: block processing by treating as duplicate
    return !failOpen;
  }

  const namespaced = `idemp:${key}`;
  try {
    const result = await redis.exists(namespaced);
    return result > 0;
  } catch (error) {
    const errorName = error instanceof Error ? error.name : "UnknownError";
    const errorMessage = error instanceof Error ? error.message : String(error);
    warnRedisUnavailable(REDIS_FEATURE, { errorMessage, errorName });
    if (!failOpen) {
      emitOperationalAlertOncePerWindow({
        attributes: {
          degradedMode: "fail_closed",
          errorMessage,
          errorName,
          namespace: getIdempotencyNamespace(key),
          reason: "redis_error",
        },
        event: "idempotency.degraded",
        windowMs: 60_000,
      });
      return true;
    }
    emitOperationalAlertOncePerWindow({
      attributes: {
        degradedMode: "fail_open",
        errorMessage,
        errorName,
        namespace: getIdempotencyNamespace(key),
        reason: "redis_error",
      },
      event: "idempotency.degraded",
      windowMs: 60_000,
    });
    return false;
  }
}

/**
 * Release an idempotency key (for rollback scenarios).
 *
 * @param key - Unique key to release
 * @param options - Optional overrides for fail mode
 * @returns true if key was released, false if not found or Redis unavailable
 */
export async function releaseKey(
  key: string,
  options?: Pick<ReserveKeyOptions, "degradedMode" | "failOpen">
): Promise<boolean> {
  const degradedMode = resolveDegradedMode(options ?? {});
  const failOpen = degradedMode === "fail_open";

  const redis = getRedis();
  if (!redis) {
    warnRedisUnavailable(REDIS_FEATURE);
    if (!failOpen) {
      throw new IdempotencyServiceUnavailableError();
    }
    return false;
  }

  const namespaced = `idemp:${key}`;
  try {
    const result = await redis.del(namespaced);
    return result > 0;
  } catch (error) {
    const errorName = error instanceof Error ? error.name : "UnknownError";
    const errorMessage = error instanceof Error ? error.message : String(error);
    warnRedisUnavailable(REDIS_FEATURE, { errorMessage, errorName });
    if (!failOpen) {
      throw new IdempotencyServiceUnavailableError();
    }
    emitOperationalAlertOncePerWindow({
      attributes: {
        degradedMode: "fail_open",
        errorMessage,
        errorName,
        namespace: getIdempotencyNamespace(key),
        reason: "redis_error",
      },
      event: "idempotency.degraded",
      windowMs: 60_000,
    });
    return false;
  }
}
