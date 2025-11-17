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
import { stepCountIs, streamText, tool } from "ai";

import { buildGuardedTool } from "@/lib/agents/guarded-tool";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { BudgetPlanRequest } from "@/lib/schemas/agents";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { toolRegistry } from "@/lib/tools";
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
    execute: (params: unknown) => Promise<unknown>;
  };

  const webSearchBatchTool = toolRegistry.webSearchBatch as unknown as ToolLike;
  const poiTool = toolRegistry.lookupPoiContext as unknown as ToolLike | undefined;
  const combineTool = toolRegistry.combineSearchResults as unknown as
    | ToolLike
    | undefined;
  const safetyTool = toolRegistry.getTravelAdvisory as unknown as ToolLike | undefined;

  const rateLimit = buildRateLimit("budgetPlanning", identifier);

  const guardedWebSearchBatch = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:budget:web-search",
      ttlSeconds: 60 * 10,
    },
    execute: async (params: unknown) => webSearchBatchTool.execute(params),
    rateLimit,
    schema: webSearchBatchInputSchema,
    toolKey: "webSearchBatch",
    workflow: "budgetPlanning",
  });

  const guardedLookupPoiContext = buildGuardedTool({
    cache: { hashInput: true, key: "agent:budget:poi", ttlSeconds: 600 },
    execute: async (params: unknown) => {
      if (!poiTool) return { inputs: params, pois: [], provider: "stub" };
      return await poiTool.execute(params);
    },
    rateLimit,
    schema: lookupPoiInputSchema,
    toolKey: "lookupPoiContext",
    workflow: "budgetPlanning",
  });

  const guardedCombineSearchResults = buildGuardedTool({
    cache: { hashInput: true, key: "agent:budget:combine", ttlSeconds: 60 * 10 },
    execute: async (params: unknown) => {
      if (!combineTool) return { combinedResults: {}, message: "stub", success: true };
      return await combineTool.execute(params);
    },
    rateLimit,
    schema: combineSearchResultsInputSchema,
    toolKey: "combineSearchResults",
    workflow: "budgetPlanning",
  });

  const guardedGetTravelAdvisory = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:budget:safety",
      ttlSeconds: 60 * 60 * 24 * 7,
    },
    execute: async (params: unknown) => {
      if (!safetyTool)
        return { categories: [], destination: "", overallScore: 75, provider: "stub" };
      return await safetyTool.execute(params);
    },
    rateLimit,
    schema: travelAdvisoryInputSchema,
    toolKey: "getTravelAdvisory",
    workflow: "budgetPlanning",
  });

  const webSearchBatch = tool({
    description: webSearchBatchTool.description ?? "Batch web search",
    execute: guardedWebSearchBatch,
    inputSchema: webSearchBatchInputSchema,
  });

  const lookupPoiContext = tool({
    description: poiTool?.description ?? "Lookup POIs (context)",
    execute: guardedLookupPoiContext,
    inputSchema: lookupPoiInputSchema,
  });

  const combineSearchResults = tool({
    description: combineTool?.description ?? "Combine search results",
    execute: guardedCombineSearchResults,
    inputSchema: combineSearchResultsInputSchema,
  });

  const getTravelAdvisory = tool({
    description: safetyTool?.description ?? "Get travel advisory and safety scores",
    execute: guardedGetTravelAdvisory,
    inputSchema: travelAdvisoryInputSchema,
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
    model: deps.model,
    prompt: userPrompt,
    stopWhen: stepCountIs(10),
    system: instructions,
    temperature: 0.3,
    tools: buildBudgetTools(deps.identifier),
  });
}
