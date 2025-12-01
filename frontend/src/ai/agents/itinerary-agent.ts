/**
 * @fileoverview Itinerary planning agent using AI SDK v6 ToolLoopAgent.
 *
 * Creates a reusable itinerary planning agent that autonomously researches
 * destinations, gathers POI information, and creates day-by-day travel
 * plans using multi-step tool calling.
 */

import "server-only";

import {
  createTravelPlan,
  lookupPoiContext,
  saveTravelPlan,
  webSearch,
  webSearchBatch,
} from "@ai/tools";
import type { ItineraryPlanRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import type { ToolSet } from "ai";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildItineraryPrompt } from "@/prompts/agents";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";
import { extractAgentParameters } from "./types";

/**
 * Tools available to the itinerary planning agent.
 *
 * These tools are imported from @ai/tools where they are already
 * created with createAiTool and have built-in guardrails for caching,
 * rate limiting, and telemetry.
 */
const ITINERARY_TOOLS = {
  createTravelPlan,
  lookupPoiContext,
  saveTravelPlan,
  webSearch,
  webSearchBatch,
} satisfies ToolSet;

/**
 * Creates an itinerary planning agent using AI SDK v6 ToolLoopAgent.
 *
 * The agent autonomously researches destinations, gathers POI information,
 * and creates day-by-day travel plans through multi-step tool calling.
 * Returns a reusable agent instance.
 *
 * @param deps - Runtime dependencies including model and identifiers.
 * @param config - Agent configuration from database.
 * @param input - Validated itinerary plan request.
 * @returns Configured ToolLoopAgent for itinerary planning.
 *
 * @example
 * ```typescript
 * const { agent } = createItineraryAgent(deps, config, {
 *   destination: "Rome, Italy",
 *   durationDays: 5,
 *   interests: ["history", "food", "art"],
 * });
 *
 * // Stream the response
 * return createAgentUIStreamResponse({
 *   agent,
 *   messages: [{ role: "user", content: "Plan my trip" }],
 * });
 * ```
 */
export function createItineraryAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: ItineraryPlanRequest
): TripSageAgentResult {
  const params = extractAgentParameters(config);
  const instructions = buildItineraryPrompt(input);

  // Token budgeting: clamp max output tokens based on prompt length
  const userPrompt = `Generate itinerary plan and summarize. Always return JSON with schemaVersion="itin.v1" and days[]. Parameters: ${JSON.stringify(
    input
  )}`;
  const schemaMessage: ChatMessage = { content: userPrompt, role: "user" };
  const clampMessages: ChatMessage[] = [
    { content: instructions, role: "system" },
    schemaMessage,
  ];
  const { maxTokens } = clampMaxTokens(clampMessages, params.maxTokens, deps.modelId);

  // Itinerary planning may need more steps for comprehensive plans
  // (researching POIs, creating day-by-day schedules, saving plan)
  const maxSteps = Math.max(params.maxSteps, 15);

  return createTripSageAgent(deps, {
    agentType: "itineraryPlanning",
    defaultMessages: [schemaMessage],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps,
    name: "Itinerary Planning Agent",
    temperature: params.temperature,
    tools: ITINERARY_TOOLS,
    topP: params.topP,
  }) as unknown as TripSageAgentResult;
}

/** Exported type for the itinerary agent's tool set. */
export type ItineraryAgentTools = typeof ITINERARY_TOOLS;
