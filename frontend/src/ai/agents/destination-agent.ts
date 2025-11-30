/**
 * @fileoverview Destination research agent using AI SDK v6 ToolLoopAgent.
 *
 * Creates a reusable destination research agent that autonomously gathers
 * information about travel destinations including attractions, weather,
 * safety advisories, and local insights using multi-step tool calling.
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
 * Tools available to the destination research agent.
 *
 * Includes web search, site crawling, weather lookup, travel advisory,
 * and POI discovery for comprehensive destination research.
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
 * Creates a destination research agent using AI SDK v6 ToolLoopAgent.
 *
 * The agent autonomously researches travel destinations, gathering
 * information about attractions, weather, safety, culture, and local
 * insights through multi-step tool calling. Returns a reusable agent
 * instance for streaming or one-shot generation.
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
 *
 * // Stream the response
 * return createAgentUIStreamResponse({
 *   agent,
 *   messages: [{ role: "user", content: "Research this destination" }],
 * });
 * ```
 */
export function createDestinationAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: DestinationResearchRequest
): TripSageAgentResult {
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

  // Destination research may need more steps for comprehensive gathering
  const maxSteps = Math.max(params.maxSteps, 15);

  return createTripSageAgent(deps, {
    agentType: "destinationResearch",
    defaultMessages: [schemaMessage],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps,
    name: "Destination Research Agent",
    temperature: params.temperature,
    tools: DESTINATION_TOOLS,
    topP: params.topP,
  });
}

/** Exported type for the destination agent's tool set. */
export type DestinationAgentTools = typeof DESTINATION_TOOLS;
