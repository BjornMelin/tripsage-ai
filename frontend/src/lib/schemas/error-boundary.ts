/**
 * @fileoverview Zod v4 schemas for error boundary components and loading states.
 */

import { z } from "zod";

/** Zod schema for error boundary component props. */
export const errorBoundaryPropsSchema = z.object({
  children: z.any(),
  className: z.string().optional(),
  fallback: z.function().optional(),
  onError: z.function().optional(),
});

/** Zod schema for error state management. */
export const errorStateSchema = z.object({
  error: z.instanceof(Error).nullable(),
  errorInfo: z.any().nullable(),
  hasError: z.boolean(),
  retryCount: z.number().default(0),
});

/** Zod schema for global error component props. */
export const globalErrorPropsSchema = z.object({
  className: z.string().optional(),
  error: z.instanceof(Error),
  reset: z.function(),
});

/** Zod schema for route-specific error component props. */
export const routeErrorPropsSchema = z.object({
  error: z.instanceof(Error),
  pathname: z.string().optional(),
  reset: z.function(),
  searchParams: z.record(z.string(), z.unknown()).optional(),
});

/** Zod schema for loading state management. */
export const loadingStateSchema = z.object({
  isLoading: z.boolean(),
  loadingText: z.string().optional(),
  showSpinner: z.boolean().default(true),
});

/** Zod schema for skeleton loading component props. */
export const skeletonPropsSchema = z.object({
  animation: z.enum(["pulse", "wave", "none"]).default("pulse"),
  className: z.string().optional(),
  height: z.union([z.string(), z.number()]).optional(),
  variant: z.enum(["rectangular", "circular", "text"]).default("rectangular"),
  width: z.union([z.string(), z.number()]).optional(),
});

/** TypeScript type for error boundary props. */
export type ErrorBoundaryProps = z.infer<typeof errorBoundaryPropsSchema>;
/** TypeScript type for error state. */
export type ErrorState = z.infer<typeof errorStateSchema>;
/** TypeScript type for global error props. */
export type GlobalErrorProps = z.infer<typeof globalErrorPropsSchema>;
/** TypeScript type for route error props. */
export type RouteErrorProps = z.infer<typeof routeErrorPropsSchema>;
/** TypeScript type for loading state. */
export type LoadingState = z.infer<typeof loadingStateSchema>;
/** TypeScript type for skeleton props. */
export type SkeletonProps = z.infer<typeof skeletonPropsSchema>;
