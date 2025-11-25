/**
 * @fileoverview Destination research agent using AI SDK v6 streaming.
 *
 * Wraps destination research tools (web search, crawl, POI lookup, weather,
 * safety) with guardrails (caching, rate limiting) and executes streaming
 * text generation to research destinations. Returns structured results
 * conforming to the destination research result schema.
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
import type { LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText } from "ai";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildDestinationPrompt } from "@/prompts/agents";

const DESTINATION_TOOLS = {
  crawlSite,
  getCurrentWeather,
  getTravelAdvisory,
  lookupPoiContext,
  webSearch,
  webSearchBatch,
} satisfies ToolSet;

/**
 * Execute the destination agent with AI SDK v6 streaming.
 *
 * Builds system instructions and messages, wraps core tools with guardrails,
 * and streams a model-guided tool loop to produce results structured per
 * `dest.v1` schema.
 *
 * @param deps Language model, model identifier, and request-scoped utilities.
 * @param input Validated destination research request.
 * @returns AI SDK stream result for UI consumption.
 */
export function runDestinationAgent(
  deps: {
    model: LanguageModel;
    modelId: string;
  },
  config: import("@schemas/configuration").AgentConfig,
  input: DestinationResearchRequest
) {
  const instructions = buildDestinationPrompt(input);
  const userPrompt = `Research destination and summarize. Always return JSON with schemaVersion="dest.v1" and sources[]. Parameters: ${JSON.stringify(
    input
  )}`;

  // Token budgeting: clamp max output tokens based on prompt length
  const messages: ChatMessage[] = [
    { content: instructions, role: "system" },
    { content: userPrompt, role: "user" },
  ];
  const desiredMaxTokens = config.parameters.maxTokens ?? 4096;
  const { maxTokens } = clampMaxTokens(messages, desiredMaxTokens, deps.modelId);

  return streamText({
    maxOutputTokens: maxTokens,
    messages: [
      { content: instructions, role: "system" },
      { content: userPrompt, role: "user" },
    ],
    model: deps.model,
    stopWhen: stepCountIs(15),
    temperature: config.parameters.temperature ?? 0.3,
    tools: DESTINATION_TOOLS,
    topP: config.parameters.topP,
  });
}
