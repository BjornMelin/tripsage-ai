/**
 * @fileoverview Registry and helpers for constructing TripSage ToolLoopAgent workflows.
 */

import "server-only";

import type { AgentWorkflowKind } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";

import { createAccommodationAgent } from "./accommodation-agent";
import { createBudgetAgent } from "./budget-agent";
import { createDestinationAgent } from "./destination-agent";
import { createFlightAgent } from "./flight-agent";
import { createItineraryAgent } from "./itinerary-agent";
import type { AgentDependencies } from "./types";

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
// Router agent (uses generateText with Output.object, not ToolLoopAgent)
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

type AgentRegistry = {
  accommodationSearch: typeof createAccommodationAgent;
  budgetPlanning: typeof createBudgetAgent;
  destinationResearch: typeof createDestinationAgent;
  flightSearch: typeof createFlightAgent;
  itineraryPlanning: typeof createItineraryAgent;
};

/** Registry of agent factory functions. */
export const agentRegistry: AgentRegistry = {
  accommodationSearch: createAccommodationAgent,
  budgetPlanning: createBudgetAgent,
  destinationResearch: createDestinationAgent,
  flightSearch: createFlightAgent,
  itineraryPlanning: createItineraryAgent,
};

/** Agent workflow kinds supported by the registry. Excludes 'memoryUpdate' and 'router'. */
export type SupportedAgentKind = keyof AgentRegistry;

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
export function createAgentForWorkflow(
  kind: "accommodationSearch",
  deps: AgentDependencies,
  config: AgentConfig,
  input: Parameters<typeof createAccommodationAgent>[2]
): ReturnType<typeof createAccommodationAgent>;
export function createAgentForWorkflow(
  kind: "budgetPlanning",
  deps: AgentDependencies,
  config: AgentConfig,
  input: Parameters<typeof createBudgetAgent>[2]
): ReturnType<typeof createBudgetAgent>;
export function createAgentForWorkflow(
  kind: "destinationResearch",
  deps: AgentDependencies,
  config: AgentConfig,
  input: Parameters<typeof createDestinationAgent>[2]
): ReturnType<typeof createDestinationAgent>;
export function createAgentForWorkflow(
  kind: "flightSearch",
  deps: AgentDependencies,
  config: AgentConfig,
  input: Parameters<typeof createFlightAgent>[2]
): ReturnType<typeof createFlightAgent>;
export function createAgentForWorkflow(
  kind: "itineraryPlanning",
  deps: AgentDependencies,
  config: AgentConfig,
  input: Parameters<typeof createItineraryAgent>[2]
): ReturnType<typeof createItineraryAgent>;
export function createAgentForWorkflow(
  kind: SupportedAgentKind,
  deps: AgentDependencies,
  config: AgentConfig,
  input: Parameters<AgentRegistry[SupportedAgentKind]>[2]
): ReturnType<AgentRegistry[SupportedAgentKind]> {
  switch (kind) {
    case "accommodationSearch":
      return createAccommodationAgent(
        deps,
        config,
        input as Parameters<typeof createAccommodationAgent>[2]
      );
    case "budgetPlanning":
      return createBudgetAgent(
        deps,
        config,
        input as Parameters<typeof createBudgetAgent>[2]
      );
    case "destinationResearch":
      return createDestinationAgent(
        deps,
        config,
        input as Parameters<typeof createDestinationAgent>[2]
      );
    case "flightSearch":
      return createFlightAgent(
        deps,
        config,
        input as Parameters<typeof createFlightAgent>[2]
      );
    case "itineraryPlanning":
      return createItineraryAgent(
        deps,
        config,
        input as Parameters<typeof createItineraryAgent>[2]
      );
    default: {
      const exhaustive: never = kind;
      throw new Error(`Unsupported agent kind: ${exhaustive}`);
    }
  }
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
