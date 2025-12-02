/**
 * @fileoverview Canonical factory for AI SDK tools with guardrails.
 *
 * Provides a single entry point for creating AI tools that automatically
 * apply telemetry spans, optional rate limiting, and Redis caching. Inspired by
 * agent guardrails (lib/agents/guarded-tool.ts) but generalized for any tool.
 */

import "server-only";

import type { RateLimitResult } from "@ai/tools/schemas/tools";
import { rateLimitResultSchema } from "@ai/tools/schemas/tools";
import { createToolError, type ToolErrorCode } from "@ai/tools/server/errors";
import type { Span } from "@opentelemetry/api";
import type { AgentWorkflowKind } from "@schemas/agents";
import { Ratelimit } from "@upstash/ratelimit";
import type { FlexibleSchema, Tool, ToolCallOptions } from "ai";
import { asSchema, tool } from "ai";
import { headers } from "next/headers";
import { hashInputForCache } from "@/lib/cache/hash";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { getRedis } from "@/lib/redis";
import { type TelemetrySpanAttributes, withTelemetrySpan } from "@/lib/telemetry/span";

/**Maximum length for rate limit identifiers to prevent abuse. */
const MAX_RATE_LIMIT_IDENTIFIER_LENGTH = 128;

/** Type alias for rate limit window duration accepted by Upstash Ratelimit. */
type RateLimitWindow = Parameters<typeof Ratelimit.slidingWindow>[1];

/**
 * Signature for tool execution functions that receive validated input and call options.
 *
 * @template InputValue - The validated input type for the tool.
 * @template OutputValue - The output type returned by the tool.
 */
type ToolExecute<InputValue, OutputValue> = (
  params: InputValue,
  callOptions: ToolCallOptions
) => Promise<OutputValue>;

/** Transform function to convert tool output for model consumption. */
export type ToModelOutputFn<OutputValue> = (output: OutputValue) => unknown;

export type ToolOptions<InputValue, OutputValue> = {
  /** Unique tool identifier used for telemetry and cache namespacing. */
  name: string;
  /** Human-readable description passed to the model. */
  description: string;
  /** Schema accepted by AI SDK tools (supports Zod/Flexible schemas). */
  inputSchema: FlexibleSchema<InputValue>;
  /** Optional output schema for runtime validation of tool results. */
  outputSchema?: FlexibleSchema<OutputValue>;
  /** Business logic implementation. */
  execute: ToolExecute<InputValue, OutputValue>;
  /** Transform tool output for model consumption. */
  toModelOutput?: ToModelOutputFn<OutputValue>;
  /** Whether to validate output against outputSchema at runtime. Defaults to false. */
  validateOutput?: boolean;
};

export type TelemetryOptions<InputValue> = {
  /** Optional custom span name suffix (defaults to tool name). */
  name?: string;
  /** Attribute builder invoked before the span starts. */
  attributes?: (params: InputValue) => TelemetrySpanAttributes;
  /** Keys whose values should be redacted on the span. */
  redactKeys?: string[];
  /** Optional agent workflow identifier for workflow-specific telemetry. */
  workflow?: AgentWorkflowKind;
};

export type CacheHitMeta = {
  startedAt: number;
};

export type CacheOptions<InputValue, OutputValue> = {
  /** Function that produces a cache key suffix; returning undefined disables caching. */
  key: (params: InputValue) => string | undefined;
  /** Optional namespace prefix (defaults to `tool:${name}`). */
  namespace?: string;
  /** If true, hash the input using SHA-256 and append first 16 hex chars to key. */
  hashInput?: boolean;
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
  /** Optional identifier override using params and/or ToolCallOptions. */
  identifier?: (
    params: InputValue,
    callOptions?: ToolCallOptions
  ) => string | undefined | null;
  /** Sliding window limit. */
  limit: number;
  /** Sliding window duration string (e.g., "1 m"). */
  window: RateLimitWindow | string;
  /** Optional prefix override for limiter namespace. */
  prefix?: string;
};

/**
 * Configuration options for tool guardrails including caching, rate limiting, and telemetry.
 *
 * @template InputValue - The input type for the tool.
 * @template OutputValue - The output type for the tool.
 */
export type GuardrailOptions<InputValue, OutputValue> = {
  cache?: CacheOptions<InputValue, OutputValue>;
  rateLimit?: RateLimitOptions<InputValue>;
  telemetry?: TelemetryOptions<InputValue>;
};

