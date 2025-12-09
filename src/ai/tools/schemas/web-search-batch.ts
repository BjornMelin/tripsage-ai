/**
 * @fileoverview Zod schemas for web search batch API responses and web search batch tool inputs.
 *
 * Core schemas: Web search batch API parameters and data structures
 * Tool schemas: Input validation for web search batch tools (batch search)
 */

import { z } from "zod";

/** Schema for web search batch tool input. */
export const webSearchBatchInputSchema = z.strictObject({
  categories: z
    .array(z.string())
    .nullable()
    .describe("Search categories to filter results"),
  fresh: z
    .boolean()
    .default(false)
    .nullable()
    .describe("Whether to prioritize fresh results"),
  limit: z
    .number()
    .int()
    .min(1)
    .max(10)
    .default(5)
    .nullable()
    .describe("Maximum results per query"),
  location: z
    .string()
    .max(120)
    .nullable()
    .describe("Geographic location for localized search"),
  queries: z
    .array(z.string().min(2).max(256))
    .min(1)
    .max(10)
    .describe("Array of search queries to execute"),
  scrapeOptions: z
    .strictObject({
      formats: z
        .array(z.enum(["markdown", "html", "links", "screenshot"]))
        .nullable()
        .describe("Content formats to return"),
      parsers: z.array(z.string()).nullable().describe("Custom parsers to apply"),
      proxy: z
        .enum(["basic", "stealth"])
        .nullable()
        .describe("Proxy type for scraping"),
    })
    .nullable()
    .describe("Options for content scraping"),
  sources: z
    .array(z.enum(["web", "news", "images"]))
    .nullable()
    .describe("Content sources to search"),
  tbs: z.string().nullable().describe("Time-based search filter"),
  timeoutMs: z.number().int().positive().nullable().describe("Timeout in milliseconds"),
  userId: z.string().nullable().describe("User identifier for the search"),
});
