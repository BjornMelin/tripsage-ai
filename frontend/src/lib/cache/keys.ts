/**
 * @fileoverview Cache key generation utilities for canonicalizing parameters.
 *
 * Ensures consistent cache keys across tools by sorting and normalizing inputs.
 * Handles arrays, primitives, and filters out null/undefined values.
 */

/**
 * Canonicalize parameters for cache key generation.
 *
 * Sorts object keys alphabetically, normalizes values (lowercase strings,
 * sorted arrays), and filters out null/undefined values to ensure consistent
 * cache keys for equivalent parameter sets.
 *
 * @param params - Parameters object to canonicalize.
 * @param prefix - Optional prefix for the cache key. If provided, prepended with colon separator.
 *                 Default: empty string.
 * @returns - Canonical cache key string in format "prefix:key1:value1|key2:value2"
 *            (or without prefix if not provided).
 */
export function canonicalizeParamsForCache(
  params: Record<string, unknown>,
  prefix = ""
): string {
  const sorted = Object.keys(params)
    .sort()
    .map((k) => {
      const v = params[k];
      if (v === undefined || v === null) return "";
      if (Array.isArray(v)) {
        return `${k}:${v
          .map((x) => String(x).toLowerCase())
          .sort()
          .join(",")}`;
      }
      return `${k}:${String(v).toLowerCase()}`;
    })
    .filter(Boolean)
    .join("|");
  return prefix ? `${prefix}:${sorted}` : sorted;
}
