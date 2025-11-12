/**
 * @fileoverview Flight search agent using AI SDK v6 streaming.
 *
 * Wraps flight search tools (search, geocode) with guardrails (caching, rate
 * limiting) and executes streaming text generation to find and summarize flight
 * options. Returns structured results conforming to the flight search result
 * schema.
 */

import "server-only";

import type { LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText, tool } from "ai";
import { z } from "zod";

import { runWithGuardrails } from "@/lib/agents/runtime";
import { buildFlightRateLimit } from "@/lib/ratelimit/flight";
import { toolRegistry } from "@/lib/tools";
import { buildFlightPrompt } from "@/prompts/agents";
import type { FlightSearchRequest } from "@/schemas/agents";

/**
 * Create wrapped tools for flight agent with guardrails.
 *
 * Applies validation, caching, and rate limits around core tool execute
 * functions. The identifier should be per-user when authenticated or a
 * hashed IP fallback.
 *
 * @param identifier Stable identifier for rate limiting.
 * @returns AI SDK ToolSet for use with streamText.
 */
function buildFlightTools(identifier: string): ToolSet {
  // Access tool registry with proper typing; runtime guardrails perform validation.
  // Tools are typed as unknown in registry, so we use type assertions for safe access.
  type ToolLike = {
    description?: string;
    execute: (params: unknown) => Promise<unknown>;
  };

  const flightTool = toolRegistry.searchFlights as unknown as ToolLike;
  const geocodeTool = toolRegistry.geocode as unknown as ToolLike;

  const searchFlights = tool({
    description: flightTool.description ?? "Search flights",
    execute: async (params: unknown) => {
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:flight:search",
            ttlSeconds: 60 * 30,
          },
          rateLimit: buildFlightRateLimit(identifier),
          tool: "searchFlights",
          workflow: "flight_search",
        },
        params,
        async (validated) => flightTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  const geocode = tool({
    description: geocodeTool.description ?? "Geocode address",
    execute: async (params: unknown) => {
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:flight:geocode",
            ttlSeconds: 60 * 60,
          },
          rateLimit: buildFlightRateLimit(identifier),
          tool: "geocode",
          workflow: "flight_search",
        },
        params,
        async (validated) => geocodeTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  return { geocode, searchFlights } satisfies ToolSet;
}

/**
 * Execute the flight agent with AI SDK v6 streaming.
 *
 * Builds system instructions and messages, wraps core tools with guardrails,
 * and streams a model-guided tool loop to produce results structured per
 * `flight.v1` schema.
 *
 * @param deps Language model and request-scoped utilities.
 * @param input Validated flight search request.
 * @returns AI SDK stream result for UI consumption.
 */
export function runFlightAgent(
  deps: {
    model: LanguageModel;
    identifier: string;
  },
  input: FlightSearchRequest
) {
  const instructions = buildFlightPrompt(input);
  return streamText({
    model: deps.model,
    prompt: `Find flight offers and summarize. Always return JSON with schemaVersion="flight.v1" and sources[]. Parameters: ${JSON.stringify(
      input
    )}`,
    stopWhen: stepCountIs(10),
    system: instructions,
    tools: buildFlightTools(deps.identifier),
  });
}
