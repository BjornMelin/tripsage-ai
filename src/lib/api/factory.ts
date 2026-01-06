/**
 * @fileoverview Higher-order function factory for Next.js route handlers.
 */

import "server-only";

import type { AgentDependencies } from "@ai/agents/types";
import type { AgentConfig, AgentType } from "@schemas/configuration";
import type { User } from "@supabase/supabase-js";
import { Ratelimit } from "@upstash/ratelimit";
import type {
  Agent,
  FinishReason,
  LanguageModelResponseMetadata,
  LanguageModelUsage,
  ToolSet,
} from "ai";
import { cookies } from "next/headers";
import type { NextRequest, NextResponse } from "next/server";
import type { z } from "zod";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import {
  checkAuthentication,
  errorResponse,
  getTrustedRateLimitIdentifier,
  parseJsonBody,
  requireUserId,
  unauthorizedResponse,
  withRequestSpan,
} from "@/lib/api/route-helpers";
import { type ApiMetric, fireAndForgetMetric } from "@/lib/metrics/api-metrics";
import { applyRateLimitHeaders } from "@/lib/ratelimit/headers";
import { hashIdentifier, normalizeIdentifier } from "@/lib/ratelimit/identifier";
import { ROUTE_RATE_LIMITS, type RouteRateLimitKey } from "@/lib/ratelimit/routes";
import { getRedis } from "@/lib/redis";
import {
  assertHumanOrThrow,
  BOT_DETECTED_RESPONSE,
  isBotDetectedError,
} from "@/lib/security/botid";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerSupabase } from "@/lib/supabase/server";
import { emitOperationalAlertOncePerWindow } from "@/lib/telemetry/degraded-mode";
import { createServerLogger } from "@/lib/telemetry/logger";
import { sanitizePathnameForTelemetry } from "@/lib/telemetry/route-key";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const apiFactoryLogger = createServerLogger("api.factory");

export type DegradedMode = "fail_closed" | "fail_open";

async function hasAuthCredentials(req: NextRequest): Promise<boolean> {
  const authorization = req.headers.get("authorization");
  if (authorization?.trim()) return true;

  try {
    const cookieStore = await cookies();
    if (cookieStore.get("sb-access-token")?.value) return true;
    if (cookieStore.get("sb-refresh-token")?.value) return true;
  } catch {
    // If cookies() is unavailable (unexpected in Route Handlers), fall back to header checks.
  }

  return false;
}

/**
 * Configuration for route handler guards.
 */
export interface GuardsConfig<T extends z.ZodType = z.ZodType> {
  /** Whether authentication is required. Defaults to false. */
  auth?: boolean;
  /**
   * Enable BotID protection to block automated bots.
   * - true: Basic mode (free) - validates browser sessions
   * - "deep": Deep Analysis mode ($1/1000 calls) - Kasada-powered analysis
   * - { mode, allowVerifiedAiAssistants }: Advanced configuration
   *
   * Verified AI assistants (ChatGPT, Perplexity, Claude, etc.) are allowed
   * through by default but still subject to rate limiting. Set
   * allowVerifiedAiAssistants to false to block them on specific routes.
   *
   * @see https://vercel.com/docs/botid
   */
  botId?: BotIdGuardConfig;
  /** Rate limit key from ROUTE_RATE_LIMITS registry. */
  rateLimit?: RouteRateLimitKey;
  /**
   * Controls behavior when rate limiting infrastructure is unavailable.
   *
   * - fail_closed: deny the request when rate limiting can't be enforced
   * - fail_open: allow the request, but emit an operational alert
   */
  degradedMode?: DegradedMode;
  /** Telemetry span name for observability. */
  telemetry?: string;
  /** Optional Zod schema for request body validation. */
  schema?: T;
  /**
   * Override maximum JSON request body size (bytes) for schema parsing.
   *
   * Defaults to `API_CONSTANTS.maxBodySizeBytes` (64KB).
   */
  maxBodyBytes?: number;
}

export type BotIdGuardConfig =
  | boolean
  | "deep"
  | {
      mode: boolean | "deep";
      allowVerifiedAiAssistants?: boolean;
    };

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
  reason?: "timeout";
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

