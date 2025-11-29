/**
 * @fileoverview Accommodation search agent using AI SDK v6 streaming.
 *
 * Executes accommodation search via tools (search, details, availability, booking)
 * with rate limiting and streaming text generation. Returns structured results
 * conforming to accommodation search schema.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { toolRegistry } from "@ai/tools";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
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
import type { LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText } from "ai";
import { getRegistryTool, invokeTool } from "@/lib/agents/registry-utils";
import { buildRateLimit } from "@/lib/ratelimit/config";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildAccommodationPrompt } from "@/prompts/agents";

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

  const maxSteps =
    "maxSteps" in config.parameters && typeof config.parameters.maxSteps === "number"
      ? config.parameters.maxSteps
      : 10;

  const callOptions = {
    maxOutputTokens: maxTokens,
    messages,
    model: deps.model,
    temperature: config.parameters.temperature ?? 0.3,
    tools: buildAccommodationTools(deps.identifier),
    topP: config.parameters.topP,
  } satisfies Parameters<typeof streamText>[0];

  return withTelemetrySpan(
    "agent.accommodation.run",
    {
      attributes: {
        identifier: deps.identifier,
        modelId: deps.modelId,
      },
    },
    () =>
      streamText({
        ...callOptions,
        stopWhen: stepCountIs(maxSteps),
      })
  );
}

/** Exported type for the accommodation agent's tool set. */
export type AccommodationTools = ReturnType<typeof buildAccommodationTools>;

/** Exported type for typed tool results from accommodation agent. */
export type AccommodationToolResult =
  import("@ai/lib/tool-type-utils").ExtractToolResult<AccommodationTools>;
