/**
 * @fileoverview Accommodation search agent using AI SDK v6 streaming.
 *
 * Wraps accommodation search tools (search, geocode, POI lookup) with
 * guardrails (caching, rate limiting) and executes streaming text generation
 * to find and summarize accommodation options. Returns structured results
 * conforming to the accommodation search result schema.
 */

import "server-only";

import {
  bookAccommodation,
  checkAvailability,
  getAccommodationDetails,
  searchAccommodations,
} from "@ai/tools";
import type { AccommodationSearchRequest } from "@schemas/agents";
import type { LanguageModel, ToolSet } from "ai";
import { streamText } from "ai";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildAccommodationPrompt } from "@/prompts/agents";

const ACCOMMODATION_TOOLS = {
  bookAccommodation,
  checkAvailability,
  getAccommodationDetails,
  searchAccommodations,
} satisfies ToolSet;

/**
 * Execute the accommodation agent with AI SDK v6 streaming.
 *
 * @param deps Language model, model identifier, and rate-limit identifier.
 * @param input Validated accommodation search request.
 */
export function runAccommodationAgent(
  deps: { model: LanguageModel; modelId: string; identifier: string },
  config: import("@schemas/configuration").AgentConfig,
  input: AccommodationSearchRequest
) {
  const instructions = buildAccommodationPrompt({
    checkIn: input.checkIn,
    checkOut: input.checkOut,
    destination: input.destination,
    guests: input.guests,
  });
  const userPrompt = `Find stays and summarize. Always return JSON with schemaVersion="stay.v1" and sources[]. Parameters: ${JSON.stringify(
    input
  )}`;

  // Token budgeting: clamp max output tokens based on prompt length
  const messages: ChatMessage[] = [
    { content: instructions, role: "system" },
    { content: userPrompt, role: "user" },
  ];
  const desiredMaxTokens = config.parameters.maxTokens ?? 4096;
  const { maxTokens } = clampMaxTokens(messages, desiredMaxTokens, deps.modelId);

  const callOptions = {
    maxOutputTokens: maxTokens,
    messages: [
      { content: instructions, role: "system" },
      { content: userPrompt, role: "user" },
    ],
    model: deps.model,
    temperature: config.parameters.temperature ?? 0.3,
    tools: ACCOMMODATION_TOOLS,
    topP: config.parameters.topP,
  } satisfies Parameters<typeof streamText>[0];

  return streamText({
    maxSteps: 10,
    ...callOptions,
  } as Parameters<typeof streamText>[0] & { maxSteps: number });
}
