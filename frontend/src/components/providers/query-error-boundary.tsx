"use client";

import { useQueryErrorResetBoundary } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw, WifiOff } from "lucide-react";
import type { ReactNode } from "react";
import { ErrorBoundary } from "react-error-boundary";
import { Button } from "@/components/ui/button";
import { getErrorMessage, isApiError, isNetworkError } from "@/lib/api/error-types";

interface QueryErrorFallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
}

function QueryErrorFallback({ error, resetErrorBoundary }: QueryErrorFallbackProps) {
  const errorMessage = getErrorMessage(error);
  const isNetwork = isNetworkError(error);
  const isApi = isApiError(error);

  // Determine error type and styling
  const getErrorDisplay = () => {
    if (isNetwork) {
      return {
        icon: <WifiOff className="h-8 w-8 text-orange-500" />,
        message: "Please check your internet connection and try again.",
        title: "Connection Error",
        variant: "network" as const,
      };
    }

    if (isApi && error.status >= 500) {
      return {
        icon: <AlertTriangle className="h-8 w-8 text-red-500" />,
        message: "Our servers are experiencing issues. Please try again later.",
        title: "Server Error",
        variant: "server" as const,
      };
    }

    if (isApi && error.status === 401) {
      return {
        icon: <AlertTriangle className="h-8 w-8 text-yellow-500" />,
        message: "Please log in to continue.",
        title: "Authentication Required",
        variant: "auth" as const,
      };
    }

    if (isApi && error.status === 403) {
      return {
        icon: <AlertTriangle className="h-8 w-8 text-red-500" />,
        message: "You don't have permission to access this resource.",
        title: "Access Denied",
        variant: "permission" as const,
      };
    }

    // Default error display
    return {
      icon: <AlertTriangle className="h-8 w-8 text-red-500" />,
      message: errorMessage,
      title: "Something went wrong",
      variant: "default" as const,
    };
  };

  const { icon, title, message, variant } = getErrorDisplay();

  const getVariantStyles = () => {
    switch (variant) {
      case "network":
        return "border-orange-200 bg-orange-50 text-orange-800";
      case "server":
        return "border-red-200 bg-red-50 text-red-800";
      case "auth":
        return "border-yellow-200 bg-yellow-50 text-yellow-800";
      case "permission":
        return "border-red-200 bg-red-50 text-red-800";
      default:
        return "border-gray-200 bg-gray-50 text-gray-800";
    }
  };

  return (
    <div className={`rounded-lg border p-6 ${getVariantStyles()}`}>
      <div className="flex items-center gap-3 mb-4">
        {icon}
        <h3 className="text-lg font-semibold">{title}</h3>
      </div>

      <p className="mb-4 text-sm opacity-90">{message}</p>

      <div className="flex items-center gap-2">
        <Button
          onClick={resetErrorBoundary}
          variant="outline"
          size="sm"
          className="flex items-center gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Try Again
        </Button>

        {variant === "auth" && (
          <Button
            onClick={() => (window.location.href = "/login")}
            size="sm"
            className="ml-2"
          >
            Go to Login
          </Button>
        )}
      </div>

      {process.env.NODE_ENV === "development" && (
        <details className="mt-4">
          <summary className="cursor-pointer text-xs opacity-70">
            Error Details (Development)
          </summary>
          <pre className="mt-2 text-xs opacity-70 overflow-auto max-h-32">
            {error.stack}
          </pre>
        </details>
      )}
    </div>
  );
}

interface QueryErrorBoundaryProps {
  children: ReactNode;
  fallback?: React.ComponentType<QueryErrorFallbackProps>;
  onError?: (error: Error, errorInfo: any) => void;
}

export function QueryErrorBoundary({
  children,
  fallback: Fallback = QueryErrorFallback,
  onError,
}: QueryErrorBoundaryProps) {
  const { reset } = useQueryErrorResetBoundary();

  return (
    <ErrorBoundary
      FallbackComponent={Fallback}
      onReset={reset}
      onError={onError}
      resetKeys={[]} // Reset when no specific dependencies change
    >
      {children}
    </ErrorBoundary>
  );
}

/**
 * Lightweight error boundary for smaller components
 */
interface InlineQueryErrorProps {
  error: Error;
  retry?: () => void;
  className?: string;
}

export function InlineQueryError({
  error,
  retry,
  className = "",
}: InlineQueryErrorProps) {
  const errorMessage = getErrorMessage(error);
  const isNetwork = isNetworkError(error);

  return (
    <div
      className={`flex items-center gap-2 p-3 text-sm rounded-md border border-red-200 bg-red-50 text-red-800 ${className}`}
    >
      {isNetwork ? (
        <WifiOff className="h-4 w-4 shrink-0" />
      ) : (
        <AlertTriangle className="h-4 w-4 shrink-0" />
      )}

      <span className="flex-1">{errorMessage}</span>

      {retry && (
        <Button
          onClick={retry}
          variant="outline"
          size="sm"
          className="h-6 px-2 text-xs"
        >
          <RefreshCw className="h-3 w-3" />
        </Button>
      )}
    </div>
  );
}

/**
 * Hook for handling query errors in components
 */
export function useQueryErrorHandler() {
  const { reset } = useQueryErrorResetBoundary();

  const handleError = (error: unknown) => {
    console.error("Query error:", error);

    // Log to external service in production
    if (process.env.NODE_ENV === "production") {
      // TODO: Integrate with error reporting service (Sentry, LogRocket, etc.)
    }
  };

  const retryQuery = () => {
    reset();
  };

  return {
    getErrorMessage: (error: unknown) => getErrorMessage(error),
    handleError,
    isRetryableError: (error: unknown) => {
      if (isNetworkError(error)) return true;
      if (isApiError(error)) return error.shouldRetry;
      return false;
    },
    retryQuery,
  };
}
