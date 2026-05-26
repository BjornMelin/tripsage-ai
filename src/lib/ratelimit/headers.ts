/**
 * @fileoverview Helpers for attaching standard rate limit response headers.
 */

import { nowIso } from "@/lib/security/random";

export type RateLimitHeaderMeta = {
  limit?: number;
  remaining?: number;
  reset?: number;
  success?: boolean;
};

const MS_PER_SECOND = 1000;

/**
 * Normalize a Unix timestamp to milliseconds.
 *
 * Upstash Ratelimit (TS) documents `reset` as a Unix timestamp in milliseconds,
 * but some call sites/tests may provide seconds. This helper converts values
 * that look like Unix seconds (10-digit epoch seconds) to milliseconds.
 */
export function normalizeRateLimitResetToMs(reset: number): number {
  // Seconds since epoch are ~1_7xx_...; milliseconds are ~1_7xx_..._000.
  if (reset >= 1_000_000_000 && reset < 10_000_000_000) {
    return reset * 1000;
  }
  return reset;
}

function getCurrentEpochMs(currentIso = nowIso()): number {
  return Date.parse(currentIso);
}

export function computeRetryAfterSeconds(
  resetMs: number,
  nowMs: number = getCurrentEpochMs()
): number {
  return Math.max(0, Math.ceil((resetMs - nowMs) / MS_PER_SECOND));
}

/**
 * Create standardized HTTP rate limit headers (X-RateLimit-* + Retry-After).
 *
 * `reset` is expected to be a Unix timestamp in milliseconds.
 * `Retry-After` is only included when `success === false` and `reset` is present.
 */
export function createRateLimitHeaders(
  meta: RateLimitHeaderMeta,
  options?: { nowMs?: number }
): Record<string, string> {
  const headers: Record<string, string> = {};
  const resetMs =
    meta.reset === undefined ? undefined : normalizeRateLimitResetToMs(meta.reset);

  if (meta.limit !== undefined) headers["X-RateLimit-Limit"] = String(meta.limit);
  if (meta.remaining !== undefined)
    headers["X-RateLimit-Remaining"] = String(meta.remaining);
  if (resetMs !== undefined) headers["X-RateLimit-Reset"] = String(resetMs);

  if (meta.success === false && resetMs !== undefined) {
    headers["Retry-After"] = String(computeRetryAfterSeconds(resetMs, options?.nowMs));
  }

  return headers;
}

/**
 * Apply standardized rate limit headers to an existing Headers object.
 */
export function applyRateLimitHeaders(
  target: Headers,
  meta: RateLimitHeaderMeta,
  options?: { nowMs?: number }
): void {
  const headers = createRateLimitHeaders(meta, options);
  for (const [key, value] of Object.entries(headers)) {
    target.set(key, value);
  }
}
