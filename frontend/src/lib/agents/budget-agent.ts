/**
 * @fileoverview Budget planning agent using AI SDK v6 streaming.
 *
 * Wraps budget planning tools (web search, POI lookup, combine results) with
 * guardrails (caching, rate limiting) and executes streaming text generation to
 * generate budget allocations. Returns structured results conforming to the budget
 * plan result schema.
 */

import "server-only";

import type { LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText } from "ai";

import { createAiTool } from "@/lib/ai/tool-factory";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { BudgetPlanRequest } from "@/lib/schemas/agents";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { toolRegistry } from "@/lib/tools";
import { TOOL_ERROR_CODES } from "@/lib/tools/errors";
import { lookupPoiInputSchema } from "@/lib/tools/google-places";
import { combineSearchResultsInputSchema } from "@/lib/tools/planning";
import { travelAdvisoryInputSchema } from "@/lib/tools/travel-advisory";
import { webSearchBatchInputSchema } from "@/lib/tools/web-search-batch";
import { buildBudgetPrompt } from "@/prompts/agents";

/**
 * Create wrapped tools for budget agent with guardrails.
 *
 * Applies validation, caching, and rate limits around core tool execute
 * functions. The identifier should be per-user when authenticated or a
 * hashed IP fallback.
 *
 * @param identifier Stable identifier for rate limiting.
 * @returns AI SDK ToolSet for use with streamText.
 */
function buildBudgetTools(identifier: string): ToolSet {
  // Access tool registry with proper typing; runtime guardrails perform validation.
  // Tools are typed as unknown in registry, so we use type assertions for safe access.
  type ToolLike = {
    description?: string;
    execute: (params: unknown, callOptions?: unknown) => Promise<unknown> | unknown;
  };

  const webSearchBatchTool = toolRegistry.webSearchBatch as unknown as ToolLike;
  const poiTool = toolRegistry.lookupPoiContext as unknown as ToolLike | undefined;
  const combineTool = toolRegistry.combineSearchResults as unknown as
    | ToolLike
    | undefined;
  const safetyTool = toolRegistry.getTravelAdvisory as unknown as ToolLike | undefined;

  const rateLimit = buildRateLimit("budgetPlanning", identifier);

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
    description: combineTool?.description ?? "Combine search results",
    // biome-ignore lint/suspicious/useAwait: Tool factory requires async signature for type compatibility
    execute: async (params, callOptions) => {
      if (!combineTool) return { combinedResults: {}, message: "stub", success: true };
      if (typeof combineTool.execute !== "function") {
        throw new Error("Tool combineSearchResults missing execute binding");
      }
      const result = combineTool.execute(params, callOptions);
      return result instanceof Promise ? result : Promise.resolve(result);
    },
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
    description: safetyTool?.description ?? "Get travel advisory and safety scores",
    execute: async (params, callOptions) => {
      if (!safetyTool)
        return { categories: [], destination: "", overallScore: 75, provider: "stub" };
      if (typeof safetyTool.execute !== "function") {
        throw new Error("Tool getTravelAdvisory missing execute binding");
      }
      return (await safetyTool.execute(params, callOptions)) as unknown;
    },
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
 * Execute the budget agent with AI SDK v6 streaming.
 *
 * Builds system instructions and messages, wraps core tools with guardrails,
 * and streams a model-guided tool loop to produce results structured per
 * `budget.v1` schema.
 *
 * @param deps Language model, model identifier, and request-scoped utilities.
 * @param input Validated budget plan request.
 * @returns AI SDK stream result for UI consumption.
 */
export function runBudgetAgent(
  deps: {
    model: LanguageModel;
    modelId: string;
    identifier: string;
  },
  input: BudgetPlanRequest
) {
  const instructions = buildBudgetPrompt(input);
  const userPrompt = `Generate a budget plan and summarize. Always return JSON with schemaVersion="budget.v1" and allocations[]. Parameters: ${JSON.stringify(
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
    stopWhen: stepCountIs(10),
    temperature: 0.3,
    tools: buildBudgetTools(deps.identifier),
  });
}
