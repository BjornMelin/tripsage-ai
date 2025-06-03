import { z } from "zod";

// Loading state schemas
export const loadingStateSchema = z.object({
  isLoading: z.boolean(),
  error: z.string().nullable(),
  data: z.any().nullable(),
});

export const skeletonPropsSchema = z.object({
  className: z.string().optional(),
  variant: z.enum(["default", "circular", "rectangular", "text"]).optional(),
  width: z.union([z.string(), z.number()]).optional(),
  height: z.union([z.string(), z.number()]).optional(),
  count: z.number().min(1).max(20).optional(),
});

// Export types
export type LoadingState = z.infer<typeof loadingStateSchema>;
export type SkeletonProps = z.infer<typeof skeletonPropsSchema>;
