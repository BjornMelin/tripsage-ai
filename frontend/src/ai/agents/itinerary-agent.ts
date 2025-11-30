/**
 * @fileoverview Itinerary planning agent using AI SDK v6 ToolLoopAgent.
 *
 * Creates a reusable itinerary planning agent that autonomously researches
 * destinations, gathers POI information, and creates day-by-day travel
 * plans using multi-step tool calling.
 */

import "server-only";

import { getRegistryTool, invokeTool } from "@ai/lib/registry-utils";
import { createAiTool } from "@ai/lib/tool-factory";
import { toolRegistry } from "@ai/tools";
import { lookupPoiInputSchema } from "@ai/tools/schemas/google-places";
import {
  createTravelPlanInputSchema,
  saveTravelPlanInputSchema,
} from "@ai/tools/schemas/planning";
import type {
  WebSearchBatchResult,
  WebSearchResult,
} from "@ai/tools/schemas/web-search";
import { webSearchInputSchema } from "@ai/tools/schemas/web-search";
import { webSearchBatchInputSchema } from "@ai/tools/schemas/web-search-batch";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import type { ItineraryPlanRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import type { ToolSet } from "ai";
import type { z } from "zod";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildItineraryPrompt } from "@/prompts/agents";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";
import { extractAgentParameters } from "./types";

/**
 * Response type for POI lookup tool.
 *
 * TODO: align with google-places tool output schema when shared response
 * typings are introduced to avoid duplication across agents.
 */
type LookupPoiResponse =
  | { error?: string; inputs: unknown; pois: unknown[]; provider: string }
  | { fromCache?: boolean; inputs: unknown; pois: unknown[]; provider: string };

/**
 * Response type for create travel plan tool.
 *
 * TODO: consolidate with planning tool schemas when shared output typings
 * are introduced to avoid duplication across agents.
 */
type CreateTravelPlanResponse =
  | { error: string; success: false }
  | { message: string; plan: unknown; planId: string; success: true };

/**
 * Response type for save travel plan tool.
 *
 * TODO: consolidate with planning tool schemas when shared output typings
 * are introduced to avoid duplication across agents.
 */
type SaveTravelPlanResponse =
  | { error: string; success: false }
  | {
      message: string;
      planId: string;
      status: string;
      success: true;
      summaryMarkdown: string;
    };

/**
 * Creates wrapped tools for itinerary agent with guardrails.
 *
 * Applies validation, caching, and rate limits around core tool execute
 * functions. Supports research, POI discovery, and travel plan creation.
 *
 * @param identifier - Stable identifier for rate limiting.
 * @returns AI SDK ToolSet for use with ToolLoopAgent.
 */
function buildItineraryTools(identifier: string): ToolSet {
  type WebSearchInput = z.infer<typeof webSearchInputSchema>;
  type WebSearchBatchInput = z.infer<typeof webSearchBatchInputSchema>;
  type LookupPoiInput = z.infer<typeof lookupPoiInputSchema>;
  type CreateTravelPlanInput = z.infer<typeof createTravelPlanInputSchema>;
  type SaveTravelPlanInput = z.infer<typeof saveTravelPlanInputSchema>;

  const webSearchTool = getRegistryTool<WebSearchInput, WebSearchResult>(
    toolRegistry,
    "webSearch"
  );
  const webSearchBatchTool = getRegistryTool<WebSearchBatchInput, WebSearchBatchResult>(
    toolRegistry,
    "webSearchBatch"
  );
  const poiTool = getRegistryTool<LookupPoiInput, LookupPoiResponse>(
    toolRegistry,
    "lookupPoiContext"
  );
  const createPlanTool = getRegistryTool<
    CreateTravelPlanInput,
    CreateTravelPlanResponse
  >(toolRegistry, "createTravelPlan");
  const savePlanTool = getRegistryTool<SaveTravelPlanInput, SaveTravelPlanResponse>(
    toolRegistry,
    "saveTravelPlan"
  );

  const rateLimit = buildRateLimit("itineraryPlanning", identifier);

  const webSearch = createAiTool({
    description: webSearchTool.description ?? "Web search",
    execute: (params, callOptions) => invokeTool(webSearchTool, params, callOptions),
    guardrails: {
      cache: {
        hashInput: true,
        key: () => `agent:itinerary:web-search:${identifier}`,
        namespace: `agent:itinerary:web-search:${identifier}`,
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
    execute: (params, callOptions) =>
      invokeTool(webSearchBatchTool, params, callOptions),
    guardrails: {
      cache: {
        hashInput: true,
        key: () => `agent:itinerary:web-search-batch:${identifier}`,
        namespace: `agent:itinerary:web-search-batch:${identifier}`,
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
    description: poiTool.description ?? "Lookup POIs (context)",
    execute: (params, callOptions) => invokeTool(poiTool, params, callOptions),
    guardrails: {
      cache: {
        hashInput: true,
        key: () => `agent:itinerary:poi:${identifier}`,
        namespace: `agent:itinerary:poi:${identifier}`,
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
    description: createPlanTool.description ?? "Create travel plan",
    execute: (params, callOptions) => invokeTool(createPlanTool, params, callOptions),
    guardrails: {
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
    description: savePlanTool.description ?? "Save travel plan",
    execute: (params, callOptions) => invokeTool(savePlanTool, params, callOptions),
    guardrails: {
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
 * Creates an itinerary planning agent using AI SDK v6 ToolLoopAgent.
 *
 * The agent autonomously researches destinations, gathers POI information,
 * and creates day-by-day travel plans through multi-step tool calling.
 * Returns a reusable agent instance.
 *
 * @param deps - Runtime dependencies including model and identifiers.
 * @param config - Agent configuration from database.
 * @param input - Validated itinerary plan request.
 * @returns Configured ToolLoopAgent for itinerary planning.
 *
 * @example
 * ```typescript
 * const { agent } = createItineraryAgent(deps, config, {
 *   destination: "Rome, Italy",
 *   durationDays: 5,
 *   interests: ["history", "food", "art"],
 * });
 *
 * // Stream the response
 * return createAgentUIStreamResponse({
 *   agent,
 *   messages: [{ role: "user", content: "Plan my trip" }],
 * });
 * ```
 */
export function createItineraryAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: ItineraryPlanRequest
): TripSageAgentResult {
  const params = extractAgentParameters(config);
  const instructions = buildItineraryPrompt(input);

  // Token budgeting: clamp max output tokens based on prompt length
  const userPrompt = `Generate itinerary plan and summarize. Always return JSON with schemaVersion="itin.v1" and days[]. Parameters: ${JSON.stringify(
    input
  )}`;
  const schemaMessage: ChatMessage = { content: userPrompt, role: "user" };
  const clampMessages: ChatMessage[] = [
    { content: instructions, role: "system" },
    schemaMessage,
  ];
  const { maxTokens } = clampMaxTokens(clampMessages, params.maxTokens, deps.modelId);

  // Itinerary planning may need more steps for comprehensive plans
  // (researching POIs, creating day-by-day schedules, saving plan)
  const maxSteps = Math.max(params.maxSteps, 15);

  return createTripSageAgent(deps, {
    agentType: "itineraryPlanning",
    defaultMessages: [schemaMessage],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps,
    name: "Itinerary Planning Agent",
    temperature: params.temperature,
    tools: buildItineraryTools(deps.identifier),
    topP: params.topP,
  });
}

/** Exported type for the itinerary agent's tool set. */
export type ItineraryAgentTools = ReturnType<typeof buildItineraryTools>;
