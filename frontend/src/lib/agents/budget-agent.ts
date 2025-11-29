/**
 * @fileoverview Budget planning agent using AI SDK v6 streaming.
 *
 * Wraps budget planning tools (web search, POI lookup, combine results) with
 * guardrails (caching, rate limiting) and executes streaming text generation to
 * generate budget allocations. Returns structured results conforming to the budget
 * plan result schema.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { toolRegistry } from "@ai/tools";
import { lookupPoiInputSchema } from "@ai/tools/schemas/google-places";
import { combineSearchResultsInputSchema } from "@ai/tools/schemas/planning";
import { travelAdvisoryInputSchema } from "@ai/tools/schemas/travel-advisory";
import { webSearchBatchInputSchema } from "@ai/tools/schemas/web-search-batch";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import type { BudgetPlanRequest } from "@schemas/agents";
import type { LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText } from "ai";
import { getRegistryTool, invokeTool } from "@/lib/agents/registry-utils";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildBudgetPrompt } from "@/prompts/agents";
import { withTelemetrySpan } from "@/lib/telemetry/span";

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
  const webSearchBatchTool = getRegistryTool(toolRegistry, "webSearchBatch");
  const poiTool = getRegistryTool(toolRegistry, "lookupPoiContext");
  const combineTool = getRegistryTool(toolRegistry, "combineSearchResults");
  const safetyTool = getRegistryTool(toolRegistry, "getTravelAdvisory");

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
  config: import("@schemas/configuration").AgentConfig,
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
  const desiredMaxTokens = config.parameters.maxTokens ?? 4096;
  const { maxTokens } = clampMaxTokens(messages, desiredMaxTokens, deps.modelId);

  return withTelemetrySpan(
    "agent.budget.run",
    {
      attributes: {
        modelId: deps.modelId,
        identifier: deps.identifier,
      },
    },
    () =>
      streamText({
        maxOutputTokens: maxTokens,
        messages: [
          { content: instructions, role: "system" },
          { content: userPrompt, role: "user" },
        ],
        model: deps.model,
        stopWhen: stepCountIs(10),
        temperature: config.parameters.temperature ?? 0.3,
        tools: buildBudgetTools(deps.identifier),
        topP: config.parameters.topP,
      })
  );
}
