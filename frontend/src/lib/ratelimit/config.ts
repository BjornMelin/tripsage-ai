/**
 * @fileoverview Rate limit configuration for agent workflows.
 *
 * Provides rate limiting for agent tool execution within agent runtime.
 * Route-level rate limiting is handled by lib/ratelimit/routes.ts via
 * withApiGuards. Per ADR-0032.
 */

import type { AgentWorkflow } from "@schemas/agents";

/**
 * Default rate limit window for all workflows.
 *
 * All workflows use a 1-minute sliding window for rate limiting.
 */
const RATE_LIMIT_WINDOW = "1 m" as const;

/**
 * Per-tool rate limit configuration mapping workflows to their request limits.
 *
 * Defines the maximum number of tool calls allowed per window for each
 * workflow. Limits are chosen based on workflow complexity and resource usage.
 */
const TOOL_RATE_LIMIT_CONFIG: Record<AgentWorkflow, { limit: number }> = {
  accommodationSearch: { limit: 10 },
  budgetPlanning: { limit: 6 },
  destinationResearch: { limit: 8 },
  flightSearch: { limit: 8 },
  itineraryPlanning: { limit: 6 },
  memoryUpdate: { limit: 20 },
  router: { limit: 100 },
};

/**
 * Workflow-specific rate limit metadata shared across guardrails.
 */
export type WorkflowRateLimit = {
  identifier: string;
  limit: number;
  window: typeof RATE_LIMIT_WINDOW;
};

/**
 * Builds a workflow-specific rate limit configuration.
 *
 * Returns a rate limit configuration object with the workflow-specific limit
 * and the default window. Uses the AgentWorkflow enum for type safety.
 *
 * @param workflow The agent workflow identifier from AgentWorkflow enum.
 * @param identifier Stable user or IP-based identifier (already hashed if needed).
 * @returns Rate limit configuration with workflow-specific limit and default window.
 * @throws {Error} If workflow is not found in configuration (should not happen due to Record type).
 */
export function buildRateLimit(
  workflow: AgentWorkflow,
  identifier: string
): WorkflowRateLimit {
  const config = TOOL_RATE_LIMIT_CONFIG[workflow];
  if (!config) {
    throw new Error(`Rate limit configuration not found for workflow: ${workflow}`);
  }
  return {
    identifier,
    limit: config.limit,
    window: RATE_LIMIT_WINDOW,
  };
}
