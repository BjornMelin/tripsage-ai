/**
 * @fileoverview Types for the web search tool (Firecrawl v2.5).
 */

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
 * Complete web search response with results array, cache status, and timing
 * metadata.
 */
export type WebSearchResult = {
  /** Array of search result sources. */
  results: WebSearchSource[];
  /** Whether results were served from cache. */
  fromCache: boolean;
  /** Total time taken for the search operation in milliseconds. */
  tookMs: number;
};
