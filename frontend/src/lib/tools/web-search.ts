/**
 * @fileoverview Web search tools using Firecrawl v2.5 API with Redis caching.
 * Library-first: prefers Firecrawl endpoints; falls back to a 400 error if misconfigured.
 * Uses direct API (not SDK) for latest v2.5 features and cost control.
 */

import { tool } from "ai";
import { z } from "zod";
import { getRedis } from "@/lib/redis";

const scrapeOptionsSchema = z
  .object({
    formats: z.array(z.enum(["markdown", "html", "links", "screenshot"])).optional(),
    parsers: z.array(z.string()).optional(),
    proxy: z.enum(["basic", "stealth"]).optional(),
  })
  .optional();

type ScrapeOptions = z.infer<typeof scrapeOptionsSchema>;

/**
 * Generates a cache key that includes all parameters affecting results.
 */
function cacheKey(params: {
  query: string;
  limit: number;
  sources?: string[];
  categories?: string[];
  tbs?: string;
  location?: string;
  timeoutMs?: number;
  scrapeOptions?: ScrapeOptions;
}): string {
  const parts = [
    "ws",
    params.limit,
    params.query.trim().toLowerCase(),
    params.sources?.sort().join(",") ?? "web",
    params.categories?.sort().join(",") ?? "",
    params.tbs ?? "",
    params.location ?? "",
    params.timeoutMs ?? "",
  ];
  if (params.scrapeOptions) {
    const so = params.scrapeOptions;
    parts.push(
      so.formats?.sort().join(",") ?? "",
      so.parsers?.sort().join(",") ?? "",
      so.proxy ?? "basic"
    );
  } else {
    parts.push("", "", "");
  }
  return parts.join(":");
}

/**
 * Builds request body with cost-safe defaults.
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
    const cacheParams = {
      categories,
      limit,
      location,
      query,
      scrapeOptions,
      sources,
      tbs,
      timeoutMs,
    };
    const k = cacheKey(cacheParams);
    if (!fresh && redis) {
      const cached = await redis.get(k);
      if (cached) return cached;
    }
    const baseUrl = process.env.FIRECRAWL_BASE_URL ?? "https://api.firecrawl.dev/v2";
    const url = `${baseUrl}/search`;
    const body = buildRequestBody(cacheParams);
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
