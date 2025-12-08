/**
 * @fileoverview Destination research agent for travel planning.
 *
 * Reusable ToolLoopAgent that gathers destination information including attractions,
 * weather, safety advisories, and local insights via multi-step tool calling.
 * Uses phased tool selection for comprehensive research workflows.
 */

import "server-only";

import {
  crawlSite,
  getCurrentWeather,
  getTravelAdvisory,
  lookupPoiContext,
  webSearch,
  webSearchBatch,
} from "@ai/tools";
import type { DestinationResearchRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import type { ToolSet } from "ai";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildDestinationPrompt } from "@/prompts/agents";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";
import { extractAgentParameters } from "./types";

/**
 * Tools available to the destination research agent with built-in
 * guardrails for caching, rate limiting, and telemetry.
 */
const DESTINATION_TOOLS = {
  crawlSite,
  getCurrentWeather,
  getTravelAdvisory,
  lookupPoiContext,
  webSearch,
  webSearchBatch,
} satisfies ToolSet;

/**
 * Creates a destination research agent for travel research.
 *
 * Returns a reusable ToolLoopAgent with phased tool selection:
 * - Phase 1: Initial search and context gathering
 * - Phase 2: Deep research via web crawling
 * - Phase 3: Weather and advisory checks
 *
 * @param deps - Runtime dependencies including model and identifiers.
 * @param config - Agent configuration from database.
 * @param input - Validated destination research request.
 * @returns Configured ToolLoopAgent for destination research.
 *
 * @example
 * ```typescript
 * const { agent } = createDestinationAgent(deps, config, {
 *   destination: "Kyoto, Japan",
 *   travelDates: "March 2025",
 *   specificInterests: ["temples", "cherry blossoms"],
 * });
 * const stream = agent.stream({ prompt: "Research this destination" });
 * ```
 */
export function createDestinationAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: DestinationResearchRequest
): TripSageAgentResult<typeof DESTINATION_TOOLS> {
  const params = extractAgentParameters(config);
  const instructions = buildDestinationPrompt(input);

  // Token budgeting: clamp max output tokens based on prompt length
  const userPrompt = `Research destination and summarize. Always return JSON with schemaVersion="dest.v1" and sources[]. Parameters: ${JSON.stringify(
    input
  )}`;
  const schemaMessage: ChatMessage = { content: userPrompt, role: "user" };
  const clampMessages: ChatMessage[] = [
    { content: instructions, role: "system" },
    schemaMessage,
  ];
  const { maxTokens } = clampMaxTokens(clampMessages, params.maxTokens, deps.modelId);

  // Destination research may need more steps for gathering
  const maxSteps = Math.max(params.maxSteps, 15);
  const phase1End = Math.max(4, Math.floor(maxSteps * 0.33));
  const phase2End = Math.max(phase1End + 1, Math.floor(maxSteps * 0.66));

  return createTripSageAgent<typeof DESTINATION_TOOLS>(deps, {
    agentType: "destinationResearch",
    defaultMessages: [schemaMessage],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps,
    name: "Destination Research Agent",
    // Note: For structured output, pass Output.object({ schema: destinationResearchResultSchema })
    // when calling agent.generate() or agent.stream()
    // Phased tool selection for destination research workflow
    prepareStep: ({ stepNumber }) => {
      // Phase 1: Initial search and POI context
      if (stepNumber <= phase1End) {
        return {
          activeTools: ["webSearch", "webSearchBatch", "lookupPoiContext"],
        };
      }
      // Phase 2: Deep research via crawling
      if (stepNumber <= phase2End) {
        return {
          activeTools: ["crawlSite", "webSearchBatch", "lookupPoiContext"],
        };
      }
      // Phase 3: Weather and safety information
      return {
        activeTools: ["getCurrentWeather", "getTravelAdvisory", "lookupPoiContext"],
      };
    },
    temperature: params.temperature,
    tools: DESTINATION_TOOLS,
    topP: params.topP,
  });
}

/** Exported type for the destination agent's tool set. */
export type DestinationAgentTools = typeof DESTINATION_TOOLS;
