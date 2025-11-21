/**
 * @fileoverview Error boundary component and loading state schemas (UI only).
 */

import { z } from "zod";

export const errorBoundarySchema = z.object({
  children: z.any(),
  className: z.string().optional(),
  fallback: z.function().optional(),
  onError: z.function().optional(),
});
export type ErrorBoundaryPropsType = z.infer<typeof errorBoundarySchema>;

export const errorStateSchema = z.object({
  error: z.instanceof(Error).nullable(),
  errorInfo: z.any().nullable(),
  hasError: z.boolean(),
  retryCount: z.number().default(0),
});
export type ErrorState = z.infer<typeof errorStateSchema>;

export const globalErrorPropsSchema = z.object({
  className: z.string().optional(),
  error: z.instanceof(Error),
  reset: z.function(),
});
export type GlobalErrorProps = z.infer<typeof globalErrorPropsSchema>;

export const routeErrorPropsSchema = z.object({
  error: z.instanceof(Error),
  pathname: z.string().optional(),
  reset: z.function(),
  searchParams: z.record(z.string(), z.unknown()).optional(),
});
export type RouteErrorProps = z.infer<typeof routeErrorPropsSchema>;

export const errorLoadingStateSchema = z.object({
  isLoading: z.boolean(),
  loadingText: z.string().optional(),
  showSpinner: z.boolean().default(true),
});
export type ErrorLoadingState = z.infer<typeof errorLoadingStateSchema>;

export const errorSkeletonPropsSchema = z.object({
  animation: z.enum(["pulse", "wave", "none"]).default("pulse"),
  className: z.string().optional(),
  height: z.union([z.string(), z.number()]).optional(),
  variant: z.enum(["rectangular", "circular", "text"]).default("rectangular"),
  width: z.union([z.string(), z.number()]).optional(),
});
export type ErrorSkeletonProps = z.infer<typeof errorSkeletonPropsSchema>;
