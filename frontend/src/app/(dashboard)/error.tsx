/**
 * @fileoverview Dashboard-level error boundary for the dashboard directory.
 * This catches errors within the dashboard layout and pages.
 */

"use client";

import { useEffect } from "react";
import { ErrorFallback } from "@/components/error/error-fallback";
import { getSessionId } from "@/lib/client/session";
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
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Report the dashboard error
    const errorReport = errorService.createErrorReport(error, undefined, {
      sessionId: getSessionId(),
      userId: getUserId(),
    });

    fireAndForget(errorService.reportError(errorReport));

    // Log error in development
    if (process.env.NODE_ENV === "development") {
      console.error("Dashboard error boundary caught error:", error);
    }
  }, [error]);

  return <ErrorFallback error={error} reset={reset} />;
}

/**
 * Gets the current user ID from the user store.
 *
 * @returns User ID or undefined if not available
 */
function getUserId(): string | undefined {
  try {
    const userStore = (window as Window & { userStore?: { user?: { id?: string } } })
      .userStore;
    return userStore?.user?.id;
  } catch {
    return undefined;
  }
}
