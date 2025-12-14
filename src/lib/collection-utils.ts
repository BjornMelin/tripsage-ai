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

/**
 * Deep equality check for objects and primitives with cycle detection.
 *
 * Compares values recursively, handling objects, arrays, dates, and primitives.
 * Property order in objects is ignored (objects with same keys/values in
 * different order are considered equal). Detects circular references to prevent
 * infinite recursion.
 *
 * @param a - First value to compare
 * @param b - Second value to compare
 * @returns True if values are deeply equal
 *
 * @example
 * deepEqual({ a: 1, b: 2 }, { b: 2, a: 1 }); // true
 * deepEqual([1, 2], [1, 2]); // true
 * deepEqual([1, 2], [2, 1]); // false (arrays are order-sensitive)
 */
export function deepEqual(a: unknown, b: unknown): boolean {
  const visited = new WeakMap<object, WeakSet<object>>();

  function compare(x: unknown, y: unknown): boolean {
    // Same reference or primitive equality
    if (x === y) return true;

    // Handle null/undefined
    if (x === null || y === null || x === undefined || y === undefined) {
      return x === y;
    }

    // Type mismatch
    if (typeof x !== typeof y) return false;

    // Handle Date objects
    if (x instanceof Date && y instanceof Date) {
      return x.getTime() === y.getTime();
    }

    // Handle arrays
    if (Array.isArray(x) && Array.isArray(y)) {
      if (x.length !== y.length) return false;

      // Check for circular reference
      if (!visited.has(x)) {
        visited.set(x, new WeakSet());
      }
      const xSet = visited.get(x);
      if (xSet?.has(y)) return true; // Already comparing this pair
      xSet?.add(y);

      return x.every((item, index) => compare(item, y[index]));
    }

    // Handle objects (but not arrays)
    if (typeof x === "object" && typeof y === "object") {
      // Check for circular reference
      if (!visited.has(x)) {
        visited.set(x, new WeakSet());
      }
      const xSet = visited.get(x);
      if (xSet?.has(y)) return true; // Already comparing this pair
      xSet?.add(y);

      const xObj = x as Record<string, unknown>;
      const yObj = y as Record<string, unknown>;
      const xKeys = Object.keys(xObj);
      const yKeys = Object.keys(yObj);

      if (xKeys.length !== yKeys.length) return false;

      return xKeys.every((key) => compare(xObj[key], yObj[key]));
    }

    return false;
  }

  return compare(a, b);
}
