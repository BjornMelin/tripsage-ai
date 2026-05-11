/**
 * @fileoverview Shared Upstash Ratelimit construction and enforcement primitives.
 */

import "server-only";

import { Ratelimit } from "@upstash/ratelimit";
import { getRedis } from "@/lib/redis";

export type DegradedMode = "fail_closed" | "fail_open";

export type RateLimitWindow = Parameters<typeof Ratelimit.slidingWindow>[1];

export type UpstashRateLimitResult = {
  limit: number;
  reason?: "cacheBlock" | "denyList" | "timeout";
  remaining: number;
  reset: number;
  success: boolean;
};

export type UpstashRateLimitUnavailableReason =
  | "enforcement_error"
  | "redis_unavailable"
  | "timeout";

export type UpstashRateLimitCheck =
  | {
      status: "pass";
      result: UpstashRateLimitResult;
    }
  | {
      status: "limited";
      result: UpstashRateLimitResult;
    }
  | {
      status: "unavailable";
      reason: UpstashRateLimitUnavailableReason;
      error?: unknown;
      result?: UpstashRateLimitResult;
    };

export interface CheckUpstashRateLimitOptions {
  analytics?: boolean;
  dynamicLimits?: boolean;
  ephemeralCache?: Map<string, number> | false;
  identifier: string;
  limit: number;
  prefix: string;
  timeout?: number;
  window: RateLimitWindow | string;
}

type RatelimitInstance = InstanceType<typeof Ratelimit>;

const MAX_RATE_LIMITER_CACHE_SIZE = 128;
const rateLimiterCache = new Map<string, RatelimitInstance>();

export function parseRateLimitWindowMs(window: string): number | null {
  const parts = window.trim().split(/\s+/);
  if (parts.length !== 2) return null;
  const value = Number(parts[0]);
  const unit = parts[1];
  if (!Number.isFinite(value) || value <= 0) return null;
  const unitMs =
    unit === "ms"
      ? 1
      : unit === "s"
        ? 1000
        : unit === "m"
          ? 60_000
          : unit === "h"
            ? 3_600_000
            : unit === "d"
              ? 86_400_000
              : null;
  if (!unitMs) return null;
  return Math.floor(value * unitMs);
}

function getCacheKey(options: CheckUpstashRateLimitOptions): string {
  return [
    options.prefix,
    options.limit,
    options.window,
    options.analytics === true ? "analytics" : "no-analytics",
    options.dynamicLimits === true ? "dynamic" : "static",
    options.ephemeralCache === false ? "no-ephemeral" : "ephemeral",
    options.timeout ?? "default-timeout",
  ].join(":");
}

function rememberLimiter(key: string, limiter: RatelimitInstance): RatelimitInstance {
  if (rateLimiterCache.size >= MAX_RATE_LIMITER_CACHE_SIZE) {
    const oldestKey = rateLimiterCache.keys().next().value;
    if (oldestKey) {
      rateLimiterCache.delete(oldestKey);
    }
  }
  rateLimiterCache.set(key, limiter);
  return limiter;
}

function getRateLimiter(
  options: CheckUpstashRateLimitOptions
): RatelimitInstance | null {
  const redis = getRedis();
  if (!redis) return null;

  const key = getCacheKey(options);
  const cached = rateLimiterCache.get(key);
  if (cached) return cached;

  return rememberLimiter(
    key,
    new Ratelimit({
      analytics: options.analytics ?? false,
      dynamicLimits: options.dynamicLimits ?? true,
      ephemeralCache: options.ephemeralCache,
      limiter: Ratelimit.slidingWindow(
        options.limit,
        options.window as RateLimitWindow
      ),
      prefix: options.prefix,
      redis,
      timeout: options.timeout,
    })
  );
}

export async function checkUpstashRateLimit(
  options: CheckUpstashRateLimitOptions
): Promise<UpstashRateLimitCheck> {
  const limiter = getRateLimiter(options);
  if (!limiter) {
    return { reason: "redis_unavailable", status: "unavailable" };
  }

  try {
    const result = await limiter.limit(options.identifier);
    const normalizedResult: UpstashRateLimitResult = {
      limit: result.limit,
      reason: result.reason,
      remaining: result.remaining,
      reset: result.reset,
      success: result.success,
    };

    if (normalizedResult.reason === "timeout") {
      return {
        reason: "timeout",
        result: normalizedResult,
        status: "unavailable",
      };
    }

    return normalizedResult.success
      ? { result: normalizedResult, status: "pass" }
      : { result: normalizedResult, status: "limited" };
  } catch (error) {
    return { error, reason: "enforcement_error", status: "unavailable" };
  }
}

export function resetUpstashRateLimiterCacheForTests(): void {
  rateLimiterCache.clear();
}
