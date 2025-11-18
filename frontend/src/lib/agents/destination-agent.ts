/**
 * @fileoverview Destination research agent using AI SDK v6 streaming.
 *
 * Wraps destination research tools (web search, crawl, POI lookup, weather,
 * safety) with guardrails (caching, rate limiting) and executes streaming
 * text generation to research destinations. Returns structured results
 * conforming to the destination research result schema.
 */

import "server-only";

import type { LanguageModel, ToolSet } from "ai";
import { stepCountIs, streamText } from "ai";

import { createAiTool } from "@/lib/ai/tool-factory";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { DestinationResearchRequest } from "@/lib/schemas/agents";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { toolRegistry } from "@/lib/tools";
import { TOOL_ERROR_CODES } from "@/lib/tools/errors";
import { lookupPoiInputSchema } from "@/lib/tools/google-places";
import { travelAdvisoryInputSchema } from "@/lib/tools/travel-advisory";
import { getCurrentWeatherInputSchema } from "@/lib/tools/weather";
import { crawlSiteInputSchema } from "@/lib/tools/web-crawl";
import { webSearchInputSchema } from "@/lib/tools/web-search";
import { webSearchBatchInputSchema } from "@/lib/tools/web-search-batch";
import { buildDestinationPrompt } from "@/prompts/agents";

/**
 * Create wrapped tools for destination agent with guardrails.
 *
 * Applies validation, caching, and rate limits around core tool execute
 * functions. The identifier should be per-user when authenticated or a
 * hashed IP fallback.
 *
 * @param identifier Stable identifier for rate limiting.
 * @returns AI SDK ToolSet for use with streamText.
 */
function buildDestinationTools(identifier: string): ToolSet {
  // Access tool registry with proper typing; runtime guardrails perform validation.
  // Tools are typed as unknown in registry, so we use type assertions for safe access.
  type ToolLike = {
    description?: string;
    execute: (params: unknown, callOptions?: unknown) => Promise<unknown> | unknown;
  };

  const webSearchTool = toolRegistry.webSearch as unknown as ToolLike;
  const webSearchBatchTool = toolRegistry.webSearchBatch as unknown as ToolLike;
  const crawlSiteTool = toolRegistry.crawlSite as unknown as ToolLike | undefined;
  const poiTool = toolRegistry.lookupPoiContext as unknown as ToolLike | undefined;
  const weatherTool = toolRegistry.getCurrentWeather as unknown as ToolLike | undefined;
  const safetyTool = toolRegistry.getTravelAdvisory as unknown as ToolLike | undefined;
  const rateLimit = buildRateLimit("destinationResearch", identifier);

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
        key: () => "agent:destination:web-search",
        namespace: "agent:destination:web-search",
        ttlSeconds: 60 * 30,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:destination:web-search",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "destinationResearch",
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
        key: () => "agent:destination:web-search-batch",
        namespace: "agent:destination:web-search-batch",
        ttlSeconds: 60 * 30,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:destination:web-search-batch",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "destinationResearch",
      },
    },
    inputSchema: webSearchBatchInputSchema,
    name: "webSearchBatch",
  });

  const crawlSite = createAiTool({
    description: crawlSiteTool?.description ?? "Crawl website",
    execute: async (params, callOptions) => {
      if (!crawlSiteTool) return { pages: [], provider: "stub" };
      if (typeof crawlSiteTool.execute !== "function") {
        throw new Error("Tool crawlSite missing execute binding");
      }
      return (await crawlSiteTool.execute(params, callOptions)) as unknown;
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:destination:crawl",
        namespace: "agent:destination:crawl",
        ttlSeconds: 60 * 60,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:destination:crawl",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "destinationResearch",
      },
    },
    inputSchema: crawlSiteInputSchema,
    name: "crawlSite",
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
        key: () => "agent:destination:poi",
        namespace: "agent:destination:poi",
        ttlSeconds: 600,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:destination:poi",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "destinationResearch",
      },
    },
    inputSchema: lookupPoiInputSchema,
    name: "lookupPoiContext",
  });

  const getCurrentWeather = createAiTool({
    description: weatherTool?.description ?? "Get current weather",
    execute: async (params, callOptions) => {
      if (!weatherTool)
        return { condition: "unknown", provider: "stub", temperature: 0 };
      if (typeof weatherTool.execute !== "function") {
        throw new Error("Tool getCurrentWeather missing execute binding");
      }
      return (await weatherTool.execute(params, callOptions)) as unknown;
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:destination:weather",
        namespace: "agent:destination:weather",
        ttlSeconds: 60 * 30,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:destination:weather",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "destinationResearch",
      },
    },
    inputSchema: getCurrentWeatherInputSchema,
    name: "getCurrentWeather",
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
        key: () => "agent:destination:safety",
        namespace: "agent:destination:safety",
        ttlSeconds: 60 * 60 * 24 * 7,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:destination:safety",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "destinationResearch",
      },
    },
    inputSchema: travelAdvisoryInputSchema,
    name: "getTravelAdvisory",
  });

  return {
    crawlSite,
    getCurrentWeather,
    getTravelAdvisory,
    lookupPoiContext,
    webSearch,
    webSearchBatch,
  } satisfies ToolSet;
}

/**
 * Execute the destination agent with AI SDK v6 streaming.
 *
 * Builds system instructions and messages, wraps core tools with guardrails,
 * and streams a model-guided tool loop to produce results structured per
 * `dest.v1` schema.
 *
 * @param deps Language model, model identifier, and request-scoped utilities.
 * @param input Validated destination research request.
 * @returns AI SDK stream result for UI consumption.
 */
export function runDestinationAgent(
  deps: {
    model: LanguageModel;
    modelId: string;
    identifier: string;
  },
  input: DestinationResearchRequest
) {
  const instructions = buildDestinationPrompt(input);
  const userPrompt = `Research destination and summarize. Always return JSON with schemaVersion="dest.v1" and sources[]. Parameters: ${JSON.stringify(
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
    tools: buildDestinationTools(deps.identifier),
  });
}
