/**
 * @fileoverview Higher-order function factory for Next.js route handlers.
 *
 * Wraps route handlers with authentication, rate limiting, error handling, and
 * telemetry. Per ADR-0029 and ADR-0032.
 */

import "server-only";

import type { User } from "@supabase/supabase-js";
import { Ratelimit } from "@upstash/ratelimit";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import {
  checkAuthentication,
  errorResponse,
  getTrustedRateLimitIdentifier,
  withRequestSpan,
} from "@/lib/next/route-helpers";
import { ROUTE_RATE_LIMITS, type RouteRateLimitKey } from "@/lib/ratelimit/routes";
import { getRedis } from "@/lib/redis";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerSupabase } from "@/lib/supabase/server";

/**
 * Configuration for route handler guards.
 */
export interface GuardsConfig {
  /** Whether authentication is required. Defaults to false. */
  auth?: boolean;
  /** Rate limit key from ROUTE_RATE_LIMITS registry. */
  rateLimit?: RouteRateLimitKey;
  /** Telemetry span name for observability. */
  telemetry?: string;
}

/**
 * Context injected into route handlers by the factory.
 */
export interface RouteContext {
  /** Supabase client instance. */
  supabase: TypedServerSupabase;
  /** Authenticated user, or null if auth disabled or unauthenticated. */
  user: User | null;
}

/**
 * Route handler function signature.
 *
 * Supports static routes (req only) and dynamic routes (req + route params).
 */
export type RouteHandler<_T = unknown> = (
  req: NextRequest,
  context: RouteContext,
  routeContext?: { params: Promise<Record<string, string>> }
) => Promise<Response> | Response;

/**
 * Retrieves rate limit configuration for a given key.
 *
 * @param key Rate limit key from registry.
 * @returns Configuration object or null if not found.
 */
function getRateLimitConfig(
  key: RouteRateLimitKey
): { limit: number; window: string } | null {
  return ROUTE_RATE_LIMITS[key] || null;
}

/**
 * Enforces rate limiting for a route.
 *
 * @param rateLimitKey Rate limit key from registry.
 * @param identifier User ID or IP address for rate limiting.
 * @returns Error response if limit exceeded, null otherwise.
 */
async function enforceRateLimit(
  rateLimitKey: RouteRateLimitKey,
  identifier: string
): Promise<NextResponse | null> {
  const config = getRateLimitConfig(rateLimitKey);
  if (!config) {
    console.warn(`Rate limit config not found for key: ${String(rateLimitKey)}`);
    return null; // Graceful degradation
  }

  const redis = getRedis();
  if (!redis) {
    return null; // Graceful degradation when Redis unavailable
  }

  try {
    const limiter = new Ratelimit({
      analytics: false,
      limiter: Ratelimit.slidingWindow(
        config.limit,
        config.window as Parameters<typeof Ratelimit.slidingWindow>[1]
      ),
      prefix: `ratelimit:route:${String(rateLimitKey)}`,
      redis,
    });

    const { success, remaining, reset } = await limiter.limit(identifier);
    if (!success) {
      return NextResponse.json(
        { error: "rate_limit_exceeded", reason: "Too many requests" },
        {
          headers: {
            "Retry-After": String(Math.ceil((reset - Date.now()) / 1000)),
            "X-RateLimit-Limit": String(config.limit),
            "X-RateLimit-Remaining": String(remaining),
            "X-RateLimit-Reset": String(reset),
          },
          status: 429,
        }
      );
    }
    return null;
  } catch (error) {
    console.error("Rate limit enforcement error", {
      error: error instanceof Error ? error.message : "Unknown error",
      key: String(rateLimitKey),
    });
    return null; // Graceful degradation on error
  }
}

/**
 * Wraps a route handler with authentication, rate limiting, error handling, and telemetry.
 *
 * @param config Guard configuration.
 * @returns Function that accepts a route handler and returns a guarded handler.
 *
 * @example
 * ```typescript
 * export const GET = withApiGuards({
 *   auth: true,
 *   rateLimit: "user-settings:get",
 *   telemetry: "user-settings.get",
 * })(async (req, { user, supabase }) => {
 *   const data = await fetchData(user!.id);
 *   return NextResponse.json(data);
 * });
 * ```
 */
export function withApiGuards<T = unknown>(
  config: GuardsConfig
): (
  handler: RouteHandler<T>
) => (
  req: NextRequest,
  routeContext?: { params: Promise<Record<string, string>> }
) => Promise<Response> {
  const { auth = false, rateLimit, telemetry } = config;

  // Validate rate limit key exists if provided
  if (rateLimit && !ROUTE_RATE_LIMITS[rateLimit]) {
    console.warn(`Rate limit key not found in registry: ${rateLimit}`);
  }

  return (handler: RouteHandler<T>) => {
    return async (
      req: NextRequest,
      routeContext?: { params: Promise<Record<string, string>> }
    ): Promise<Response> => {
      // Create Supabase client
      const supabase = await createServerSupabase();

      // Handle authentication if required
      let user: User | null = null;
      if (auth) {
        const authResult = await checkAuthentication(supabase);
        if (!authResult.isAuthenticated) {
          return NextResponse.json(
            { error: "unauthorized", reason: "Authentication required" },
            { status: 401 }
          );
        }
        user = authResult.user as User | null;
      }

      // Handle rate limiting if configured
      if (rateLimit) {
        const identifier = user?.id ?? getTrustedRateLimitIdentifier(req);
        const rateLimitError = await enforceRateLimit(rateLimit, identifier);
        if (rateLimitError) {
          return rateLimitError;
        }
      }

      // Execute handler with telemetry if configured
      const executeHandler = async () => {
        try {
          return await handler(req, { supabase, user }, routeContext);
        } catch (error) {
          return errorResponse({
            err: error,
            error: "internal",
            reason: "Internal server error",
            status: 500,
          });
        }
      };

      if (telemetry) {
        return await withRequestSpan(
          telemetry,
          {
            identifierType: user?.id ? "user" : "ip",
            method: req.method,
            route: req.nextUrl.pathname,
          },
          executeHandler
        );
      }

      return await executeHandler();
    };
  };
}
