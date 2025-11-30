/**
 * @fileoverview Flight search agent using AI SDK v6 ToolLoopAgent.
 *
 * Creates a reusable flight search agent that autonomously searches
 * for flights, resolves airport codes, and summarizes options using
 * multi-step tool calling.
 */

import "server-only";

import { getRegistryTool, invokeTool } from "@ai/lib/registry-utils";
import { createAiTool } from "@ai/lib/tool-factory";
import { toolRegistry } from "@ai/tools";
import { lookupPoiInputSchema } from "@ai/tools/schemas/google-places";
import { distanceMatrixInputSchema, geocodeInputSchema } from "@ai/tools/schemas/maps";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { searchFlightsInputSchema } from "@ai/tools/server/flights";
import type { AgentConfig } from "@schemas/configuration";
import type { FlightSearchRequest } from "@schemas/flights";
import type { ToolSet } from "ai";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildFlightPrompt } from "@/prompts/agents";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";
import { extractAgentParameters } from "./types";

/**
 * Builds guarded tools for the flight search agent.
 */
function buildFlightTools(identifier: string): ToolSet {
  const geocodeTool = getRegistryTool(toolRegistry, "geocode");
  const distanceMatrixTool = getRegistryTool(toolRegistry, "distanceMatrix");
  const poiTool = getRegistryTool(toolRegistry, "lookupPoiContext");
  const searchFlightsTool = getRegistryTool(toolRegistry, "searchFlights");

  const rateLimit = buildRateLimit("flightSearch", identifier);

  const geocode = createAiTool({
    description: geocodeTool.description ?? "Geocode address",
    execute: (params, callOptions) => invokeTool(geocodeTool, params, callOptions),
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:flight:geocode",
        namespace: `agent:flight:geocode:${identifier}`,
        ttlSeconds: 60 * 30,
      },
      telemetry: { workflow: "flightSearch" },
    },
    inputSchema: geocodeInputSchema,
    name: "geocode",
  });

  const distanceMatrix = createAiTool({
    description: distanceMatrixTool.description ?? "Distance matrix",
    execute: (params, callOptions) =>
      invokeTool(distanceMatrixTool, params, callOptions),
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:flight:distance-matrix",
        namespace: `agent:flight:distance-matrix:${identifier}`,
        ttlSeconds: 60 * 15,
      },
      telemetry: { workflow: "flightSearch" },
    },
    inputSchema: distanceMatrixInputSchema,
    name: "distanceMatrix",
  });

  const lookupPoiContext = createAiTool({
    description: poiTool.description ?? "Lookup POIs (context)",
    execute: (params, callOptions) => invokeTool(poiTool, params, callOptions),
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:flight:poi",
        namespace: `agent:flight:poi:${identifier}`,
        ttlSeconds: 600,
      },
      telemetry: { workflow: "flightSearch" },
    },
    inputSchema: lookupPoiInputSchema,
    name: "lookupPoiContext",
  });

  const searchFlights = createAiTool({
    description: searchFlightsTool.description ?? "Search flights",
    execute: (params, callOptions) =>
      invokeTool(searchFlightsTool, params, callOptions),
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:flight:search",
        namespace: `agent:flight:search:${identifier}`,
        ttlSeconds: 60 * 5,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:flight:search",
        window: rateLimit.window,
      },
      telemetry: { workflow: "flightSearch" },
    },
    inputSchema: searchFlightsInputSchema,
    name: "searchFlights",
  });

  return { distanceMatrix, geocode, lookupPoiContext, searchFlights } satisfies ToolSet;
}

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
    tools: buildFlightTools(deps.identifier),
    topP: params.topP,
  });
}

/** Exported type for the flight agent's tool set. */
export type FlightAgentTools = ReturnType<typeof buildFlightTools>;
