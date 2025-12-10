// biome-ignore-all lint/style/useNamingConvention: Keys match Supabase table names (snake_case)

/**
 * @fileoverview Cache tag registry for database table to cache tag mappings.
 *
 * Centralizes cache invalidation logic to avoid hardcoded mappings scattered
 * across handlers. Edit this file to add/modify cache relationships.
 *
 * @see SPEC-0021 for the full webhook flow mapping table
 */

import "server-only";

// ===== REGISTRY =====

/**
 * Cache tag registry mapping database tables to their cache tags.
 *
 * When a table changes, all associated tags should have their version bumped.
 * Tags are used to compose cache keys as `tag:v{version}:{key}`.
 *
 * Note: Keys use snake_case to match Supabase table naming convention.
 *
 * @see src/lib/cache/tags.ts for bumpTags and getTagVersion functions
 */
export const CACHE_TAG_REGISTRY = {
  // Accommodation-related tables
  accommodations: ["accommodation", "hotel_search", "search", "search_cache"],

  // Chat/memory tables
  chat_messages: ["memory", "conversation", "chat_memory"],
  chat_sessions: ["memory", "conversation", "chat_memory"],

  // File attachments
  file_attachments: ["files", "trip_files"],

  // Flight-related tables
  flights: ["flight", "flight_search", "search", "search_cache"],
  search_activities: ["search", "search_cache"],

  // Search result tables
  search_destinations: ["search", "search_cache"],
  search_flights: ["search", "search_cache"],
  search_hotels: ["search", "search_cache"],
  trip_collaborators: ["trips", "users", "search"],
  // Trip-related tables
  trips: ["trip", "user_trips", "trip_search", "search", "search_cache"],
} as const satisfies Record<string, readonly string[]>;

/**
 * Type for valid cache table names.
 */
export type CacheTable = keyof typeof CACHE_TAG_REGISTRY;

/**
 * Default tags used when a table is not in the registry.
 * These are generic catch-all tags for unknown tables.
 */
const DEFAULT_TAGS = ["search", "cache"] as const;

// ===== EXPORTS =====

/**
 * Get cache tags for a database table.
 *
 * Returns the registered tags for known tables, or default tags for unknown tables.
 * This is the primary interface for cache invalidation handlers.
 *
 * @param table - Database table name
 * @returns Array of cache tags to invalidate
 *
 * @example
 * ```ts
 * const tags = getTagsForTable("trips");
 * // => ["trip", "user_trips", "trip_search", "search", "search_cache"]
 *
 * const unknown = getTagsForTable("unknown_table");
 * // => ["search", "cache"]
 * ```
 */
export function getTagsForTable(table: string): string[] {
  const registeredTags = CACHE_TAG_REGISTRY[table as CacheTable];
  return registeredTags ? [...registeredTags] : [...DEFAULT_TAGS];
}

/**
 * Check if a table is registered in the cache tag registry.
 *
 * @param table - Database table name to check
 * @returns true if the table has registered cache tags
 */
export function isRegisteredTable(table: string): table is CacheTable {
  return table in CACHE_TAG_REGISTRY;
}

/**
 * Get all registered table names.
 *
 * @returns Array of all registered table names
 */
export function getRegisteredTables(): CacheTable[] {
  return Object.keys(CACHE_TAG_REGISTRY) as CacheTable[];
}

/**
 * Get all unique cache tags from the registry.
 *
 * @returns Array of all unique cache tags
 */
export function getAllCacheTags(): string[] {
  const allTags = new Set<string>();
  for (const tags of Object.values(CACHE_TAG_REGISTRY)) {
    for (const tag of tags) {
      allTags.add(tag);
    }
  }
  return [...allTags].sort();
}