/**
 * Complete configuration for creating an AI tool with optional guardrails.
 *
 * @template InputValue - The input type for the tool.
 * @template OutputValue - The output type for the tool.
 */
export type CreateAiToolOptions<InputValue, OutputValue> = ToolOptions<
  InputValue,
  OutputValue
> & {
  guardrails?: GuardrailOptions<InputValue, OutputValue>;
};

/**
 * Result of a cache lookup operation indicating whether a cached value was found.
 *
 * @template OutputValue - The cached value type.
 */
type CacheLookupResult<OutputValue> =
  | { hit: true; value: OutputValue }
  | { hit: false };

const rateLimiterCache = new Map<string, InstanceType<typeof Ratelimit>>();

/**
 * Creates an AI SDK v6 tool with optional guardrails (caching, rate limiting, telemetry).
 *
 * @template InputValue - Input schema type for the tool.
 * @template OutputValue - Output type returned by the tool.
 * @param options - Tool configuration including guardrails and output validation.
 * @returns AI SDK tool instance with guardrails applied.
 */
export function createAiTool<InputValue, OutputValue>(
  options: CreateAiToolOptions<InputValue, OutputValue>
): Tool<InputValue, OutputValue> {
  const { guardrails } = options;
  const telemetryName = guardrails?.telemetry?.name ?? options.name;

  // Build output validator if validation is requested
  const outputValidator =
    options.validateOutput && options.outputSchema
      ? buildOutputValidator(options.outputSchema, options.name)
      : null;

  // AI SDK v6 tool() cannot infer generics from object literals; safe assertion since structure matches.
  // biome-ignore lint/suspicious/noExplicitAny: Type assertion needed for AI SDK v6 tool() generic inference
  return (tool as any)({
    description: options.description,
    execute: (params: InputValue, callOptions: ToolCallOptions) => {
      const startedAt = Date.now();
      return withTelemetrySpan(
        `tool.${telemetryName}`,
        {
          attributes: {
            ...buildTelemetryAttributes(options.name, guardrails?.telemetry, params),
            ...(callOptions.toolCallId
              ? { "tool.call_id": callOptions.toolCallId }
              : {}),
            ...(guardrails?.telemetry?.workflow
              ? { "agent.workflow": guardrails.telemetry.workflow }
              : {}),
          },
          redactKeys: guardrails?.telemetry?.redactKeys,
        },
        async (span) => {
          if (guardrails?.rateLimit) {
            await enforceRateLimit(
              guardrails.rateLimit,
              options.name,
              params,
              callOptions,
              span
            );
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

          // Validate output if requested
          if (outputValidator) {
            const validation = await outputValidator(result);
            if (!validation.success) {
              span.addEvent("output_validation_failed", {
                error: validation.error,
              });
              // Using "invalid_params" with validationType metadata to distinguish output errors
              // Consider adding "invalid_output" to ToolErrorCode if this pattern is common
              throw createToolError("invalid_params", validation.error, {
                tool: options.name,
                validationType: "output",
              });
            }
          }

          if (guardrails?.cache) {
            await writeToCache(guardrails.cache, options.name, params, result, span);
          }

          return result;
        }
      );
    },
    inputSchema: options.inputSchema as FlexibleSchema<InputValue>,
    ...(options.outputSchema
      ? { outputSchema: options.outputSchema as FlexibleSchema<OutputValue> }
      : {}),
    ...(options.toModelOutput ? { toModelOutput: options.toModelOutput } : {}),
  }) as Tool<InputValue, OutputValue>;
}

/**
 * Builds an output validator function from a FlexibleSchema.
 *
 * Uses AI SDK's asSchema to convert the schema for validation.
 *
 * @template OutputValue - Output type to validate.
 * @param schema - Flexible schema for validation.
 * @param toolName - Tool name for error messages.
 * @returns Async validator function.
 */
function buildOutputValidator<OutputValue>(
  schema: FlexibleSchema<OutputValue>,
  toolName: string
): (output: unknown) => Promise<{ success: true } | { success: false; error: string }> {
  const convertedSchema = asSchema(schema);

  return async (output: unknown) => {
    if (!convertedSchema?.validate) {
      // Schema doesn't support validation, consider it valid
      return { success: true };
    }

    try {
      const result = await convertedSchema.validate(output);
      if (result.success) {
        return { success: true };
      }
      return {
        error: `Output validation failed for ${toolName}: ${result.error.message}`,
        success: false,
      };
    } catch (error) {
      return {
        error: `Output validation error for ${toolName}: ${error instanceof Error ? error.message : "Unknown error"}`,
        success: false,
      };
    }
  };
}

/**
 * Builds telemetry attributes for an OpenTelemetry span.
 *
 * Combines base tool attributes with custom attributes from telemetry configuration.
 *
 * @template InputValue - Input type for the tool.
 * @param toolName - Name of the tool being executed.
 * @param telemetry - Optional telemetry configuration.
 * @param params - Input parameters for attribute generation.
 * @returns Attributes object for the telemetry span.
 */
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

/**
 * Attempts to read a cached result from Redis.
 *
 * Resolves cache key, checks for cached data, applies deserialization if configured.
 * Records cache events and handles Redis/deserialization errors gracefully.
 *
 * @template InputValue - Input type for the tool.
 * @template OutputValue - Output type for the tool.
 * @param cache - Cache configuration options.
 * @param toolName - Tool name for key namespacing.
 * @param params - Input parameters for key resolution and deserialization.
 * @param span - OpenTelemetry span for event recording.
 * @param startedAt - Request start timestamp for cache hit metadata.
 * @returns Cache lookup result with hit status and value if found.
 */
async function readFromCache<InputValue, OutputValue>(
  cache: CacheOptions<InputValue, OutputValue>,
  toolName: string,
  params: InputValue,
  span: Span,
  startedAt: number
): Promise<CacheLookupResult<OutputValue>> {
  const redisKey = resolveCacheKey(cache, toolName, params);
  if (!redisKey) return { hit: false };

  try {
    const cached = await getCachedJson<OutputValue>(redisKey);
    if (!cached) return { hit: false };

    // Apply deserialization if provided
    const value = cache.deserialize ? cache.deserialize(cached, params) : cached;

    // Apply onHit transformation if provided
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

/**
 * Writes a tool execution result to Redis cache.
 *
 * Resolves cache key, applies serialization if configured, stores result with TTL.
 * Records cache events and handles Redis/serialization errors gracefully.
 *
 * @template InputValue - Input type for the tool.
 * @template OutputValue - Output type for the tool.
 * @param cache - Cache configuration options.
 * @param toolName - Tool name for key namespacing.
 * @param params - Input parameters for key resolution and serialization.
 * @param result - Execution result to cache.
 * @param span - OpenTelemetry span for event recording.
 */
async function writeToCache<InputValue, OutputValue>(
  cache: CacheOptions<InputValue, OutputValue>,
  toolName: string,
  params: InputValue,
  result: OutputValue,
  span: Span
): Promise<void> {
  const redisKey = resolveCacheKey(cache, toolName, params);
  if (!redisKey) return;

  const payload = cache.serialize ? cache.serialize(result, params) : result;
  if (payload === undefined) return;

  const ttl =
    typeof cache.ttlSeconds === "function"
      ? cache.ttlSeconds(params, result)
      : cache.ttlSeconds;

  try {
    // Use existing helper which handles Redis unavailability gracefully
    await setCachedJson(
      redisKey,
      payload,
      ttl ? Math.max(1, Math.floor(ttl)) : undefined
    );
    span.addEvent("cache_write", { key: redisKey, ttl });
  } catch (error) {
    span.addEvent("cache_error", {
      key: redisKey,
      reason: error instanceof Error ? error.message : "unknown_error",
    });
  }
}

/**
 * Resolves the full Redis cache key from cache configuration and parameters.
 *
 * Applies bypass logic, key generation, input hashing if enabled, and namespacing.
 *
 * @template InputValue - Input type for the tool.
 * @template OutputValue - Output type for the tool.
 * @param cache - Cache configuration options.
 * @param toolName - Tool name for default namespacing.
 * @param params - Input parameters for key generation.
 * @returns Full Redis key string or null if caching is bypassed.
 */
function resolveCacheKey<InputValue, OutputValue>(
  cache: CacheOptions<InputValue, OutputValue>,
  toolName: string,
  params: InputValue
): string | null {
  if (cache.shouldBypass?.(params)) {
    return null;
  }
  let suffix = cache.key(params);
  if (!suffix) return null;

  // Apply SHA-256 hashing if enabled
  if (cache.hashInput) {
    const hash = hashInputForCache(params);
    suffix = `${suffix}:${hash}`;
  }

  const namespace = cache.namespace ?? `tool:${toolName}`;
  return namespace ? `${namespace}:${suffix}` : suffix;
}

/**
 * Enforces rate limiting using Upstash Ratelimit.
 *
 * Resolves identifier, creates cached limiter instance, checks limit, throws if exceeded.
 * Records events and handles Redis unavailability gracefully.
 *
 * @template InputValue - Input type for the tool.
 * @param config - Rate limit configuration options.
 * @param toolName - Tool name for limiter namespacing.
 * @param params - Input parameters for identifier resolution.
 * @param callOptions - Tool call options for identifier resolution.
 * @param span - OpenTelemetry span for event recording.
 * @throws {ToolError} When rate limit is exceeded.
 */
async function enforceRateLimit<InputValue>(
  config: RateLimitOptions<InputValue>,
  toolName: string,
  params: InputValue,
  callOptions: ToolCallOptions,
  span: Span
): Promise<void> {
  const identifier =
    sanitizeRateLimitIdentifier(config.identifier?.(params, callOptions)) ??
    (await getRateLimitIdentifier());

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

  const result = await limiter.limit(identifier);
  // Validate rate limit result structure using schema
  const validatedResult: RateLimitResult = rateLimitResultSchema.parse({
    limit: result.limit,
    remaining: result.remaining,
    reset: result.reset,
    success: result.success,
  });

  if (validatedResult.success) return;

  span.addEvent("rate_limited", { identifier });
  const nowSeconds = Math.floor(Date.now() / 1000);
  const retryAfter = validatedResult.reset
    ? Math.max(0, validatedResult.reset - nowSeconds)
    : undefined;
  throw createToolError(config.errorCode, undefined, {
    identifier,
    limit: validatedResult.limit,
    remaining: validatedResult.remaining,
    reset: validatedResult.reset,
    retryAfter,
  });
}

/**
 * Sanitizes a rate limit identifier by trimming whitespace and validating length.
 *
 * Returns undefined if the identifier is null, undefined, or empty after trimming.
 *
 * @param identifier - Raw identifier string from configuration or headers.
 * @returns Sanitized identifier or undefined if invalid.
 */
function sanitizeRateLimitIdentifier(identifier?: string | null): string | undefined {
  if (typeof identifier !== "string") {
    return undefined;
  }

  const trimmed = identifier.trim();
  if (trimmed.length === 0) {
    return undefined;
  }
  if (trimmed.length > MAX_RATE_LIMIT_IDENTIFIER_LENGTH) {
    // Truncate overly long identifiers
    return trimmed.slice(0, MAX_RATE_LIMIT_IDENTIFIER_LENGTH);
  }
  return trimmed;
}

/**
 * Validates if a string is a valid IPv4 or IPv6 address.
 *
 * @param ip - String to validate as IP address
 * @returns True if valid IPv4 or IPv6 format, false otherwise
 */
function isValidIpAddress(ip: string): boolean {
  // IPv4 regex: 4 octets (0-255) separated by dots
  const ipv4Regex =
    /^(?:(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)$/;

  // IPv6 regex: supports full, compressed, and IPv4-mapped forms
  const ipv6Regex =
    /^(?:(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})|:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]+|::(?:ffff(?::0{1,4})?:)?(?:(?:25[0-5]|(?:2[0-4]|1?\d)?\d)\.){3}(?:25[0-5]|(?:2[0-4]|1?\d)?\d)|(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1?\d)?\d)\.){3}(?:25[0-5]|(?:2[0-4]|1?\d)?\d))$/;

  return ipv4Regex.test(ip) || ipv6Regex.test(ip);
}

/**
 * Derives a rate limit identifier from request headers.
 *
 * Extracts user ID from x-user-id header first, then falls back to first IP
 * from x-forwarded-for (after validating IP format to prevent spoofing).
 * Returns "unknown" if no valid identifier found.
 *
 * @returns Rate limit identifier in format "user:{id}", "ip:{ip}", or "unknown".
 */
async function getRateLimitIdentifier(): Promise<string> {
  try {
    const requestHeaders = await headers();
    const userId = requestHeaders.get("x-user-id");
    if (userId) {
      const trimmed = userId.trim();
      if (trimmed) {
        return `user:${trimmed}`;
      }
    }

    const forwardedFor = requestHeaders.get("x-forwarded-for");
    if (forwardedFor) {
      const primaryIp = forwardedFor.split(",")[0]?.trim();
      // Validate IP format to prevent spoofing attacks
      if (primaryIp && isValidIpAddress(primaryIp)) {
        return `ip:${primaryIp}`;
      }
    }
  } catch {
    // headers() throws when executed outside of a request context. Fall through.
  }

  return "unknown";
}
