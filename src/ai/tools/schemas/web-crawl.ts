/**
 * @fileoverview Zod schemas for web crawl API responses and web crawl tool inputs.
 *
 * Core schemas: Web crawl API parameters and data structures
 * Tool schemas: Input validation for web crawl tools (site crawling)
 */

import { z } from "zod";

const scrapeOptionsSchema = z
  .strictObject({
    actions: z
      .array(z.record(z.string(), z.unknown()))
      .nullable()
      .describe("Custom scraping actions to perform"),
    formats: z
      .array(
        z.union([
          z
            .enum(["markdown", "html", "links", "screenshot", "summary"])
            .describe("Standard output format"),
          z
            .strictObject({
              prompt: z
                .string()
                .nullable()
                .describe("Custom prompt for JSON extraction"),
              schema: z
                .record(z.string(), z.unknown())
                .nullable()
                .describe("JSON schema for structured output"),
              type: z.literal("json").describe("Output type"),
            })
            .describe("Custom JSON extraction format"),
        ])
      )
      .nullable()
      .describe("Output formats for scraped content"),
    location: z
      .strictObject({
        country: z.string().nullable().describe("Country for geo-targeted scraping"),
        languages: z
          .array(z.string())
          .nullable()
          .describe("Preferred languages for content"),
      })
      .nullable()
      .describe("Geographic and language preferences"),
    maxAge: z
      .number()
      .int()
      .nonnegative()
      .nullable()
      .describe("Maximum age of cached content in seconds"),
    onlyMainContent: z
      .boolean()
      .nullable()
      .describe("Whether to extract only main content"),
    parsers: z.array(z.string()).nullable().describe("Custom parsers to apply"),
    proxy: z
      .enum(["basic", "stealth", "auto"])
      .nullable()
      .describe("Proxy configuration for scraping"),
  })
  .nullable()
  .describe("Options for content scraping");

/** Schema for crawl site tool input. */
export const crawlSiteInputSchema = z.strictObject({
  excludePaths: z
    .array(z.string())
    .nullable()
    .describe("URL paths to exclude from crawling"),
  fresh: z.boolean().default(false).describe("Whether to bypass cached results"),
  includePaths: z
    .array(z.string())
    .nullable()
    .describe("URL paths to include in crawling"),
  limit: z
    .number()
    .int()
    .min(1)
    .max(100)
    .default(10)
    .describe("Maximum number of pages to crawl"),
  maxPages: z.number().int().positive().nullable().describe("Maximum pages to crawl"),
  maxResults: z
    .number()
    .int()
    .positive()
    .nullable()
    .describe("Maximum results to return"),
  maxWaitTime: z
    .number()
    .int()
    .positive()
    .nullable()
    .describe("Maximum wait time between requests"),
  pollInterval: z
    .number()
    .int()
    .positive()
    .default(2)
    .nullable()
    .describe("Interval between crawl checks"),
  scrapeOptions: scrapeOptionsSchema.describe("Scraping configuration options"),
  sitemap: z
    .enum(["include", "skip", "only"])
    .nullable()
    .describe("How to handle sitemap"),
  timeoutMs: z
    .number()
    .int()
    .positive()
    .default(120000)
    .nullable()
    .describe("Timeout in milliseconds"),
  url: z.url().describe("Starting URL for the crawl"),
});
