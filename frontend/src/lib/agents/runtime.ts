/**
 * @fileoverview Agent tool execution runtime with guardrails.
 *
 * Provides validation, caching, rate limiting, and telemetry wrappers for
 * agent tool execution across different workflows. Supports configurable
 * input validation, Redis caching with key hashing, Upstash rate limiting,
 * and OpenTelemetry event recording.
 */

import "server-only";

import { createHash } from "node:crypto";
import { Ratelimit } from "@upstash/ratelimit";
import type { ZodType } from "zod";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { getRedis } from "@/lib/redis";
import type { AgentWorkflow } from "@/lib/schemas/agents";
import { recordAgentToolEvent } from "@/lib/telemetry/agents";

/**
 * Rate limiting configuration for agent tool guardrails.
 *
 * Defines the identifier (user ID or session), request limit, and time window
 * for sliding window rate limiting via Upstash Redis.
 */
export type GuardrailRateLimit = {
  identifier: string;
  limit: number;
  window: string;
};

/**
 * Caching configuration for agent tool guardrails.
 *
 * Defines the cache key prefix, TTL in seconds, and optional input hashing
 * for cache key generation.
 */
export type GuardrailCacheConfig = {
  key: string;
  ttlSeconds: number;
  hashInput?: boolean;
};

/**
 * Parameters schema type for guardrails.
 *
 * Accepts Zod schemas for validation. Can be extended to support
 * FlexibleSchema from AI SDK if needed in the future.
 */
export type ParametersSchema = ZodType<unknown>;

/**
 * Complete guardrail configuration for agent tool execution.
 *
 * Combines workflow context, tool name, optional input validation schema,
 * caching, and rate limiting settings.
 */
export type GuardrailConfig = {
  workflow: AgentWorkflow;
  tool: string;
  parametersSchema?: ParametersSchema;
  cache?: GuardrailCacheConfig;
  rateLimit?: GuardrailRateLimit;
};

/**
 * Result from guardrail-wrapped tool execution.
 *
 * Includes the tool result and cache hit status for observability.
 */
export type GuardrailResult<T> = {
  result: T;
  cacheHit: boolean;
};

/**
 * Wrap a tool execution with validation, caching, rate limiting, and telemetry.
 *
 * Executes the provided tool function with:
 * - Input validation via optional Zod schema
 * - Redis caching with configurable TTL and key hashing
 * - Rate limiting via Upstash sliding window
 * - Telemetry recording for success/error events
 *
 * @param config - Guardrail configuration including workflow, tool name, schema, cache, and rate limit settings.
 * @param input - Raw input to validate and pass to the tool.
 * @param execute - Tool execution function that receives validated input.
 * @returns Promise resolving to guardrail result with tool output and cache hit status.
 * @throws {Error} "Rate limit exceeded for agent workflow" when rate limit is exceeded.
 */
export async function runWithGuardrails<InputValue, ResultValue>(
  config: GuardrailConfig,
  input: InputValue,
  execute: (validatedInput: InputValue) => Promise<ResultValue>
): Promise<GuardrailResult<ResultValue>> {
  const validatedInput = config.parametersSchema
    ? (config.parametersSchema.parse(input) as InputValue)
    : input;

  const cacheKey = config.cache
    ? buildCacheKey(config.cache, validatedInput)
    : undefined;

  if (cacheKey) {
    const cached = await getCachedJson<ResultValue>(cacheKey);
    if (cached) {
      await recordAgentToolEvent({
        cacheHit: true,
        durationMs: 0,
        status: "success",
        tool: config.tool,
        workflow: config.workflow,
      });
      return { cacheHit: true, result: cached };
    }
  }

  await enforceRateLimit(config);

  const start = Date.now();
  try {
    const result = await execute(validatedInput);
    if (cacheKey && config.cache) {
      await setCachedJson(cacheKey, result, config.cache.ttlSeconds);
    }
    const durationMs = Date.now() - start;
    await recordAgentToolEvent({
      cacheHit: false,
      durationMs,
      status: "success",
      tool: config.tool,
      workflow: config.workflow,
    });
    return { cacheHit: false, result };
  } catch (error) {
    const durationMs = Date.now() - start;
    await recordAgentToolEvent({
      cacheHit: false,
      durationMs,
      errorMessage: error instanceof Error ? error.message : "Unknown error",
      status: "error",
      tool: config.tool,
      workflow: config.workflow,
    });
    throw error;
  }
}

/**
 * Build cache key from configuration and input.
 *
 * If hashInput is enabled, computes SHA-256 hash of JSON-serialized input
 * and appends first 16 hex characters to the base key. Otherwise returns
 * the base key unchanged.
 *
 * @param cache - Cache configuration with key prefix and optional hashing.
 * @param input - Input value to hash if hashInput is enabled.
 * @returns Cache key string ready for Redis storage.
 */
function buildCacheKey(cache: GuardrailCacheConfig, input: unknown): string {
  if (!cache.hashInput) return cache.key;
  const hash = createHash("sha256")
    .update(JSON.stringify(input))
    .digest("hex")
    .slice(0, 16);
  return `${cache.key}:${hash}`;
}

/**
 * Enforce rate limiting for agent tool execution.
 *
 * Creates an Upstash Ratelimit instance with sliding window limiter and
 * checks the configured identifier. Throws an error if rate limit is exceeded.
 * Skips rate limiting if Redis is unavailable or not configured.
 *
 * @param config - Guardrail configuration containing rate limit settings.
 * @throws {Error} "Rate limit exceeded for agent workflow" when limit is exceeded.
 */
async function enforceRateLimit(config: GuardrailConfig): Promise<void> {
  const rate = config.rateLimit;
  if (!rate) return;
  const redis = getRedis();
  if (!redis) return;
  const limiter = new Ratelimit({
    analytics: false,
    limiter: Ratelimit.slidingWindow(
      rate.limit,
      rate.window as Parameters<typeof Ratelimit.slidingWindow>[1]
    ),
    prefix: `ratelimit:agent:${config.workflow}:${config.tool}`,
    redis,
  });
  const { success } = await limiter.limit(rate.identifier);
  if (!success) {
    throw new Error("Rate limit exceeded for agent workflow");
  }
}
