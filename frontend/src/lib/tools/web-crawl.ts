/**
 * @fileoverview Web crawl/scrape tools using Firecrawl v2.5 API with Redis caching.
 * Library-first: prefers Firecrawl endpoints; falls back to a 400 error if misconfigured.
 * Uses direct API (not SDK) for latest v2.5 features and cost control.
 */

import "server-only";

import { tool } from "ai";
import { z } from "zod";
import { getRedis } from "@/lib/redis";

const scrapeOptionsSchema = z
  .object({
    actions: z.array(z.record(z.string(), z.unknown())).optional(),
    formats: z
      .array(
        z.union([
          z.enum(["markdown", "html", "links", "screenshot", "summary"]),
          z.object({
            prompt: z.string().optional(),
            schema: z.record(z.string(), z.unknown()).optional(),
            type: z.literal("json"),
          }),
        ])
      )
      .optional(),
    location: z
      .object({
        country: z.string().optional(),
        languages: z.array(z.string()).optional(),
      })
      .optional(),
    maxAge: z.number().int().nonnegative().optional(),
    onlyMainContent: z.boolean().optional(),
    parsers: z.array(z.string()).optional(),
    proxy: z.enum(["basic", "stealth", "auto"]).optional(),
  })
  .optional();

type ScrapeOptions = z.infer<typeof scrapeOptionsSchema>;

/**
 * Normalizes URL for cache key generation.
 */
function kv(s: string): string {
  return s.trim().toLowerCase();
}

/**
 * Generates cache key for scrape including all options affecting results.
 */
function scrapeCacheKey(url: string, scrapeOptions?: ScrapeOptions): string {
  const parts = ["wc", kv(url)];
  if (scrapeOptions) {
    const so = scrapeOptions;
    parts.push(
      so.formats
        ?.map((f) => (typeof f === "string" ? f : "json"))
        .sort()
        .join(",") ?? "",
      so.parsers?.sort().join(",") ?? "",
      so.proxy ?? "basic",
      so.onlyMainContent ? "1" : "0",
      so.maxAge?.toString() ?? ""
    );
  }
  return parts.join(":");
}

/**
 * Generates cache key for crawl including all options affecting results.
 */
function crawlCacheKey(
  url: string,
  limit: number,
  includePaths?: string[],
  excludePaths?: string[],
  sitemap?: string,
  scrapeOptions?: ScrapeOptions
): string {
  const parts = [
    "wcs",
    kv(url),
    limit.toString(),
    includePaths?.sort().join(",") ?? "",
    excludePaths?.sort().join(",") ?? "",
    sitemap ?? "",
  ];
  if (scrapeOptions) {
    const so = scrapeOptions;
    parts.push(
      so.formats
        ?.map((f) => (typeof f === "string" ? f : "json"))
        .sort()
        .join(",") ?? "",
      so.parsers?.sort().join(",") ?? "",
      so.proxy ?? "basic"
    );
  }
  return parts.join(":");
}

/**
 * Builds scrape request body with cost-safe defaults.
 */
function buildScrapeBody(
  url: string,
  scrapeOptions?: ScrapeOptions
): Record<string, unknown> {
  const body: Record<string, unknown> = { url };
  if (scrapeOptions) {
    const so = scrapeOptions;
    body.formats = so.formats ?? ["markdown"];
    if (so.parsers !== undefined) {
      body.parsers = so.parsers;
    } else {
      body.parsers = []; // Cost-safe: avoid PDF parsing unless explicit
    }
    body.proxy = so.proxy ?? "basic"; // Cost-safe: avoid stealth unless needed
    if (so.onlyMainContent !== undefined) {
      body.onlyMainContent = so.onlyMainContent;
    }
    if (so.maxAge !== undefined) {
      body.maxAge = so.maxAge;
    }
    if (so.actions && so.actions.length > 0) {
      body.actions = so.actions;
    }
    if (so.location) {
      body.location = so.location;
    }
  } else {
    body.formats = ["markdown"];
    body.parsers = [];
    body.proxy = "basic";
  }
  return body;
}

/**
 * Builds crawl request body with cost-safe defaults.
 */
