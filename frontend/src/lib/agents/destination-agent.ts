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
import { z } from "zod";

import { runWithGuardrails } from "@/lib/agents/runtime";
import { buildRateLimit } from "@/lib/ratelimit/config";
import { toolRegistry } from "@/lib/tools";
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

  const webSearch = tool({
    description: webSearchTool.description ?? "Web search",
    execute: async (params: unknown) => {
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:destination:web-search",
            ttlSeconds: 60 * 30,
          },
          rateLimit: buildRateLimit("destinationResearch", identifier),
          tool: "webSearch",
          workflow: "destinationResearch",
        },
        params,
        async (validated) => webSearchTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  const webSearchBatch = tool({
    description: webSearchBatchTool.description ?? "Batch web search",
    execute: async (params: unknown) => {
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:destination:web-search-batch",
            ttlSeconds: 60 * 30,
          },
          rateLimit: buildRateLimit("destinationResearch", identifier),
          tool: "webSearchBatch",
          workflow: "destinationResearch",
        },
        params,
        async (validated) => webSearchBatchTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  const crawlSite = tool({
    description: crawlSiteTool?.description ?? "Crawl website",
    execute: async (params: unknown) => {
      if (!crawlSiteTool) return { pages: [], provider: "stub" };
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:destination:crawl",
            ttlSeconds: 60 * 60,
          },
          rateLimit: buildRateLimit("destinationResearch", identifier),
          tool: "crawlSite",
          workflow: "destinationResearch",
        },
        params,
        async (validated) => crawlSiteTool.execute(validated)
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
          cache: { hashInput: true, key: "agent:destination:poi", ttlSeconds: 600 },
          rateLimit: buildRateLimit("destinationResearch", identifier),
          tool: "lookupPoiContext",
          workflow: "destinationResearch",
        },
        params,
        async (validated) => poiTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
  });

  const getCurrentWeather = tool({
    description: weatherTool?.description ?? "Get current weather",
    execute: async (params: unknown) => {
      if (!weatherTool)
        return { condition: "unknown", provider: "stub", temperature: 0 };
      const { result } = await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "agent:destination:weather",
            ttlSeconds: 60 * 30,
          },
          rateLimit: buildRateLimit("destinationResearch", identifier),
          tool: "getCurrentWeather",
          workflow: "destinationResearch",
        },
        params,
        async (validated) => weatherTool.execute(validated)
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
            key: "agent:destination:safety",
            ttlSeconds: 60 * 60 * 24 * 7,
          },
          rateLimit: buildRateLimit("destinationResearch", identifier),
          tool: "getTravelAdvisory",
          workflow: "destinationResearch",
        },
        params,
        async (validated) => safetyTool.execute(validated)
      );
      return result;
    },
    inputSchema: z.any(),
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
