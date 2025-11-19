/**
 * @fileoverview Normalization utilities for web search tool results.
 *
 * Strips extra fields from Firecrawl API responses to ensure strict schema
 * compliance. Firecrawl may return additional fields (for example content,
 * score, source) that are not part of our strict output schema.
 */

import type { WebSearchSource } from "@ai/tools/schemas/web-search";

/**
 * Normalizes a single search result item to match the strict schema.
 *
 * Extracts only the allowed fields (url, title, snippet, publishedAt) and
 * filters out any extra fields that Firecrawl may include.
 *
 * @param item Raw result item from Firecrawl API (may contain extra fields).
 * @returns Normalized result matching WebSearchSource schema, or null if invalid.
 */
export function normalizeWebSearchResult(item: unknown): WebSearchSource | null {
  if (!item || typeof item !== "object") {
    return null;
  }

  const record = item as Record<string, unknown>;
  const url = typeof record.url === "string" ? record.url : null;

  if (!url) {
    return null;
  }

  const normalized: WebSearchSource = {
    url,
  };

  if (typeof record.title === "string") {
    normalized.title = record.title;
  }

  if (typeof record.snippet === "string") {
    normalized.snippet = record.snippet;
  }

  if (typeof record.publishedAt === "string") {
    normalized.publishedAt = record.publishedAt;
  }

  return normalized;
}

/**
 * Normalizes an array of search results.
 *
 * Filters out invalid items and normalizes valid ones to match the strict schema.
 *
 * @param items Array of raw result items from Firecrawl API.
 * @returns Array of normalized results matching WebSearchSource schema.
 */
export function normalizeWebSearchResults(items: unknown[]): WebSearchSource[] {
  if (!Array.isArray(items)) {
    return [];
  }

  return items
    .map(normalizeWebSearchResult)
    .filter((result): result is WebSearchSource => result !== null);
}
