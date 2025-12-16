/**
 * @fileoverview Collection utility functions for array manipulation.
 */

/**
 * Groups array items by a key derived from each item.
 *
 * @template T - The type of items in the array
 * @template K - The type of the grouping key (string or number)
 * @param arr - The array to group
 * @param key - Function that returns the grouping key for each item
 * @returns An object where keys are the grouping values and values are arrays of items
 *
 * @example
 * const users = [
 *   { id: 1, role: 'admin' },
 *   { id: 2, role: 'user' },
 *   { id: 3, role: 'admin' }
 * ];
 * const byRole = groupBy(users, u => u.role);
 * // { admin: [...], user: [...] }
 */
export function groupBy<T, K extends string | number>(
  arr: T[],
  key: (item: T) => K
): Record<K, T[]> {
  const result = {} as Record<K, T[]>;
  for (const item of arr) {
    const k = key(item);
    if (!result[k]) {
      result[k] = [];
    }
    result[k].push(item);
  }
  return result;
}

/**
 * Maps items to values and returns unique results (preserving first-seen order).
 *
 * @template T - The type of items in the array
 * @template U - The mapped value type
 *
 * @remarks
 * Uniqueness is determined by JavaScript `Set` equality (SameValueZero): primitives
 * are deduplicated by value, while objects/arrays/functions are deduplicated by
 * reference. If your mapper returns objects, different instances with the same
 * contents will not be considered equal—prefer returning a stable primitive key
 * (e.g., an `id`) when you need value-based deduplication.
 * @param arr - The array to map
 * @param mapper - Function that maps each item to a value
 * @returns A list of unique mapped values
 */
export function mapToUnique<T, U>(arr: ReadonlyArray<T>, mapper: (item: T) => U): U[] {
  return [...new Set(arr.map(mapper))];
}
