/**
 * @fileoverview Shared request-scoped rate limiter builder for BYOK key routes.
 */

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";

const RATELIMIT_PREFIX = "ratelimit:keys";

export type KeyRateLimiter = InstanceType<typeof Ratelimit>;
export type RateLimitResult = Awaited<ReturnType<KeyRateLimiter["limit"]>>;

/**
 * Builds a new Upstash rate limiter instance per request.
 *
 * Reading environment variables inside this function avoids module-scope state
 * so that tests and serverless runtimes stay isolated.
 *
 * @returns Rate limiter instance or undefined when Upstash is not configured.
 */
export function buildRateLimiter(): KeyRateLimiter | undefined {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) return undefined;
  return new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(10, "1 m"),
    prefix: RATELIMIT_PREFIX,
    redis: Redis.fromEnv(),
  });
}
