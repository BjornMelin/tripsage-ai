/**
 * @fileoverview Rate limiting for webhook handlers.
 *
 * Uses Upstash Ratelimit with sliding window algorithm to protect against DoS
 * attacks and resource exhaustion. Configured for 100 requests per minute per IP.
 */

import "server-only";

import { Ratelimit } from "@upstash/ratelimit";
import { NextResponse } from "next/server";
import { getClientIpFromHeaders } from "@/lib/http/ip";
import { createRateLimitHeaders as createStandardRateLimitHeaders } from "@/lib/ratelimit/headers";
import { hashIdentifier } from "@/lib/ratelimit/identifier";
import { getRedis } from "@/lib/redis";
import { emitOperationalAlertOncePerWindow } from "@/lib/telemetry/degraded-mode";
import { warnRedisUnavailable } from "@/lib/telemetry/redis";
import { sanitizePathnameForTelemetry } from "@/lib/telemetry/route-key";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

const REDIS_FEATURE = "webhooks.rate_limit";

/**
 * Result of a rate limit check.
 */
export interface RateLimitResult {
  /** Whether the request is allowed */
  success: boolean;
  /** Why the check failed (only set when success === false) */
  reason?: "limiter_unavailable" | "rate_limited";
  /** Unix timestamp (ms) when the rate limit window resets */
  reset?: number;
  /** Number of requests remaining in the current window */
  remaining?: number;
  /** Maximum requests allowed in the window */
  limit?: number;
}

export type DegradedMode = "fail_closed" | "fail_open";

/**
 * Extract client IP address from request headers.
 *
 * Checks headers in order:
 * 1. X-Real-IP (Vercel canonical)
 * 2. X-Forwarded-For (first IP in comma-separated list)
 * 3. CF-Connecting-IP (Cloudflare)
 * 4. Fallback to "unknown" (logged for monitoring)
 *
 * @param req - The incoming request
 * @returns Client IP address string
 */
export function getClientIp(req: Request): string {
  const ip = getClientIpFromHeaders(req.headers);
  if (ip !== "unknown") return ip;

  // Log fallback when no IP headers are present (rate-limited via telemetry)
  const url = new URL(req.url);
  recordTelemetryEvent("webhook.ip_missing", {
    attributes: {
      "request.cf_connecting_ip_present": req.headers.has("cf-connecting-ip"),
      "request.method": req.method,
      "request.url": sanitizePathnameForTelemetry(url.pathname),
      "request.x_forwarded_for_present": req.headers.has("x-forwarded-for"),
      "request.x_real_ip_present": req.headers.has("x-real-ip"),
    },
    level: "warning",
  });

  // Single shared bucket to prevent UA rotation from bypassing rate limits
  return "unknown";
}

/**
 * Check rate limit for a webhook request.
 *
 * Defaults to fail-closed (returns 503) when Redis is unavailable to avoid
 * accepting unthrottled traffic. Use `checkWebhookRateLimitWithPolicy` with
 * `{ degradedMode: "fail_open" }` to allow processing during outages.
 *
 * @param req - The incoming request
 * @returns Rate limit check result
 */
export async function checkWebhookRateLimit(req: Request): Promise<RateLimitResult> {
  return await checkWebhookRateLimitWithPolicy(req, {});
}

export async function checkWebhookRateLimitWithPolicy(
  req: Request,
  options: { degradedMode?: DegradedMode } = {}
): Promise<RateLimitResult> {
  const degradedMode = options.degradedMode ?? "fail_closed";
  const route = sanitizePathnameForTelemetry(new URL(req.url).pathname);
  const redis = getRedis();
  if (!redis) {
    warnRedisUnavailable(REDIS_FEATURE);
    if (degradedMode === "fail_open") {
      emitOperationalAlertOncePerWindow({
        attributes: {
          degradedMode: "fail_open",
          feature: REDIS_FEATURE,
          reason: "redis_unavailable",
          route,
        },
        event: "ratelimit.degraded",
        windowMs: 60_000,
      });
      return { reason: "limiter_unavailable", success: true };
    }
    return { reason: "limiter_unavailable", success: false };
  }

  const rateLimiter = new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(100, "1 m"),
    prefix: "webhook:rl",
    redis,
  });

  const ip = getClientIp(req);
  const identifier = ip === "unknown" ? "ip:unknown" : `ip:${hashIdentifier(ip)}`;
  try {
    const { success, reset, remaining, limit, reason } =
      await rateLimiter.limit(identifier);
    if (reason === "timeout") {
      if (degradedMode === "fail_open") {
        emitOperationalAlertOncePerWindow({
          attributes: {
            degradedMode: "fail_open",
            feature: REDIS_FEATURE,
            reason: "timeout",
            route,
          },
          event: "ratelimit.degraded",
          windowMs: 60_000,
        });
        return { reason: "limiter_unavailable", success: true };
      }
      recordTelemetryEvent("webhook.rate_limit_timeout", {
        attributes: {
          feature: REDIS_FEATURE,
          route,
        },
        level: "error",
      });
      return { reason: "limiter_unavailable", success: false };
    }
    if (!success) return { limit, reason: "rate_limited", remaining, reset, success };
    return { limit, remaining, reset, success };
  } catch (error) {
    if (degradedMode === "fail_open") {
      emitOperationalAlertOncePerWindow({
        attributes: {
          degradedMode: "fail_open",
          feature: REDIS_FEATURE,
          reason: "enforcement_error",
          route,
        },
        event: "ratelimit.degraded",
        windowMs: 60_000,
      });
      return { reason: "limiter_unavailable", success: true };
    }
    recordTelemetryEvent("webhook.rate_limit_error", {
      attributes: {
        error: error instanceof Error ? error.message : "unknown_error",
        feature: REDIS_FEATURE,
        route,
      },
      level: "error",
    });
    return { reason: "limiter_unavailable", success: false };
  }
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
  return createStandardRateLimitHeaders(result);
}

/**
 * Response payload structure for webhook responses.
 */
interface WebhookResponsePayload {
  /** Response body (will be JSON-serialized) */
  body: Record<string, unknown>;
  /** HTTP status code (defaults to 200) */
  status?: number;
}

/**
 * Create a NextResponse with rate limit headers attached.
 *
 * This helper combines response creation and header attachment in a single call,
 * reducing boilerplate at call sites.
 *
 * @param rateLimitResult - Rate limit check result for headers
 * @param payload - Response body and optional status code
 * @returns NextResponse with rate limit headers attached
 *
 * @example
 * ```ts
 * return createWebhookResponse(rateLimitResult, {
 *   body: { code: "RATE_LIMITED", error: "rate_limit_exceeded" },
 *   status: 429,
 * });
 * ```
 */
export function createWebhookResponse(
  rateLimitResult: RateLimitResult,
  payload: WebhookResponsePayload
): NextResponse {
  const response = NextResponse.json(payload.body, {
    status: payload.status ?? 200,
  });
  const headers = createRateLimitHeaders(rateLimitResult);
  for (const [key, value] of Object.entries(headers)) {
    response.headers.set(key, value);
  }
  return response;
}
