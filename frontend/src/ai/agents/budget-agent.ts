/**
 * @fileoverview Budget planning agent using AI SDK v6 ToolLoopAgent.
 *
 * Creates a reusable budget planning agent that autonomously researches
 * destinations, gathers pricing data, and generates budget allocations
 * using multi-step tool calling.
 */

import "server-only";

import { getRegistryTool, invokeTool } from "@ai/lib/registry-utils";
import { createAiTool } from "@ai/lib/tool-factory";
import { toolRegistry } from "@ai/tools";
import { lookupPoiInputSchema } from "@ai/tools/schemas/google-places";
import { combineSearchResultsInputSchema } from "@ai/tools/schemas/planning";
import { travelAdvisoryInputSchema } from "@ai/tools/schemas/travel-advisory";
import { webSearchBatchInputSchema } from "@ai/tools/schemas/web-search-batch";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import type { BudgetPlanRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import type { ToolSet } from "ai";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildBudgetPrompt } from "@/prompts/agents";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";
import { extractAgentParameters } from "./types";

const TOOL_NAMES = {
  combineResults: "combineSearchResults",
  lookupPoi: "lookupPoiContext",
  travelAdvisory: "getTravelAdvisory",
  webSearchBatch: "webSearchBatch",
} as const;

/**
 * Create wrapped tools for budget agent with guardrails.
 *
 * Applies validation, caching, and rate limits around core tool execute
 * functions. The identifier should be per-user when authenticated or a
 * hashed IP fallback.
 *
 * @param identifier - Stable identifier for rate limiting.
 * @returns AI SDK ToolSet for use with ToolLoopAgent.
 */
function buildBudgetTools(identifier: string): ToolSet {
  const webSearchBatchTool = getRegistryTool(toolRegistry, TOOL_NAMES.webSearchBatch);
  const poiTool = getRegistryTool(toolRegistry, TOOL_NAMES.lookupPoi);
  const combineTool = getRegistryTool(toolRegistry, TOOL_NAMES.combineResults);
  const safetyTool = getRegistryTool(toolRegistry, TOOL_NAMES.travelAdvisory);

  const rateLimit = buildRateLimit("budgetPlanning", identifier);

  const webSearchBatch = createAiTool({
    description: webSearchBatchTool.description ?? "Batch web search",
    execute: (params, callOptions) =>
      invokeTool(webSearchBatchTool, params, callOptions),
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:budget:web-search",
        namespace: "agent:budget:web-search",
        ttlSeconds: 60 * 10,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:budget:web-search",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "budgetPlanning",
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
        key: () => "agent:budget:poi",
        namespace: "agent:budget:poi",
        ttlSeconds: 600,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:budget:poi",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "budgetPlanning",
      },
    },
    inputSchema: lookupPoiInputSchema,
    name: "lookupPoiContext",
  });

  const combineSearchResults = createAiTool({
    description: combineTool.description ?? "Combine search results",
    execute: (params, callOptions) => invokeTool(combineTool, params, callOptions),
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:budget:combine",
        namespace: "agent:budget:combine",
        ttlSeconds: 60 * 10,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:budget:combine",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "budgetPlanning",
      },
    },
    inputSchema: combineSearchResultsInputSchema,
    name: "combineSearchResults",
  });

  const getTravelAdvisory = createAiTool({
    description: safetyTool.description ?? "Get travel advisory and safety scores",
    execute: (params, callOptions) => invokeTool(safetyTool, params, callOptions),
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:budget:safety",
        namespace: "agent:budget:safety",
        ttlSeconds: 60 * 60 * 24 * 7,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:budget:safety",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "budgetPlanning",
      },
    },
    inputSchema: travelAdvisoryInputSchema,
    name: "getTravelAdvisory",
  });

  return {
    combineSearchResults,
    getTravelAdvisory,
    lookupPoiContext,
    webSearchBatch,
  } satisfies ToolSet;
}

/**
 * Creates a budget planning agent using AI SDK v6 ToolLoopAgent.
 *
 * The agent autonomously researches destinations, gathers pricing data,
 * and generates structured budget allocations through multi-step tool
 * calling. Returns a reusable agent instance that can be used for
 * streaming or one-shot generation.
 *
 * @param deps - Runtime dependencies including model and identifiers.
 * @param config - Agent configuration from database.
 * @param input - Validated budget plan request.
 * @returns Configured ToolLoopAgent for budget planning.
 *
 * @example
 * ```typescript
 * const { agent } = createBudgetAgent(deps, config, {
 *   destination: "Tokyo, Japan",
 *   durationDays: 7,
 *   travelStyle: "mid-range",
 * });
 *
 * // Stream the response
 * return createAgentUIStreamResponse({
 *   agent,
 *   messages: [{ role: "user", content: "Plan my budget" }],
 * });
 * ```
 */
export function createBudgetAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: BudgetPlanRequest
): TripSageAgentResult {
  const params = extractAgentParameters(config);
  const instructions = buildBudgetPrompt(input);

  // Token budgeting: clamp max output tokens based on prompt length
  const userPrompt = `Generate a budget plan and summarize. Always return JSON with schemaVersion="budget.v1" and allocations[]. Parameters: ${JSON.stringify(
    input
  )}`;
  const schemaMessage: ChatMessage = { content: userPrompt, role: "user" };
  const clampMessages: ChatMessage[] = [
    { content: instructions, role: "system" },
    schemaMessage,
  ];
  const { maxTokens } = clampMaxTokens(clampMessages, params.maxTokens, deps.modelId);

  return createTripSageAgent(deps, {
    agentType: "budgetPlanning",
    defaultMessages: [schemaMessage],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps: params.maxSteps,
    name: "Budget Planning Agent",
    temperature: params.temperature,
    tools: buildBudgetTools(deps.identifier),
    topP: params.topP,
  });
}

/** Exported type for the budget agent's tool set. */
export type BudgetAgentTools = ReturnType<typeof buildBudgetTools>;
