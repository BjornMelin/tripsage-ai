/**
 * @fileoverview Zod v4 schemas for the web search tool (Firecrawl v2.5).
 */

import { z } from "zod";

/** TypeScript type for web search query parameters. */
export type WebSearchParams = {
  query: string;
  limit?: number;
  fresh?: boolean;
  sources?: ("web" | "news" | "images")[];
  categories?: string[];
  tbs?: string;
  location?: string;
  timeoutMs?: number;
  // UNVERIFIED forward-compat fields
  region?: string;
  freshness?: string;
  userId?: string;
};

/** TypeScript type for web search result source metadata. */
export type WebSearchSource = {
  url: string;
  title?: string;
  snippet?: string;
  publishedAt?: string;
};

/** Zod schema for web search API response data. */
export const WEB_SEARCH_OUTPUT_SCHEMA = z.strictObject({
  fromCache: z.boolean(),
  results: z
    .array(
      z.strictObject({
        publishedAt: z.string().optional(),
        snippet: z.string().optional(),
        title: z.string().optional(),
        url: z.string(),
      })
    )
    .default([]),
  tookMs: z.number(),
});
/** TypeScript type for web search results. */
export type WebSearchResult = z.infer<typeof WEB_SEARCH_OUTPUT_SCHEMA>;

/** Zod schema for batch web search API response data. */
export const WEB_SEARCH_BATCH_OUTPUT_SCHEMA = z.strictObject({
  results: z.array(
    z.strictObject({
      error: z
        .strictObject({
          code: z.string(),
          message: z.string().optional(),
        })
        .optional(),
      ok: z.boolean(),
      query: z.string(),
      value: WEB_SEARCH_OUTPUT_SCHEMA.optional(),
    })
  ),
  tookMs: z.number(),
});
/** TypeScript type for batch web search results. */
export type WebSearchBatchResult = z.infer<typeof WEB_SEARCH_BATCH_OUTPUT_SCHEMA>;
