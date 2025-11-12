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
import { z } from "zod";

import { runWithGuardrails } from "@/lib/agents/runtime";
import { buildRateLimit } from "@/lib/ratelimit/config";
import { toolRegistry } from "@/lib/tools";
import { buildBudgetPrompt } from "@/prompts/agents";
import type { BudgetPlanRequest } from "@/schemas/agents";

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

  const webSearchBatch = tool({
    description: webSearchBatchTool.description ?? "Batch web search",
    execute: async (params: unknown) => {
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:budget:web-search",
            ttlSeconds: 60 * 10,
          },
          rateLimit: buildRateLimit("budgetPlanning", identifier),
          tool: "webSearchBatch",
          workflow: "budgetPlanning",
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
          cache: { hashInput: true, key: "agent:budget:poi", ttlSeconds: 600 },
          rateLimit: buildRateLimit("budgetPlanning", identifier),
          tool: "lookupPoiContext",
          workflow: "budgetPlanning",
        },
        params,
        async (validated) => poiTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  const combineSearchResults = tool({
    description: combineTool?.description ?? "Combine search results",
    execute: async (params: unknown) => {
      if (!combineTool) return { combinedResults: {}, message: "stub", success: true };
      const { result } = await runWithGuardrails(
        {
          cache: { hashInput: true, key: "agent:budget:combine", ttlSeconds: 60 * 10 },
          rateLimit: buildRateLimit("budgetPlanning", identifier),
          tool: "combineSearchResults",
          workflow: "budgetPlanning",
        },
        params,
        async (validated) => combineTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  const getTravelAdvisory = tool({
    description: safetyTool?.description ?? "Get travel advisory and safety scores",
    execute: async (params: unknown) => {
      if (!safetyTool)
        return { categories: [], destination: "", overallScore: 75, provider: "stub" };
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:budget:safety",
            ttlSeconds: 60 * 60 * 24 * 7,
          },
          rateLimit: buildRateLimit("budgetPlanning", identifier),
          tool: "getTravelAdvisory",
          workflow: "budgetPlanning",
        },
        params,
        async (validated) => safetyTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
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
 * @param deps Language model and request-scoped utilities.
 * @param input Validated budget plan request.
 * @returns AI SDK stream result for UI consumption.
 */
export function runBudgetAgent(
  deps: {
    model: LanguageModel;
    identifier: string;
  },
  input: BudgetPlanRequest
) {
  const instructions = buildBudgetPrompt(input);
  return streamText({
    model: deps.model,
    prompt: `Generate a budget plan and summarize. Always return JSON with schemaVersion="budget.v1" and allocations[]. Parameters: ${JSON.stringify(
      input
    )}`,
    stopWhen: stepCountIs(10),
    system: instructions,
    temperature: 0.3,
    tools: buildBudgetTools(deps.identifier),
  });
}
