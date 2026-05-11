/**
 * @fileoverview Rate limiting for webhook handlers.
 */

import "server-only";

import { NextResponse } from "next/server";
import { getClientIpFromHeaders } from "@/lib/http/ip";
import { createRateLimitHeaders as createStandardRateLimitHeaders } from "@/lib/ratelimit/headers";
import { hashIdentifier } from "@/lib/ratelimit/identifier";
import { checkUpstashRateLimit, type DegradedMode } from "@/lib/ratelimit/upstash";
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
  /** Why the check failed, or why fail-open degraded mode allowed the request */
  reason?: "limiter_unavailable" | "rate_limited";
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

  const ip = getClientIp(req);
  const identifier = ip === "unknown" ? "ip:unknown" : `ip:${hashIdentifier(ip)}`;
  const result = await checkUpstashRateLimit({
    analytics: true,
    dynamicLimits: true,
    ephemeralCache: false,
    identifier,
    limit: 100,
    prefix: "webhook:rl",
    window: "1 m",
  });

  if (result.status === "unavailable") {
    if (result.reason === "redis_unavailable") {
      warnRedisUnavailable(REDIS_FEATURE);
    }
    if (degradedMode === "fail_open") {
      emitOperationalAlertOncePerWindow({
        attributes: {
          degradedMode: "fail_open",
          feature: REDIS_FEATURE,
          reason: result.reason,
          route,
        },
        event: "ratelimit.degraded",
        windowMs: 60_000,
      });
      return { reason: "limiter_unavailable", success: true };
    }

    if (result.reason === "timeout") {
      recordTelemetryEvent("webhook.rate_limit_timeout", {
        attributes: {
          feature: REDIS_FEATURE,
          route,
        },
        level: "error",
      });
    } else if (result.reason === "enforcement_error") {
      recordTelemetryEvent("webhook.rate_limit_error", {
        attributes: {
          error: result.error instanceof Error ? result.error.message : "unknown_error",
          feature: REDIS_FEATURE,
          route,
        },
        level: "error",
      });
    }
    return { reason: "limiter_unavailable", success: false };
  }

  if (result.status === "limited") {
    return {
      limit: result.result.limit,
      reason: "rate_limited",
      remaining: result.result.remaining,
      reset: result.result.reset,
      success: false,
    };
  }

  return {
    limit: result.result.limit,
    remaining: result.result.remaining,
    reset: result.result.reset,
    success: true,
  };
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
