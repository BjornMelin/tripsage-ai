/**
 * @fileoverview Flight search agent using AI SDK v6 streaming.
 *
 * Wraps flight search tools (search, geocode) with guardrails (caching, rate
 * limiting) and executes streaming text generation to find and summarize flight
 * options. Returns structured results conforming to the flight search result
 * schema.
 */

import "server-only";

import type { LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText } from "ai";

import { createAiTool } from "@/lib/ai/tool-factory";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { FlightSearchRequest } from "@/lib/schemas/agents";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { toolRegistry } from "@/lib/tools";
import { TOOL_ERROR_CODES } from "@/lib/tools/errors";
import { searchFlightsInputSchema } from "@/lib/tools/flights";
import { lookupPoiInputSchema } from "@/lib/tools/google-places";
import { distanceMatrixInputSchema, geocodeInputSchema } from "@/lib/tools/maps";
import { buildFlightPrompt } from "@/prompts/agents";

/**
 * Create wrapped tools for flight agent with guardrails.
 *
 * Applies validation, caching, and rate limits around core tool execute
 * functions. The identifier should be per-user when authenticated or a
 * hashed IP fallback.
 *
 * @param identifier Stable identifier for rate limiting.
 * @returns AI SDK ToolSet for use with streamText.
 */
function buildFlightTools(identifier: string): ToolSet {
  // Access tool registry with proper typing; runtime guardrails perform validation.
  // Tools are typed as unknown in registry, so we use type assertions for safe access.
  type ToolLike = {
    description?: string;
    execute: (params: unknown, callOptions?: unknown) => Promise<unknown> | unknown;
  };

  const flightTool = toolRegistry.searchFlights as unknown as ToolLike;
  const geocodeTool = toolRegistry.geocode as unknown as ToolLike;
  const poiTool = toolRegistry.lookupPoiContext as unknown as ToolLike | undefined;
  const distanceMatrixTool = toolRegistry.distanceMatrix as unknown as
    | ToolLike
    | undefined;

  const rateLimit = buildRateLimit("flightSearch", identifier);

  const searchFlights = createAiTool({
    description: flightTool.description ?? "Search flights",
    execute: async (params, callOptions) => {
      if (typeof flightTool.execute !== "function") {
        throw new Error("Tool searchFlights missing execute binding");
      }
      return (await flightTool.execute(params, callOptions)) as unknown;
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:flight:search",
        namespace: "agent:flight:search",
        ttlSeconds: 60 * 30,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:flight:search",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "flightSearch",
      },
    },
    inputSchema: searchFlightsInputSchema,
    name: "searchFlights",
  });

  const geocode = createAiTool({
    description: geocodeTool.description ?? "Geocode address",
    execute: async (params, callOptions) => {
      if (typeof geocodeTool.execute !== "function") {
        throw new Error("Tool geocode missing execute binding");
      }
      return (await geocodeTool.execute(params, callOptions)) as unknown;
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:flight:geocode",
        namespace: "agent:flight:geocode",
        ttlSeconds: 60 * 60,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:flight:geocode",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "flightSearch",
      },
    },
    inputSchema: geocodeInputSchema,
    name: "geocode",
  });

  const lookupPoiContext = createAiTool({
    description: poiTool?.description ?? "Lookup POIs (context)",
    execute: async (params, callOptions) => {
      if (!poiTool) return { inputs: params, pois: [], provider: "stub" };
      if (typeof poiTool.execute !== "function") {
        throw new Error("Tool lookupPoiContext missing execute binding");
      }
      return (await poiTool.execute(params, callOptions)) as unknown;
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:flight:poi",
        namespace: "agent:flight:poi",
        ttlSeconds: 600,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:flight:poi",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "flightSearch",
      },
    },
    inputSchema: lookupPoiInputSchema,
    name: "lookupPoiContext",
  });

  const distanceMatrix = createAiTool({
    description: distanceMatrixTool?.description ?? "Distance matrix",
    execute: async (params, callOptions) => {
      if (!distanceMatrixTool)
        return { distances: [], inputs: params, provider: "stub" };
      if (typeof distanceMatrixTool.execute !== "function") {
        throw new Error("Tool distanceMatrix missing execute binding");
      }
      return (await distanceMatrixTool.execute(params, callOptions)) as unknown;
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:flight:distance",
        namespace: "agent:flight:distance",
        ttlSeconds: 3600,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:flight:distance",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "flightSearch",
      },
    },
    inputSchema: distanceMatrixInputSchema,
    name: "distanceMatrix",
  });

  return { distanceMatrix, geocode, lookupPoiContext, searchFlights } satisfies ToolSet;
}

/**
 * Execute the flight agent with AI SDK v6 streaming.
 *
 * Builds system instructions and messages, wraps core tools with guardrails,
 * and streams a model-guided tool loop to produce results structured per
 * `flight.v1` schema.
 *
 * @param deps Language model, model identifier, and request-scoped utilities.
 * @param input Validated flight search request.
 * @returns AI SDK stream result for UI consumption.
 */
export function runFlightAgent(
  deps: {
    model: LanguageModel;
    modelId: string;
    identifier: string;
  },
  input: FlightSearchRequest
) {
  const instructions = buildFlightPrompt(input);
  const userPrompt = `Find flight offers and summarize. Always return JSON with schemaVersion="flight.v1" and sources[]. Parameters: ${JSON.stringify(
    input
  )}`;

  // Token budgeting: clamp max output tokens based on prompt length
  const messages: ChatMessage[] = [
    { content: instructions, role: "system" },
    { content: userPrompt, role: "user" },
  ];
  const desiredMaxTokens = 4096; // Default for agent responses
  const { maxTokens } = clampMaxTokens(messages, desiredMaxTokens, deps.modelId);

  return streamText({
    maxOutputTokens: maxTokens,
    messages: [
      { content: instructions, role: "system" },
      { content: userPrompt, role: "user" },
    ],
    model: deps.model,
    stopWhen: stepCountIs(10),
    temperature: 0.3,
    tools: buildFlightTools(deps.identifier),
  });
}
