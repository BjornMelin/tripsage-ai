/**
 * @fileoverview Query error boundary with OTEL-backed telemetry.
 * Refer to docs/development/observability.md for tracing and alerting standards.
 */

"use client";

import { useQueryErrorResetBoundary } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw, WifiOff } from "lucide-react";
import type { ComponentType, ErrorInfo, JSX, ReactNode } from "react";
import { useRef } from "react";
import { ErrorBoundary, type FallbackProps } from "react-error-boundary";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  getErrorMessage,
  handleApiError,
  isNetworkError,
  shouldRetryError,
} from "@/lib/api/error-types";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { cn } from "@/lib/utils";

type ErrorVariant = "network" | "server" | "auth" | "permission" | "default";

/** Metadata extracted from an error for categorization and display. */
interface ErrorMeta {
  variant: ErrorVariant;
  isRetryable: boolean;
  statusCode?: number;
  errorCode?: string;
}

/**
 * Props for the error fallback component.
 *
 * @param meta - Error metadata including variant and retryability.
 * @param onRetry - Callback to retry the failed operation.
 */
interface QueryErrorFallbackProps extends FallbackProps {
  meta: ErrorMeta;
  onRetry: () => void;
  loginHref?: string;
}

/**
 * Optional async error handler that may be invoked when errors occur.
 *
 * @param error - The error that was caught.
 * @param info - React error info including component stack.
 * @param meta - Resolved error metadata.
 * @returns Promise or void - failures are swallowed to prevent boundary loops.
 */
type OptionalAsyncHandler = (
  error: Error,
  info?: ErrorInfo,
  meta?: ErrorMeta
) => void | Promise<void>;

const COMPONENT_CONTEXT = "QueryErrorBoundary" as const;

/**
 * Safely invokes an optional async handler, swallowing any errors to prevent
 * recursive boundary failures.
 *
 * @param handler - Optional handler to invoke; no-op if undefined.
 * @param error - Error to pass to the handler.
 * @param info - React error info to pass to the handler.
 * @param meta - Error metadata to pass to the handler.
 */
function SafeInvoke(
  handler: OptionalAsyncHandler | undefined,
  error: Error,
  info: ErrorInfo | undefined,
  meta: ErrorMeta
) {
  if (!handler) return;

  queueMicrotask(() => {
    try {
      const result = handler(error, info, meta);
      Promise.resolve(result).catch(() => {
        // Swallow handler failures to avoid error boundary loops
      });
    } catch {
      // Swallow handler errors to avoid recursive boundary failures
    }
  });
}

/**
 * Resolves error metadata by normalizing the error and categorizing its variant.
 *
 * @param error - Unknown error value to analyze.
 * @returns Error metadata with variant, retryability, and status/error codes.
 */
function ResolveMeta(error: unknown): ErrorMeta {
  const normalized = handleApiError(error);
  const variant: ErrorVariant = (() => {
    if (isNetworkError(normalized)) return "network";
    if (normalized instanceof ApiError) {
      if (normalized.status >= 500) return "server";
      if (normalized.status === 401) return "auth";
      if (normalized.status === 403) return "permission";
    }
    return "default";
  })();

  const statusCode = normalized instanceof ApiError ? normalized.status : undefined;
  const errorCode = normalized instanceof ApiError ? normalized.code : undefined;

  return {
    errorCode,
    isRetryable: shouldRetryError(normalized),
    statusCode,
    variant,
  };
}

/**
 * Records error telemetry to the active OTEL span.
 * Failures are swallowed to ensure telemetry never breaks the UI.
 *
 * @param error - The error to record.
 * @param info - React error info including component stack.
 * @param meta - Resolved error metadata.
 */
function RecordTelemetry(error: Error, info: ErrorInfo, meta: ErrorMeta) {
  try {
    recordClientErrorOnActiveSpan(error, {
      action: "render",
      componentStack: info.componentStack,
      context: COMPONENT_CONTEXT,
      errorCode: meta.errorCode,
      retryable: meta.isRetryable,
      statusCode: meta.statusCode,
      variant: meta.variant,
    });
  } catch {
    // Telemetry failures must never break the UI
  }
}

const VARIANT_STYLES: Record<ErrorVariant, string> = {
  auth: "border-yellow-200 bg-yellow-50 text-yellow-800",
  default: "border-gray-200 bg-gray-50 text-gray-800",
  network: "border-orange-200 bg-orange-50 text-orange-800",
  permission: "border-red-200 bg-red-50 text-red-800",
  server: "border-red-200 bg-red-50 text-red-800",
};

const VARIANT_DISPLAY: Record<
  ErrorVariant,
  { icon: JSX.Element; message: string; title: string }
> = {
  auth: {
    icon: <AlertTriangle className="h-8 w-8 text-yellow-500" />,
    message: "Please log in to continue.",
    title: "Authentication Required",
  },
  default: {
    icon: <AlertTriangle className="h-8 w-8 text-red-500" />,
    message: "Something went wrong. Please try again.",
    title: "Something went wrong",
  },
  network: {
    icon: <WifiOff className="h-8 w-8 text-orange-500" />,
    message: "Please check your internet connection and try again.",
    title: "Connection Error",
  },
  permission: {
    icon: <AlertTriangle className="h-8 w-8 text-red-500" />,
    message: "You don't have permission to access this resource.",
    title: "Access Denied",
  },
  server: {
    icon: <AlertTriangle className="h-8 w-8 text-red-500" />,
    message: "Our servers are experiencing issues. Please try again later.",
    title: "Server Error",
  },
};

