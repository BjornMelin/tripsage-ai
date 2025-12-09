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
import { wrapToolsWithUserId } from "@ai/tools/server/injection";
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
 * Base tools available to the itinerary planning agent.
 *
 * These tools are imported from @ai/tools where they are already
 * created with createAiTool and have built-in guardrails for caching,
 * rate limiting, and telemetry.
 */
const BASE_ITINERARY_TOOLS = {
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
): TripSageAgentResult<typeof BASE_ITINERARY_TOOLS> {
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

  // Define phased tool sets with type safety
  type ToolName = keyof typeof BASE_ITINERARY_TOOLS;
  const ResearchTools: ToolName[] = ["webSearch", "webSearchBatch", "lookupPoiContext"];
  const PlanningTools: ToolName[] = ["createTravelPlan", "lookupPoiContext"];
  const SaveTools: ToolName[] = ["saveTravelPlan", "createTravelPlan"];

  // Compute phase boundaries from maxSteps (40% research, 33% planning, 27% save)
  const phase1End = Math.floor(maxSteps * 0.4);
  const phase2End = Math.floor(maxSteps * 0.73);

  if (!deps.userId) {
    throw new Error(
      "Itinerary agent requires a valid userId for user-scoped tool operations (createTravelPlan, saveTravelPlan)"
    );
  }

  // Wrap tools that require userId for user-scoped operations
  // createTravelPlan and saveTravelPlan require userId in their input schema
  const itineraryTools = wrapToolsWithUserId(
    BASE_ITINERARY_TOOLS,
    deps.userId,
    ["createTravelPlan", "saveTravelPlan"],
    deps.sessionId
  );

  return createTripSageAgent<typeof BASE_ITINERARY_TOOLS>(deps, {
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
      // Phase 1: Research destination
      if (stepNumber <= phase1End) {
        return {
          activeTools: ResearchTools,
        };
      }
      // Phase 2: Create the plan
      if (stepNumber <= phase2End) {
        return {
          activeTools: PlanningTools,
        };
      }
      // Phase 3: Save and finalize
      return {
        activeTools: SaveTools,
      };
    },
    temperature: params.temperature,
    tools: itineraryTools,
    topP: params.topP,
  });
}

/** Exported type for the itinerary agent's tool set. */
export type ItineraryAgentTools = typeof BASE_ITINERARY_TOOLS;
