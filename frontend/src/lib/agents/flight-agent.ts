/**
 * @fileoverview Flight search agent using AI SDK v6 streaming.
 *
 * Wraps flight search tools (search, geocode) with guardrails (caching, rate
 * limiting) and executes streaming text generation to find and summarize flight
 * options. Returns structured results conforming to the flight search result
 * schema.
 */

import "server-only";

import { distanceMatrix, geocode, lookupPoiContext, searchFlights } from "@ai/tools";
import type { FlightSearchRequest } from "@schemas/flights";
import type { LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText } from "ai";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildFlightPrompt } from "@/prompts/agents";

const FLIGHT_TOOLS = {
  distanceMatrix,
  geocode,
  lookupPoiContext,
  searchFlights,
} satisfies ToolSet;

/**
 * Execute the flight agent with AI SDK v6 streaming.
 *
 * Builds system instructions and messages, wraps core tools with guardrails,
 * and streams a model-guided tool loop to produce results structured per
 * `flight.v1` schema.
 *
 * @param deps Language model, model identifier, and request-scoped utilities.
 * @param input Validated flight search request.
 * @returns AI SDK stream result for UI consumption.
 */
export function runFlightAgent(
  deps: {
    model: LanguageModel;
    modelId: string;
  },
  input: FlightSearchRequest
) {
  const instructions = buildFlightPrompt(input);
  const userPrompt = `Find flight offers and summarize. Always return JSON with schemaVersion="flight.v1" and sources[]. Parameters: ${JSON.stringify(
    input
  )}`;

  // Token budgeting: clamp max output tokens based on prompt length
  const messages: ChatMessage[] = [
    { content: instructions, role: "system" },
    { content: userPrompt, role: "user" },
  ];
  const desiredMaxTokens = 4096; // Default for agent responses
  const { maxTokens } = clampMaxTokens(messages, desiredMaxTokens, deps.modelId);

  return streamText({
    maxOutputTokens: maxTokens,
    messages: [
      { content: instructions, role: "system" },
      { content: userPrompt, role: "user" },
    ],
    model: deps.model,
    stopWhen: stepCountIs(10),
    temperature: 0.3,
    tools: FLIGHT_TOOLS,
  });
}
