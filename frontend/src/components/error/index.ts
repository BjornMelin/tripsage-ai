/**
 * @fileoverview Error boundary components and utilities export barrel. Includes
 * error boundaries, fallback UI components, and the error reporting service.
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
} from "@/lib/schemas/errors";
export { ErrorBoundary, WithErrorBoundary } from "./error-boundary";
export {
  ErrorFallback,
  MinimalErrorFallback,
  PageErrorFallback,
} from "./error-fallback";
