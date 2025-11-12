/**
 * @fileoverview Itinerary planning agent using AI SDK v6 streaming.
 *
 * Wraps itinerary planning tools (web search, POI lookup, planning tools) with
 * guardrails (caching, rate limiting) and executes streaming text generation to
 * generate multi-day itineraries. Returns structured results conforming to the
 * itinerary plan result schema.
 */

import "server-only";

import type { LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText, tool } from "ai";
import { z } from "zod";

import { runWithGuardrails } from "@/lib/agents/runtime";
import { buildRateLimit } from "@/lib/ratelimit/config";
import { toolRegistry } from "@/lib/tools";
import { buildItineraryPrompt } from "@/prompts/agents";
import type { ItineraryPlanRequest } from "@/schemas/agents";

/**
 * Create wrapped tools for itinerary agent with guardrails.
 *
 * Applies validation, caching, and rate limits around core tool execute
 * functions. The identifier should be per-user when authenticated or a
 * hashed IP fallback.
 *
 * @param identifier Stable identifier for rate limiting.
 * @returns AI SDK ToolSet for use with streamText.
 */
function buildItineraryTools(identifier: string): ToolSet {
  // Access tool registry with proper typing; runtime guardrails perform validation.
  // Tools are typed as unknown in registry, so we use type assertions for safe access.
  type ToolLike = {
    description?: string;
    execute: (params: unknown) => Promise<unknown>;
  };

  const webSearchTool = toolRegistry.webSearch as unknown as ToolLike;
  const webSearchBatchTool = toolRegistry.webSearchBatch as unknown as ToolLike;
  const poiTool = toolRegistry.lookupPoiContext as unknown as ToolLike | undefined;
  const createPlanTool = toolRegistry.createTravelPlan as unknown as
    | ToolLike
    | undefined;
  const savePlanTool = toolRegistry.saveTravelPlan as unknown as ToolLike | undefined;

  const webSearch = tool({
    description: webSearchTool.description ?? "Web search",
    execute: async (params: unknown) => {
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:itinerary:web-search",
            ttlSeconds: 60 * 30,
          },
          rateLimit: buildRateLimit("itineraryPlanning", identifier),
          tool: "webSearch",
          workflow: "itineraryPlanning",
        },
        params,
        async (validated) => webSearchTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  const webSearchBatch = tool({
    description: webSearchBatchTool.description ?? "Batch web search",
    execute: async (params: unknown) => {
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:itinerary:web-search-batch",
            ttlSeconds: 60 * 30,
          },
          rateLimit: buildRateLimit("itineraryPlanning", identifier),
          tool: "webSearchBatch",
          workflow: "itineraryPlanning",
        },
        params,
        async (validated) => webSearchBatchTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  const lookupPoiContext = tool({
    description: poiTool?.description ?? "Lookup POIs (context)",
    execute: async (params: unknown) => {
      if (!poiTool) return { inputs: params, pois: [], provider: "stub" };
      const { result } = await runWithGuardrails(
        {
          cache: { hashInput: true, key: "agent:itinerary:poi", ttlSeconds: 600 },
          rateLimit: buildRateLimit("itineraryPlanning", identifier),
          tool: "lookupPoiContext",
          workflow: "itineraryPlanning",
        },
        params,
        async (validated) => poiTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  const createTravelPlan = tool({
    description: createPlanTool?.description ?? "Create travel plan",
    execute: async (params: unknown) => {
      if (!createPlanTool) return { error: "stub", success: false };
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:itinerary:create-plan",
            ttlSeconds: 60 * 5,
          },
          rateLimit: buildRateLimit("itineraryPlanning", identifier),
          tool: "createTravelPlan",
          workflow: "itineraryPlanning",
        },
        params,
        async (validated) => createPlanTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  const saveTravelPlan = tool({
    description: savePlanTool?.description ?? "Save travel plan",
    execute: async (params: unknown) => {
      if (!savePlanTool) return { error: "stub", success: false };
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:itinerary:save-plan",
            ttlSeconds: 60 * 5,
          },
          rateLimit: buildRateLimit("itineraryPlanning", identifier),
          tool: "saveTravelPlan",
          workflow: "itineraryPlanning",
        },
        params,
        async (validated) => savePlanTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  return {
    createTravelPlan,
    lookupPoiContext,
    saveTravelPlan,
    webSearch,
    webSearchBatch,
  } satisfies ToolSet;
}

/**
 * Execute the itinerary agent with AI SDK v6 streaming.
 *
 * Builds system instructions and messages, wraps core tools with guardrails,
 * and streams a model-guided tool loop to produce results structured per
 * `itin.v1` schema.
 *
 * @param deps Language model and request-scoped utilities.
 * @param input Validated itinerary plan request.
 * @returns AI SDK stream result for UI consumption.
 */
export function runItineraryAgent(
  deps: {
    model: LanguageModel;
    identifier: string;
  },
  input: ItineraryPlanRequest
) {
  const instructions = buildItineraryPrompt(input);
  return streamText({
    model: deps.model,
    prompt: `Generate itinerary plan and summarize. Always return JSON with schemaVersion="itin.v1" and days[]. Parameters: ${JSON.stringify(
      input
    )}`,
    stopWhen: stepCountIs(15),
    system: instructions,
    temperature: 0.3,
    tools: buildItineraryTools(deps.identifier),
  });
}
