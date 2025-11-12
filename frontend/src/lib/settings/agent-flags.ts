/**
 * @fileoverview Agent feature flag configuration via environment variables.
 *
 * Reads boolean feature flags from environment variables to enable/disable
 * agent workflows (flights, accommodations, budget, memory, router).
 * Accepts multiple truthy string values: "1", "true", "yes", "on".
 */

import "server-only";

/**
 * Agent feature flag configuration type.
 *
 * Boolean flags for enabling/disabling agent workflows. Each flag corresponds
 * to an environment variable (AGENT_WAVE_*).
 */
export type AgentFeatureFlags = {
  flights: boolean;
  accommodations: boolean;
  budget: boolean;
  memory: boolean;
  router: boolean;
};

// Set of string values considered truthy for environment variable parsing
const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);

/**
 * Read a boolean flag from an environment variable.
 *
 * Returns true if the environment variable value (case-insensitive, trimmed)
 * matches one of the truthy values. Returns false if the variable is missing
 * or does not match.
 *
 * @param envKey - Environment variable key to read.
 * @returns True if the variable is set to a truthy value, false otherwise.
 */
function readFlag(envKey: string): boolean {
  const raw = process.env[envKey];
  if (!raw) return false;
  return TRUE_VALUES.has(raw.trim().toLowerCase());
}

/**
 * Get agent feature flags from environment variables.
 *
 * Reads all agent workflow feature flags from their corresponding environment
 * variables and returns a typed configuration object.
 *
 * @returns AgentFeatureFlags object with boolean values for each workflow.
 */
export function getAgentFeatureFlags(): AgentFeatureFlags {
  return {
    accommodations: readFlag("AGENT_WAVE_ACCOMMODATION"),
    budget: readFlag("AGENT_WAVE_BUDGET"),
    flights: readFlag("AGENT_WAVE_FLIGHT"),
    memory: readFlag("AGENT_WAVE_MEMORY"),
    router: readFlag("AGENT_WAVE_ROUTER"),
  };
}

export { readFlag as __testOnlyReadFlag };
