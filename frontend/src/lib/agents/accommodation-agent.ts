/**
 * @fileoverview Accommodation search agent using AI SDK v6 streaming.
 *
 * Wraps accommodation search tools (search, geocode, POI lookup) with
 * guardrails (caching, rate limiting) and executes streaming text generation
 * to find and summarize accommodation options. Returns structured results
 * conforming to the accommodation search result schema.
 */

import "server-only";

import { toolRegistry } from "@ai/tools";
import type { AccommodationSearchRequest } from "@schemas/agents";
import type { LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText } from "ai";
import { createAiTool } from "@ai/lib/tool-factory";
import { getRegistryTool, invokeTool } from "@/lib/agents/registry-utils";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildAccommodationPrompt } from "@/prompts/agents";
import { buildRateLimit } from "@/lib/ratelimit/config";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import {
  accommodationBookingInputSchema,
  accommodationCheckAvailabilityInputSchema,
  accommodationDetailsInputSchema,
  accommodationSearchInputSchema,
  type AccommodationBookingRequest,
  type AccommodationBookingResult,
  type AccommodationCheckAvailabilityParams,
  type AccommodationCheckAvailabilityResult,
  type AccommodationDetailsParams,
  type AccommodationDetailsResult,
  type AccommodationSearchParams,
  type AccommodationSearchResult,
} from "@schemas/accommodations";

function buildAccommodationTools(identifier: string): ToolSet {
  type SearchInput = AccommodationSearchParams;
  type SearchResult = AccommodationSearchResult;
  type DetailsInput = AccommodationDetailsParams;
  type DetailsResult = AccommodationDetailsResult;
  type AvailabilityInput = AccommodationCheckAvailabilityParams;
  type AvailabilityResult = AccommodationCheckAvailabilityResult;
  type BookingInput = AccommodationBookingRequest;
  type BookingResult = AccommodationBookingResult;

  const searchTool = getRegistryTool<SearchInput, SearchResult>(
    toolRegistry,
    "searchAccommodations"
  );
  const detailsTool = getRegistryTool<DetailsInput, DetailsResult>(
    toolRegistry,
    "getAccommodationDetails"
  );
  const availabilityTool = getRegistryTool<AvailabilityInput, AvailabilityResult>(
    toolRegistry,
    "checkAvailability"
  );
  const bookingTool = getRegistryTool<BookingInput, BookingResult>(
    toolRegistry,
    "bookAccommodation"
  );

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
  });

  const getAccommodationDetails = createAiTool({
    description: detailsTool.description ?? "Get accommodation details",
    execute: (params, callOptions) => invokeTool(detailsTool, params, callOptions),
    guardrails: {
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
  });

  return {
    bookAccommodation,
    checkAvailability,
    getAccommodationDetails,
    searchAccommodations,
  } satisfies ToolSet;
}

/**
 * Execute the accommodation agent with AI SDK v6 streaming.
 *
 * @param deps Language model, model identifier, and rate-limit identifier.
 * @param input Validated accommodation search request.
 */
export function runAccommodationAgent(
  deps: { model: LanguageModel; modelId: string; identifier: string },
  config: import("@schemas/configuration").AgentConfig,
  input: AccommodationSearchRequest
) {
  const instructions = buildAccommodationPrompt({
    checkIn: input.checkIn,
    checkOut: input.checkOut,
    destination: input.destination,
    guests: input.guests,
  });
  const userPrompt = `Find stays and summarize. Always return JSON with schemaVersion="stay.v1" and sources[]. Parameters: ${JSON.stringify(
    input
  )}`;

  // Token budgeting: clamp max output tokens based on prompt length
  const messages: ChatMessage[] = [
    { content: instructions, role: "system" },
    { content: userPrompt, role: "user" },
  ];
  const desiredMaxTokens = config.parameters.maxTokens ?? 4096;
  const { maxTokens } = clampMaxTokens(messages, desiredMaxTokens, deps.modelId);

  const callOptions = {
    maxOutputTokens: maxTokens,
    messages: [
      { content: instructions, role: "system" },
      { content: userPrompt, role: "user" },
    ],
    model: deps.model,
    temperature: config.parameters.temperature ?? 0.3,
    tools: buildAccommodationTools(deps.identifier),
    topP: config.parameters.topP,
  } satisfies Parameters<typeof streamText>[0];

  return withTelemetrySpan(
    "agent.accommodation.run",
    {
      attributes: {
        modelId: deps.modelId,
        identifier: deps.identifier,
      },
    },
    () =>
      streamText({
        ...callOptions,
        stopWhen: stepCountIs(10),
      })
  );
}
