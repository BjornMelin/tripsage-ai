/**
 * @fileoverview Next.js Cache Components helpers for public endpoints.
 *
 * IMPORTANT: Do NOT use "use cache" in modules that access:
 * - cookies() or headers()
 * - params or searchParams
 * - supabase.auth.getUser() or any auth state
 *
 * For auth-protected routes, use Upstash Redis caching instead.
 * See: docs/development/backend/cache-versioned-keys.md
 *
 * Currently, no routes in this codebase qualify for Cache Components because
 * all data routes are auth-protected. This module provides infrastructure
 * for future public endpoints that may benefit from HTTP-level caching.
 */

import { cacheLife, cacheTag } from "next/cache";

/**
 * Pre-configured cache profiles aligned with existing Redis TTLs.
 *
 * Usage in public server components/functions:
 * ```
 * "use cache";
 * import { applyCacheProfile } from "@/lib/cache/next-cache";
 *
 * export async function getPublicData() {
 *   applyCacheProfile("hour", nextCacheTags.publicConfig);
 *   return await fetchData();
 * }
 * ```
 *
 * @param profile - Cache duration profile
 * @param tag - Cache tag for invalidation via revalidateTag()
 */
export function applyCacheProfile(
  profile: "short" | "hour" | "long",
  tag: NextCacheTag
): void {
  cacheTag(tag);
  switch (profile) {
    case "short":
      cacheLife("minutes"); // ~5 min
      break;
    case "hour":
      cacheLife("hours");
      break;
    case "long":
      cacheLife("days"); // ~24 hours
      break;
  }
}

/**
 * Constants for Next.js cache tags.
 *
 * Use revalidateTag() with these to invalidate HTTP-level caches.
 * For Upstash Redis cache invalidation, use bumpTag() from @/lib/cache/tags.
 *
 * @example
 * ```
 * import { revalidateTag } from "next/cache";
 * import { nextCacheTags } from "@/lib/cache/next-cache";
 *
 * // Invalidate public destinations cache
 * revalidateTag(nextCacheTags.popularDestinationsGlobal);
 * ```
 */
export const nextCacheTags = {
  /** Global popular destinations (unauthenticated variant) */
  popularDestinationsGlobal: "popular-destinations-global",
  /** Public configuration data */
  publicConfig: "public-config",
} as const;

/** Type for available cache tags */
export type NextCacheTag = (typeof nextCacheTags)[keyof typeof nextCacheTags];
