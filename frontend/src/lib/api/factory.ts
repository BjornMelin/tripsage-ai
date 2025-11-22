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
import type { z } from "zod";
import {
  checkAuthentication,
  errorResponse,
  getTrustedRateLimitIdentifier,
  parseJsonBody,
  withRequestSpan,
} from "@/lib/next/route-helpers";
import { ROUTE_RATE_LIMITS, type RouteRateLimitKey } from "@/lib/ratelimit/routes";
import { getRedis } from "@/lib/redis";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";

const apiFactoryLogger = createServerLogger("api.factory");

/**
 * Configuration for route handler guards.
 */
export interface GuardsConfig<T extends z.ZodType = z.ZodType> {
  /** Whether authentication is required. Defaults to false. */
  auth?: boolean;
  /** Rate limit key from ROUTE_RATE_LIMITS registry. */
  rateLimit?: RouteRateLimitKey;
  /** Telemetry span name for observability. */
  telemetry?: string;
  /** Optional Zod schema for request body validation. */
  schema?: T;
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
 * Next.js route params context. Always present per Next.js 16 route handler signature.
 */
export type RouteParamsContext = { params: Promise<Record<string, string>> };

type RateLimitResult = {
  limit: number;
  remaining: number;
  reset: number;
  success: boolean;
};

type RateLimitFactory = (
  key: RouteRateLimitKey,
  identifier: string
) => Promise<RateLimitResult>;

let rateLimitFactory: RateLimitFactory | null = null;
let supabaseFactory: () => Promise<TypedServerSupabase> = createServerSupabase;

// Test-only override to inject deterministic rate limiting behaviour.
export function setRateLimitFactoryForTests(factory: RateLimitFactory | null): void {
  rateLimitFactory = factory;
}

// Test-only override for Supabase factory to avoid Next.js request-store dependencies.
export function setSupabaseFactoryForTests(
  factory: (() => Promise<TypedServerSupabase>) | null
): void {
  supabaseFactory = factory ?? createServerSupabase;
}

/**
 * Route handler function signature.
 *
 * Supports static routes (req only) and dynamic routes (req + route params).
 * When a schema is provided in GuardsConfig, the handler receives validated
 * data as the third argument.
 */
export type RouteHandler<Data = unknown> = (
  req: NextRequest,
  context: RouteContext,
  data: Data,
  routeContext: RouteParamsContext
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
    apiFactoryLogger.warn("missing_rate_limit_config", {
      key: String(rateLimitKey),
    });
    return null; // Graceful degradation
  }

  const redis = getRedis();
  if (!redis && !rateLimitFactory) {
    return null; // Graceful degradation when Redis unavailable and no override set
  }

  try {
    if (rateLimitFactory) {
      const { success, remaining, reset, limit } = await rateLimitFactory(
        rateLimitKey,
        identifier
      );
      if (!success) {
        return NextResponse.json(
          { error: "rate_limit_exceeded", reason: "Too many requests" },
          {
            headers: {
              "Retry-After": String(Math.ceil((reset - Date.now()) / 1000)),
              "X-RateLimit-Limit": String(limit),
              "X-RateLimit-Remaining": String(remaining),
              "X-RateLimit-Reset": String(reset),
            },
            status: 429,
          }
        );
      }
      return null;
    }

    // At this point, rateLimitFactory is falsy, so redis must be defined
    if (!redis) {
      return null; // Should not reach here due to earlier check, but satisfy TypeScript
    }

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
    apiFactoryLogger.error("rate_limit_enforcement_error", {
      error: error instanceof Error ? error.message : "unknown_error",
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
 *
 * @example
 * ```typescript
 * export const POST = withApiGuards({
 *   auth: true,
 *   schema: RequestSchema,
 * })(async (req, { user }, body) => {
 *   // body is typed as z.infer<typeof RequestSchema>
 *   return NextResponse.json({ success: true });
 * });
 * ```
 */
export function withApiGuards<SchemaType extends z.ZodType>(
  config: GuardsConfig<SchemaType> & { schema: SchemaType }
): (
  handler: RouteHandler<z.infer<SchemaType>>
) => (req: NextRequest, routeContext: RouteParamsContext) => Promise<Response>;
export function withApiGuards(
  config: GuardsConfig
): (
  handler: RouteHandler<unknown>
) => (req: NextRequest, routeContext: RouteParamsContext) => Promise<Response>;
export function withApiGuards<SchemaType extends z.ZodType>(
  config: GuardsConfig<SchemaType>
): (
  handler: RouteHandler<SchemaType extends z.ZodType ? z.infer<SchemaType> : unknown>
) => (req: NextRequest, routeContext: RouteParamsContext) => Promise<Response> {
  const { auth = false, rateLimit, telemetry, schema } = config;

  // Validate rate limit key exists if provided
  if (rateLimit && !ROUTE_RATE_LIMITS[rateLimit]) {
    apiFactoryLogger.warn("unknown_rate_limit_key", { rateLimit });
  }

  return (
    handler: RouteHandler<SchemaType extends z.ZodType ? z.infer<SchemaType> : unknown>
  ) => {
    return async (
      req: NextRequest,
      routeContext: RouteParamsContext
    ): Promise<Response> => {
      // Create Supabase client
      const supabase = await supabaseFactory();

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

      // Parse and validate request body if schema is provided
      let validatedData: SchemaType extends z.ZodType ? z.infer<SchemaType> : unknown;
      if (schema) {
        const parsed = await parseJsonBody(req);
        if ("error" in parsed) {
          return parsed.error;
        }

        const parseResult = schema.safeParse(parsed.body);
        if (!parseResult.success) {
          return errorResponse({
            err: parseResult.error,
            error: "invalid_request",
            issues: parseResult.error.issues,
            reason: "Request validation failed",
            status: 400,
          });
        }
        validatedData = parseResult.data as SchemaType extends z.ZodType
          ? z.infer<SchemaType>
          : unknown;
      } else {
        validatedData = undefined as SchemaType extends z.ZodType
          ? z.infer<SchemaType>
          : unknown;
      }

      // Execute handler with telemetry if configured
      const executeHandler = async () => {
        try {
          return await handler(req, { supabase, user }, validatedData, routeContext);
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
