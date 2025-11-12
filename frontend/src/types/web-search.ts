/**
 * @fileoverview Types and Zod schemas for the web search tool (Firecrawl v2.5).
 */

import { z } from "zod";

/**
 * Parameters for executing a web search query with configuration options for
 * result limits, source filtering, caching behavior, and geographic preferences.
 */
export type WebSearchParams = {
  /** Search query string. */
  query: string;
  /** Maximum number of results to return (range: 1-10). */
  limit?: number;
  /** Whether to bypass cache and fetch fresh results. */
  fresh?: boolean;
  /** Source types to include: "web", "news", "images". */
  sources?: ("web" | "news" | "images")[];
  /** Search categories to filter by (includes standard and custom strings). */
  categories?: string[];
  /** Time-based search filter (e.g., "qdr:d" for past day). */
  tbs?: string;
  /** Geographic region or language hint for localized results. */
  location?: string;
  /** Request timeout in milliseconds. */
  timeoutMs?: number;
  // Forward-compat fields (UNVERIFIED):
  /** Geographic region override. */
  region?: string;
  /** Result freshness preference. */
  freshness?: string;
  // Tool wrapper may inject:
  /** User identifier for per-user rate limiting or caching. */
  userId?: string;
};

/**
 * Single search result source with URL, title, snippet, and publication date
 * metadata when available.
 */
export type WebSearchSource = {
  /** Canonical URL of the search result. */
  url: string;
  /** Page title, if available. */
  title?: string;
  /** Text snippet or excerpt from the page, if available. */
  snippet?: string;
  /** Publication or last modified date in ISO format, if available. */
  publishedAt?: string;
};

/**
 * Strict output schema for webSearch tool.
 *
 * Enforces that tool always returns a validated object matching this schema.
 * Results array defaults to empty array; fromCache and tookMs are always present.
 */
export const WEB_SEARCH_OUTPUT_SCHEMA = z
  .object({
    fromCache: z.boolean(),
    results: z
      .array(
        z
          .object({
            publishedAt: z.string().optional(),
            snippet: z.string().optional(),
            title: z.string().optional(),
            url: z.string(),
          })
          .strict()
      )
      .default([]),
    tookMs: z.number(),
  })
  .strict();

/**
 * Complete web search response with results array, cache status, and timing
 * metadata.
 */
export type WebSearchResult = z.infer<typeof WEB_SEARCH_OUTPUT_SCHEMA>;

/**
 * Strict output schema for webSearchBatch tool.
 *
 * Enforces that tool always returns a validated object matching this schema.
 * Each query result has ok boolean, query string, and either value (success) or error (failure).
 * Total execution time (tookMs) is always present.
 */
export const WEB_SEARCH_BATCH_OUTPUT_SCHEMA = z
  .object({
    results: z.array(
      z
        .object({
          // When ok=false: error object with code and optional message
          error: z
            .object({
              code: z.string(),
              message: z.string().optional(),
            })
            .strict()
            .optional(),
          ok: z.boolean(),
          query: z.string(),
          // When ok=true: value must match webSearch output schema
          value: WEB_SEARCH_OUTPUT_SCHEMA.optional(),
        })
        .strict()
    ),
    tookMs: z.number(),
  })
  .strict();

/**
 * Batch web search response with per-query results and total execution time.
 */
export type WebSearchBatchResult = z.infer<typeof WEB_SEARCH_BATCH_OUTPUT_SCHEMA>;
