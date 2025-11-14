/**
 * @fileoverview Cache tag versioning utilities for invalidation tracking.
 */

import "server-only";

import { getRedis } from "@/lib/redis";
import { warnRedisUnavailable } from "@/lib/telemetry/redis";

const REDIS_FEATURE = "cache.tags";

const NS = "tagver"; // namespace for tag versions

function acquireRedis() {
  const client = getRedis();
  if (!client) warnRedisUnavailable(REDIS_FEATURE);
  return client;
}

/**
 * Gets the current version number for a cache tag.
 *
 * @param tag - The cache tag name.
 * @return Current version number, defaults to 1 if not found.
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
 * Increments the version number for a cache tag.
 *
 * @param tag - The cache tag name to bump.
 * @return New version number.
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
 * @param tags - Array of cache tag names to bump.
 * @return Map of tag names to their new version numbers.
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
 * Creates a versioned cache key by prefixing with tag version.
 *
 * @param tag - The cache tag name.
 * @param key - The base cache key.
 * @return Versioned cache key string.
 */
export async function versionedKey(tag: string, key: string): Promise<string> {
  const v = await getTagVersion(tag);
  return `${tag}:v${v}:${key}`;
}
