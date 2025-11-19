/**
 * @fileoverview Itinerary planning agent using AI SDK v6 streaming.
 *
 * Wraps itinerary planning tools (web search, POI lookup, planning tools) with
 * guardrails (caching, rate limiting) and executes streaming text generation to
 * generate multi-day itineraries. Returns structured results conforming to the
 * itinerary plan result schema.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { toolRegistry } from "@ai/tools";
import { lookupPoiInputSchema } from "@ai/tools/schemas/google-places";
import {
  createTravelPlanInputSchema,
  saveTravelPlanInputSchema,
} from "@ai/tools/schemas/planning";
import { webSearchInputSchema } from "@ai/tools/schemas/web-search";
import { webSearchBatchInputSchema } from "@ai/tools/schemas/web-search-batch";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import type { ItineraryPlanRequest } from "@schemas/agents";
import type { LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText } from "ai";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
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
    execute: (params: unknown, callOptions?: unknown) => Promise<unknown> | unknown;
  };

  const webSearchTool = toolRegistry.webSearch as unknown as ToolLike;
  const webSearchBatchTool = toolRegistry.webSearchBatch as unknown as ToolLike;
  const poiTool = toolRegistry.lookupPoiContext as unknown as ToolLike | undefined;
  const createPlanTool = toolRegistry.createTravelPlan as unknown as
    | ToolLike
    | undefined;
  const savePlanTool = toolRegistry.saveTravelPlan as unknown as ToolLike | undefined;
  const rateLimit = buildRateLimit("itineraryPlanning", identifier);

  const webSearch = createAiTool({
    description: webSearchTool.description ?? "Web search",
    execute: async (params, callOptions) => {
      if (typeof webSearchTool.execute !== "function") {
        throw new Error("Tool webSearch missing execute binding");
      }
      return (await webSearchTool.execute(params, callOptions)) as unknown;
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:itinerary:web-search",
        namespace: "agent:itinerary:web-search",
        ttlSeconds: 60 * 30,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:itinerary:web-search",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "itineraryPlanning",
      },
    },
    inputSchema: webSearchInputSchema,
    name: "webSearch",
  });

  const webSearchBatch = createAiTool({
    description: webSearchBatchTool.description ?? "Batch web search",
    execute: async (params, callOptions) => {
      if (typeof webSearchBatchTool.execute !== "function") {
        throw new Error("Tool webSearchBatch missing execute binding");
      }
      return (await webSearchBatchTool.execute(params, callOptions)) as unknown;
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:itinerary:web-search-batch",
        namespace: "agent:itinerary:web-search-batch",
        ttlSeconds: 60 * 30,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:itinerary:web-search-batch",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "itineraryPlanning",
      },
    },
    inputSchema: webSearchBatchInputSchema,
    name: "webSearchBatch",
  });

  const lookupPoiContext = createAiTool({
    description: poiTool?.description ?? "Lookup POIs (context)",
    execute: async (params, callOptions) => {
      if (!poiTool) return { inputs: params, pois: [], provider: "stub" };
      if (typeof poiTool.execute !== "function") {
        throw new Error("Tool lookupPoiContext missing execute binding");
      }
      return (await poiTool.execute(params, callOptions)) as unknown;
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:itinerary:poi",
        namespace: "agent:itinerary:poi",
        ttlSeconds: 600,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:itinerary:poi",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "itineraryPlanning",
      },
    },
    inputSchema: lookupPoiInputSchema,
    name: "lookupPoiContext",
  });

  const createTravelPlan = createAiTool({
    description: createPlanTool?.description ?? "Create travel plan",
    execute: async (params, callOptions) => {
      if (!createPlanTool) return { error: "stub", success: false };
      if (typeof createPlanTool.execute !== "function") {
        throw new Error("Tool createTravelPlan missing execute binding");
      }
      return (await createPlanTool.execute(params, callOptions)) as unknown;
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:itinerary:create-plan",
        namespace: "agent:itinerary:create-plan",
        ttlSeconds: 60 * 5,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:itinerary:create-plan",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "itineraryPlanning",
      },
    },
    inputSchema: createTravelPlanInputSchema,
    name: "createTravelPlan",
  });

  const saveTravelPlan = createAiTool({
    description: savePlanTool?.description ?? "Save travel plan",
    execute: async (params, callOptions) => {
      if (!savePlanTool) return { error: "stub", success: false };
      if (typeof savePlanTool.execute !== "function") {
        throw new Error("Tool saveTravelPlan missing execute binding");
      }
      return (await savePlanTool.execute(params, callOptions)) as unknown;
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:itinerary:save-plan",
        namespace: "agent:itinerary:save-plan",
        ttlSeconds: 60 * 5,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:itinerary:save-plan",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "itineraryPlanning",
      },
    },
    inputSchema: saveTravelPlanInputSchema,
    name: "saveTravelPlan",
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
 * @param deps Language model, model identifier, and request-scoped utilities.
 * @param input Validated itinerary plan request.
 * @returns AI SDK stream result for UI consumption.
 */
export function runItineraryAgent(
  deps: {
    model: LanguageModel;
    modelId: string;
    identifier: string;
  },
  input: ItineraryPlanRequest
) {
  const instructions = buildItineraryPrompt(input);
  const userPrompt = `Generate itinerary plan and summarize. Always return JSON with schemaVersion="itin.v1" and days[]. Parameters: ${JSON.stringify(
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
    stopWhen: stepCountIs(15),
    temperature: 0.3,
    tools: buildItineraryTools(deps.identifier),
  });
}
