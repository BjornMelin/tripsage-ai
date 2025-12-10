/**
 * @fileoverview Rate limiting for webhook handlers.
 *
 * Uses Upstash Ratelimit with sliding window algorithm to protect against DoS
 * attacks and resource exhaustion. Configured for 100 requests per minute per IP.
 */

import "server-only";

import { Ratelimit } from "@upstash/ratelimit";
import { getRedis } from "@/lib/redis";
import { warnRedisUnavailable } from "@/lib/telemetry/redis";

const REDIS_FEATURE = "webhooks.rate_limit";

/**
 * Webhook rate limiter configuration.
 * - 100 requests per minute per IP address
 * - Sliding window algorithm for smooth traffic control
 * - Analytics enabled for monitoring in Upstash dashboard
 */
let webhookRateLimiter: Ratelimit | null = null;

function getWebhookRateLimiter(): Ratelimit | null {
  if (webhookRateLimiter) return webhookRateLimiter;

  const redis = getRedis();
  if (!redis) return null;

  webhookRateLimiter = new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(100, "1 m"),
    prefix: "webhook:rl",
    redis,
  });

  return webhookRateLimiter;
}

/**
 * Result of a rate limit check.
 */
export interface RateLimitResult {
  /** Whether the request is allowed */
  success: boolean;
  /** Unix timestamp (ms) when the rate limit window resets */
  reset?: number;
  /** Number of requests remaining in the current window */
  remaining?: number;
  /** Maximum requests allowed in the window */
  limit?: number;
}

/**
 * Extract client IP address from request headers.
 *
 * Checks headers in order:
 * 1. X-Forwarded-For (first IP in comma-separated list)
 * 2. CF-Connecting-IP (Cloudflare)
 * 3. Fallback to "unknown"
 *
 * @param req - The incoming request
 * @returns Client IP address string
 */
export function getClientIp(req: Request): string {
  const forwardedFor = req.headers.get("x-forwarded-for");
  if (forwardedFor) {
    return forwardedFor.split(",")[0]?.trim() ?? "unknown";
  }

  const cfIp = req.headers.get("cf-connecting-ip");
  if (cfIp) return cfIp;

  return "unknown";
}

/**
 * Check rate limit for a webhook request.
 *
 * If Redis is unavailable, fails open (allows request) with a warning.
 * This is intentional to avoid blocking legitimate traffic during Redis outages.
 *
 * @param req - The incoming request
 * @returns Rate limit check result
 */
export async function checkWebhookRateLimit(req: Request): Promise<RateLimitResult> {
  const rateLimiter = getWebhookRateLimiter();
  if (!rateLimiter) {
    warnRedisUnavailable(REDIS_FEATURE);
    // Fail open if Redis unavailable to not block legitimate traffic
    return { success: true };
  }

  const ip = getClientIp(req);
  const { success, reset, remaining, limit } = await rateLimiter.limit(ip);

  return { limit, remaining, reset, success };
}

/**
 * Create rate limit headers for HTTP response.
 *
 * @param result - Rate limit check result
 * @returns Headers object with rate limit information
 */
export function createRateLimitHeaders(
  result: RateLimitResult
): Record<string, string> {
  const headers: Record<string, string> = {};

  if (result.limit !== undefined) {
    headers["X-RateLimit-Limit"] = result.limit.toString();
  }
  if (result.remaining !== undefined) {
    headers["X-RateLimit-Remaining"] = result.remaining.toString();
  }
  if (result.reset !== undefined) {
    headers["X-RateLimit-Reset"] = result.reset.toString();
  }

  return headers;
}
