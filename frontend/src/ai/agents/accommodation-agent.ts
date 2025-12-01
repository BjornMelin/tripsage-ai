/**
 * @fileoverview Accommodation search agent using AI SDK v6 ToolLoopAgent.
 *
 * Creates a reusable accommodation search agent that autonomously searches
 * for properties, retrieves details, checks availability, and handles
 * bookings using multi-step tool calling.
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
    tools: ACCOMMODATION_TOOLS,
    topP: params.topP,
  }) as unknown as TripSageAgentResult;
}

/** Exported type for the accommodation agent's tool set. */
export type AccommodationAgentTools = typeof ACCOMMODATION_TOOLS;
