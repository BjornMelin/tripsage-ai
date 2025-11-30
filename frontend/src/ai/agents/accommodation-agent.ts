/**
 * @fileoverview Accommodation search agent using AI SDK v6 ToolLoopAgent.
 *
 * Creates a reusable accommodation search agent that autonomously searches
 * for properties, retrieves details, checks availability, and handles
 * bookings using multi-step tool calling.
 */

import "server-only";

import { getRegistryTool, invokeTool } from "@ai/lib/registry-utils";
import { createAiTool } from "@ai/lib/tool-factory";
import { toolRegistry } from "@ai/tools";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";

/** Schema version for accommodation stay responses. */
const STAY_SCHEMA_VERSION = "stay.v1";

import {
  type AccommodationBookingRequest,
  type AccommodationBookingResult,
  type AccommodationCheckAvailabilityParams,
  type AccommodationCheckAvailabilityResult,
  type AccommodationDetailsParams,
  type AccommodationDetailsResult,
  type AccommodationSearchParams,
  type AccommodationSearchResult,
  accommodationBookingInputSchema,
  accommodationBookingOutputSchema,
  accommodationCheckAvailabilityInputSchema,
  accommodationCheckAvailabilityOutputSchema,
  accommodationDetailsInputSchema,
  accommodationDetailsOutputSchema,
  accommodationSearchInputSchema,
  accommodationSearchOutputSchema,
} from "@schemas/accommodations";
import type { AccommodationSearchRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import type { ToolSet } from "ai";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildAccommodationPrompt } from "@/prompts/agents";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";
import { extractAgentParameters } from "./types";

/**
 * Creates wrapped tools for accommodation agent with guardrails.
 *
 * Applies validation, rate limits, and telemetry around core tool
 * execute functions. Supports the full booking flow from search
 * through reservation.
 *
 * @param identifier - Stable identifier for rate limiting.
 * @returns AI SDK ToolSet for use with ToolLoopAgent.
 */
function buildAccommodationTools(identifier: string): ToolSet {
  const searchTool = getRegistryTool<
    AccommodationSearchParams,
    AccommodationSearchResult
  >(toolRegistry, "searchAccommodations");
  const detailsTool = getRegistryTool<
    AccommodationDetailsParams,
    AccommodationDetailsResult
  >(toolRegistry, "getAccommodationDetails");
  const availabilityTool = getRegistryTool<
    AccommodationCheckAvailabilityParams,
    AccommodationCheckAvailabilityResult
  >(toolRegistry, "checkAvailability");
  const bookingTool = getRegistryTool<
    AccommodationBookingRequest,
    AccommodationBookingResult
  >(toolRegistry, "bookAccommodation");

  const rateLimit = buildRateLimit("accommodationSearch", identifier);

  const searchAccommodations = createAiTool({
    description: searchTool.description ?? "Search accommodations",
    execute: (params, callOptions) => invokeTool(searchTool, params, callOptions),
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:accommodation:search",
        namespace: "agent:accommodation:search",
        ttlSeconds: 60 * 10,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:accommodation:search",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "accommodationSearch",
      },
    },
    inputSchema: accommodationSearchInputSchema,
    name: "searchAccommodations",
    outputSchema: accommodationSearchOutputSchema,
  });

  const getAccommodationDetails = createAiTool({
    description: detailsTool.description ?? "Get accommodation details",
    execute: (params, callOptions) => invokeTool(detailsTool, params, callOptions),
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:accommodation:details",
        namespace: "agent:accommodation:details",
        ttlSeconds: 60 * 30,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:accommodation:details",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "accommodationSearch",
      },
    },
    inputSchema: accommodationDetailsInputSchema,
    name: "getAccommodationDetails",
    outputSchema: accommodationDetailsOutputSchema,
  });

  const checkAvailability = createAiTool({
    description: availabilityTool.description ?? "Check accommodation availability",
    execute: (params, callOptions) => invokeTool(availabilityTool, params, callOptions),
    guardrails: {
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:accommodation:availability",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "accommodationSearch",
      },
    },
    inputSchema: accommodationCheckAvailabilityInputSchema,
    name: "checkAvailability",
    outputSchema: accommodationCheckAvailabilityOutputSchema,
  });

  const bookAccommodation = createAiTool({
    description: bookingTool.description ?? "Book accommodation",
    execute: (params, callOptions) => invokeTool(bookingTool, params, callOptions),
    guardrails: {
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:accommodation:booking",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "accommodationSearch",
      },
    },
    inputSchema: accommodationBookingInputSchema,
    name: "bookAccommodation",
    outputSchema: accommodationBookingOutputSchema,
  });

  return {
    bookAccommodation,
    checkAvailability,
    getAccommodationDetails,
    searchAccommodations,
  } satisfies ToolSet;
}

/**
 * Creates an accommodation search agent using AI SDK v6 ToolLoopAgent.
 *
 * The agent autonomously searches for properties, retrieves details,
 * checks availability, and can complete bookings through multi-step
 * tool calling. Returns a reusable agent instance.
 *
 * @param deps - Runtime dependencies including model and identifiers.
 * @param config - Agent configuration from database.
 * @param input - Validated accommodation search request.
 * @returns Configured ToolLoopAgent for accommodation search.
 *
 * @example
 * ```typescript
 * const { agent } = createAccommodationAgent(deps, config, {
 *   destination: "Paris, France",
 *   checkIn: "2025-03-15",
 *   checkOut: "2025-03-20",
 *   guests: 2,
 * });
 *
 * // Stream the response
 * return createAgentUIStreamResponse({
 *   agent,
 *   messages: [{ role: "user", content: "Find hotels" }],
 * });
 * ```
 */
export function createAccommodationAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: AccommodationSearchRequest
): TripSageAgentResult {
  const params = extractAgentParameters(config);
  const instructions = buildAccommodationPrompt({
    checkIn: input.checkIn,
    checkOut: input.checkOut,
    destination: input.destination,
    guests: input.guests,
  });

  // Token budgeting: clamp max output tokens based on prompt length
  const userPrompt = `Find stays and summarize. Always return JSON with schemaVersion="${STAY_SCHEMA_VERSION}" and sources[]. Parameters: ${JSON.stringify(
    input
  )}`;
  const schemaMessage: ChatMessage = { content: userPrompt, role: "user" };
  const clampMessages: ChatMessage[] = [
    { content: instructions, role: "system" },
    schemaMessage,
  ];
  const { maxTokens } = clampMaxTokens(clampMessages, params.maxTokens, deps.modelId);

  return createTripSageAgent(deps, {
    agentType: "accommodationSearch",
    defaultMessages: [schemaMessage],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps: params.maxSteps,
    name: "Accommodation Search Agent",
    temperature: params.temperature,
    tools: buildAccommodationTools(deps.identifier),
    topP: params.topP,
  });
}

/** Exported type for the accommodation agent's tool set. */
export type AccommodationAgentTools = ReturnType<typeof buildAccommodationTools>;