/**
 * Default fallback component that renders error UI based on error variant.
 * Displays variant-specific icons, messages, and retry/login actions.
 *
 * @param error - The error that triggered the boundary.
 * @param meta - Resolved error metadata.
 * @param onRetry - Callback to retry the failed operation.
 * @returns Rendered error UI component.
 */
function QueryErrorFallback({
  error,
  meta,
  onRetry,
  loginHref,
}: QueryErrorFallbackProps) {
  const errorMessage = getErrorMessage(error);
  const display = VARIANT_DISPLAY[meta.variant];
  const showLogin = meta.variant === "auth";
  const message = meta.variant === "default" ? errorMessage : display.message;

  return (
    <div
      className={cn("rounded-lg border p-6", VARIANT_STYLES[meta.variant])}
      data-error-variant={meta.variant}
      data-error-retryable={meta.isRetryable}
    >
      <div className="mb-4 flex items-center gap-3">
        {display.icon}
        <h3 className="text-lg font-semibold">{display.title}</h3>
      </div>

      <p className="mb-4 text-sm opacity-90">{message}</p>

      <div className="flex items-center gap-2">
        <Button
          onClick={onRetry}
          variant="outline"
          size="sm"
          className="flex items-center gap-2"
          disabled={!meta.isRetryable}
          aria-label="Try Again"
        >
          <RefreshCw className="h-4 w-4" />
          Try Again
        </Button>

        {showLogin && (
          <Button
            onClick={() => {
              window.location.href = loginHref ?? "/login";
            }}
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
          <pre className="mt-2 max-h-32 overflow-auto text-xs opacity-70">
            {error.stack}
          </pre>
        </details>
      )}
    </div>
  );
}

/**
 * Props for the QueryErrorBoundary component.
 *
 * @param children - React children to wrap with error boundary.
 * @param fallback - Optional custom fallback component; defaults to QueryErrorFallback.
 * @param onError - Optional handler invoked when errors are caught.
 * @param onOperationalAlert - Optional handler for operational alerting; invoked before onError.
 */
interface QueryErrorBoundaryProps {
  children: ReactNode;
  fallback?: ComponentType<QueryErrorFallbackProps>;
  onError?: OptionalAsyncHandler;
  onOperationalAlert?: OptionalAsyncHandler;
  loginHref?: string;
}

/**
 * React Query-aware error boundary that records OTEL telemetry and supports
 * optional error handlers.
 *
 * Integrates with React Query's error reset mechanism and provides variant-aware
 * error categorization (network, server, auth, permission, default).
 *
 * @param children - React children to wrap with error boundary.
 * @param fallback - Optional custom fallback component; defaults to QueryErrorFallback.
 * @param onError - Optional handler invoked when errors are caught.
 * @param onOperationalAlert - Optional handler for operational alerting; invoked before onError.
 * @returns ErrorBoundary component wrapping the children.
 */
export function QueryErrorBoundary({
  children,
  fallback: Fallback = QueryErrorFallback,
  onError,
  onOperationalAlert,
  loginHref,
}: QueryErrorBoundaryProps) {
  const { reset } = useQueryErrorResetBoundary();
  const latestMetaRef = useRef<ErrorMeta | null>(null);

  /**
   * Handles boundary errors by emitting telemetry and delegating to injected sinks.
   */
  const handleError = (error: Error, info: ErrorInfo) => {
    const meta = ResolveMeta(error);
    latestMetaRef.current = meta;
    RecordTelemetry(error, info, meta);
    SafeInvoke(onOperationalAlert, error, info, meta);
    SafeInvoke(onError, error, info, meta);
  };

  const handleReset = () => {
    latestMetaRef.current = null;
    reset();
  };

  return (
    <ErrorBoundary
      FallbackComponent={(props) => {
        const meta = latestMetaRef.current ?? ResolveMeta(props.error);
        return (
          <Fallback
            {...props}
            meta={meta}
            onRetry={props.resetErrorBoundary}
            loginHref={loginHref}
          />
        );
      }}
      onReset={handleReset}
      onError={handleError}
      resetKeys={[]}
    >
      {children}
    </ErrorBoundary>
  );
}

/**
 * Props for the InlineQueryError component.
 *
 * @param error - The error to display.
 * @param retry - Optional retry callback; button is shown if provided.
 * @param className - Additional CSS classes to apply.
 */
interface InlineQueryErrorProps {
  error: Error;
  retry?: () => void;
  className?: string;
}

/**
 * Inline, non-boundary rendering for query errors with retry affordance.
 *
 * Use this component to display query errors inline within the UI rather than
 * as a full-page boundary fallback. Automatically categorizes errors and shows
 * appropriate styling and retry controls.
 *
 * @param error - The error to display.
 * @param retry - Optional retry callback; button is shown if provided.
 * @param className - Additional CSS classes to apply.
 * @returns Inline error UI component.
 */
export function InlineQueryError({
  error,
  retry,
  className = "",
}: InlineQueryErrorProps) {
  const meta = ResolveMeta(error);
  const errorMessage = getErrorMessage(error);

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md border p-3 text-sm",
        meta.variant === "network"
          ? "border-orange-200 bg-orange-50 text-orange-800"
          : "border-red-200 bg-red-50 text-red-800",
        className
      )}
      data-error-variant={meta.variant}
      data-error-retryable={meta.isRetryable}
    >
      {meta.variant === "network" ? (
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
          aria-label="Try Again"
          disabled={!meta.isRetryable}
        >
          <RefreshCw className="h-3 w-3" />
        </Button>
      )}
    </div>
  );
}
