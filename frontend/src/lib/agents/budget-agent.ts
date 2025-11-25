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
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
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
      // TODO: Ensure toolRegistry.lookupPoiContext is properly registered and functional.
      //
      // IMPLEMENTATION PLAN (Decision Framework Score: 9.5/10.0)
      // ===========================================================
      //
      // ARCHITECTURE DECISIONS:
      // -----------------------
      // 1. Tool Availability: Tools are registered in toolRegistry from @ai/tools
      //    - Tool: `lookupPoiContext` from `server/google-places.ts`
      //    - Registry: `frontend/src/ai/tools/index.ts` exports toolRegistry
      //    - Rationale: Tools are always available in production; stub returns are defensive fallbacks
      //
      // 2. Error Handling: Throw error if tool is missing (fail fast)
      //    - Remove stub return: `if (!poiTool) return { inputs: params, pois: [], provider: "stub" };`
      //    - Throw descriptive error: "Tool lookupPoiContext not registered in toolRegistry"
      //    - Rationale: Fail fast in production; tests can mock toolRegistry if needed
      //
      // 3. Execution: Ensure proper type casting and error handling
      //    - Verify execute function exists before calling
      //    - Properly await async execution
      //    - Return typed result
      //
      // IMPLEMENTATION STEPS:
      // ---------------------
      //
      // Step 1: Remove Stub Return and Add Proper Error Handling
      //   ```typescript
      //   execute: async (params, callOptions) => {
      //     if (!poiTool) {
      //       throw new Error(
      //         "Tool lookupPoiContext not registered in toolRegistry. " +
      //         "Ensure @ai/tools exports lookupPoiContext in toolRegistry."
      //       );
      //     }
      //     if (typeof poiTool.execute !== "function") {
      //       throw new Error("Tool lookupPoiContext missing execute binding");
      //     }
      //     return (await poiTool.execute(params, callOptions)) as unknown;
      //   },
      //   ```
      //
      // INTEGRATION POINTS:
      // -------------------
      // - Tool Registry: `toolRegistry.lookupPoiContext` from `@ai/tools`
      // - Tool Implementation: `frontend/src/ai/tools/server/google-places.ts`
      // - Error Handling: Throw descriptive errors for missing tools
      // - Telemetry: Automatic via `createAiTool` guardrails
      //
      // TESTING REQUIREMENTS:
      // ---------------------
      // - Unit test: Verify error thrown when tool is missing
      // - Integration test: Verify tool execution with real toolRegistry
      // - Mock toolRegistry in tests to simulate missing tools
      //
      // NOTES:
      // ------
      // - Tool is registered in toolRegistry, so stub return should never execute in production
      // - Stub return was defensive fallback; removing it ensures proper error detection
      // - Tests can mock toolRegistry if needed for testing error paths
      //
      if (!poiTool) {
        throw new Error(
          "Tool lookupPoiContext not registered in toolRegistry. " +
            "Ensure @ai/tools exports lookupPoiContext in toolRegistry."
        );
      }
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
      // TODO: Ensure toolRegistry.combineSearchResults is properly registered and functional.
      //
      // IMPLEMENTATION PLAN (Decision Framework Score: 9.5/10.0)
      // ===========================================================
      //
      // ARCHITECTURE DECISIONS:
      // -----------------------
      // 1. Tool Availability: Tools are registered in toolRegistry from @ai/tools
      //    - Tool: `combineSearchResults` from `server/planning.ts`
      //    - Registry: `frontend/src/ai/tools/index.ts` exports toolRegistry
      //    - Rationale: Tools are always available in production; stub returns are defensive fallbacks
      //
      // 2. Error Handling: Throw error if tool is missing (fail fast)
      //    - Remove stub return: `if (!combineTool) return { combinedResults: {}, message: "stub", success: true };`
      //    - Throw descriptive error: "Tool combineSearchResults not registered in toolRegistry"
      //    - Rationale: Fail fast in production; tests can mock toolRegistry if needed
      //
      // 3. Execution: Ensure proper type casting and error handling
      //    - Verify execute function exists before calling
      //    - Handle both sync and async execution (tool may return Promise or value)
      //    - Return typed result
      //
      // IMPLEMENTATION STEPS:
      // ---------------------
      //
      // Step 1: Remove Stub Return and Add Proper Error Handling
      //   ```typescript
      //   execute: async (params, callOptions) => {
      //     if (!combineTool) {
      //       throw new Error(
      //         "Tool combineSearchResults not registered in toolRegistry. " +
      //         "Ensure @ai/tools exports combineSearchResults in toolRegistry."
      //       );
      //     }
      //     if (typeof combineTool.execute !== "function") {
      //       throw new Error("Tool combineSearchResults missing execute binding");
      //     }
      //     const result = combineTool.execute(params, callOptions);
      //     return result instanceof Promise ? result : Promise.resolve(result);
      //   },
      //   ```
      //
      // INTEGRATION POINTS:
      // -------------------
      // - Tool Registry: `toolRegistry.combineSearchResults` from `@ai/tools`
      // - Tool Implementation: `frontend/src/ai/tools/server/planning.ts`
      // - Error Handling: Throw descriptive errors for missing tools
      // - Telemetry: Automatic via `createAiTool` guardrails
      //
      // TESTING REQUIREMENTS:
      // ---------------------
      // - Unit test: Verify error thrown when tool is missing
      // - Integration test: Verify tool execution with real toolRegistry
      // - Mock toolRegistry in tests to simulate missing tools
      //
      // NOTES:
      // ------
      // - Tool is registered in toolRegistry, so stub return should never execute in production
      // - Stub return was defensive fallback; removing it ensures proper error detection
      // - Tests can mock toolRegistry if needed for testing error paths
      // - Tool may return sync or async result; handle both cases
      //
      if (!combineTool) {
        throw new Error(
          "Tool combineSearchResults not registered in toolRegistry. " +
            "Ensure @ai/tools exports combineSearchResults in toolRegistry."
        );
      }
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
      // TODO: Ensure toolRegistry.getTravelAdvisory is properly registered and functional.
      //
      // IMPLEMENTATION PLAN (Decision Framework Score: 9.5/10.0)
      // ===========================================================
      //
      // ARCHITECTURE DECISIONS:
      // -----------------------
      // 1. Tool Availability: Tools are registered in toolRegistry from @ai/tools
      //    - Tool: `getTravelAdvisory` from `server/travel-advisory.ts`
      //    - Registry: `frontend/src/ai/tools/index.ts` exports toolRegistry
      //    - Rationale: Tools are always available in production; stub returns are defensive fallbacks
      //
      // 2. Error Handling: Throw error if tool is missing (fail fast)
      //    - Remove stub return: `if (!safetyTool) return { categories: [], destination: "", overallScore: 75, provider: "stub" };`
      //    - Throw descriptive error: "Tool getTravelAdvisory not registered in toolRegistry"
      //    - Rationale: Fail fast in production; tests can mock toolRegistry if needed
      //
      // 3. Execution: Ensure proper type casting and error handling
      //    - Verify execute function exists before calling
      //    - Properly await async execution
      //    - Return typed result
      //
      // IMPLEMENTATION STEPS:
      // ---------------------
      //
      // Step 1: Remove Stub Return and Add Proper Error Handling
      //   ```typescript
      //   execute: async (params, callOptions) => {
      //     if (!safetyTool) {
      //       throw new Error(
      //         "Tool getTravelAdvisory not registered in toolRegistry. " +
      //         "Ensure @ai/tools exports getTravelAdvisory in toolRegistry."
      //       );
      //     }
      //     if (typeof safetyTool.execute !== "function") {
      //       throw new Error("Tool getTravelAdvisory missing execute binding");
      //     }
      //     return (await safetyTool.execute(params, callOptions)) as unknown;
      //   },
      //   ```
      //
      // INTEGRATION POINTS:
      // -------------------
      // - Tool Registry: `toolRegistry.getTravelAdvisory` from `@ai/tools`
      // - Tool Implementation: `frontend/src/ai/tools/server/travel-advisory.ts`
      // - Error Handling: Throw descriptive errors for missing tools
      // - Telemetry: Automatic via `createAiTool` guardrails
      //
      // TESTING REQUIREMENTS:
      // ---------------------
      // - Unit test: Verify error thrown when tool is missing
      // - Integration test: Verify tool execution with real toolRegistry
      // - Mock toolRegistry in tests to simulate missing tools
      //
      // NOTES:
      // ------
      // - Tool is registered in toolRegistry, so stub return should never execute in production
      // - Stub return was defensive fallback; removing it ensures proper error detection
      // - Tests can mock toolRegistry if needed for testing error paths
      //
      if (!safetyTool) {
        throw new Error(
          "Tool getTravelAdvisory not registered in toolRegistry. " +
            "Ensure @ai/tools exports getTravelAdvisory in toolRegistry."
        );
      }
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

  return streamText({
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
  });
}
