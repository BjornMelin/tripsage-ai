/**
 * @fileoverview Web search tools using Firecrawl v2.5 API with Redis caching.
 * Library-first: prefers Firecrawl endpoints; falls back to a 400 error if misconfigured.
 * Uses direct API (not SDK) for latest v2.5 features and cost control.
 */

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import { tool } from "ai";
import { z } from "zod";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { fetchWithRetry } from "@/lib/http/fetch-retry";
import { getRedis } from "@/lib/redis";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Build a per-request Upstash rate limiter for the web search tool.
 * When Upstash env vars are missing, returns undefined (graceful in dev/test).
 */
let cachedLimiter: InstanceType<typeof Ratelimit> | undefined;
function buildToolRateLimiter(): InstanceType<typeof Ratelimit> | undefined {
  if (cachedLimiter) return cachedLimiter;
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) return undefined;
  cachedLimiter = new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(20, "1 m"),
    prefix: "ratelimit:tools:web-search",
    redis: Redis.fromEnv(),
  });
  return cachedLimiter;
}

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
  // Forward-compat parameters (UNVERIFIED in Firecrawl docs)
  region?: string | undefined;
  freshness?: string | undefined;
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
  if (params.region) {
    body.region = params.region; // UNVERIFIED
  }
  if (params.freshness) {
    body.freshness = params.freshness; // UNVERIFIED
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
 * Infer cache TTL seconds from query content, mirroring Python heuristics.
 */
function inferTtlSeconds(query: string): number {
  const q = query.toLowerCase();
  if (/(\bnow\b|today|right now|weather)/.test(q)) return 120; // realtime
  if (/(breaking|\bnews\b|update)/.test(q)) return 600; // time-sensitive
  if (/(price|fare|flight|deal)/.test(q)) return 3600; // daily-ish
  if (/(menu|hours|schedule)/.test(q)) return 21600; // semi-static
  return 3600; // default
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
  // structured output optional; the tool returns a JSON object with results/fromCache/tookMs
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
    userId,
    region,
    freshness,
  }) => {
    return await withTelemetrySpan(
      "tool.web_search",
      {
        attributes: {
          categoriesCount: Array.isArray(categories) ? categories.length : 0,
          fresh: Boolean(fresh),
          hasLocation: Boolean(location),
          hasTbs: Boolean(tbs),
          limit,
          sourcesCount: Array.isArray(sources) ? sources.length : 0,
          "tool.name": "webSearch",
        },
        redactKeys: ["query"],
      },
      async (span) => {
        const apiKey = process.env.FIRECRAWL_API_KEY;
        if (!apiKey) {
          span.addEvent("not_configured");
          throw new Error("web_search_not_configured");
        }
        const startedAt = Date.now();
        const redis = getRedis();
        // Optional Upstash rate limiting per user
        try {
          const rl = buildToolRateLimiter();
          if (rl) {
            const identifier = `${userId ?? "anonymous"}`;
            const res = await rl.limit(identifier);
            if (!res.success) {
              span.addEvent("rate_limited", { identifier });
              const retrySec = res.reset
                ? Math.max(0, res.reset - Math.floor(Date.now() / 1000))
                : 60;
              const rateErr = new Error("web_search_rate_limited") as Error & {
                meta?: {
                  limit?: number;
                  remaining?: number;
                  reset?: number;
                  retryAfter?: number;
                };
              };
              rateErr.meta = {
                limit: res.limit,
                remaining: res.remaining,
                reset: res.reset,
                retryAfter: retrySec,
              };
              throw rateErr;
            }
          }
        } catch (e) {
          if ((e as Error).message?.startsWith?.("web_search_rate_limited")) throw e;
          // continue without RL if construction fails
        }
        // Prepare params for request body (keep scrapeOptions nested)
        const requestParams = {
          categories,
          freshness,
          limit,
          location,
          query,
          region,
          scrapeOptions,
          sources,
          tbs,
          timeoutMs,
        };
        // Flatten scrapeOptions for cache key generation
        const cacheParams: Record<string, unknown> = {
          categories,
          freshness,
          limit,
          location,
          query: query.trim().toLowerCase(),
          region,
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
          if (cached) {
            span.addEvent("cache_hit");
            span.setAttribute("from_cache", true);
            return { ...cached, fromCache: true, tookMs: Date.now() - startedAt };
          }
        }
        const baseUrl =
          process.env.FIRECRAWL_BASE_URL ?? "https://api.firecrawl.dev/v2";
        const url = `${baseUrl}/search`;
        const body = buildRequestBody(requestParams);
        span.addEvent("http_post", { url });
        const res = await fetchWithRetry(
          url,
          {
            body: JSON.stringify(body),
            headers: {
              authorization: `Bearer ${apiKey}`,
              "content-type": "application/json",
            },
            method: "POST",
          },
          { retries: 2, timeoutMs: Math.min(20000, Math.max(5000, timeoutMs ?? 12000)) }
        );
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
        if (redis) {
          const ttl = inferTtlSeconds(query);
          await redis.set(k, data, { ex: ttl });
        }
        const out = { ...data, fromCache: false, tookMs: Date.now() - startedAt } as {
          tookMs: number;
          fromCache: boolean;
        } & Record<string, unknown>;
        span.setAttribute("from_cache", false);
        span.setAttribute("took_ms", out.tookMs);
        return out;
      }
    );
  },
  inputSchema: z.object({
    categories: z
      .array(z.union([z.enum(["github", "research", "pdf"]), z.string()]))
      .optional(),
    fresh: z.boolean().default(false),
    freshness: z.string().optional(), // UNVERIFIED
    limit: z.number().int().min(1).max(10).default(5),
    location: z.string().max(120).optional(),
    query: z.string().min(2).max(256),
    region: z.string().optional(), // UNVERIFIED
    scrapeOptions: scrapeOptionsSchema,
    sources: z
      .array(z.enum(["web", "news", "images"]))
      .default(["web"])
      .optional(),
    tbs: z.string().optional(),
    timeoutMs: z.number().int().positive().optional(),
    userId: z.string().optional(),
  }),
});
