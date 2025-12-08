/**
 * @fileoverview Type definitions for activities domain.
 *
 * Reuses Zod schemas from @schemas/search.ts to avoid duplication.
 */

import type { Activity, ActivitySearchParams } from "@schemas/search";

export type { Activity, ActivitySearchParams };

/**
 * Service context for activities operations.
 */
export interface ServiceContext {
  /** User ID for cache lookups and RLS. */
  userId?: string;
  /** Locale for internationalization. */
  locale?: string;
  /** IP address for rate limiting. */
  ip?: string;
  /** Feature flags. */
  featureFlags?: Record<string, boolean>;
}

/**
 * Activity search result metadata.
 */
export interface ActivitySearchMetadata {
  /** Total number of activities found. */
  total: number;
  /** Whether results came from cache. */
  cached: boolean;
  /** Primary source of results. */
  primarySource: "googleplaces" | "ai_fallback" | "mixed";
  /** All sources present in results. */
  sources: Array<"googleplaces" | "ai_fallback" | "cached">;
  /** Optional notes for UI/chat (e.g., caveats about AI suggestions). */
  notes?: string[];
}

/**
 * Activity search result.
 */
export interface ActivitySearchResult {
  /** Array of activities. */
  activities: Activity[];
  /** Search metadata. */
  metadata: ActivitySearchMetadata;
}
