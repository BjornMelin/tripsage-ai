/**
 * @fileoverview Zod v4 schemas for realtime connection and backoff configuration.
 */

import { z } from "zod";

/** Zod schema for exponential backoff configuration. */
export const backoffConfigSchema = z.object({
  /** Exponential factor (e.g., 2 for doubling, 1.5 for 50% increase). */
  factor: z.number().positive(),
  /** Initial delay in milliseconds before the first retry. */
  initialDelayMs: z.number().int().positive(),
  /** Maximum delay in milliseconds (caps exponential growth). */
  maxDelayMs: z.number().int().positive(),
});
/** TypeScript type for backoff configuration. */
export type BackoffConfig = z.infer<typeof backoffConfigSchema>;