function parseRateLimitWindowMs(window: string): number | null {
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

/**
 * Determine the degraded mode for a rate limit key when Redis is unavailable.
 *
 * SECURITY: Cost-sensitive routes must fail_closed to prevent:
 * - Massive AI provider costs (OpenAI, Anthropic)
 * - Third-party API quota exhaustion (Amadeus, accommodations)
 * - Memory/data manipulation abuse
 *
 * Only read-only, low-cost routes should fail_open.
 */
function defaultDegradedModeForRateLimitKey(key: RouteRateLimitKey): DegradedMode {
  // Explicit high-cost routes
  if (key === "embeddings" || key === "ai:stream" || key === "telemetry:ai-demo") {
    return "fail_closed";
  }

  // Security-critical routes
  if (key.startsWith("auth:")) return "fail_closed";
  if (key.startsWith("keys:")) return "fail_closed";
  if (key.startsWith("agents:")) return "fail_closed";

  // AI/LLM routes - fail closed to prevent cost abuse
  if (key.startsWith("chat:")) return "fail_closed";
  if (key.startsWith("ai:")) return "fail_closed";

  // Travel API routes - fail closed to prevent third-party quota exhaustion
  if (key.startsWith("flights:")) return "fail_closed";
  if (key.startsWith("accommodations:")) return "fail_closed";
  if (key.startsWith("activities:")) return "fail_closed";

  // Data manipulation routes - fail closed to prevent abuse
  if (key.startsWith("memory:")) return "fail_closed";
  if (key.startsWith("trips:")) return "fail_closed";
  if (key.startsWith("calendar:")) return "fail_closed";

  // Read-only, low-cost routes can fail open
  return "fail_open";
}

function getSafeRouteKeyForTelemetry(options: {
  telemetry?: string;
  rateLimit?: RouteRateLimitKey;
  pathname: string;
}): string {
  if (options.telemetry) return options.telemetry;
  if (options.rateLimit) return options.rateLimit;
  return sanitizePathnameForTelemetry(options.pathname);
}

/**
 * Handles rate limit timeout by either failing closed (503) or failing open with an alert.
 *
 * @returns Response if should fail closed, null if failing open
 */
function handleRateLimitTimeout(
  rateLimitKey: RouteRateLimitKey,
  windowMs: number,
  degradedMode: DegradedMode
): NextResponse | null {
  if (degradedMode === "fail_closed") {
    return errorResponse({
      error: "rate_limit_unavailable",
      reason: "Rate limiting unavailable",
      status: 503,
    });
  }
  emitOperationalAlertOncePerWindow({
    attributes: {
      degradedMode: "fail_open",
      rateLimitKey,
      reason: "timeout",
    },
    event: "ratelimit.degraded",
    windowMs,
  });
  return null;
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
  identifier: string,
  options: { degradedMode: DegradedMode }
): Promise<NextResponse | null> {
  const config = getRateLimitConfig(rateLimitKey);
  if (!config) {
    apiFactoryLogger.warn("missing_rate_limit_config", {
      key: String(rateLimitKey),
    });
    if (options.degradedMode === "fail_closed") {
      return errorResponse({
        error: "rate_limit_unavailable",
        reason: "Rate limiting misconfigured",
        status: 503,
      });
    }
    emitOperationalAlertOncePerWindow({
      attributes: {
        degradedMode: "fail_open",
        rateLimitKey,
        reason: "missing_config",
      },
      event: "ratelimit.degraded",
      windowMs: 60_000,
    });
    return null;
  }

  const redis = getRedis();
  if (!redis && !rateLimitFactory) {
    if (options.degradedMode === "fail_closed") {
      return errorResponse({
        error: "rate_limit_unavailable",
        reason: "Rate limiting unavailable",
        status: 503,
      });
    }

    emitOperationalAlertOncePerWindow({
      attributes: {
        degradedMode: "fail_open",
        rateLimitKey,
        reason: "redis_unavailable",
      },
      event: "ratelimit.degraded",
      windowMs: parseRateLimitWindowMs(config.window) ?? 60_000,
    });
    return null;
  }

  try {
    if (rateLimitFactory) {
      const { success, remaining, reset, limit, reason } = await rateLimitFactory(
        rateLimitKey,
        identifier
      );
      if (reason === "timeout") {
        const windowMs = parseRateLimitWindowMs(config.window) ?? 60_000;
        return handleRateLimitTimeout(rateLimitKey, windowMs, options.degradedMode);
      }
      if (!success) {
        const response = errorResponse({
          error: "rate_limit_exceeded",
          reason: "Too many requests",
          status: 429,
        });
        applyRateLimitHeaders(response.headers, {
          limit,
          remaining,
          reset,
          success,
        });
        return response;
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

    const { success, remaining, reset, reason } = await limiter.limit(identifier);
    if (reason === "timeout") {
      const windowMs = parseRateLimitWindowMs(config.window) ?? 60_000;
      return handleRateLimitTimeout(rateLimitKey, windowMs, options.degradedMode);
    }
    if (!success) {
      const response = errorResponse({
        error: "rate_limit_exceeded",
        reason: "Too many requests",
        status: 429,
      });
      applyRateLimitHeaders(response.headers, {
        limit: config.limit,
        remaining,
        reset,
        success,
      });
      return response;
    }
    return null;
  } catch (error) {
    apiFactoryLogger.error("rate_limit_enforcement_error", {
      error: error instanceof Error ? error.message : "unknown_error",
      key: String(rateLimitKey),
    });
    if (options.degradedMode === "fail_closed") {
      return errorResponse({
        err: error,
        error: "rate_limit_unavailable",
        reason: "Rate limiting unavailable",
        status: 503,
      });
    }
    emitOperationalAlertOncePerWindow({
      attributes: {
        degradedMode: "fail_open",
        rateLimitKey,
        reason: "enforcement_error",
      },
      event: "ratelimit.degraded",
      windowMs: parseRateLimitWindowMs(config.window) ?? 60_000,
    });
    return null;
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
  const { auth = false, botId, rateLimit, telemetry, schema } = config;
  const botIdConfig: {
    mode: boolean | "deep";
    allowVerifiedAiAssistants: boolean;
  } | null = botId
    ? typeof botId === "object"
      ? {
          allowVerifiedAiAssistants: botId.allowVerifiedAiAssistants ?? true,
          mode: botId.mode,
        }
      : { allowVerifiedAiAssistants: true, mode: botId }
    : null;

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
      // Handle authentication if required
      let supabase: TypedServerSupabase | null = null;
      let user: User | null = null;
      if (auth) {
        // Fast-fail without hitting Supabase when no auth credentials are present.
        if (!(await hasAuthCredentials(req))) {
          return unauthorizedResponse();
        }
        supabase = await supabaseFactory();
        const authResult = await checkAuthentication(supabase);
        if (!authResult.isAuthenticated) {
          return unauthorizedResponse();
        }
        user = authResult.user as User | null;
      }

      // Handle BotID protection if configured (after auth, before rate limiting)
      // Bot traffic shouldn't count against rate limits
      if (botIdConfig?.mode) {
        try {
          await assertHumanOrThrow(
            getSafeRouteKeyForTelemetry({
              pathname: req.nextUrl.pathname,
              rateLimit,
              telemetry,
            }),
            {
              allowVerifiedAiAssistants: botIdConfig.allowVerifiedAiAssistants,
              level: botIdConfig.mode === "deep" ? "deep" : "basic",
            }
          );
        } catch (error) {
          if (isBotDetectedError(error)) {
            return errorResponse({
              ...BOT_DETECTED_RESPONSE,
              status: 403,
            });
          }
          throw error;
        }
      }

      // Handle rate limiting early so invalid payloads can't bypass throttling.
      if (rateLimit) {
        let identifier: string;
        if (user?.id) {
          identifier = `user:${hashIdentifier(normalizeIdentifier(user.id))}`;
        } else {
          const ipHash = getTrustedRateLimitIdentifier(req);
          identifier = ipHash === "unknown" ? "ip:unknown" : `ip:${ipHash}`;
        }
        const degradedMode =
          config.degradedMode ?? defaultDegradedModeForRateLimitKey(rateLimit);
        const rateLimitError = await enforceRateLimit(rateLimit, identifier, {
          degradedMode,
        });
        if (rateLimitError) {
          return rateLimitError;
        }
      }

      // Parse and validate request body (bounded) when a schema is configured.
      let validatedData: SchemaType extends z.ZodType ? z.infer<SchemaType> : unknown =
        undefined as SchemaType extends z.ZodType ? z.infer<SchemaType> : unknown;
      if (schema) {
        const parsed = await parseJsonBody(req, { maxBytes: config.maxBodyBytes });
        if (!parsed.ok) return parsed.error;

        const parseResult = schema.safeParse(parsed.data);
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
      }

      const routeKey = getSafeRouteKeyForTelemetry({
        pathname: req.nextUrl.pathname,
        rateLimit,
        telemetry,
      });

      // Execute handler with telemetry if configured
      const executeHandler = async () => {
        const startTime = process.hrtime.bigint();
        try {
          let supabaseClient = supabase;
          if (!supabaseClient) {
            supabaseClient = await supabaseFactory();
            supabase = supabaseClient;
          }
          const response = await handler(
            req,
            { supabase: supabaseClient, user },
            validatedData,
            routeContext
          );
          const durationMs = Number(process.hrtime.bigint() - startTime) / 1e6;

          // Record metric (fire-and-forget)
          fireAndForgetMetric({
            durationMs,
            endpoint: routeKey,
            method: req.method as ApiMetric["method"],
            rateLimitKey: rateLimit,
            statusCode: response.status,
          });

          return response;
        } catch (error) {
          const durationMs = Number(process.hrtime.bigint() - startTime) / 1e6;

          // Record error metric (fire-and-forget)
          fireAndForgetMetric({
            durationMs,
            endpoint: routeKey,
            errorType: error instanceof Error ? error.name : "UnknownError",
            method: req.method as ApiMetric["method"],
            rateLimitKey: rateLimit,
            statusCode: 500,
          });

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
            route: routeKey,
          },
          executeHandler
        );
      }

      return await executeHandler();
    };
  };
}

/**
 * Represents the output specification for an AI SDK Agent.
 *
 * This mirrors the AI SDK `Output<OUTPUT, PARTIAL>` interface. The `ai` package
 * exports `Output` as a runtime namespace (factory functions) rather than a
 * directly importable type, so we use a structural type compatible with the SDK.
 */
type AgentOutput<OutputType = unknown, PartialType = unknown> = {
  responseFormat: PromiseLike<
    { type: "text" } | { type: "json"; schema?: unknown } | undefined
  >;
  parseCompleteOutput: (
    options: { text: string },
    context: {
      response: LanguageModelResponseMetadata;
      usage: LanguageModelUsage;
      finishReason: FinishReason;
    }
  ) => Promise<OutputType>;
  parsePartialOutput: (options: {
    text: string;
  }) => Promise<{ partial: PartialType } | undefined>;
};

type AgentRouteFactoryResult<
  CallOptions = never,
  Tools extends ToolSet = Record<string, never>,
  OutputType extends AgentOutput = AgentOutput,
> = {
  agent: Agent<CallOptions, Tools, OutputType>;
  defaultMessages: unknown[];
};

type CreateAgentRouteOptions<
  SchemaType extends z.ZodType,
  CallOptions = never,
  Tools extends ToolSet = Record<string, never>,
  OutputType extends AgentOutput = AgentOutput,
> = {
  agentFactory: (
    deps: AgentDependencies,
    agentConfig: AgentConfig,
    input: z.infer<SchemaType>
  ) =>
    | AgentRouteFactoryResult<CallOptions, Tools, OutputType>
    | Promise<AgentRouteFactoryResult<CallOptions, Tools, OutputType>>;
  agentType: AgentType;
  botId?: BotIdGuardConfig;
  getModelHint?: (params: {
    agentConfig: AgentConfig;
    req: NextRequest;
  }) => string | undefined;
  rateLimit: RouteRateLimitKey;
  schema: SchemaType;
  telemetry: string;
};

/**
 * Creates a standardized POST route handler for AI ToolLoopAgent endpoints.
 *
 * Centralizes auth, request validation, agent config + provider resolution, and
 * AI SDK v6 streaming response creation so agent routes stay thin and consistent.
 */
export function createAgentRoute<
  SchemaType extends z.ZodType,
  CallOptions = never,
  Tools extends ToolSet = Record<string, never>,
  OutputType extends AgentOutput = AgentOutput,
>(
  options: CreateAgentRouteOptions<SchemaType, CallOptions, Tools, OutputType>
): (req: NextRequest, routeContext: RouteParamsContext) => Promise<Response> {
  return withApiGuards({
    auth: true,
    botId: options.botId,
    rateLimit: options.rateLimit,
    schema: options.schema,
    telemetry: options.telemetry,
  })(async (req, { user }, input) => {
    const userResult = requireUserId(user);
    if (!userResult.ok) return userResult.error;
    const userId = userResult.data;

    return await withTelemetrySpan(
      "agent.route",
      {
        attributes: {
          agentType: options.agentType,
          rateLimit: options.rateLimit,
          telemetry: options.telemetry,
        },
      },
      async (span) => {
        const resolvedConfig = await resolveAgentConfig(options.agentType);
        const agentConfig = resolvedConfig.config;

        const urlModel = req.nextUrl.searchParams.get("model") ?? undefined;
        const modelHint =
          options.getModelHint?.({ agentConfig, req }) ?? agentConfig.model ?? urlModel;

        const { resolveProvider } = await import("@ai/models/registry");
        const { model, modelId, provider } = await resolveProvider(userId, modelHint);
        span.setAttribute("modelId", modelId);
        span.setAttribute("provider", provider);

        const deps = {
          identifier: userId,
          model,
          modelId,
          userId,
        } satisfies AgentDependencies;

        const { agent, defaultMessages } = await options.agentFactory(
          deps,
          agentConfig,
          input
        );

        const { createAgentUIStreamResponse } = await import("ai");

        const { createErrorHandler } = await import("@/lib/agents/error-recovery");

        return createAgentUIStreamResponse({
          abortSignal: req.signal,
          agent,
          onError: createErrorHandler(),
          uiMessages: defaultMessages,
        });
      }
    );
  });
}
