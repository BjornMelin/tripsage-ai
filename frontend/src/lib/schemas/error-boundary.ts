import { z } from "zod";

// Error boundary schemas
export const errorBoundaryPropsSchema = z.object({
  children: z.any(),
  fallback: z.function().optional(),
  onError: z.function().optional(),
  errorComponent: z.any().optional(),
});

export const errorStateSchema = z.object({
  hasError: z.boolean(),
  error: z
    .object({
      name: z.string(),
      message: z.string(),
      stack: z.string().optional(),
      digest: z.string().optional(),
    })
    .nullable(),
  errorInfo: z
    .object({
      componentStack: z.string().optional(),
    })
    .nullable(),
});

export const routeErrorPropsSchema = z.object({
  error: z.object({
    name: z.string(),
    message: z.string(),
    digest: z.string().optional(),
  }),
  reset: z.function(),
});

export const globalErrorPropsSchema = z.object({
  error: z.object({
    name: z.string(),
    message: z.string(),
    digest: z.string().optional(),
  }),
  reset: z.function(),
});

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
export type ErrorBoundaryProps = z.infer<typeof errorBoundaryPropsSchema>;
export type ErrorState = z.infer<typeof errorStateSchema>;
export type RouteErrorProps = z.infer<typeof routeErrorPropsSchema>;
export type GlobalErrorProps = z.infer<typeof globalErrorPropsSchema>;
export type LoadingState = z.infer<typeof loadingStateSchema>;
export type SkeletonProps = z.infer<typeof skeletonPropsSchema>;
