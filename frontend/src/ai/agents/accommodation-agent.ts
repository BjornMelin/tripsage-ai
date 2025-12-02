/**
 * @fileoverview Accommodation search agent for travel planning.
 *
 * Reusable ToolLoopAgent that autonomously searches for properties, retrieves
 * details, checks availability, and handles bookings via multi-step tool calling.
 * Uses AI SDK v6 structured output and phased tool selection.
 */

import "server-only";

import {
  bookAccommodation,
  checkAvailability,
  getAccommodationDetails,
  searchAccommodations,
} from "@ai/tools";
import type { AccommodationSearchRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import type { ToolSet } from "ai";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildAccommodationPrompt } from "@/prompts/agents";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";
import { extractAgentParameters } from "./types";

/** Schema version for accommodation stay responses. */
const STAY_SCHEMA_VERSION = "stay.v1";

/**
 * Tools available to the accommodation search agent with built-in
 * guardrails for caching, rate limiting, and telemetry.
 */
const ACCOMMODATION_TOOLS = {
  bookAccommodation,
  checkAvailability,
  getAccommodationDetails,
  searchAccommodations,
} satisfies ToolSet;

/**
 * Creates an accommodation search agent for autonomous property search, availability checks, and bookings.
 *
 * Uses phased tool selection: search → details → availability/booking.
 * Returns structured AccommodationSearchResult via Output.object().
 *
 * @param deps - Runtime dependencies (model, identifiers).
 * @param config - Agent configuration from database.
 * @param input - Accommodation search request (destination, dates, guests).
 * @returns Configured ToolLoopAgent for accommodation search.
 */
export function createAccommodationAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: AccommodationSearchRequest
): TripSageAgentResult<typeof ACCOMMODATION_TOOLS> {
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

  return createTripSageAgent<typeof ACCOMMODATION_TOOLS>(deps, {
    agentType: "accommodationSearch",
    defaultMessages: [schemaMessage],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps: params.maxSteps,
    name: "Accommodation Search Agent",
    // Note: For structured output, pass Output.object({ schema: accommodationSearchResultSchema })
    // when calling agent.generate() or agent.stream()
    // Phased tool selection for accommodation workflow
    prepareStep: ({ stepNumber }) => {
      // Phase 1 (steps 0-2): Search for accommodations
      if (stepNumber <= 2) {
        return {
          activeTools: ["searchAccommodations"],
        };
      }
      // Phase 2 (steps 3-5): Get details for promising options
      if (stepNumber <= 5) {
        return {
          activeTools: ["searchAccommodations", "getAccommodationDetails"],
        };
      }
      // Phase 3 (steps 6+): Check availability and allow booking
      return {
        activeTools: [
          "getAccommodationDetails",
          "checkAvailability",
          "bookAccommodation",
        ],
      };
    },
    temperature: params.temperature,
    tools: ACCOMMODATION_TOOLS,
    topP: params.topP,
  });
}

/** Exported type for the accommodation agent's tool set. */
export type AccommodationAgentTools = typeof ACCOMMODATION_TOOLS;
