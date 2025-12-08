/**
 * @fileoverview Zod v4 schemas for web search API responses and web search tool inputs.
 *
 * Core schemas: Web search API parameters, results, and data structures
 * Tool schemas: Input validation for web search tools (search, batch search)
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

// ===== TOOL INPUT SCHEMAS =====
// Schemas for web search tool input validation

/** Schema for web search tool input. */
export const webSearchInputSchema = z.strictObject({
  categories: z
    .array(z.union([z.enum(["github", "research", "pdf"]), z.string()]))
    .nullable()
    .describe("Search categories to filter results"),
  fresh: z.boolean().default(false).describe("Whether to prioritize fresh results"),
  freshness: z.string().nullable().describe("Time-based freshness filter"), // UNVERIFIED
  limit: z
    .number()
    .int()
    .min(1)
    .max(10)
    .default(5)
    .describe("Maximum number of results"),
  location: z
    .string()
    .max(120)
    .nullable()
    .describe("Geographic location for localized search"),
  query: z.string().min(2).max(256).describe("Search query string"),
  region: z.string().nullable().describe("Region code for search"), // UNVERIFIED
  scrapeOptions: z
    .strictObject({
      formats: z
        .array(z.enum(["markdown", "html", "links", "screenshot"]))
        .nullable()
        .describe("Content formats to return"),
      parsers: z.array(z.string()).nullable().describe("Custom parsers to apply"),
      proxy: z.enum(["basic", "stealth"]).nullable().describe("Proxy configuration"),
    })
    .nullable()
    .describe("Options for content scraping"),
  sources: z
    .array(z.enum(["web", "news", "images"]))
    .default(["web"])
    .nullable()
    .describe("Content sources to search"),
  tbs: z.string().nullable().describe("Time-based search filter"),
  timeoutMs: z
    .number()
    .int()
    .positive()
    .nullable()
    .describe("Search timeout in milliseconds"),
  userId: z.string().nullable().describe("User identifier for the search"),
});
