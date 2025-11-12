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
import { stepCountIs, streamText, tool } from "ai";

import { buildGuardedTool } from "@/lib/agents/guarded-tool";
import { buildRateLimit } from "@/lib/ratelimit/config";
import { toolRegistry } from "@/lib/tools";
import { lookupPoiInputSchema } from "@/lib/tools/google-places";
import { travelAdvisoryInputSchema } from "@/lib/tools/travel-advisory";
import { getCurrentWeatherInputSchema } from "@/lib/tools/weather";
import { crawlSiteInputSchema } from "@/lib/tools/web-crawl";
import { webSearchInputSchema } from "@/lib/tools/web-search";
import { webSearchBatchInputSchema } from "@/lib/tools/web-search-batch";
import { buildDestinationPrompt } from "@/prompts/agents";
import type { DestinationResearchRequest } from "@/schemas/agents";

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
    execute: (params: unknown) => Promise<unknown>;
  };

  const webSearchTool = toolRegistry.webSearch as unknown as ToolLike;
  const webSearchBatchTool = toolRegistry.webSearchBatch as unknown as ToolLike;
  const crawlSiteTool = toolRegistry.crawlSite as unknown as ToolLike | undefined;
  const poiTool = toolRegistry.lookupPoiContext as unknown as ToolLike | undefined;
  const weatherTool = toolRegistry.getCurrentWeather as unknown as ToolLike | undefined;
  const safetyTool = toolRegistry.getTravelAdvisory as unknown as ToolLike | undefined;
  const rateLimit = buildRateLimit("destinationResearch", identifier);

  const guardedWebSearch = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:destination:web-search",
      ttlSeconds: 60 * 30,
    },
    execute: async (params: unknown) => await webSearchTool.execute(params),
    rateLimit,
    schema: webSearchInputSchema,
    toolKey: "webSearch",
    workflow: "destinationResearch",
  });

  const guardedWebSearchBatch = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:destination:web-search-batch",
      ttlSeconds: 60 * 30,
    },
    execute: async (params: unknown) => await webSearchBatchTool.execute(params),
    rateLimit,
    schema: webSearchBatchInputSchema,
    toolKey: "webSearchBatch",
    workflow: "destinationResearch",
  });

  const guardedCrawlSite = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:destination:crawl",
      ttlSeconds: 60 * 60,
    },
    execute: async (params: unknown) => {
      if (!crawlSiteTool) return { pages: [], provider: "stub" };
      return await crawlSiteTool.execute(params);
    },
    rateLimit,
    schema: crawlSiteInputSchema,
    toolKey: "crawlSite",
    workflow: "destinationResearch",
  });

  const guardedLookupPoi = buildGuardedTool({
    cache: { hashInput: true, key: "agent:destination:poi", ttlSeconds: 600 },
    execute: async (params: unknown) => {
      if (!poiTool) return { inputs: params, pois: [], provider: "stub" };
      return await poiTool.execute(params);
    },
    rateLimit,
    schema: lookupPoiInputSchema,
    toolKey: "lookupPoiContext",
    workflow: "destinationResearch",
  });

  const guardedGetCurrentWeather = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:destination:weather",
      ttlSeconds: 60 * 30,
    },
    execute: async (params: unknown) => {
      if (!weatherTool)
        return { condition: "unknown", provider: "stub", temperature: 0 };
      return await weatherTool.execute(params);
    },
    rateLimit,
    schema: getCurrentWeatherInputSchema,
    toolKey: "getCurrentWeather",
    workflow: "destinationResearch",
  });

  const guardedGetTravelAdvisory = buildGuardedTool({
    cache: {
      hashInput: true,
      key: "agent:destination:safety",
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
    workflow: "destinationResearch",
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

  const crawlSite = tool({
    description: crawlSiteTool?.description ?? "Crawl website",
    execute: guardedCrawlSite,
    inputSchema: crawlSiteInputSchema,
  });

  const lookupPoiContext = tool({
    description: poiTool?.description ?? "Lookup POIs (context)",
    execute: guardedLookupPoi,
    inputSchema: lookupPoiInputSchema,
  });

  const getCurrentWeather = tool({
    description: weatherTool?.description ?? "Get current weather",
    execute: guardedGetCurrentWeather,
    inputSchema: getCurrentWeatherInputSchema,
  });

  const getTravelAdvisory = tool({
    description: safetyTool?.description ?? "Get travel advisory and safety scores",
    execute: guardedGetTravelAdvisory,
    inputSchema: travelAdvisoryInputSchema,
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
 * @param deps Language model and request-scoped utilities.
 * @param input Validated destination research request.
 * @returns AI SDK stream result for UI consumption.
 */
export function runDestinationAgent(
  deps: {
    model: LanguageModel;
    identifier: string;
  },
  input: DestinationResearchRequest
) {
  const instructions = buildDestinationPrompt(input);
  return streamText({
    model: deps.model,
    prompt: `Research destination and summarize. Always return JSON with schemaVersion="dest.v1" and sources[]. Parameters: ${JSON.stringify(
      input
    )}`,
    stopWhen: stepCountIs(15),
    system: instructions,
    temperature: 0.3,
    tools: buildDestinationTools(deps.identifier),
  });
}
