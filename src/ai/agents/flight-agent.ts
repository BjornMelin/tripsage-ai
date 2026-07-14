/**
 * @fileoverview Flight search agent for travel planning.
 */

import "server-only";

import {
  distanceMatrix,
  geocode,
  placeDetails,
  searchFlights,
  searchPlaces,
} from "@ai/tools";
import type { AgentConfig } from "@schemas/configuration";
import type { FlightSearchRequest } from "@schemas/flights";
import type { ToolSet } from "ai";
import { buildFlightPrompt } from "@/prompts/agents";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";
import { extractAgentParameters, prepareSchemaPrompt } from "./types";

/**
 * Tools available to the flight search agent with built-in guardrails
 * for caching, rate limiting, and telemetry.
 */
const FLIGHT_TOOLS = {
  distanceMatrix,
  geocode,
  searchFlights,
  searchPlaceDetails: placeDetails,
  searchPlaces,
} satisfies ToolSet;

/**
 * Creates a flight search agent with phased tool selection.
 *
 * Phases:
 * - Phase 1: Resolve locations via geocoding and POI lookup
 * - Phase 2: Search flights and compute distances
 *
 * @remarks
 * SPEC-0008 documents the AI SDK v6 foundations used by this agent.
 *
 * @param deps - Runtime dependencies including model and identifiers.
 * @param config - Agent configuration from database.
 * @param input - Validated flight search request.
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
  input: FlightSearchRequest
): TripSageAgentResult<typeof FLIGHT_TOOLS> {
  const params = extractAgentParameters(config);
  const instructions = buildFlightPrompt(input);

  const { maxOutputTokens, uiMessages } = prepareSchemaPrompt({
    instructions,
    maxOutputTokens: params.maxOutputTokens,
    modelId: deps.modelId,
    userPrompt: `Find flight offers and summarize. Always return JSON with schemaVersion="flight.v1" and sources[]. Parameters: ${JSON.stringify(
      input
    )}`,
  });

  return createTripSageAgent<typeof FLIGHT_TOOLS>(deps, {
    agentType: "flightSearch",
    instructions,
    maxOutputTokens,
    name: "Flight Search Agent",
    // Phased tool selection for flight search workflow
    prepareStep: ({ stepNumber }) => {
      // Phase 1 (steps 0-2): Resolve locations
      if (stepNumber <= 2) {
        return {
          activeTools: ["geocode", "searchPlaces", "searchPlaceDetails"],
        };
      }
      // Phase 2 (steps 3+): Search flights
      return {
        activeTools: ["searchFlights", "distanceMatrix"],
      };
    },
    stepLimit: params.stepLimit,
    temperature: params.temperature,
    tools: FLIGHT_TOOLS,
    topP: params.topP,
    uiMessages,
  });
}
