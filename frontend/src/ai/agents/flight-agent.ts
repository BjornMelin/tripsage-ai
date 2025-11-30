/**
 * @fileoverview Flight search agent using AI SDK v6 ToolLoopAgent.
 *
 * Creates a reusable flight search agent that autonomously searches
 * for flights, resolves airport codes, and summarizes options using
 * multi-step tool calling.
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
 * Tools available to the flight search agent.
 *
 * Includes geocoding, distance calculation, POI lookup, and flight search
 * for comprehensive flight planning capabilities.
 */
const FLIGHT_TOOLS = {
  distanceMatrix,
  geocode,
  lookupPoiContext,
  searchFlights,
} satisfies ToolSet;

/**
 * Creates a flight search agent using AI SDK v6 ToolLoopAgent.
 *
 * The agent autonomously resolves airport codes, searches for flights,
 * and generates structured summaries through multi-step tool calling.
 * Returns a reusable agent instance for streaming or one-shot generation.
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
 * });
 *
 * // Stream the response
 * return createAgentUIStreamResponse({
 *   agent,
 *   messages: [{ role: "user", content: "Find me flights" }],
 * });
 * ```
 */
export function createFlightAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: FlightSearchRequest,
  contextMessages: ChatMessage[] = []
): TripSageAgentResult {
  const params = extractAgentParameters(config);
  const instructions = buildFlightPrompt(input);

  // Token budgeting: clamp max output tokens based on prompt length
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

  return createTripSageAgent(deps, {
    agentType: "flightSearch",
    defaultMessages: [schemaMessage],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps: params.maxSteps,
    name: "Flight Search Agent",
    temperature: params.temperature,
    tools: FLIGHT_TOOLS,
    topP: params.topP,
  });
}

/** Exported type for the flight agent's tool set. */
export type FlightAgentTools = typeof FLIGHT_TOOLS;
