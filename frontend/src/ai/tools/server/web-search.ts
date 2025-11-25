/**
 * @fileoverview Web search tool powered by Firecrawl v2.5 with guardrails.
 * Provides standardized caching, rate limiting, telemetry, and error handling
 * through the createAiTool factory.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import {
  WEB_SEARCH_OUTPUT_SCHEMA,
  webSearchInputSchema,
} from "@ai/tools/schemas/web-search";
import {
  createToolError,
  isToolError,
  TOOL_ERROR_CODES,
} from "@ai/tools/server/errors";
import { normalizeWebSearchResults } from "@ai/tools/server/web-search-normalize";
import type { ToolCallOptions } from "ai";
import { z } from "zod";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { getServerEnvVar, getServerEnvVarWithFallback } from "@/lib/env/server";
import { fetchWithRetry } from "@/lib/http/retry";

const scrapeOptionsSchema = z
  .object({
    formats: z.array(z.enum(["markdown", "html", "links", "screenshot"])).optional(),
    parsers: z.array(z.string()).optional(),
    proxy: z.enum(["basic", "stealth"]).optional(),
  })
  .optional();

type ScrapeOptions = z.infer<typeof scrapeOptionsSchema>;

type WebSearchInput = z.infer<typeof webSearchInputSchema>;
type WebSearchResult = z.infer<typeof WEB_SEARCH_OUTPUT_SCHEMA>;

export const webSearch = createAiTool<WebSearchInput, WebSearchResult>({
  description:
    "Search the web via Firecrawl v2.5 and return normalized results. " +
    "Supports sources (web/news/images), categories (github/research/pdf), " +
    "time filters (tbs), location, and optional content scraping.",
  execute: async (params, callOptions) => runWebSearch(params, callOptions),
  guardrails: {
    cache: {
      deserialize: (payload) => {
        const data = (payload ?? {}) as Partial<WebSearchResult>;
        const rawResults = Array.isArray(data.results) ? data.results : [];
        const normalized = normalizeWebSearchResults(rawResults);
        return WEB_SEARCH_OUTPUT_SCHEMA.parse({
          fromCache: Boolean(data.fromCache),
          results: normalized,
          tookMs: typeof data.tookMs === "number" ? data.tookMs : 0,
        });
      },
      key: (params) => buildCacheKeySuffix(params),
      onHit: (cached, _params, meta) => ({
        ...cached,
        fromCache: true,
        tookMs: Date.now() - meta.startedAt,
      }),
      shouldBypass: (params) => Boolean(params.fresh),
      ttlSeconds: (params) => inferTtlSeconds(params.query),
    },
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
      identifier: (params) => params.userId ?? "anonymous",
      limit: 20,
      prefix: "ratelimit:tools:web-search",
      window: "1 m",
    },
    telemetry: {
      attributes: (params) => ({
        categoriesCount: Array.isArray(params.categories)
          ? params.categories.length
          : 0,
        fresh: Boolean(params.fresh),
        hasLocation: Boolean(params.location),
        hasTbs: Boolean(params.tbs),
        limit: params.limit,
        sourcesCount: Array.isArray(params.sources) ? params.sources.length : 0,
      }),
      redactKeys: ["query"],
    },
  },
  inputSchema: webSearchInputSchema,
  name: "webSearch",
});

async function runWebSearch(
  params: WebSearchInput,
  _callOptions?: ToolCallOptions
): Promise<WebSearchResult> {
  try {
    const apiKey = resolveFirecrawlApiKey();
    const startedAt = Date.now();
    const scrapeOptions =
      params.scrapeOptions !== null
        ? {
            formats: params.scrapeOptions?.formats ?? undefined,
            parsers: params.scrapeOptions?.parsers ?? undefined,
            proxy: params.scrapeOptions?.proxy ?? undefined,
          }
        : undefined;
    const requestParams = {
      categories: params.categories ?? undefined,
      freshness: params.freshness ?? undefined,
      limit: params.limit,
      location: params.location ?? undefined,
      query: params.query,
      region: params.region ?? undefined,
      scrapeOptions,
      sources: params.sources ?? undefined,
      tbs: params.tbs ?? undefined,
      timeoutMs: params.timeoutMs ?? undefined,
    } satisfies Parameters<typeof buildRequestBody>[0];
    const baseUrl = getServerEnvVarWithFallback(
      "FIRECRAWL_BASE_URL",
      "https://api.firecrawl.dev/v2"
    );
    const url = `${baseUrl}/search`;
    const body = buildRequestBody(requestParams);
    const response = await fetchWithRetry(
      url,
      {
        body: JSON.stringify(body),
        headers: {
          authorization: `Bearer ${apiKey}`,
          "content-type": "application/json",
        },
        method: "POST",
      },
      { retries: 2, timeoutMs: getTimeout(params.timeoutMs ?? undefined) }
    );
    if (!response.ok) {
      await handleHttpError(response);
    }
    const data = await response.json();
    const rawResults = Array.isArray(data.results) ? data.results : [];
    const normalized = normalizeWebSearchResults(rawResults);
    return WEB_SEARCH_OUTPUT_SCHEMA.parse({
      fromCache: false,
      results: normalized,
      tookMs: Date.now() - startedAt,
    });
  } catch (error) {
    if (isToolError(error)) {
      throw error;
    }
    throw createToolError(
      TOOL_ERROR_CODES.webSearchFailed,
      (error as Error).message || undefined
    );
  }
}

function resolveFirecrawlApiKey(): string {
  try {
    const key = getServerEnvVar("FIRECRAWL_API_KEY") as unknown as string;
    if (!key) {
      throw createToolError(TOOL_ERROR_CODES.webSearchNotConfigured);
    }
    return key;
  } catch {
    throw createToolError(TOOL_ERROR_CODES.webSearchNotConfigured);
  }
}

async function handleHttpError(response: Response): Promise<never> {
  const text = await response.text();
  if (response.status === 429) {
    throw createToolError(TOOL_ERROR_CODES.webSearchRateLimited, undefined, {
      body: text,
    });
  }
  if (response.status === 401) {
    throw createToolError(TOOL_ERROR_CODES.webSearchUnauthorized, undefined, {
      body: text,
    });
  }
  if (response.status === 402) {
    throw createToolError(TOOL_ERROR_CODES.webSearchPaymentRequired, undefined, {
      body: text,
    });
  }
  throw createToolError(TOOL_ERROR_CODES.webSearchFailed, undefined, {
    body: text,
    status: response.status,
  });
}

function getTimeout(timeoutMs?: number): number {
  const defaultMs = 12000;
  if (!timeoutMs) return defaultMs;
  return Math.min(20000, Math.max(5000, timeoutMs));
}

function buildCacheKeySuffix(params: WebSearchInput): string {
  const cacheParams: Record<string, unknown> = {
    categories: params.categories,
    freshness: params.freshness,
    limit: params.limit,
    location: params.location,
    query: params.query.trim().toLowerCase(),
    region: params.region,
    sources: params.sources,
    tbs: params.tbs,
    timeoutMs: params.timeoutMs,
  };

  if (params.scrapeOptions) {
    const { formats, parsers, proxy } = params.scrapeOptions;
    if (formats?.length) {
      cacheParams.scrapeOptionsFormats = [...formats].sort();
    }
    if (parsers?.length) {
      cacheParams.scrapeOptionsParsers = parsers;
    }
    if (proxy) {
      cacheParams.scrapeOptionsProxy = proxy;
    }
  }

  return canonicalizeParamsForCache(cacheParams, "ws");
}

function buildRequestBody(params: {
  query: string;
  limit: number;
  sources?: string[];
  categories?: string[];
  tbs?: string;
  location?: string;
  timeoutMs?: number;
  scrapeOptions?: ScrapeOptions;
  region?: string | undefined;
  freshness?: string | undefined;
}): Record<string, unknown> {
  const body: Record<string, unknown> = {
    query: params.query,
  };
  if (params.limit !== undefined) {
    body.limit = params.limit;
  }
  if (params.sources?.length) {
    body.sources = params.sources;
  }
  if (params.categories?.length) {
    body.categories = params.categories;
  }
  if (params.tbs) {
    body.tbs = params.tbs;
  }
  if (params.location) {
    body.location = params.location;
  }
  if (params.region) {
    body.region = params.region;
  }
  if (params.freshness) {
    body.freshness = params.freshness;
  }
  if (params.timeoutMs) {
    body.timeout = params.timeoutMs;
  }
  if (params.scrapeOptions) {
    const so = params.scrapeOptions;
    body.scrapeOptions = {
      ...(so.formats && so.formats.length > 0 && { formats: [...so.formats].sort() }),
      ...(so.parsers && so.parsers.length > 0 && { parsers: so.parsers }),
      ...(so.proxy && { proxy: so.proxy }),
    };
  }
  return body;
}

function inferTtlSeconds(query: string): number {
  const q = query.toLowerCase();
  if (/(\bnow\b|today|right now|weather)/.test(q)) return 120;
  if (/(breaking|\bnews\b|update)/.test(q)) return 600;
  if (/(price|fare|flight|deal)/.test(q)) return 3600;
  if (/(menu|hours|schedule)/.test(q)) return 21600;
  return 3600;
}
