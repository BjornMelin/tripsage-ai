/**
 * @fileoverview Agent registry for TripSage AI agents.
 *
 * Provides a centralized registry for all available agents with type-safe
 * lookup and factory function access.
 */

import "server-only";

import type { AgentWorkflowKind } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import type { ToolSet } from "ai";

import { createAccommodationAgent } from "./accommodation-agent";
import { createBudgetAgent } from "./budget-agent";
import { createDestinationAgent } from "./destination-agent";
import { createFlightAgent } from "./flight-agent";
import { createItineraryAgent } from "./itinerary-agent";
import type { AgentDependencies, TripSageAgentResult } from "./types";

// Re-export all agent creators for direct imports
export { createAccommodationAgent } from "./accommodation-agent";
// Re-export factory and types
export { createTripSageAgent, isToolError } from "./agent-factory";
export { createBudgetAgent } from "./budget-agent";
export {
  CHAT_DEFAULT_SYSTEM_PROMPT,
  type ChatAgentConfig,
  type ChatValidationResult,
  createChatAgent,
  toModelMessages,
  validateChatMessages,
} from "./chat-agent";
export { createDestinationAgent } from "./destination-agent";
export { createFlightAgent } from "./flight-agent";
export { createItineraryAgent } from "./itinerary-agent";
// Memory agent (uses streamText, not ToolLoopAgent)
export { persistMemoryRecords, runMemoryAgent } from "./memory-agent";
// Router agent (uses generateObject, not ToolLoopAgent)
export { classifyUserMessage } from "./router-agent";
export type {
  AgentDependencies,
  AgentExecutionMeta,
  AgentFactory,
  AgentParameters,
  InferTripSageUIMessage,
  TripSageAgentConfig,
  TripSageAgentResult,
} from "./types";
export { extractAgentParameters } from "./types";

/** Input types for each agent workflow. */
export interface AgentInputTypes {
  // Supported by agentRegistry and createAgentForWorkflow
  accommodationSearch: import("@schemas/agents").AccommodationSearchRequest;
  budgetPlanning: import("@schemas/agents").BudgetPlanRequest;
  destinationResearch: import("@schemas/agents").DestinationResearchRequest;
  flightSearch: import("@schemas/flights").FlightSearchRequest;
  itineraryPlanning: import("@schemas/agents").ItineraryPlanRequest;
  // Special handling - not supported via agentRegistry
  memoryUpdate: never;
  router: never; // Router uses generateObject, not ToolLoopAgent
}

/** Registry of agent factory functions. */
export const agentRegistry = {
  accommodationSearch: createAccommodationAgent,
  budgetPlanning: createBudgetAgent,
  destinationResearch: createDestinationAgent,
  flightSearch: createFlightAgent,
  itineraryPlanning: createItineraryAgent,
} as const;

/** Agent workflow kinds supported by the registry. Excludes 'memoryUpdate' and 'router'. */
export type SupportedAgentKind = keyof typeof agentRegistry;

/**
 * Checks if an agent workflow kind is supported by the registry.
 *
 * @param kind - Agent workflow kind to check.
 * @returns True if the kind is supported.
 */
export function isSupportedAgentKind(
  kind: AgentWorkflowKind
): kind is SupportedAgentKind {
  return kind in agentRegistry;
}

/**
 * Creates an agent for the specified workflow kind.
 *
 * @param kind - Agent workflow kind.
 * @param deps - Runtime dependencies.
 * @param config - Agent configuration.
 * @param input - Workflow-specific input.
 * @returns Configured ToolLoopAgent instance.
 * @throws Error if the agent kind is not supported.
 */
export function createAgentForWorkflow<Kind extends SupportedAgentKind>(
  kind: Kind,
  deps: AgentDependencies,
  config: AgentConfig,
  input: AgentInputTypes[Kind]
): TripSageAgentResult<ToolSet> {
  const factory = agentRegistry[kind];
  // Defensive check (compile-time constraint already guarantees presence)
  if (!factory) {
    throw new Error(`Unsupported agent kind: ${kind}`);
  }

  // Type assertion needed because factory functions have different specific tool sets
  // but all return TripSageAgentResult. We cast through unknown to satisfy TypeScript.
  return (
    factory as unknown as (
      deps: AgentDependencies,
      config: AgentConfig,
      input: unknown
    ) => TripSageAgentResult<ToolSet>
  )(deps, config, input);
}

/**
 * Gets the human-readable name for an agent workflow kind.
 *
 * @param kind - Agent workflow kind.
 * @returns Human-readable agent name.
 */
export function getAgentName(kind: AgentWorkflowKind): string {
  const names: Record<AgentWorkflowKind, string> = {
    accommodationSearch: "Accommodation Search Agent",
    budgetPlanning: "Budget Planning Agent",
    destinationResearch: "Destination Research Agent",
    flightSearch: "Flight Search Agent",
    itineraryPlanning: "Itinerary Planning Agent",
    memoryUpdate: "Memory Update Agent",
    router: "Router Agent",
  };
  return names[kind] ?? "Unknown Agent";
}

/**
 * Gets the minimum max-step floor for an agent workflow kind.
 *
 * @param kind - Agent workflow kind.
 * @returns Minimum max steps enforced by the agent.
 */
export function getMinimumMaxSteps(kind: AgentWorkflowKind): number {
  const defaults: Record<AgentWorkflowKind, number> = {
    accommodationSearch: 10,
    budgetPlanning: 10,
    destinationResearch: 15,
    flightSearch: 10,
    itineraryPlanning: 15,
    memoryUpdate: 5,
    router: 1,
  };
  return defaults[kind] ?? 10;
}