function buildCrawlBody(
  url: string,
  limit: number,
  includePaths?: string[],
  excludePaths?: string[],
  sitemap?: string,
  scrapeOptions?: ScrapeOptions
): Record<string, unknown> {
  const body: Record<string, unknown> = {
    limit,
    url,
  };
  if (includePaths && includePaths.length > 0) {
    body.includePaths = includePaths;
  }
  if (excludePaths && excludePaths.length > 0) {
    body.excludePaths = excludePaths;
  }
  if (sitemap) {
    body.sitemap = sitemap;
  }
  if (scrapeOptions) {
    const so = scrapeOptions;
    body.scrapeOptions = {
      actions: so.actions,
      formats: so.formats ?? ["markdown"],
      location: so.location,
      maxAge: so.maxAge,
      onlyMainContent: so.onlyMainContent,
      parsers: so.parsers ?? [],
      proxy: so.proxy ?? "basic",
    };
  } else {
    body.scrapeOptions = {
      formats: ["markdown"],
      parsers: [],
      proxy: "basic",
    };
  }
  return body;
}

/**
 * Polls crawl status until completion or timeout.
 */
async function pollCrawlStatus(
  baseUrl: string,
  apiKey: string,
  crawlId: string,
  options: {
    pollInterval?: number;
    timeoutMs?: number;
    maxPages?: number;
    maxResults?: number;
    maxWaitTime?: number;
  }
): Promise<Record<string, unknown>> {
  const {
    pollInterval = 2,
    timeoutMs = 120000,
    maxPages,
    maxResults,
    maxWaitTime,
  } = options;
  const startTime = Date.now();
  const maxWaitMs = maxWaitTime ? maxWaitTime * 1000 : timeoutMs;
  let pageCount = 0;
  let resultCount = 0;
  const allData: unknown[] = [];
  let next: string | null = null;

  while (true) {
    const elapsed = Date.now() - startTime;
    if (elapsed > maxWaitMs) {
      throw new Error(`web_crawl_timeout:${maxWaitMs}ms`);
    }

    const statusUrl: string = next
      ? `${baseUrl}/crawl/${crawlId}?skip=${resultCount}`
      : `${baseUrl}/crawl/${crawlId}`;
    const res: Response = await fetch(statusUrl, {
      headers: {
        authorization: `Bearer ${apiKey}`,
        "content-type": "application/json",
      },
    });

    if (!res.ok) {
      const text = await res.text();
      if (res.status === 429) {
        throw new Error(`web_crawl_rate_limited:${text}`);
      }
      if (res.status === 401) {
        throw new Error(`web_crawl_unauthorized:${text}`);
      }
      if (res.status === 402) {
        throw new Error(`web_crawl_payment_required:${text}`);
      }
      throw new Error(`web_crawl_failed:${res.status}:${text}`);
    }

    const status = (await res.json()) as {
      status: string;
      data?: unknown[];
      next?: string | null;
      total?: number;
      completed?: number;
    };
    const data = status.data || [];
    allData.push(...data);
    resultCount += data.length;
    pageCount += 1;

    if (status.status === "completed" || status.status === "failed") {
      return {
        ...status,
        data: allData,
        next: null,
      };
    }

    if (maxPages && pageCount >= maxPages) {
      return {
        ...status,
        data: allData,
        next: status.next || null,
      };
    }

    if (maxResults && resultCount >= maxResults) {
      return {
        ...status,
        data: allData,
        next: status.next || null,
      };
    }

    next = status.next || null;
    await new Promise((resolve) => setTimeout(resolve, pollInterval * 1000));
  }
}

