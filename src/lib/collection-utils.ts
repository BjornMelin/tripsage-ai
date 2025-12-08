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
 * Removes null and undefined values from an array.
 *
 * @template T - The type of non-null items in the array
 * @param arr - The array to compact
 * @returns A new array with all null and undefined values removed
 *
 * @example
 * compact([1, null, 2, undefined, 3]); // [1, 2, 3]
 */
export function compact<T>(arr: (T | null | undefined)[]): T[] {
  return arr.filter((item): item is T => item !== null && item !== undefined);
}

/**
 * Creates a new array excluding specified items.
 *
 * @template T - The type of items in the array
 * @param arr - The source array
 * @param items - Items to exclude
 * @returns A new array with specified items removed
 *
 * @example
 * without([1, 2, 3, 4], 2, 4); // [1, 3]
 */
export function without<T>(arr: T[], ...items: T[]): T[] {
  const excludeSet = new Set(items);
  return arr.filter((item) => !excludeSet.has(item));
}

/**
 * Creates a new array with only unique values.
 *
 * @template T - The type of items in the array
 * @param arr - The array to deduplicate
 * @returns A new array containing only unique values
 *
 * @example
 * unique([1, 2, 2, 3, 1]); // [1, 2, 3]
 */
export function unique<T>(arr: T[]): T[] {
  return Array.from(new Set(arr));
}
