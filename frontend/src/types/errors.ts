/**
 * @fileoverview Error info and reporting types used by error boundaries and
 * logging services. Backed by Zod for runtime validation.
 */
import { z } from "zod";

/**
 * Zod schema for error information
 */
export const ErrorInfoSchema = z.object({
  componentStack: z.string(),
  errorBoundary: z.string().optional(),
  errorBoundaryStack: z.string().optional(),
});

/**
 * Zod schema for error details
 */
export const ErrorDetailsSchema = z.object({
  digest: z.string().optional(),
  message: z.string(),
  name: z.string(),
  stack: z.string().optional(),
});

/**
 * Zod schema for error report
 */
export const ErrorReportSchema = z.object({
  error: ErrorDetailsSchema,
  errorInfo: ErrorInfoSchema.optional(),
  sessionId: z.string().optional(),
  timestamp: z.string(),
  url: z.string(),
  userAgent: z.string(),
  userId: z.string().optional(),
});

/**
 * Type definitions derived from Zod schemas
 */
export type ErrorInfo = z.infer<typeof ErrorInfoSchema>;
export type ErrorDetails = z.infer<typeof ErrorDetailsSchema>;
export type ErrorReport = z.infer<typeof ErrorReportSchema>;

/**
 * Error boundary fallback component props
 */
export interface ErrorFallbackProps {
  error: Error & { digest?: string };
  reset?: () => void;
  retry?: () => void;
}

/**
 * Error boundary component props
 */
export interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<ErrorFallbackProps>;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  level?: "page" | "component" | "global";
}

/**
 * Error service configuration
 */
export interface ErrorServiceConfig {
  enabled: boolean;
  endpoint?: string;
  apiKey?: string;
  maxRetries?: number;
  enableLocalStorage?: boolean;
}
