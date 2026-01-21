/**
 * @fileoverview Dashboard-level error boundary for the dashboard directory. This catches errors within the dashboard layout and pages.
 */

"use client";

import { useEffect } from "react";
import { ErrorFallback } from "@/components/error/error-fallback";
import { normalizeThrownError } from "@/lib/client/normalize-thrown-error";
import { getSessionId } from "@/lib/client/session";
import { getUserIdFromUserStore } from "@/lib/client/user-store";
import { errorService } from "@/lib/error-service";
import { fireAndForget } from "@/lib/utils";

/**
 * Dashboard-level error boundary
 * Catches errors within the dashboard layout and pages
 */
export default function DashboardError({
  error,
  reset,
}: {
  error: unknown;
  reset: () => void;
}) {
  useEffect(() => {
    const normalized = normalizeThrownError(error);
    // Report the dashboard error
    const errorReport = errorService.createErrorReport(normalized, undefined, {
      sessionId: getSessionId(),
      userId: getUserIdFromUserStore(),
    });

    fireAndForget(errorService.reportError(errorReport));

    // Log error in development
    if (process.env.NODE_ENV === "development") {
      console.error("Dashboard error boundary caught error:", normalized);
    }
  }, [error]);

  return <ErrorFallback error={error} reset={reset} />;
}
