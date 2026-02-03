/**
 * Patch Next.js Cache Components typing for custom cacheLife profiles.
 *
 * In this repo we use custom `cacheLife("<profile>")` names configured in `next.config.ts`.
 * Some Next.js/TS resolution paths can miss the generic-string overload, so we
 * re-declare it here for consistent type-checking.
 */

import "next/cache";

declare module "next/cache" {
  /**
   * Registers a cache lifetime profile by name for Cache Components.
   */
  export function cacheLife(profile: string): void;
}
