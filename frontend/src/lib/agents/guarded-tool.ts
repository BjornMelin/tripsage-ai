/**
 * @fileoverview Helper to build guarded tools with consistent guardrails.
 *
 * Helper for wrapping tool executions with validation, caching, rate limiting,
 * and telemetry. Reduces duplication across agent orchestrators.
 */

import "server-only";

import type { AgentWorkflow } from "@/schemas/agents";
import type {
  GuardrailCacheConfig,
  GuardrailRateLimit,
  ParametersSchema,
} from "./runtime";
import { runWithGuardrails } from "./runtime";

/**
 * Options for building a guarded tool wrapper.
 */
export type BuildGuardedToolOptions<T, R> = {
  /** Tool key/name for telemetry and error messages. */
  toolKey: string;
  /** Agent workflow identifier. */
  workflow: AgentWorkflow;
  /** Zod schema for input parameter validation. */
  schema: ParametersSchema;
  /** Tool execution function. */
  execute: (params: T) => Promise<R>;
  /** Optional cache configuration. */
  cache?: GuardrailCacheConfig;
  /** Optional rate limit configuration. */
  rateLimit?: GuardrailRateLimit;
};

/**
 * Build a guarded tool wrapper with validation, caching, rate limiting, and telemetry.
 *
 * Returns an async function that wraps tool execution with guardrails. The returned
 * function validates input using the provided schema, checks cache, enforces rate limits,
 * executes the tool, and records telemetry events.
 *
 * @param options - Configuration for the guarded tool wrapper.
 * @returns Async function that executes the tool with guardrails applied.
 */
export function buildGuardedTool<T, R>(
  options: BuildGuardedToolOptions<T, R>
): (params: T) => Promise<R> {
  const { toolKey, workflow, schema, execute, cache, rateLimit } = options;

  return async (params: T): Promise<R> => {
    const { result } = await runWithGuardrails<T, R>(
      {
        cache,
        parametersSchema: schema,
        rateLimit,
        tool: toolKey,
        workflow,
      },
      params,
      execute
    );
    return result;
  };
}
