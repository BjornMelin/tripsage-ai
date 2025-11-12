/**
 * @fileoverview Accommodation search agent using AI SDK v6 streaming.
 *
 * Wraps accommodation search tools (search, geocode, POI lookup) with
 * guardrails (caching, rate limiting) and executes streaming text generation
 * to find and summarize accommodation options. Returns structured results
 * conforming to the accommodation search result schema.
 */

import "server-only";

import type { LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText, tool } from "ai";
import { z } from "zod";

import { runWithGuardrails } from "@/lib/agents/runtime";
import { buildAccommodationRateLimit } from "@/lib/ratelimit/accommodation";
import { toolRegistry } from "@/lib/tools";
import { buildAccommodationPrompt } from "@/prompts/agents";
import type { AccommodationSearchRequest } from "@/schemas/agents";

/**
 * Create wrapped tools for accommodation agent with guardrails.
 *
 * @param identifier Stable identifier for rate limiting.
 * @returns AI SDK ToolSet for use with streamText.
 */
function buildAccommodationTools(identifier: string): ToolSet {
  // Access tool registry with proper typing; runtime guardrails perform validation.
  // Tools are typed as unknown in registry, so we use type assertions for safe access.
  type ToolLike = {
    description?: string;
    execute: (params: unknown) => Promise<unknown>;
  };

  const searchTool = toolRegistry.searchAccommodations as unknown as ToolLike;
  const geocodeTool = toolRegistry.geocode as unknown as ToolLike;
  const poiTool = toolRegistry.lookupPoiContext as unknown as ToolLike;

  const searchAccommodations = tool({
    description: searchTool.description ?? "Search stays",
    execute: async (params: unknown) => {
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:accom:search",
            ttlSeconds: 60 * 30,
          },
          rateLimit: buildAccommodationRateLimit(identifier),
          tool: "searchAccommodations",
          workflow: "accommodation_search",
        },
        params,
        async (validated) => searchTool.execute(validated)
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
            key: "agent:accom:geocode",
            ttlSeconds: 60 * 60,
          },
          rateLimit: buildAccommodationRateLimit(identifier),
          tool: "geocode",
          workflow: "accommodation_search",
        },
        params,
        async (validated) => geocodeTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  const lookupPoiContext = tool({
    description: poiTool.description ?? "Lookup POIs",
    execute: async (params: unknown) => {
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:accom:poi",
            ttlSeconds: 60 * 10,
          },
          rateLimit: buildAccommodationRateLimit(identifier),
          tool: "lookupPoiContext",
          workflow: "accommodation_search",
        },
        params,
        async (validated) => poiTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  return { geocode, lookupPoiContext, searchAccommodations } satisfies ToolSet;
}

/**
 * Execute the accommodation agent with AI SDK v6 streaming.
 *
 * @param deps Language model and rate-limit identifier.
 * @param input Validated accommodation search request.
 */
export function runAccommodationAgent(
  deps: { model: LanguageModel; identifier: string },
  input: AccommodationSearchRequest
) {
  const instructions = buildAccommodationPrompt({
    checkIn: input.checkIn,
    checkOut: input.checkOut,
    destination: input.destination,
    guests: input.guests,
  });
  return streamText({
    model: deps.model,
    prompt: `Find stays and summarize. Always return JSON with schemaVersion="stay.v1" and sources[]. Parameters: ${JSON.stringify(
      input
    )}`,
    stopWhen: stepCountIs(10),
    system: instructions,
    temperature: 0.3,
    tools: buildAccommodationTools(deps.identifier),
  });
}
