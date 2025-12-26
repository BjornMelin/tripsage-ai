/**
 * @fileoverview Cache keys/constants for popular flight routes.
 */

/**
 * Bump this version whenever the popular routes response structure changes
 * to force cache invalidation.
 */
export const POPULAR_ROUTES_CACHE_VERSION = "v1" as const;

export const POPULAR_ROUTES_CACHE_KEY_GLOBAL =
  `popular-routes:${POPULAR_ROUTES_CACHE_VERSION}:global` as const;
