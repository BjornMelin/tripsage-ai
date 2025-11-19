/**
 * @fileoverview Error boundary component and loading state schemas.
 * Includes error boundary props, error state, loading state, and skeleton component props.
 */

import { z } from "zod";

// ===== CORE SCHEMAS =====
// Core business logic schemas for error boundaries and loading states

/**
 * Zod schema for error boundary component props.
 * Validates error boundary configuration including children, fallback, and error handlers.
 */
export const errorBoundarySchema = z.object({
  children: z.any(),
  className: z.string().optional(),
  fallback: z.function().optional(),
  onError: z.function().optional(),
});

/** TypeScript type for error boundary props. */
export type ErrorBoundaryPropsType = z.infer<typeof errorBoundarySchema>;

/**
 * Zod schema for error state management.
 * Validates error state including error instance, error info, and retry count.
 */
export const errorStateSchema = z.object({
  error: z.instanceof(Error).nullable(),
  errorInfo: z.any().nullable(),
  hasError: z.boolean(),
  retryCount: z.number().default(0),
});

/** TypeScript type for error state. */
export type ErrorState = z.infer<typeof errorStateSchema>;

/**
 * Zod schema for global error component props.
 * Validates global error display configuration including error and reset handler.
 */
export const globalErrorPropsSchema = z.object({
  className: z.string().optional(),
  error: z.instanceof(Error),
  reset: z.function(),
});

/** TypeScript type for global error props. */
export type GlobalErrorProps = z.infer<typeof globalErrorPropsSchema>;

/**
 * Zod schema for route-specific error component props.
 * Validates route error display configuration including pathname and search params.
 */
export const routeErrorPropsSchema = z.object({
  error: z.instanceof(Error),
  pathname: z.string().optional(),
  reset: z.function(),
  searchParams: z.record(z.string(), z.unknown()).optional(),
});

/** TypeScript type for route error props. */
export type RouteErrorProps = z.infer<typeof routeErrorPropsSchema>;

/**
 * Zod schema for loading state management.
 * Validates loading state including loading indicator and optional loading text.
 */
export const errorLoadingStateSchema = z.object({
  isLoading: z.boolean(),
  loadingText: z.string().optional(),
  showSpinner: z.boolean().default(true),
});

/** TypeScript type for loading state. */
export type ErrorLoadingState = z.infer<typeof errorLoadingStateSchema>;

/**
 * Zod schema for skeleton loading component props.
 * Validates skeleton display configuration including animation, variant, and dimensions.
 */
export const errorSkeletonPropsSchema = z.object({
  animation: z.enum(["pulse", "wave", "none"]).default("pulse"),
  className: z.string().optional(),
  height: z.union([z.string(), z.number()]).optional(),
  variant: z.enum(["rectangular", "circular", "text"]).default("rectangular"),
  width: z.union([z.string(), z.number()]).optional(),
});

/** TypeScript type for skeleton props. */
export type ErrorSkeletonProps = z.infer<typeof errorSkeletonPropsSchema>;
