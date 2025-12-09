/**
 * @fileoverview Cache key generation utilities for consistent key canonicalization.
 *
 * Ensures cache keys are deterministic by sorting and normalizing input
 * parameters. Handles arrays, primitives, and filters null/undefined values.
 *
 * @example
 * ```ts
 * // Same filters in different order produce same key
 * canonicalizeParamsForCache({ status: "active", limit: 10 }, "trips");
 * // => "trips:limit:10|status:active"
 *
 * canonicalizeParamsForCache({ limit: 10, status: "active" }, "trips");
 * // => "trips:limit:10|status:active" (same result)
 * ```
 */

/**
 * Canonicalizes parameters into a deterministic cache key string.
 *
 * Keys are sorted alphabetically, values are lowercased, arrays are
 * sorted and joined with commas. Null/undefined values are omitted.
 *
 * @param params - Parameters object to canonicalize.
 * @param prefix - Optional prefix prepended with colon separator.
 * @returns Canonical cache key string.
 *
 * @example
 * ```ts
 * // Basic usage
 * canonicalizeParamsForCache({ destination: "Paris", status: "planning" });
 * // => "destination:paris|status:planning"
 *
 * // With prefix
 * canonicalizeParamsForCache({ status: "active" }, "trips:user-123");
 * // => "trips:user-123:status:active"
 *
 * // Array values
 * canonicalizeParamsForCache({ tags: ["beach", "adventure"] });
 * // => "tags:adventure,beach" (sorted)
 *
 * // Null/undefined filtered
 * canonicalizeParamsForCache({ status: "active", limit: undefined });
 * // => "status:active"
 * ```
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
