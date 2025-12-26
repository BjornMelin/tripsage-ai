/** @fileoverview Normalization utilities for web search tool results. */

import type { WebSearchSource } from "@ai/tools/schemas/web-search";
import { sanitizeForPrompt } from "@/lib/security/prompt-sanitizer";

/**
 * Normalizes a single search result item to match the strict schema.
 *
 * Extracts only the allowed fields (url, title, snippet, publishedAt) and
 * filters out any extra fields that Firecrawl may include.
 *
 * SECURITY: Title and snippet are sanitized to prevent indirect prompt
 * injection from malicious websites embedding hidden manipulation text.
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

  // SECURITY: Sanitize title to prevent injection via search results
  if (typeof record.title === "string") {
    normalized.title = sanitizeForPrompt(record.title, 200);
  }

  // SECURITY: Sanitize snippet to prevent injection via search results
  if (typeof record.snippet === "string") {
    normalized.snippet = sanitizeForPrompt(record.snippet, 500);
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
