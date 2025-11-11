/**
 * @fileoverview Web search tools using Firecrawl v2.5 API with Redis caching.
 * Library-first: prefers Firecrawl endpoints; falls back to a 400 error if misconfigured.
 * Uses direct API (not SDK) for latest v2.5 features and cost control.
 */

import { tool } from "ai";
import { z } from "zod";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { getRedis } from "@/lib/redis";

/**
 * Zod schema for optional scraping configuration.
 *
 * Controls content extraction formats, parsers, and proxy type for Firecrawl
 * search results.
 */
const scrapeOptionsSchema = z
  .object({
    formats: z.array(z.enum(["markdown", "html", "links", "screenshot"])).optional(),
    parsers: z.array(z.string()).optional(),
    proxy: z.enum(["basic", "stealth"]).optional(),
  })
  .optional();

/**
 * Type for scraping options configuration.
 *
 * Extracted from scrapeOptionsSchema for type-safe usage.
 */
type ScrapeOptions = z.infer<typeof scrapeOptionsSchema>;

/**
 * Builds request body for Firecrawl search API with cost-safe defaults.
 *
 * Applies cost-safe defaults for scrapeOptions (empty parsers array, basic proxy)
 * to minimize API costs. Sorts array values for consistent request formatting.
 *
 * @param params - Search parameters including query, filters, and scrape options.
 * @returns Request body object ready for JSON serialization.
 */
function buildRequestBody(params: {
  query: string;
  limit: number;
  sources?: string[];
  categories?: string[];
  tbs?: string;
  location?: string;
  timeoutMs?: number;
  scrapeOptions?: ScrapeOptions;
}): Record<string, unknown> {
  const body: Record<string, unknown> = {
    query: params.query,
  };
  if (params.limit !== undefined) {
    body.limit = params.limit;
  }
  if (params.sources && params.sources.length > 0) {
    body.sources = params.sources;
  }
  if (params.categories && params.categories.length > 0) {
    body.categories = params.categories;
  }
  if (params.tbs) {
    body.tbs = params.tbs;
  }
  if (params.location) {
    body.location = params.location;
  }
  if (params.timeoutMs) {
    body.timeout = params.timeoutMs;
  }
  if (params.scrapeOptions) {
    const so = params.scrapeOptions;
    body.scrapeOptions = {
      formats: so.formats ? [...so.formats].sort() : undefined,
      parsers: so.parsers ?? [], // Cost-safe: avoid PDF parsing unless explicit
      proxy: so.proxy ?? "basic", // Cost-safe: avoid stealth unless needed
    };
  }
  return body;
}

/**
 * Web search tool using Firecrawl v2.5 API.
 *
 * Searches the web via Firecrawl v2.5 and returns normalized results. Supports
 * multiple sources (web/news/images), categories (github/research/pdf), time
 * filters (tbs), location-based searches, and optional content scraping. Results
 * are cached in Redis for performance (1 hour TTL).
 *
 * @returns Search results object with normalized data from Firecrawl.
 * @throws {Error} Error with code indicating failure reason:
 *   - "web_search_not_configured": FIRECRAWL_API_KEY missing
 *   - "web_search_rate_limited": Rate limit exceeded (429)
 *   - "web_search_unauthorized": Authentication failed (401)
 *   - "web_search_payment_required": Payment required (402)
 *   - "web_search_failed": Generic API error with status code
 */
export const webSearch = tool({
  description:
    "Search the web via Firecrawl v2.5 and return normalized results. " +
    "Supports sources (web/news/images), categories (github/research/pdf), " +
    "time filters (tbs), location, and optional content scraping.",
  execute: async ({
    query,
    limit = 5,
    fresh,
    sources,
    categories,
    tbs,
    location,
    timeoutMs,
    scrapeOptions,
  }) => {
    const apiKey = process.env.FIRECRAWL_API_KEY;
    if (!apiKey) {
      throw new Error("web_search_not_configured");
    }
    const redis = getRedis();
    // Prepare params for request body (keep scrapeOptions nested)
    const requestParams = {
      categories,
      limit,
      location,
      query,
      scrapeOptions,
      sources,
      tbs,
      timeoutMs,
    };
    // Flatten scrapeOptions for cache key generation
    const cacheParams: Record<string, unknown> = {
      categories,
      limit,
      location,
      query: query.trim(),
      sources,
      tbs,
      timeoutMs,
    };
    // Flatten nested scrapeOptions object into cache params
    if (scrapeOptions) {
      if (scrapeOptions.formats && scrapeOptions.formats.length > 0) {
        cacheParams.scrapeOptionsFormats = scrapeOptions.formats;
      }
      if (scrapeOptions.parsers && scrapeOptions.parsers.length > 0) {
        cacheParams.scrapeOptionsParsers = scrapeOptions.parsers;
      }
      if (scrapeOptions.proxy) {
        cacheParams.scrapeOptionsProxy = scrapeOptions.proxy;
      }
    }
    const k = canonicalizeParamsForCache(cacheParams, "ws");
    if (!fresh && redis) {
      const cached = await redis.get(k);
      if (cached) return cached;
    }
    const baseUrl = process.env.FIRECRAWL_BASE_URL ?? "https://api.firecrawl.dev/v2";
    const url = `${baseUrl}/search`;
    const body = buildRequestBody(requestParams);
    const res = await fetch(url, {
      body: JSON.stringify(body),
      headers: {
        authorization: `Bearer ${apiKey}`,
        "content-type": "application/json",
      },
      method: "POST",
    });
    if (!res.ok) {
      const text = await res.text();
      if (res.status === 429) {
        throw new Error(`web_search_rate_limited:${text}`);
      }
      if (res.status === 401) {
        throw new Error(`web_search_unauthorized:${text}`);
      }
      if (res.status === 402) {
        throw new Error(`web_search_payment_required:${text}`);
      }
      throw new Error(`web_search_failed:${res.status}:${text}`);
    }
    const data = await res.json();
    if (redis) await redis.set(k, data, { ex: 3600 });
    return data;
  },
  inputSchema: z.object({
    categories: z.array(z.enum(["github", "research", "pdf"])).optional(),
    fresh: z.boolean().default(false),
    limit: z.number().int().min(1).max(10).default(5),
    location: z.string().optional(),
    query: z.string().min(2),
    scrapeOptions: scrapeOptionsSchema,
    sources: z
      .array(z.enum(["web", "news", "images"]))
      .default(["web"])
      .optional(),
    tbs: z.string().optional(),
    timeoutMs: z.number().int().positive().optional(),
  }),
});
