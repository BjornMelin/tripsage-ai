/**
 * @fileoverview Shared type-guard utilities.
 */

/**
 * Determines whether a value is a plain object (object literal or Object.create(null)),
 * excluding arrays, null, and class instances like Date.
 *
 * @param {unknown} value - The value to evaluate.
 * @returns {value is Record<string, unknown>} True when the value is a plain object.
 * @example isPlainObject({ a: 1 }) // true
 * @example isPlainObject([1]) // false
 * @example isPlainObject(new Date()) // false
 */
export function isPlainObject(value: unknown): value is Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}
