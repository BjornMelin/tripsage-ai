/**
 * @fileoverview Canonical factory for AI SDK tools with guardrails.
 *
 * Provides a single entry point for creating AI tools that automatically
 * apply telemetry spans, optional rate limiting, and Redis caching. Inspired by
 * agent guardrails (lib/agents/guarded-tool.ts) but generalized for any tool.
 */

import "server-only";

import type { Span } from "@opentelemetry/api";
import { Ratelimit } from "@upstash/ratelimit";
import type { FlexibleSchema, Tool, ToolCallOptions } from "ai";
import { tool } from "ai";
import { getRedis } from "@/lib/redis";
import { type TelemetrySpanAttributes, withTelemetrySpan } from "@/lib/telemetry/span";
import { createToolError, type ToolErrorCode } from "@/lib/tools/errors";

type RateLimitWindow = Parameters<typeof Ratelimit.slidingWindow>[1];

type ToolExecute<InputValue, OutputValue> = (
  params: InputValue,
  context?: unknown
) => Promise<OutputValue>;

export type ToolOptions<InputValue, OutputValue> = {
  /** Unique tool identifier used for telemetry and cache namespacing. */
  name: string;
  /** Human-readable description passed to the model. */
  description: string;
  /** Schema accepted by AI SDK tools (supports Zod/Flexible schemas). */
  inputSchema: FlexibleSchema<InputValue>;
  /** Business logic implementation. */
  execute: ToolExecute<InputValue, OutputValue>;
};

export type TelemetryOptions<InputValue> = {
  /** Optional custom span name suffix (defaults to tool name). */
  name?: string;
  /** Attribute builder invoked before the span starts. */
  attributes?: (params: InputValue) => TelemetrySpanAttributes;
  /** Keys whose values should be redacted on the span. */
  redactKeys?: string[];
};

export type CacheHitMeta = {
  startedAt: number;
};

export type CacheOptions<InputValue, OutputValue> = {
  /** Function that produces a cache key suffix; returning undefined disables caching. */
  key: (params: InputValue) => string | undefined;
  /** Optional namespace prefix (defaults to `tool:${name}`). */
  namespace?: string;
  /** Serialize result before persistence. Returning undefined skips caching. */
  serialize?: (result: OutputValue, params: InputValue) => unknown;
  /** Deserialize cached payload back into the expected result shape. */
  deserialize?: (payload: unknown, params: InputValue) => OutputValue;
  /** Transform cached value before returning to caller (meta includes request start time). */
  onHit?: (cached: OutputValue, params: InputValue, meta: CacheHitMeta) => OutputValue;
  /** Decide whether a given request should bypass caching entirely. */
  shouldBypass?: (params: InputValue) => boolean;
  /** TTL seconds (number or function of (params, result)). */
  ttlSeconds?:
    | number
    | ((params: InputValue, result: OutputValue) => number | undefined);
};

export type RateLimitOptions<InputValue> = {
  /** Error code to emit when the limit is exceeded. */
  errorCode: ToolErrorCode;
  /** Build identifier (user/session/IP) for rate limiting. */
  identifier: (params: InputValue) => string | undefined | null;
  /** Sliding window limit. */
  limit: number;
  /** Sliding window duration string (e.g., "1 m"). */
  window: RateLimitWindow | string;
  /** Optional prefix override for limiter namespace. */
  prefix?: string;
};

export type GuardrailOptions<InputValue, OutputValue> = {
  cache?: CacheOptions<InputValue, OutputValue>;
  rateLimit?: RateLimitOptions<InputValue>;
  telemetry?: TelemetryOptions<InputValue>;
};

export type CreateAiToolOptions<InputValue, OutputValue> = ToolOptions<
  InputValue,
  OutputValue
> & {
  guardrails?: GuardrailOptions<InputValue, OutputValue>;
};

type CacheLookupResult<OutputValue> =
  | { hit: true; value: OutputValue }
  | { hit: false };

const rateLimiterCache = new Map<string, InstanceType<typeof Ratelimit>>();

/**
 * Canonical AI tool factory with optional guardrails.
 */
export function createAiTool<InputValue, OutputValue>(
  options: CreateAiToolOptions<InputValue, OutputValue>
) {
  const { guardrails } = options;
  const telemetryName = guardrails?.telemetry?.name ?? options.name;

  const toolDefinition = {
    description: options.description,
    execute: (params: InputValue, callOptions: ToolCallOptions) => {
      const startedAt = Date.now();
      return withTelemetrySpan(
        `tool.${telemetryName}`,
        {
          attributes: buildTelemetryAttributes(
            options.name,
            guardrails?.telemetry,
            params
          ),
          redactKeys: guardrails?.telemetry?.redactKeys,
        },
        async (span) => {
          if (guardrails?.rateLimit) {
            await enforceRateLimit(guardrails.rateLimit, options.name, params, span);
          }

          const cache = guardrails?.cache
            ? await readFromCache(
                guardrails.cache,
                options.name,
                params,
                span,
                startedAt
              )
            : null;

          if (cache?.hit) {
            span.setAttribute("tool.cache_hit", true);
            return cache.value;
          }

          span.setAttribute("tool.cache_hit", false);

          const result = await options.execute(params, callOptions);

          if (guardrails?.cache) {
            await writeToCache(guardrails.cache, options.name, params, result, span);
          }

          return result;
        }
      );
    },
    inputSchema: options.inputSchema,
  } as unknown as Tool<InputValue, OutputValue>;

  return tool(toolDefinition);
}

