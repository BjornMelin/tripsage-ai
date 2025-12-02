/**
 * @fileoverview Flight search agent for travel planning.
 *
 * Reusable ToolLoopAgent that searches flights, resolves airport codes,
 * and summarizes options via multi-step tool calling with phased tool selection.
 */

import "server-only";

import { distanceMatrix, geocode, lookupPoiContext, searchFlights } from "@ai/tools";
import type { AgentConfig } from "@schemas/configuration";
import type { FlightSearchRequest } from "@schemas/flights";
import type { ToolSet } from "ai";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildFlightPrompt } from "@/prompts/agents";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";
import { extractAgentParameters } from "./types";

/**
 * Tools available to the flight search agent with built-in guardrails
 * for caching, rate limiting, and telemetry.
 */
const FLIGHT_TOOLS = {
  distanceMatrix,
  geocode,
  lookupPoiContext,
  searchFlights,
} satisfies ToolSet;

/**
 * Creates a flight search agent with phased tool selection.
 *
 * Phases:
 * - Phase 1: Resolve locations via geocoding and POI lookup
 * - Phase 2: Search flights and compute distances
 *
 * @param deps - Runtime dependencies including model and identifiers.
 * @param config - Agent configuration from database.
 * @param input - Validated flight search request.
 * @param contextMessages - Optional context messages to include.
 * @returns Configured ToolLoopAgent for flight search.
 *
 * @example
 * ```typescript
 * const { agent } = createFlightAgent(deps, config, {
 *   origin: "New York",
 *   destination: "Tokyo",
 *   departureDate: "2025-03-15",
 *   passengers: 2,
 *   cabinClass: "economy",
 *   currency: "USD",
 * });
 * const stream = agent.stream({ prompt: "Find flights" });
 * ```
 */
export function createFlightAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: FlightSearchRequest,
  contextMessages: ChatMessage[] = []
): TripSageAgentResult<typeof FLIGHT_TOOLS> {
  const params = extractAgentParameters(config);
  const instructions = buildFlightPrompt(input);

  const userPrompt = `Find flight offers and summarize. Always return JSON with schemaVersion="flight.v1" and sources[]. Parameters: ${JSON.stringify(
    input
  )}`;
  const schemaMessage: ChatMessage = { content: userPrompt, role: "user" };
  const clampMessages: ChatMessage[] = [
    { content: instructions, role: "system" },
    schemaMessage,
    ...contextMessages,
  ];
  const { maxTokens } = clampMaxTokens(clampMessages, params.maxTokens, deps.modelId);

  return createTripSageAgent<typeof FLIGHT_TOOLS>(deps, {
    agentType: "flightSearch",
    defaultMessages: [schemaMessage],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps: params.maxSteps,
    name: "Flight Search Agent",
    // Note: For structured output, pass Output.object({ schema: flightSearchResultSchema })
    // when calling agent.generate() or agent.stream()
    // Phased tool selection for flight search workflow
    prepareStep: ({ stepNumber }) => {
      // Phase 1 (steps 0-2): Resolve locations
      if (stepNumber <= 2) {
        return {
          activeTools: ["geocode", "lookupPoiContext"],
        };
      }
      // Phase 2 (steps 3+): Search flights
      return {
        activeTools: ["searchFlights", "distanceMatrix"],
      };
    },
    temperature: params.temperature,
    tools: FLIGHT_TOOLS,
    topP: params.topP,
  });
}

/** Exported type for the flight agent's tool set. */
export type FlightAgentTools = typeof FLIGHT_TOOLS;
