/**
 * Error Boundary Components - Export index
 *
 * This module provides error handling components for React applications,
 * including error boundaries, fallback UI components, and error reporting services.
 */

export { useErrorHandler } from "@/hooks/use-error-handler";
// Re-export error service utilities
export { ErrorService, errorService } from "@/lib/error-service";

// Re-export types for convenience
export type {
  ErrorBoundaryProps,
  ErrorDetails,
  ErrorFallbackProps,
  ErrorInfo,
  ErrorReport,
  ErrorServiceConfig,
} from "@/types/errors";
export { ErrorBoundary, withErrorBoundary } from "./error-boundary";
export {
  ErrorFallback,
  MinimalErrorFallback,
  PageErrorFallback,
} from "./error-fallback";
