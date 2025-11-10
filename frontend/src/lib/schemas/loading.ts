import { z } from "zod";

// Loading state schemas
export const loadingStateSchema = z.object({
  data: z.any().nullable(),
  error: z.string().nullable(),
  isLoading: z.boolean(),
});

export const skeletonPropsSchema = z.object({
  className: z.string().optional(),
  count: z.number().min(1).max(20).optional(),
  height: z.union([z.string(), z.number()]).optional(),
  variant: z.enum(["default", "circular", "rectangular", "text"]).optional(),
  width: z.union([z.string(), z.number()]).optional(),
});

// Export types
export type LoadingState = z.infer<typeof loadingStateSchema>;
export type SkeletonProps = z.infer<typeof skeletonPropsSchema>;
