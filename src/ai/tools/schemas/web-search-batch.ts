/**
 * @fileoverview Zod schemas for web search batch API responses and web search batch tool inputs.
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
  userId: z.string().min(1).nullish().describe("User identifier for the search"),
});

// ===== MODEL OUTPUT SCHEMAS =====

/** Individual search result for model consumption. */
const webSearchResultModelOutputSchema = z.strictObject({
  title: z.string().optional(),
  url: z.string(),
});

/** Per-query result value for model consumption. */
const webSearchQueryValueModelOutputSchema = z.strictObject({
  resultCount: z.number().int(),
  results: z.array(webSearchResultModelOutputSchema),
});

/** Per-query result entry for model consumption. */
const webSearchBatchResultEntryModelOutputSchema = z.strictObject({
  error: z.string().optional(),
  ok: z.boolean(),
  query: z.string(),
  value: webSearchQueryValueModelOutputSchema.optional(),
});

/** Web search batch result output schema for model consumption. */
export const webSearchBatchModelOutputSchema = z.strictObject({
  queryCount: z.number().int(),
  results: z.array(webSearchBatchResultEntryModelOutputSchema),
  tookMs: z.number(),
});

export type WebSearchBatchModelOutput = z.infer<typeof webSearchBatchModelOutputSchema>;
