/**
 * @fileoverview Client error boundary wrapper with error reporting and user/session context.
 */

"use client";

import type { ErrorBoundaryProps, ErrorInfo } from "@schemas/errors";
import type React from "react";
import { useCallback } from "react";
import {
  type FallbackProps,
  ErrorBoundary as ReactErrorBoundary,
} from "react-error-boundary";
import { getSessionId } from "@/lib/client/session";
import { errorService } from "@/lib/error-service";
import { fireAndForget } from "@/lib/utils";
import { ErrorFallback } from "./error-fallback";

const COMPONENT_CONTEXT = "ErrorBoundary" as const;

type ErrorWithDigest = Error & { digest?: string };

/**
 * Extract the user ID from the global window.userStore.
 *
 * `window.userStore` is initialized by the Zustand auth store during app bootstrap
 * (see src/stores/auth-store.ts). This function is defensive: the try-catch guards
 * against environments or timings where the global may not yet be available.
 *
 * @returns The current user ID if available, or undefined if not set or inaccessible.
 */
function GetUserId(): string | undefined {
  try {
    return window.userStore?.user?.id;
  } catch {
    return undefined;
  }
}

function ToSchemaErrorInfo(
  info: { componentStack?: string | null } | undefined
): ErrorInfo {
  return {
    componentStack: info?.componentStack ?? "",
  };
}

function GetFallbackComponent(
  fallback: ErrorBoundaryProps["fallback"] | undefined
): React.ComponentType<{
  error: ErrorWithDigest;
  reset?: () => void;
  retry?: () => void;
}> {
  return fallback ?? ErrorFallback;
}

export function ErrorBoundary({
  children,
  fallback,
  onError,
  level,
}: ErrorBoundaryProps) {
  const FallbackComponent = GetFallbackComponent(fallback);

  const handleError = useCallback(
    (error: Error, info: { componentStack?: string | null }) => {
      const schemaInfo = ToSchemaErrorInfo(info);
      onError?.(error, schemaInfo);

      const errorReport = errorService.createErrorReport(
        error,
        schemaInfo.componentStack
          ? { componentStack: schemaInfo.componentStack }
          : undefined,
        {
          sessionId: getSessionId(),
          userId: GetUserId(),
        }
      );

      fireAndForget(
        errorService.reportError(errorReport, {
          action: "render",
          componentStack: schemaInfo.componentStack,
          context: COMPONENT_CONTEXT,
          level,
        })
      );

      if (process.env.NODE_ENV === "development") {
        console.error("ErrorBoundary caught error:", error);
      }
    },
    [level, onError]
  );

  return (
    <ReactErrorBoundary
      fallbackRender={({ error, resetErrorBoundary }: FallbackProps) => (
        <FallbackComponent
          error={error as ErrorWithDigest}
          reset={resetErrorBoundary}
          retry={resetErrorBoundary}
        />
      )}
      onError={handleError}
    >
      {children}
    </ReactErrorBoundary>
  );
}

/**
 * Higher-order component to wrap components with error boundary
 */
export function WithErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, "children">
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `WithErrorBoundary(${
    Component.displayName || Component.name
  })`;

  return WrappedComponent;
}
