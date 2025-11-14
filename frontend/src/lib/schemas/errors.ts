/**
 * @fileoverview Zod v4 schemas and related types for error reporting.
 */

import { z } from "zod";

/** Zod schema for React error boundary information. */
export const ERROR_INFO_SCHEMA = z.object({
  componentStack: z.string(),
  errorBoundary: z.string().optional(),
  errorBoundaryStack: z.string().optional(),
});

/** Zod schema for error details and stack traces. */
export const ERROR_DETAILS_SCHEMA = z.object({
  digest: z.string().optional(),
  message: z.string(),
  name: z.string(),
  stack: z.string().optional(),
});

/** Zod schema for complete error reports sent to monitoring services. */
export const ERROR_REPORT_SCHEMA = z.object({
  error: ERROR_DETAILS_SCHEMA,
  errorInfo: ERROR_INFO_SCHEMA.optional(),
  sessionId: z.string().optional(),
  timestamp: z.string(),
  url: z.string(),
  userAgent: z.string(),
  userId: z.string().optional(),
});

/** TypeScript type for error boundary information. */
export type ErrorInfo = z.infer<typeof ERROR_INFO_SCHEMA>;
/** TypeScript type for error details. */
export type ErrorDetails = z.infer<typeof ERROR_DETAILS_SCHEMA>;
/** TypeScript type for error reports. */
export type ErrorReport = z.infer<typeof ERROR_REPORT_SCHEMA>;

/** Props for error fallback UI components. */
export interface ErrorFallbackProps {
  error: Error & { digest?: string };
  reset?: () => void;
  retry?: () => void;
}

/** Props for error boundary wrapper components. */
export interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<ErrorFallbackProps>;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  level?: "page" | "component" | "global";
}

/** Configuration for error reporting and monitoring services. */
export interface ErrorServiceConfig {
  enabled: boolean;
  endpoint?: string;
  apiKey?: string;
  maxRetries?: number;
  enableLocalStorage?: boolean;
}
