/**
 * @fileoverview Loading states and skeleton UI props schemas.
 * Includes async operation loading states and skeleton component configuration.
 */

import { z } from "zod";

// ===== CORE SCHEMAS =====
// Core business logic schemas for loading states

/**
 * Zod schema for async operation loading states.
 * Validates loading state including data, error, and loading indicator.
 */
export const loadingStateSchema = z.object({
  data: z.any().nullable(),
  error: z.string().nullable(),
  isLoading: z.boolean(),
});

/** TypeScript type for loading states. */
export type LoadingState = z.infer<typeof loadingStateSchema>;

/**
 * Zod schema for skeleton loading component props.
 * Validates skeleton display configuration including variant, dimensions, and count.
 */
export const skeletonPropsSchema = z.object({
  className: z.string().optional(),
  count: z.number().min(1).max(20).optional(),
  height: z.union([z.string(), z.number()]).optional(),
  variant: z.enum(["default", "circular", "rectangular", "text"]).optional(),
  width: z.union([z.string(), z.number()]).optional(),
});

/** TypeScript type for skeleton props. */
export type SkeletonProps = z.infer<typeof skeletonPropsSchema>;