export const crawlUrl = tool({
  description:
    "Scrape a single URL via Firecrawl v2.5. Supports multiple formats " +
    "(markdown, html, links, screenshot, summary, json), cost-safe defaults, " +
    "and optional page interactions.",
  execute: async ({ url, fresh, scrapeOptions }) => {
    const apiKey = process.env.FIRECRAWL_API_KEY;
    if (!apiKey) {
      throw new Error("web_crawl_not_configured");
    }
    const redis = getRedis();
    const ck = scrapeCacheKey(url, scrapeOptions);
    if (!fresh && redis) {
      const cached = await redis.get(ck);
      if (cached) return cached;
    }
    const baseUrl = process.env.FIRECRAWL_BASE_URL ?? "https://api.firecrawl.dev/v2";
    const body = buildScrapeBody(url, scrapeOptions);
    const res = await fetch(`${baseUrl}/scrape`, {
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
        throw new Error(`web_crawl_rate_limited:${text}`);
      }
      if (res.status === 401) {
        throw new Error(`web_crawl_unauthorized:${text}`);
      }
      if (res.status === 402) {
        throw new Error(`web_crawl_payment_required:${text}`);
      }
      throw new Error(`web_crawl_failed:${res.status}:${text}`);
    }
    const data = await res.json();
    if (redis) await redis.set(ck, data, { ex: 6 * 3600 });
    return data;
  },
  inputSchema: z.object({
    fresh: z.boolean().default(false),
    scrapeOptions: scrapeOptionsSchema,
    url: z.string().url(),
  }),
});

export const crawlSiteInputSchema = z.object({
  excludePaths: z.array(z.string()).optional(),
  fresh: z.boolean().default(false),
  includePaths: z.array(z.string()).optional(),
  limit: z.number().int().min(1).max(100).default(10),
  maxPages: z.number().int().positive().optional(),
  maxResults: z.number().int().positive().optional(),
  maxWaitTime: z.number().int().positive().optional(),
  pollInterval: z.number().int().positive().default(2).optional(),
  scrapeOptions: scrapeOptionsSchema,
  sitemap: z.enum(["include", "skip", "only"]).optional(),
  timeoutMs: z.number().int().positive().default(120000).optional(),
  url: z.string().url(),
});

export const crawlSite = tool({
  description:
    "Crawl a site (limited) via Firecrawl v2.5. Supports path filtering " +
    "(includePaths, excludePaths), sitemap control, scrape options per page, " +
    "and client-side polling with limits.",
  execute: async ({
    url,
    limit,
    fresh,
    includePaths,
    excludePaths,
    sitemap,
    scrapeOptions,
    pollInterval,
    timeoutMs,
    maxPages,
    maxResults,
    maxWaitTime,
  }) => {
    const apiKey = process.env.FIRECRAWL_API_KEY;
    if (!apiKey) {
      throw new Error("web_crawl_not_configured");
    }
    const redis = getRedis();
    const ck = crawlCacheKey(
      url,
      limit,
      includePaths,
      excludePaths,
      sitemap,
      scrapeOptions
    );
    if (!fresh && redis) {
      const cached = await redis.get(ck);
      if (cached) return cached;
    }
    const baseUrl = process.env.FIRECRAWL_BASE_URL ?? "https://api.firecrawl.dev/v2";
    const body = buildCrawlBody(
      url,
      limit,
      includePaths,
      excludePaths,
      sitemap,
      scrapeOptions
    );
    const startRes = await fetch(`${baseUrl}/crawl`, {
      body: JSON.stringify(body),
      headers: {
        authorization: `Bearer ${apiKey}`,
        "content-type": "application/json",
      },
      method: "POST",
    });
    if (!startRes.ok) {
      const text = await startRes.text();
      if (startRes.status === 429) {
        throw new Error(`web_crawl_rate_limited:${text}`);
      }
      if (startRes.status === 401) {
        throw new Error(`web_crawl_unauthorized:${text}`);
      }
      if (startRes.status === 402) {
        throw new Error(`web_crawl_payment_required:${text}`);
      }
      throw new Error(`web_crawl_failed:${startRes.status}:${text}`);
    }
    const startData = await startRes.json();
    const crawlId = startData.id as string;
    if (!crawlId) {
      throw new Error("web_crawl_failed:no_crawl_id");
    }
    const result = await pollCrawlStatus(baseUrl, apiKey, crawlId, {
      maxPages,
      maxResults,
      maxWaitTime,
      pollInterval: pollInterval ?? 2,
      timeoutMs: timeoutMs ?? 120000,
    });
    if (redis) await redis.set(ck, result, { ex: 6 * 3600 });
    return result;
  },
  inputSchema: crawlSiteInputSchema,
});