function buildTelemetryAttributes<InputValue>(
  toolName: string,
  telemetry: TelemetryOptions<InputValue> | undefined,
  params: InputValue
): TelemetrySpanAttributes {
  const base: TelemetrySpanAttributes = {
    "tool.name": toolName,
  };
  if (!telemetry?.attributes) {
    return base;
  }
  return {
    ...base,
    ...telemetry.attributes(params),
  };
}

async function readFromCache<InputValue, OutputValue>(
  cache: CacheOptions<InputValue, OutputValue>,
  toolName: string,
  params: InputValue,
  span: Span,
  startedAt: number
): Promise<CacheLookupResult<OutputValue>> {
  const redisKey = resolveCacheKey(cache, toolName, params);
  if (!redisKey) return { hit: false };

  const redis = getRedis();
  if (!redis) {
    span.addEvent("cache_skipped", { reason: "redis_unavailable" });
    return { hit: false };
  }

  try {
    const payload = await redis.get<string>(redisKey);
    if (!payload) return { hit: false };
    const parsed = JSON.parse(payload);
    const value = cache.deserialize
      ? cache.deserialize(parsed, params)
      : (parsed as OutputValue);
    const hydrated = cache.onHit ? cache.onHit(value, params, { startedAt }) : value;
    span.addEvent("cache_hit", { key: redisKey });
    return { hit: true, value: hydrated };
  } catch (error) {
    span.addEvent("cache_error", {
      key: redisKey,
      reason: error instanceof Error ? error.message : "unknown_error",
    });
    return { hit: false };
  }
}

async function writeToCache<InputValue, OutputValue>(
  cache: CacheOptions<InputValue, OutputValue>,
  toolName: string,
  params: InputValue,
  result: OutputValue,
  span: Span
): Promise<void> {
  const redisKey = resolveCacheKey(cache, toolName, params);
  if (!redisKey) return;

  const redis = getRedis();
  if (!redis) {
    span.addEvent("cache_skipped", { reason: "redis_unavailable" });
    return;
  }

  const payload = cache.serialize ? cache.serialize(result, params) : result;
  if (payload === undefined) return;

  const ttl =
    typeof cache.ttlSeconds === "function"
      ? cache.ttlSeconds(params, result)
      : cache.ttlSeconds;

  try {
    const serialized = JSON.stringify(payload);
    if (ttl && ttl > 0) {
      await redis.set(redisKey, serialized, { ex: Math.max(1, Math.floor(ttl)) });
    } else {
      await redis.set(redisKey, serialized);
    }
    span.addEvent("cache_write", { key: redisKey, ttl });
  } catch (error) {
    span.addEvent("cache_error", {
      key: redisKey,
      reason: error instanceof Error ? error.message : "unknown_error",
    });
  }
}

function resolveCacheKey<InputValue, OutputValue>(
  cache: CacheOptions<InputValue, OutputValue>,
  toolName: string,
  params: InputValue
): string | null {
  if (cache.shouldBypass?.(params)) {
    return null;
  }
  const suffix = cache.key(params);
  if (!suffix) return null;
  const namespace = cache.namespace ?? `tool:${toolName}`;
  return namespace ? `${namespace}:${suffix}` : suffix;
}

async function enforceRateLimit<InputValue>(
  config: RateLimitOptions<InputValue>,
  toolName: string,
  params: InputValue,
  span: Span
): Promise<void> {
  const identifier = config.identifier(params);
  if (!identifier) return;

  const redis = getRedis();
  if (!redis) {
    span.addEvent("ratelimit_skipped", { reason: "redis_unavailable" });
    return;
  }

  const limiterNamespace = config.prefix ?? `ratelimit:tool:${toolName}`;
  const limiterKey = `${limiterNamespace}:${config.limit}:${config.window}`;
  let limiter = rateLimiterCache.get(limiterKey);
  if (!limiter) {
    limiter = new Ratelimit({
      analytics: false,
      limiter: Ratelimit.slidingWindow(config.limit, config.window as RateLimitWindow),
      prefix: limiterNamespace,
      redis,
    });
    rateLimiterCache.set(limiterKey, limiter);
  }

  const { success, remaining, limit, reset } = await limiter.limit(identifier);
  if (success) return;

  span.addEvent("rate_limited", { identifier });
  const nowSeconds = Math.floor(Date.now() / 1000);
  const retryAfter = reset ? Math.max(0, reset - nowSeconds) : undefined;
  throw createToolError(config.errorCode, undefined, {
    identifier,
    limit,
    remaining,
    reset,
    retryAfter,
  });
}
