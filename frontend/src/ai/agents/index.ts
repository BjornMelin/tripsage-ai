/**
 * @fileoverview Agent registry for TripSage AI agents using AI SDK v6 ToolLoopAgent.
 *
 * Provides a centralized registry for all available agents with type-safe
 * lookup and factory function access. The registry maps agent workflow
 * kinds to their factory functions for dynamic agent instantiation.
 */

import "server-only";

import type { AgentWorkflowKind } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";

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

/**
 * Input types for each agent workflow.
 *
 * Maps agent workflow kinds to their expected input types for type-safe
 * factory function invocation.
 */
export interface AgentInputTypes {
  accommodationSearch: import("@schemas/agents").AccommodationSearchRequest;
  budgetPlanning: import("@schemas/agents").BudgetPlanRequest;
  destinationResearch: import("@schemas/agents").DestinationResearchRequest;
  flightSearch: import("@schemas/flights").FlightSearchRequest;
  itineraryPlanning: import("@schemas/agents").ItineraryPlanRequest;
  memoryUpdate: import("@schemas/agents").MemoryUpdateRequest;
  router: never; // Router uses generateObject, not ToolLoopAgent
}

/**
 * Registry of agent factory functions.
 *
 * Maps agent workflow kinds to their factory functions for dynamic
 * agent creation. Each factory returns a configured ToolLoopAgent
 * instance ready for streaming or one-shot generation.
 */
export const agentRegistry = {
  accommodationSearch: createAccommodationAgent,
  budgetPlanning: createBudgetAgent,
  destinationResearch: createDestinationAgent,
  flightSearch: createFlightAgent,
  itineraryPlanning: createItineraryAgent,
} as const;

/**
 * Agent workflow kinds that are supported by the registry.
 *
 * Excludes 'memoryUpdate' and 'router' which have special handling.
 */
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
 * Dynamically looks up the appropriate factory function and creates
 * a configured ToolLoopAgent instance. Throws for unsupported kinds.
 *
 * @template TKind - Agent workflow kind type.
 * @param kind - Agent workflow kind.
 * @param deps - Runtime dependencies.
 * @param config - Agent configuration.
 * @param input - Workflow-specific input.
 * @returns Configured ToolLoopAgent instance.
 * @throws Error if the agent kind is not supported.
 *
 * @example
 * ```typescript
 * const { agent } = createAgentForWorkflow(
 *   "budgetPlanning",
 *   deps,
 *   config,
 *   { destination: "Tokyo", durationDays: 7 }
 * );
 * ```
 */
// biome-ignore lint/style/useNamingConvention: TypeScript generic convention
export function createAgentForWorkflow<TKind extends SupportedAgentKind>(
  kind: TKind,
  deps: AgentDependencies,
  config: AgentConfig,
  input: AgentInputTypes[TKind]
): TripSageAgentResult {
  const factory = agentRegistry[kind];
  if (!factory) {
    throw new Error(`Unsupported agent kind: ${kind}`);
  }

  // Type assertion needed due to input type variance
  // biome-ignore lint/suspicious/noExplicitAny: Dynamic dispatch requires any
  return factory(deps, config, input as any);
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
 * Gets the default max steps for an agent workflow kind.
 *
 * @param kind - Agent workflow kind.
 * @returns Default max steps for the agent.
 */
export function getDefaultMaxSteps(kind: AgentWorkflowKind): number {
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
