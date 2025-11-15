/**
 * @fileoverview Exponential backoff helper for Realtime reconnection logic.
 * Pure, deterministic utility with no React or Supabase dependencies.
 */

/**
 * Configuration for exponential backoff delay calculation.
 */
export interface BackoffConfig {
  /** Initial delay in milliseconds before the first retry. */
  initialDelayMs: number;
  /** Maximum delay in milliseconds (caps exponential growth). */
  maxDelayMs: number;
  /** Exponential factor (e.g., 2 for doubling, 1.5 for 50% increase). */
  factor: number;
}

/**
 * Computes the backoff delay for a given attempt number using exponential backoff.
 *
 * @param attempt - Zero-based attempt number (0 = first retry, 1 = second retry, etc.).
 * @param config - Backoff configuration parameters.
 * @returns Delay in milliseconds. Returns 0 for attempt <= 0.
 *
 * @example
 * ```ts
 * const config = { initialDelayMs: 1000, maxDelayMs: 30000, factor: 2 };
 * computeBackoffDelay(0, config); // 1000ms
 * computeBackoffDelay(1, config); // 2000ms
 * computeBackoffDelay(2, config); // 4000ms
 * computeBackoffDelay(10, config); // 30000ms (capped at maxDelayMs)
 * ```
 */
export function computeBackoffDelay(attempt: number, config: BackoffConfig): number {
  if (attempt <= 0) {
    return 0;
  }
  const base = config.initialDelayMs * config.factor ** (attempt - 1);
  return Math.min(base, config.maxDelayMs);
}
