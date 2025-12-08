/**
 * @fileoverview Error reporting schemas and related types.
 * Includes error boundary information, error details, error reports, and component props.
 */

import type React from "react";
import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core business logic schemas for error reporting

/**
 * Zod schema for React error boundary information.
 * Validates error boundary context including component stack and error boundary details.
 */
export const errorInfoSchema = z.object({
  componentStack: z.string(),
  errorBoundary: z.string().optional(),
  errorBoundaryStack: z.string().optional(),
});

/** TypeScript type for error boundary information. */
export type ErrorInfo = z.infer<typeof errorInfoSchema>;

/**
 * Zod schema for error details and stack traces.
 * Validates error structure including message, name, stack, and digest.
 */
export const errorDetailsSchema = z.object({
  digest: z.string().optional(),
  message: z.string(),
  name: z.string(),
  stack: z.string().optional(),
});

/** TypeScript type for error details. */
export type ErrorDetails = z.infer<typeof errorDetailsSchema>;

/**
 * Zod schema for complete error reports sent to monitoring services.
 * Validates error report structure including error details, context, and metadata.
 */
export const errorReportSchema = z.object({
  error: errorDetailsSchema,
  errorInfo: errorInfoSchema.optional(),
  sessionId: z.string().optional(),
  timestamp: primitiveSchemas.isoDateTime,
  url: z.string(),
  userAgent: z.string(),
  userId: z.string().optional(),
});

/** TypeScript type for error reports. */
export type ErrorReport = z.infer<typeof errorReportSchema>;

// ===== COMPONENT PROPS =====
// TypeScript interfaces for error boundary component props

/**
 * Props for error fallback UI components.
 * Defines error display and recovery action props.
 */
export interface ErrorFallbackProps {
  error: Error & { digest?: string };
  reset?: () => void;
  retry?: () => void;
}

/**
 * Props for error boundary wrapper components.
 * Defines error boundary configuration including fallback and error handlers.
 */
export interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<ErrorFallbackProps>;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  level?: "page" | "component" | "global";
}

/**
 * Configuration for error reporting and monitoring services.
 * Defines error service settings including endpoint, API key, and retry configuration.
 */
export interface ErrorServiceConfig {
  enabled: boolean;
  endpoint?: string;
  apiKey?: string;
  maxRetries?: number;
  enableLocalStorage?: boolean;
}
