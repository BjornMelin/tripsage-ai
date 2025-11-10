import { z } from "zod";

/**
 * Error Boundary Props Schema
 * Validates props for error boundary components
 */
export const errorBoundaryPropsSchema = z.object({
  children: z.any(),
  className: z.string().optional(),
  fallback: z.function().optional(),
  onError: z.function().optional(),
});

/**
 * Error State Schema
 * Validates error state structure
 */
export const errorStateSchema = z.object({
  error: z.instanceof(Error).nullable(),
  errorInfo: z.any().nullable(),
  hasError: z.boolean(),
  retryCount: z.number().default(0),
});

/**
 * Global Error Props Schema
 * Validates props for global error components
 */
export const globalErrorPropsSchema = z.object({
  className: z.string().optional(),
  error: z.instanceof(Error),
  reset: z.function(),
});

/**
 * Route Error Props Schema
 * Validates props for route-specific error components
 */
export const routeErrorPropsSchema = z.object({
  error: z.instanceof(Error),
  pathname: z.string().optional(),
  reset: z.function(),
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
  animation: z.enum(["pulse", "wave", "none"]).default("pulse"),
  className: z.string().optional(),
  height: z.union([z.string(), z.number()]).optional(),
  variant: z.enum(["rectangular", "circular", "text"]).default("rectangular"),
  width: z.union([z.string(), z.number()]).optional(),
});

export type ErrorBoundaryProps = z.infer<typeof errorBoundaryPropsSchema>;
export type ErrorState = z.infer<typeof errorStateSchema>;
export type GlobalErrorProps = z.infer<typeof globalErrorPropsSchema>;
export type RouteErrorProps = z.infer<typeof routeErrorPropsSchema>;
export type LoadingState = z.infer<typeof loadingStateSchema>;
export type SkeletonProps = z.infer<typeof skeletonPropsSchema>;
