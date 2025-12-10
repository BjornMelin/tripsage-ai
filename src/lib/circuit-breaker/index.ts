/**
 * @fileoverview Circuit breaker pattern implementation using Upstash Redis.
 *
 * Prevents cascading failures during external service outages by:
 * - Tracking failure counts per service
 * - Opening circuit when threshold exceeded
 * - Allowing half-open probes after cooldown
 * - Auto-closing after successful probes
 *
 * @see https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker
 */

import "server-only";

import { getRedis } from "@/lib/redis";
import { recordTelemetryEvent, withTelemetrySpan } from "@/lib/telemetry/span";

// ===== TYPES =====

/**
 * Circuit breaker state.
 */
export type CircuitState = "closed" | "open" | "half-open";

/**
 * Configuration for a circuit breaker.
 */
export interface CircuitBreakerConfig {
  /** Service name for identification */
  name: string;
  /** Number of failures before opening circuit */
  failureThreshold?: number;
  /** Cooldown period in seconds before trying half-open */
  cooldownSeconds?: number;
  /** Number of successful probes needed to close circuit */
  successThreshold?: number;
  /** TTL for failure count in seconds */
  failureWindowSeconds?: number;
}

/**
 * Result of a circuit breaker check.
 */
export interface CircuitCheckResult {
  /** Whether the request should be allowed */
  allowed: boolean;
  /** Current circuit state */
  state: CircuitState;
  /** If not allowed, reason for rejection */
  reason?: string;
}

// ===== CONSTANTS =====

const REDIS_PREFIX = "circuit:";
const DEFAULT_FAILURE_THRESHOLD = 5;
const DEFAULT_COOLDOWN_SECONDS = 30;
const DEFAULT_SUCCESS_THRESHOLD = 2;
const DEFAULT_FAILURE_WINDOW_SECONDS = 60;

// ===== HELPERS =====

function getFailureCountKey(name: string): string {
  return `${REDIS_PREFIX}${name}:failures`;
}

function getOpenedAtKey(name: string): string {
  return `${REDIS_PREFIX}${name}:opened_at`;
}

function getSuccessCountKey(name: string): string {
  return `${REDIS_PREFIX}${name}:successes`;
}

// ===== CIRCUIT BREAKER =====

/**
 * Check if a request should be allowed through the circuit breaker.
 *
 * @param config - Circuit breaker configuration
 * @returns Whether the request is allowed and current state
 */
export async function checkCircuit(
  config: CircuitBreakerConfig
): Promise<CircuitCheckResult> {
  const redis = getRedis();

  // Fail open if Redis unavailable
  if (!redis) {
    return { allowed: true, state: "closed" };
  }

  const {
    name,
    failureThreshold = DEFAULT_FAILURE_THRESHOLD,
    cooldownSeconds = DEFAULT_COOLDOWN_SECONDS,
  } = config;

  const openedAtKey = getOpenedAtKey(name);

  // Check if circuit is open
  const openedAt = await redis.get(openedAtKey);

  if (openedAt) {
    const openedAtMs = parseInt(openedAt as string, 10);
    const elapsedSeconds = (Date.now() - openedAtMs) / 1000;

    if (elapsedSeconds < cooldownSeconds) {
      // Circuit is open, reject request
      const remaining = Math.ceil(cooldownSeconds - elapsedSeconds);
      return {
        allowed: false,
        reason: `Circuit open for ${name}, cooldown remaining: ${remaining}s`,
        state: "open",
      };
    }

    // Cooldown passed, allow half-open probe
    return { allowed: true, state: "half-open" };
  }

  // Check failure count
  const failureCountKey = getFailureCountKey(name);
  const failures = await redis.get(failureCountKey);
  const failureCount = failures ? parseInt(failures as string, 10) : 0;

  if (failureCount >= failureThreshold) {
    // Threshold exceeded, open circuit
    await redis.set(openedAtKey, Date.now().toString(), { ex: cooldownSeconds * 2 });

    recordTelemetryEvent("circuit_breaker.opened", {
      attributes: {
        "circuit.failure_count": failureCount,
        "circuit.name": name,
        "circuit.threshold": failureThreshold,
      },
      level: "error",
    });

    return {
      allowed: false,
      reason: `Circuit opened for ${name} after ${failureCount} failures`,
      state: "open",
    };
  }

  return { allowed: true, state: "closed" };
}

