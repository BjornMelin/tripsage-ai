import { z } from "zod";

/**
 * Error Boundary Props Schema
 * Validates props for error boundary components
 */
export const errorBoundaryPropsSchema = z.object({
  children: z.any(),
  fallback: z.function().optional(),
  onError: z.function().optional(),
  className: z.string().optional(),
});

/**
 * Error State Schema
 * Validates error state structure
 */
export const errorStateSchema = z.object({
  hasError: z.boolean(),
  error: z.instanceof(Error).nullable(),
  errorInfo: z.any().nullable(),
  retryCount: z.number().default(0),
});

/**
 * Global Error Props Schema
 * Validates props for global error components
 */
export const globalErrorPropsSchema = z.object({
  error: z.instanceof(Error),
  reset: z.function(),
  className: z.string().optional(),
});

/**
 * Route Error Props Schema
 * Validates props for route-specific error components
 */
export const routeErrorPropsSchema = z.object({
  error: z.instanceof(Error),
  reset: z.function(),
  pathname: z.string().optional(),
  searchParams: z.record(z.string(), z.unknown()).optional(),
});

/**
 * Loading State Schema
 * Validates loading state structure
 */
export const loadingStateSchema = z.object({
  isLoading: z.boolean(),
  loadingText: z.string().optional(),
  showSpinner: z.boolean().default(true),
});

/**
 * Skeleton Props Schema
 * Validates props for skeleton loading components
 */
export const skeletonPropsSchema = z.object({
  className: z.string().optional(),
  width: z.union([z.string(), z.number()]).optional(),
  height: z.union([z.string(), z.number()]).optional(),
  variant: z.enum(["rectangular", "circular", "text"]).default("rectangular"),
  animation: z.enum(["pulse", "wave", "none"]).default("pulse"),
});

export type ErrorBoundaryProps = z.infer<typeof errorBoundaryPropsSchema>;
export type ErrorState = z.infer<typeof errorStateSchema>;
export type GlobalErrorProps = z.infer<typeof globalErrorPropsSchema>;
export type RouteErrorProps = z.infer<typeof routeErrorPropsSchema>;
export type LoadingState = z.infer<typeof loadingStateSchema>;
export type SkeletonProps = z.infer<typeof skeletonPropsSchema>;
