/**
 * @fileoverview Shared request-scoped rate limiter builder for BYOK key routes.
 */

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import { getServerEnvVar, getServerEnvVarWithFallback } from "@/lib/env/server";

const RATELIMIT_PREFIX = "ratelimit:keys";

export type KeyRateLimiter = InstanceType<typeof Ratelimit>;
export type RateLimitResult = Awaited<ReturnType<KeyRateLimiter["limit"]>>;

/**
 * Error thrown when rate limiter configuration is missing in production.
 */
export class RateLimiterConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "RateLimiterConfigurationError";
  }
}

/**
 * Builds a new Upstash rate limiter instance per request.
 *
 * Reading environment variables inside this function avoids module-scope state
 * so that tests and serverless runtimes stay isolated.
 *
 * In production, missing Upstash configuration causes a fatal error to enforce
 * fail-closed behavior. In development/test environments, returns undefined to
 * allow graceful degradation.
 *
 * @returns Rate limiter instance or undefined when Upstash is not configured
 *   (development/test only).
 * @throws {RateLimiterConfigurationError} When Upstash env vars are missing in
 *   production.
 */
export function buildRateLimiter(): KeyRateLimiter | undefined {
  const url = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_URL", undefined);
  const token = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_TOKEN", undefined);
  const isProduction = getServerEnvVar("NODE_ENV") === "production";

  if (!url || !token) {
    if (isProduction) {
      const errorMessage =
        "Rate limiter configuration missing: UPSTASH_REDIS_REST_URL and " +
        "UPSTASH_REDIS_REST_TOKEN must be set in production";
      console.error("/api/keys rate limiter configuration error:", {
        hasToken: Boolean(token),
        hasUrl: Boolean(url),
        message: errorMessage,
      });
      throw new RateLimiterConfigurationError(errorMessage);
    }
    // In development/test, allow graceful degradation
    return undefined;
  }

  return new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(10, "1 m"),
    prefix: RATELIMIT_PREFIX,
    redis: Redis.fromEnv(),
  });
}
