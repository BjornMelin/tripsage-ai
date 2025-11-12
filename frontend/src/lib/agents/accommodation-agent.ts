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

import { buildGuardedTool } from "@/lib/agents/guarded-tool";
import { buildRateLimit } from "@/lib/ratelimit/config";
import { toolRegistry } from "@/lib/tools";
import { searchAccommodationsInputSchema } from "@/lib/tools/accommodations";
import { geocodeInputSchema } from "@/lib/tools/maps";
import { lookupPoiInputSchema } from "@/lib/tools/opentripmap";
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

  const rateLimit = buildRateLimit("accommodationSearch", identifier);

  const guardedSearchAccommodations = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:accom:search",
      ttlSeconds: 60 * 30,
    },
    execute: async (params: unknown) => searchTool.execute(params),
    rateLimit,
    schema: searchAccommodationsInputSchema,
    toolKey: "searchAccommodations",
    workflow: "accommodationSearch",
  });

  const guardedGeocode = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:accom:geocode",
      ttlSeconds: 60 * 60,
    },
    execute: async (params: unknown) => geocodeTool.execute(params),
    rateLimit,
    schema: geocodeInputSchema,
    toolKey: "geocode",
    workflow: "accommodationSearch",
  });

  const guardedLookupPoi = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:accom:poi",
      ttlSeconds: 60 * 10,
    },
    execute: async (params: unknown) => poiTool.execute(params),
    rateLimit,
    schema: lookupPoiInputSchema,
    toolKey: "lookupPoiContext",
    workflow: "accommodationSearch",
  });

  const searchAccommodations = tool({
    description: searchTool.description ?? "Search stays",
    execute: guardedSearchAccommodations,
    inputSchema: searchAccommodationsInputSchema,
  });

  const geocode = tool({
    description: geocodeTool.description ?? "Geocode address",
    execute: guardedGeocode,
    inputSchema: geocodeInputSchema,
  });

  const lookupPoiContext = tool({
    description: poiTool.description ?? "Lookup POIs",
    execute: guardedLookupPoi,
    inputSchema: lookupPoiInputSchema,
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
