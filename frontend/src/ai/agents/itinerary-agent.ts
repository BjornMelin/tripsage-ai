/**
 * @fileoverview Itinerary planning agent for travel plans.
 *
 * Reusable ToolLoopAgent that researches destinations, gathers POI information,
 * and creates day-by-day travel plans via multi-step tool calling with phased
 * tool selection for research, planning, and persistence.
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
 * Creates an itinerary planning agent with phased tool selection.
 *
 * Phases:
 * - Phase 1: Research destination via web search and POI lookup
 * - Phase 2: Create the travel plan structure
 * - Phase 3: Save and finalize the plan
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
 * const stream = agent.stream({ prompt: "Plan my trip" });
 * ```
 */
export function createItineraryAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: ItineraryPlanRequest
): TripSageAgentResult<typeof ITINERARY_TOOLS> {
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
  const maxSteps = Math.max(params.maxSteps, 15);

  return createTripSageAgent<typeof ITINERARY_TOOLS>(deps, {
    agentType: "itineraryPlanning",
    defaultMessages: [schemaMessage],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps,
    name: "Itinerary Planning Agent",
    // Note: For structured output, pass Output.object({ schema: itineraryPlanResultSchema })
    // when calling agent.generate() or agent.stream()
    // Phased tool selection for itinerary workflow
    prepareStep: ({ stepNumber }) => {
      // Phase 1 (steps 0-6): Research destination
      if (stepNumber <= 6) {
        return {
          activeTools: ["webSearch", "webSearchBatch", "lookupPoiContext"],
        };
      }
      // Phase 2 (steps 7-11): Create the plan
      if (stepNumber <= 11) {
        return {
          activeTools: ["createTravelPlan", "lookupPoiContext"],
        };
      }
      // Phase 3 (steps 12+): Save and finalize
      return {
        activeTools: ["saveTravelPlan", "createTravelPlan"],
      };
    },
    temperature: params.temperature,
    tools: ITINERARY_TOOLS,
    topP: params.topP,
  });
}

/** Exported type for the itinerary agent's tool set. */
export type ItineraryAgentTools = typeof ITINERARY_TOOLS;
