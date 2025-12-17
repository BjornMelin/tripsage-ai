/**
 * @fileoverview Test-only unsafe type coercion helper for complex SDK mocks.
 *
 * Prefer real implementations or `satisfies` where practical. Use this when a
 * third-party type is too large to model for unit tests.
 */

export function unsafeCast<T>(value: unknown): T {
  return value as T;
}
