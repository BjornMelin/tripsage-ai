/**
 * @fileoverview Authentication-level error boundary for the auth directory. This catches errors within the auth layout and pages.
 */

"use client";

import { useEffect } from "react";
import { ErrorFallback } from "@/components/error/error-fallback";
import { normalizeThrownError } from "@/lib/client/normalize-thrown-error";
import { getSessionId } from "@/lib/client/session";
import { errorService } from "@/lib/error-service";
import { fireAndForget } from "@/lib/utils";

/**
 * Authentication-level error boundary
 * Catches errors within the auth layout and pages
 */
export default function AuthError({
  error,
  reset,
}: {
  error: unknown;
  reset: () => void;
}) {
  useEffect(() => {
    const normalized = normalizeThrownError(error);
    // Report the auth error
    const errorReport = errorService.createErrorReport(normalized, undefined, {
      sessionId: getSessionId(),
    });

    fireAndForget(errorService.reportError(errorReport));

    // Log error in development
    if (process.env.NODE_ENV === "development") {
      console.error("Auth error boundary caught error:", normalized);
    }
  }, [error]);

  return <ErrorFallback error={error} reset={reset} />;
}
