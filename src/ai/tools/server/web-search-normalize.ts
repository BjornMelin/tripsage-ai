/**
 * @fileoverview Normalization utilities for web search tool results.
 */

import type { WebSearchSource } from "@ai/tools/schemas/web-search";
import { sanitizeForPrompt } from "@/lib/security/prompt-sanitizer";

const FIRECRAWL_SEARCH_SOURCE_KEYS = ["web", "news", "images"] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Extracts result arrays from Firecrawl search payloads.
 *
 * Firecrawl v2 returns results under `data.web`, `data.news`, and `data.images`.
 * Older local tests and adapters may still return a flat `results` array, so this
 * keeps that legacy shape readable while normalizing the documented v2 shape.
 */
export function extractFirecrawlSearchResults(payload: unknown): unknown[] {
  if (!isRecord(payload)) {
    return [];
  }

  if (Array.isArray(payload.results)) {
    return payload.results;
  }

  const data = payload.data;
  if (!isRecord(data)) {
    return [];
  }

  return FIRECRAWL_SEARCH_SOURCE_KEYS.flatMap((key) => {
    const value = data[key];
    return Array.isArray(value) ? value : [];
  });
}

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
  } else if (typeof record.description === "string") {
    normalized.snippet = sanitizeForPrompt(record.description, 500);
  }

  if (typeof record.publishedAt === "string") {
    normalized.publishedAt = record.publishedAt;
  } else if (typeof record.date === "string") {
    normalized.publishedAt = record.date;
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
