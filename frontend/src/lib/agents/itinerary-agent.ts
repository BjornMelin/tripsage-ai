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

import { buildGuardedTool } from "@/lib/agents/guarded-tool";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { ItineraryPlanRequest } from "@/lib/schemas/agents";
import { toolRegistry } from "@/lib/tools";
import { lookupPoiInputSchema } from "@/lib/tools/google-places";
import {
  createTravelPlanInputSchema,
  saveTravelPlanInputSchema,
} from "@/lib/tools/planning";
import { webSearchInputSchema } from "@/lib/tools/web-search";
import { webSearchBatchInputSchema } from "@/lib/tools/web-search-batch";
import { buildItineraryPrompt } from "@/prompts/agents";

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
  const rateLimit = buildRateLimit("itineraryPlanning", identifier);

  const guardedWebSearch = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:itinerary:web-search",
      ttlSeconds: 60 * 30,
    },
    execute: async (params: unknown) => await webSearchTool.execute(params),
    rateLimit,
    schema: webSearchInputSchema,
    toolKey: "webSearch",
    workflow: "itineraryPlanning",
  });

  const guardedWebSearchBatch = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:itinerary:web-search-batch",
      ttlSeconds: 60 * 30,
    },
    execute: async (params: unknown) => await webSearchBatchTool.execute(params),
    rateLimit,
    schema: webSearchBatchInputSchema,
    toolKey: "webSearchBatch",
    workflow: "itineraryPlanning",
  });

  const guardedLookupPoi = buildGuardedTool({
    cache: { hashInput: true, key: "agent:itinerary:poi", ttlSeconds: 600 },
    execute: async (params: unknown) => {
      if (!poiTool) return { inputs: params, pois: [], provider: "stub" };
      return await poiTool.execute(params);
    },
    rateLimit,
    schema: lookupPoiInputSchema,
    toolKey: "lookupPoiContext",
    workflow: "itineraryPlanning",
  });

  const guardedCreatePlan = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:itinerary:create-plan",
      ttlSeconds: 60 * 5,
    },
    execute: async (params: unknown) => {
      if (!createPlanTool) return { error: "stub", success: false };
      return await createPlanTool.execute(params);
    },
    rateLimit,
    schema: createTravelPlanInputSchema,
    toolKey: "createTravelPlan",
    workflow: "itineraryPlanning",
  });

  const guardedSavePlan = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:itinerary:save-plan",
      ttlSeconds: 60 * 5,
    },
    execute: async (params: unknown) => {
      if (!savePlanTool) return { error: "stub", success: false };
      return await savePlanTool.execute(params);
    },
    rateLimit,
    schema: saveTravelPlanInputSchema,
    toolKey: "saveTravelPlan",
    workflow: "itineraryPlanning",
  });

  const webSearch = tool({
    description: webSearchTool.description ?? "Web search",
    execute: guardedWebSearch,
    inputSchema: webSearchInputSchema,
  });

  const webSearchBatch = tool({
    description: webSearchBatchTool.description ?? "Batch web search",
    execute: guardedWebSearchBatch,
    inputSchema: webSearchBatchInputSchema,
  });

  const lookupPoiContext = tool({
    description: poiTool?.description ?? "Lookup POIs (context)",
    execute: guardedLookupPoi,
    inputSchema: lookupPoiInputSchema,
  });

  const createTravelPlan = tool({
    description: createPlanTool?.description ?? "Create travel plan",
    execute: guardedCreatePlan,
    inputSchema: createTravelPlanInputSchema,
  });

  const saveTravelPlan = tool({
    description: savePlanTool?.description ?? "Save travel plan",
    execute: guardedSavePlan,
    inputSchema: saveTravelPlanInputSchema,
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
