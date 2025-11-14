/**
 * @fileoverview Zod v4 schemas for loading states and skeleton UI props.
 */

import { z } from "zod";

/** Zod schema for async operation loading states. */
export const loadingStateSchema = z.object({
  data: z.any().nullable(),
  error: z.string().nullable(),
  isLoading: z.boolean(),
});

/** Zod schema for skeleton loading component props. */
export const skeletonPropsSchema = z.object({
  className: z.string().optional(),
  count: z.number().min(1).max(20).optional(),
  height: z.union([z.string(), z.number()]).optional(),
  variant: z.enum(["default", "circular", "rectangular", "text"]).optional(),
  width: z.union([z.string(), z.number()]).optional(),
});

/** TypeScript type for loading states. */
export type LoadingState = z.infer<typeof loadingStateSchema>;
/** TypeScript type for skeleton props. */
export type SkeletonProps = z.infer<typeof skeletonPropsSchema>;
