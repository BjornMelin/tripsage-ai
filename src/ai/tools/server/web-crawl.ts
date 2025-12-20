/**
 * @fileoverview Firecrawl-backed web scrape/crawl tools with Redis caching.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import {
  crawlSiteInputSchema,
  crawlSiteOutputSchema,
  crawlUrlInputSchema,
  crawlUrlOutputSchema,
} from "@ai/tools/schemas/web-crawl";
import type { z } from "zod";

type RawScrapeOptions = z.infer<typeof crawlSiteInputSchema.shape.scrapeOptions>;

type ScrapeFormat =
  | "markdown"
  | "html"
  | "links"
  | "screenshot"
  | "summary"
  | {
      type: "json";
      prompt?: string;
      schema?: Record<string, unknown>;
    };

type ScrapeOptions = {
  actions?: Record<string, unknown>[];
  formats?: ScrapeFormat[];
  location?: { country?: string; languages?: string[] };
  maxAge?: number;
  onlyMainContent?: boolean;
  parsers?: string[];
  proxy?: "basic" | "stealth" | "auto";
};

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
    const formatsKey = so.formats
      ? so.formats
          .map((f) => (typeof f === "string" ? f : "json"))
          .sort()
          .join(",")
      : "";
    const parsersKey = so.parsers ? [...so.parsers].sort().join(",") : "";
    parts.push(
      formatsKey,
      parsersKey,
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
    includePaths ? [...includePaths].sort().join(",") : "",
    excludePaths ? [...excludePaths].sort().join(",") : "",
    sitemap ?? "",
  ];
  if (scrapeOptions) {
    const so = scrapeOptions;
    const formatsKey = so.formats
      ? so.formats
          .map((f) => (typeof f === "string" ? f : "json"))
          .sort()
          .join(",")
      : "";
    const parsersKey = so.parsers ? [...so.parsers].sort().join(",") : "";
    parts.push(formatsKey, parsersKey, so.proxy ?? "basic");
  }
  return parts.join(":");
}

function normalizeScrapeOptionsForCache(
  scrapeOptions: RawScrapeOptions
): ScrapeOptions | undefined {
  if (scrapeOptions === null) {
    return undefined;
  }
  const normalized: ScrapeOptions = {};
  if (scrapeOptions.actions !== null) {
    normalized.actions = scrapeOptions.actions;
  }
  if (scrapeOptions.formats !== null) {
    const formats: ScrapeFormat[] = [];
    for (const f of scrapeOptions.formats) {
      if (typeof f === "object" && f !== null && "type" in f && f.type === "json") {
        const jsonFormat: {
          type: "json";
          prompt?: string;
          schema?: Record<string, unknown>;
        } = { type: "json" };
        if (f.prompt !== null) {
          jsonFormat.prompt = f.prompt;
        }
        if (f.schema !== null) {
          jsonFormat.schema = f.schema;
        }
        formats.push(jsonFormat);
      } else if (
        f === "markdown" ||
        f === "html" ||
        f === "links" ||
        f === "screenshot" ||
        f === "summary"
      ) {
        formats.push(f);
      }
    }
    normalized.formats = formats;
  }
  if (scrapeOptions.location !== null) {
    const loc: { country?: string; languages?: string[] } = {};
    if (scrapeOptions.location.country !== null) {
      loc.country = scrapeOptions.location.country;
    }
    if (scrapeOptions.location.languages !== null) {
      loc.languages = scrapeOptions.location.languages;
    }
    normalized.location = loc;
  }
  if (scrapeOptions.maxAge !== null) {
    normalized.maxAge = scrapeOptions.maxAge;
  }
  if (scrapeOptions.onlyMainContent !== null) {
    normalized.onlyMainContent = scrapeOptions.onlyMainContent;
  }
  if (scrapeOptions.parsers !== null) {
    normalized.parsers = scrapeOptions.parsers;
  }
  if (scrapeOptions.proxy !== null) {
    normalized.proxy = scrapeOptions.proxy;
  }
  if (Object.keys(normalized).length === 0) {
    return undefined;
  }
  return normalized;
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
      ...(so.actions && { actions: so.actions }),
      formats: so.formats ?? ["markdown"],
      ...(so.location && { location: so.location }),
      ...(so.maxAge !== undefined && { maxAge: so.maxAge }),
      ...(so.onlyMainContent !== undefined && { onlyMainContent: so.onlyMainContent }),
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

export const crawlUrl = createAiTool({
  description:
    "Scrape a single URL via Firecrawl v2.5. Supports multiple formats " +
    "(markdown, html, links, screenshot, summary, json), cost-safe defaults, " +
    "and optional page interactions.",
  execute: async ({ url, scrapeOptions }) => {
    const { getServerEnvVar, getServerEnvVarWithFallback } = await import(
      "@/lib/env/server"
    );
    let apiKey: string;
    try {
      apiKey = getServerEnvVar("FIRECRAWL_API_KEY");
    } catch {
      // Normalize missing configuration into a tool-specific error code
      throw new Error("web_crawl_not_configured");
    }
    if (!apiKey) throw new Error("web_crawl_not_configured");
    const baseUrl =
      getServerEnvVarWithFallback(
        "FIRECRAWL_BASE_URL",
        "https://api.firecrawl.dev/v2"
      ) ?? "https://api.firecrawl.dev/v2";
    const normalizedScrapeOptions = normalizeScrapeOptionsForCache(scrapeOptions);
    const body = buildScrapeBody(url, normalizedScrapeOptions);
    const endpoint = `${baseUrl}/scrape`;
    const res = await fetch(endpoint, {
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
    return await res.json();
  },
  guardrails: {
    cache: {
      key: (params) =>
        scrapeCacheKey(
          params.url,
          normalizeScrapeOptionsForCache(params.scrapeOptions)
        ),
      namespace: "tool:web-crawl:scrape",
      shouldBypass: (params) => Boolean(params.fresh),
      ttlSeconds: 6 * 3600,
    },
    telemetry: {
      attributes: (params) => ({
        fresh: Boolean(params.fresh),
      }),
      redactKeys: ["url"],
    },
  },
  inputSchema: crawlUrlInputSchema,
  name: "crawlUrl",
  outputSchema: crawlUrlOutputSchema,
  validateOutput: true,
});

export const crawlSite = createAiTool({
  description:
    "Crawl a site (limited) via Firecrawl v2.5. Supports path filtering " +
    "(includePaths, excludePaths), sitemap control, scrape options per page, " +
    "and client-side polling with limits.",
  execute: async ({
    url,
    limit,
    fresh: _fresh,
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
    const { getServerEnvVar, getServerEnvVarWithFallback } = await import(
      "@/lib/env/server"
    );
    let apiKey: string;
    try {
      apiKey = getServerEnvVar("FIRECRAWL_API_KEY");
    } catch {
      throw new Error("web_crawl_not_configured");
    }
    if (!apiKey) throw new Error("web_crawl_not_configured");
    const baseUrl =
      getServerEnvVarWithFallback(
        "FIRECRAWL_BASE_URL",
        "https://api.firecrawl.dev/v2"
      ) ?? "https://api.firecrawl.dev/v2";
    const normalizedScrapeOptions = normalizeScrapeOptionsForCache(scrapeOptions);
    const body = buildCrawlBody(
      url,
      limit,
      includePaths ?? undefined,
      excludePaths ?? undefined,
      sitemap ?? undefined,
      normalizedScrapeOptions
    );
    const startEndpoint = `${baseUrl}/crawl`;
    const startRes = await fetch(startEndpoint, {
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
    const startData = (await startRes.json()) as { id?: unknown };
    const rawId = startData.id;
    let crawlId: string;
    if (typeof rawId === "string") {
      crawlId = rawId;
    } else if (typeof rawId === "number") {
      crawlId = String(rawId);
    } else {
      throw new Error("web_crawl_failed:no_crawl_id");
    }
    return await pollCrawlStatus(baseUrl, apiKey, crawlId, {
      maxPages: maxPages ?? undefined,
      maxResults: maxResults ?? undefined,
      maxWaitTime: maxWaitTime ?? undefined,
      pollInterval: pollInterval ?? 2,
      timeoutMs: timeoutMs ?? 120000,
    });
  },
  guardrails: {
    cache: {
      key: (params) =>
        crawlCacheKey(
          params.url,
          params.limit,
          params.includePaths ?? undefined,
          params.excludePaths ?? undefined,
          params.sitemap ?? undefined,
          normalizeScrapeOptionsForCache(params.scrapeOptions)
        ),
      namespace: "tool:web-crawl:crawl",
      shouldBypass: (params) => Boolean(params.fresh),
      ttlSeconds: 6 * 3600,
    },
    telemetry: {
      attributes: (params) => ({
        fresh: Boolean(params.fresh),
        limit: params.limit,
      }),
      redactKeys: ["url"],
    },
  },
  inputSchema: crawlSiteInputSchema,
  name: "crawlSite",
  outputSchema: crawlSiteOutputSchema,
  validateOutput: true,
});
