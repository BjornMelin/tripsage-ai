/**
 * @fileoverview Centralized rate limit configuration for agent workflows.
 *
 * Provides a single source of truth for rate limit configurations across
 * all agent workflows. Uses AgentWorkflow enum for type safety and ensures
 * all workflows have consistent rate limiting behavior.
 */

import { Ratelimit } from "@upstash/ratelimit";
import type { Redis } from "@upstash/redis";
import type { GuardrailRateLimit } from "@/lib/agents/runtime";
import type { AgentWorkflow } from "@/schemas/agents";

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
 * Route-level rate limit configuration mapping workflows to their request limits.
 *
 * Defines the maximum number of route requests allowed per window. These limits
 * are higher than tool-level limits since routes are entry points before tool calls.
 */
const ROUTE_RATE_LIMIT_CONFIG: Record<AgentWorkflow, { limit: number }> = {
  accommodationSearch: { limit: 30 },
  budgetPlanning: { limit: 30 },
  destinationResearch: { limit: 30 },
  flightSearch: { limit: 30 },
  itineraryPlanning: { limit: 30 },
  memoryUpdate: { limit: 30 },
  router: { limit: 100 },
};

/**
 * Build a GuardrailRateLimit configuration for a specific workflow.
 *
 * Returns a rate limit configuration object with the workflow-specific limit
 * and the default window. Uses the AgentWorkflow enum for type safety.
 *
 * @param workflow - The agent workflow identifier from AgentWorkflow enum.
 * @param identifier - Stable user or IP-based identifier (already hashed if needed).
 * @returns Rate limit configuration with workflow-specific limit and default window.
 * @throws {Error} If workflow is not found in configuration (should not happen due to Record type).
 */
export function buildRateLimit(
  workflow: AgentWorkflow,
  identifier: string
): GuardrailRateLimit {
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

/**
 * Build a route-level Ratelimit instance for a specific workflow.
 *
 * Creates an Upstash Ratelimit instance configured for route-level rate limiting.
 * Route limits are higher than tool-level limits since routes are entry points.
 *
 * @param workflow - The agent workflow identifier from AgentWorkflow enum.
 * @param redis - Upstash Redis instance.
 * @returns Configured Ratelimit instance for route-level limiting.
 * @throws {Error} If workflow is not found in configuration.
 */
export function buildRouteRateLimiter(
  workflow: AgentWorkflow,
  redis: Redis
): Ratelimit {
  const config = ROUTE_RATE_LIMIT_CONFIG[workflow];
  if (!config) {
    throw new Error(
      `Route rate limit configuration not found for workflow: ${workflow}`
    );
  }
  return new Ratelimit({
    analytics: false,
    limiter: Ratelimit.slidingWindow(
      config.limit,
      RATE_LIMIT_WINDOW as Parameters<typeof Ratelimit.slidingWindow>[1]
    ),
    prefix: `ratelimit:agent:route:${workflow}`,
    redis,
  });
}

/**
 * Enforce route-level rate limiting for agent workflows.
 *
 * Checks Redis availability, builds a route-level limiter, and enforces the limit.
 * Returns null if rate limit passes, or an error response if exceeded or Redis unavailable.
 * Skips rate limiting gracefully if Redis is not configured (development/test).
 *
 * @param workflow - The agent workflow identifier.
 * @param identifier - Stable user or IP-based identifier for rate limiting.
 * @param getRedis - Function to get Redis instance (allows dependency injection for testing).
 * @returns Error response if rate limit exceeded, null if limit passes or Redis unavailable.
 */
export async function enforceRouteRateLimit(
  workflow: AgentWorkflow,
  identifier: string,
  getRedis: () => Redis | undefined
): Promise<{ error: string; reason: string; status: number } | null> {
  const redis = getRedis();
  if (!redis) return null; // Graceful degradation when Redis unavailable

  try {
    const limiter = buildRouteRateLimiter(workflow, redis);
    const { success } = await limiter.limit(identifier);
    if (!success) {
      return {
        error: "rate_limit_exceeded",
        reason: "Too many requests",
        status: 429,
      };
    }
    return null;
  } catch (error) {
    // Log but don't fail the request if rate limiting errors
    console.error("Route rate limit enforcement error", {
      error: error instanceof Error ? error.message : "Unknown error",
      workflow,
    });
    return null; // Graceful degradation on error
  }
}
