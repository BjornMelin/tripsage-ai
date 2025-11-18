/**
 * @fileoverview Accommodation search agent using AI SDK v6 streaming.
 *
 * Wraps accommodation search tools (search, geocode, POI lookup) with
 * guardrails (caching, rate limiting) and executes streaming text generation
 * to find and summarize accommodation options. Returns structured results
 * conforming to the accommodation search result schema.
 */

import "server-only";

import { createHash } from "node:crypto";
import type { FlexibleSchema, LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText } from "ai";

import { createAiTool } from "@/lib/ai/tool-factory";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { AccommodationSearchRequest } from "@/lib/schemas/agents";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { toolRegistry } from "@/lib/tools";
import { searchAccommodationsInputSchema } from "@/lib/tools/accommodations";
import { TOOL_ERROR_CODES } from "@/lib/tools/errors";
import { lookupPoiInputSchema } from "@/lib/tools/google-places";
import { geocodeInputSchema } from "@/lib/tools/maps";
import { buildAccommodationPrompt } from "@/prompts/agents";

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
    execute?: (params: unknown, context: unknown) => Promise<unknown>;
  };

  const searchTool = toolRegistry.searchAccommodations as unknown as ToolLike;
  const geocodeTool = toolRegistry.geocode as unknown as ToolLike;
  const poiTool = toolRegistry.lookupPoiContext as unknown as ToolLike;

  const rateLimit = buildRateLimit("accommodationSearch", identifier);

  const makeAgentTool = <SchemaType extends FlexibleSchema<unknown>>(options: {
    baseTool: ToolLike;
    cacheNamespace: string;
    cacheTtlSeconds: number;
    descriptionFallback: string;
    name: string;
    rateLimitPrefix: string;
    schema: SchemaType;
  }) =>
    createAiTool({
      description: options.baseTool.description ?? options.descriptionFallback,
      execute: (params, context) => {
        if (typeof options.baseTool.execute !== "function") {
          throw new Error(`Tool ${options.name} missing execute binding`);
        }
        return options.baseTool.execute(params, context);
      },
      guardrails: {
        cache: {
          key: (params) => hashAgentCacheKey(params),
          namespace: options.cacheNamespace,
          ttlSeconds: options.cacheTtlSeconds,
        },
        rateLimit: {
          errorCode: TOOL_ERROR_CODES.accomSearchRateLimited,
          identifier: () => rateLimit.identifier,
          limit: rateLimit.limit,
          prefix: options.rateLimitPrefix,
          window: rateLimit.window,
        },
      },
      inputSchema: options.schema,
      name: options.name,
    });

  const searchAccommodations = makeAgentTool({
    baseTool: searchTool,
    cacheNamespace: "agent:accom:search",
    cacheTtlSeconds: 60 * 30,
    descriptionFallback: "Search stays",
    name: "agentSearchAccommodations",
    rateLimitPrefix: "ratelimit:agent:accom:search",
    schema: searchAccommodationsInputSchema,
  });

  const geocode = makeAgentTool({
    baseTool: geocodeTool,
    cacheNamespace: "agent:accom:geocode",
    cacheTtlSeconds: 60 * 60,
    descriptionFallback: "Geocode address",
    name: "agentGeocode",
    rateLimitPrefix: "ratelimit:agent:accom:geocode",
    schema: geocodeInputSchema,
  });

  const lookupPoiContext = makeAgentTool({
    baseTool: poiTool,
    cacheNamespace: "agent:accom:poi",
    cacheTtlSeconds: 60 * 10,
    descriptionFallback: "Lookup POIs",
    name: "agentLookupPoiContext",
    rateLimitPrefix: "ratelimit:agent:accom:poi",
    schema: lookupPoiInputSchema,
  });

  return { geocode, lookupPoiContext, searchAccommodations } satisfies ToolSet;
}

function hashAgentCacheKey(input: unknown): string {
  return createHash("sha256").update(JSON.stringify(input)).digest("hex").slice(0, 16);
}

/**
 * Execute the accommodation agent with AI SDK v6 streaming.
 *
 * @param deps Language model, model identifier, and rate-limit identifier.
 * @param input Validated accommodation search request.
 */
export function runAccommodationAgent(
  deps: { model: LanguageModel; modelId: string; identifier: string },
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
  const desiredMaxTokens = 4096; // Default for agent responses
  const { maxTokens } = clampMaxTokens(messages, desiredMaxTokens, deps.modelId);

  return streamText({
    maxOutputTokens: maxTokens,
    model: deps.model,
    prompt: userPrompt,
    stopWhen: stepCountIs(10),
    system: instructions,
    temperature: 0.3,
    tools: buildAccommodationTools(deps.identifier),
  });
}