/**
 * Record a failure for a service.
 *
 * @param config - Circuit breaker configuration
 */
export async function recordFailure(
  config: Pick<CircuitBreakerConfig, "name" | "failureWindowSeconds">
): Promise<void> {
  const redis = getRedis();
  if (!redis) return;

  const { name, failureWindowSeconds = DEFAULT_FAILURE_WINDOW_SECONDS } = config;
  const failureCountKey = getFailureCountKey(name);

  // Increment failure count with TTL
  await redis.incr(failureCountKey);
  await redis.expire(failureCountKey, failureWindowSeconds);

  // Reset success count on failure
  const successCountKey = getSuccessCountKey(name);
  await redis.del(successCountKey);
}

/**
 * Record a success for a service.
 *
 * If in half-open state, may close the circuit after enough successes.
 *
 * @param config - Circuit breaker configuration
 */
export async function recordSuccess(
  config: Pick<CircuitBreakerConfig, "name" | "successThreshold">
): Promise<void> {
  const redis = getRedis();
  if (!redis) return;

  const { name, successThreshold = DEFAULT_SUCCESS_THRESHOLD } = config;

  const openedAtKey = getOpenedAtKey(name);
  const successCountKey = getSuccessCountKey(name);

  // Check if circuit was open (we're in half-open)
  const openedAt = await redis.get(openedAtKey);

  if (openedAt) {
    // In half-open state, track successes
    const successCount = await redis.incr(successCountKey);

    if (successCount >= successThreshold) {
      // Enough successes, close circuit
      await redis.del(openedAtKey);
      await redis.del(getFailureCountKey(name));
      await redis.del(successCountKey);

      recordTelemetryEvent("circuit_breaker.closed", {
        attributes: {
          "circuit.name": name,
          "circuit.success_count": successCount,
        },
        level: "info",
      });
    }
  } else {
    // Circuit was closed, just reset failure count on success
    await redis.del(getFailureCountKey(name));
  }
}

/**
 * Get the current state of a circuit breaker.
 *
 * @param name - Service name
 * @returns Current circuit state
 */
export async function getCircuitState(name: string): Promise<CircuitState> {
  const result = await checkCircuit({ name });
  return result.state;
}

/**
 * Manually reset a circuit breaker (for admin/recovery).
 *
 * @param name - Service name
 */
export async function resetCircuit(name: string): Promise<void> {
  const redis = getRedis();
  if (!redis) return;

  await redis.del(getOpenedAtKey(name));
  await redis.del(getFailureCountKey(name));
  await redis.del(getSuccessCountKey(name));

  recordTelemetryEvent("circuit_breaker.reset", {
    attributes: { "circuit.name": name },
    level: "info",
  });
}

/**
 * Execute a function with circuit breaker protection.
 *
 * @param config - Circuit breaker configuration
 * @param fn - Function to execute
 * @returns Function result or null if circuit is open
 */
export async function withCircuitBreaker<T>(
  config: CircuitBreakerConfig,
  fn: () => Promise<T>
): Promise<{ result: T | null; circuitOpen: boolean; state: CircuitState }> {
  return await withTelemetrySpan(
    `circuit_breaker.${config.name}`,
    { attributes: { "circuit.service": config.name } },
    async (span) => {
      const check = await checkCircuit(config);

      span.setAttribute("circuit.state", check.state);
      span.setAttribute("circuit.allowed", check.allowed);

      if (!check.allowed) {
        span.setAttribute("circuit.rejected", true);
        span.setAttribute("circuit.reason", check.reason ?? "unknown");
        return { circuitOpen: true, result: null, state: check.state };
      }

      try {
        const result = await fn();
        await recordSuccess(config);
        span.setAttribute("circuit.success", true);
        return { circuitOpen: false, result, state: check.state };
      } catch (error) {
        await recordFailure(config);
        span.setAttribute("circuit.failure", true);
        span.recordException(error as Error);
        throw error;
      }
    }
  );
}
