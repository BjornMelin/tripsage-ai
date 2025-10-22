/**
 * Error Boundary Components - Export index
 *
 * This module provides error handling components for React applications,
 * including error boundaries, fallback UI components, and error reporting services.
 */

export { ErrorBoundary, withErrorBoundary } from "./error-boundary";
export {
  ErrorFallback,
  MinimalErrorFallback,
  PageErrorFallback,
} from "./error-fallback";

// Re-export types for convenience
export type {
  ErrorFallbackProps,
  ErrorBoundaryProps,
  ErrorInfo,
  ErrorDetails,
  ErrorReport,
  ErrorServiceConfig,
} from "@/types/errors";

// Re-export error service utilities
export { errorService, ErrorService } from "@/lib/error-service";
export { useErrorHandler } from "@/hooks/use-error-handler";
