/**
 * @fileoverview Exponential backoff helper for Realtime reconnection logic.
 * Pure, deterministic utility with no React or Supabase dependencies.
 */

import type { BackoffConfig } from "@/lib/schemas/realtime";
import { backoffConfigSchema } from "@/lib/schemas/realtime";

// Re-export type from schemas
export type { BackoffConfig };

/**
 * Computes the backoff delay for a given attempt number using exponential backoff.
 *
 * @param attempt - Zero-based attempt number (0 = first retry, 1 = second retry, etc.).
 * @param config - Backoff configuration parameters (validated via Zod schema).
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
  // Validate config using Zod schema
  const validated = backoffConfigSchema.parse(config);
  if (attempt <= 0) {
    return 0;
  }
  const base = validated.initialDelayMs * validated.factor ** (attempt - 1);
  return Math.min(base, validated.maxDelayMs);
}
