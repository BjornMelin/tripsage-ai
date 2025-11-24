/**
 * @fileoverview Cache tag versioning for fine-grained invalidation.
 *
 * Implements a version-based cache invalidation strategy using Redis.
 * Each tag has a monotonically increasing version number. Cache keys
 * include the version, so bumping a tag's version effectively
 * invalidates all entries associated with that tag.
 *
 * @example
 * ```ts
 * // Create versioned cache key
 * const key = await versionedKey("trips", "user:123:list");
 * // => "trips:v1:user:123:list"
 *
 * // After bumping the tag version
 * await bumpTag("trips");
 * const newKey = await versionedKey("trips", "user:123:list");
 * // => "trips:v2:user:123:list" (new version, cache miss)
 * ```
 */

import "server-only";

import { getRedis } from "@/lib/redis";
import { warnRedisUnavailable } from "@/lib/telemetry/redis";

/** Redis feature identifier for telemetry. */
const REDIS_FEATURE = "cache.tags";

/** Namespace prefix for tag version keys. */
const NS = "tagver";

/**
 * Acquires Redis client with telemetry warning on unavailability.
 *
 * @returns Redis client or undefined if unavailable.
 */
function acquireRedis() {
  const client = getRedis();
  if (!client) warnRedisUnavailable(REDIS_FEATURE);
  return client;
}

/**
 * Gets the current version number for a cache tag.
 *
 * Returns 1 if tag doesn't exist or Redis is unavailable,
 * providing a safe default for cache key generation.
 *
 * @param tag - Cache tag name (e.g., "trips", "attachments").
 * @returns Current version number (>= 1).
 *
 * @example
 * ```ts
 * const version = await getTagVersion("trips");
 * // => 1 (initial) or higher after bumps
 * ```
 */
export async function getTagVersion(tag: string): Promise<number> {
  const redis = acquireRedis();
  if (!redis) return 1;

  const raw = await redis.get<number | string>(`${NS}:${tag}`);
  const parsed = typeof raw === "string" ? Number(raw) : raw;

  if (typeof parsed === "number" && Number.isFinite(parsed) && parsed > 0) {
    return parsed;
  }
  return 1;
}

/**
 * Increments a cache tag's version number.
 *
 * All cache entries using this tag in their versioned key will
 * effectively become stale (cache miss on next read).
 *
 * @param tag - Cache tag name to bump.
 * @returns New version number.
 *
 * @example
 * ```ts
 * // On trip creation, invalidate trips cache
 * await bumpTag("trips");
 * ```
 */
export async function bumpTag(tag: string): Promise<number> {
  const redis = acquireRedis();
  if (!redis) return 1;

  const v = await redis.incr(`${NS}:${tag}`);
  return v;
}

/**
 * Increments version numbers for multiple cache tags.
 *
 * Efficient batch invalidation when an operation affects multiple
 * cache categories.
 *
 * @param tags - Array of cache tag names to bump.
 * @returns Map of tag names to their new version numbers.
 *
 * @example
 * ```ts
 * // Invalidate multiple related caches
 * const versions = await bumpTags(["trips", "itineraries", "suggestions"]);
 * // => { trips: 2, itineraries: 1, suggestions: 3 }
 * ```
 */
export async function bumpTags(tags: string[]): Promise<Record<string, number>> {
  const redis = acquireRedis();
  if (!redis) {
    return Object.fromEntries(tags.map((tag) => [tag, 1]));
  }

  const entries = await Promise.all(
    tags.map(async (tag) => {
      const version = await redis.incr(`${NS}:${tag}`);
      return [tag, version] as const;
    })
  );

  return Object.fromEntries(entries);
}

/**
 * Creates a versioned cache key by prefixing with current tag version.
 *
 * The resulting key includes the tag's current version, so when the
 * tag is bumped, subsequent reads will generate different keys
 * (cache miss), effectively invalidating the old entries.
 *
 * @param tag - Cache tag name.
 * @param key - Base cache key.
 * @returns Versioned cache key in format "tag:vN:key".
 *
 * @example
 * ```ts
 * const key = await versionedKey("trips", "user:123:list:all");
 * // => "trips:v1:user:123:list:all"
 *
 * // After bumpTag("trips")
 * const newKey = await versionedKey("trips", "user:123:list:all");
 * // => "trips:v2:user:123:list:all"
 * ```
 */
export async function versionedKey(tag: string, key: string): Promise<string> {
  const v = await getTagVersion(tag);
  return `${tag}:v${v}:${key}`;
}
