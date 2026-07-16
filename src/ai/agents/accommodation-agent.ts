/**
 * @fileoverview Accommodation search agent for travel planning.
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
import { buildAccommodationPrompt } from "@/prompts/agents";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";
import { extractAgentParameters, prepareSchemaPrompt } from "./types";

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
 * Encourages schema-versioned JSON payloads in the assistant text (schema cards) for UI rendering.
 *
 * @param deps - Runtime dependencies (model, identifiers).
 * @param config - Agent configuration from database.
 * @param input - Accommodation search request (destination, dates, guests).
 * @returns Configured agent and canonical UI messages for accommodation search.
 */
export function createAccommodationAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: AccommodationSearchRequest
): TripSageAgentResult<typeof ACCOMMODATION_TOOLS> {
  const params = extractAgentParameters(config);
  const instructions = buildAccommodationPrompt();

  const { maxOutputTokens, uiMessages } = prepareSchemaPrompt({
    instructions,
    maxOutputTokens: params.maxOutputTokens,
    modelId: deps.modelId,
    userPrompt: `Find stays and summarize. Always return JSON with schemaVersion="${STAY_SCHEMA_VERSION}" and sources[]. Parameters: ${JSON.stringify(
      input
    )}`,
  });

  return createTripSageAgent<typeof ACCOMMODATION_TOOLS>(deps, {
    agentType: "accommodationSearch",
    instructions,
    maxOutputTokens,
    name: "Accommodation Search Agent",
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
    stepLimit: params.stepLimit,
    temperature: params.temperature,
    tools: ACCOMMODATION_TOOLS,
    topP: params.topP,
    uiMessages,
  });
}
