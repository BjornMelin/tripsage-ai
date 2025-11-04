/**
 * @fileoverview Dashboard-level error boundary for the dashboard directory.
 * This catches errors within the dashboard layout and pages.
 */

"use client";

import { useEffect } from "react";
import { ErrorFallback } from "@/components/error/error-fallback";
import { errorService } from "@/lib/error-service";
import { secureUuid } from "@/lib/security/random";

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

    errorService.reportError(errorReport);

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

/**
 * Gets or creates a session ID from sessionStorage for error tracking.
 *
 * @returns Session ID or undefined if sessionStorage is unavailable
 */
function getSessionId(): string | undefined {
  try {
    let sessionId = sessionStorage.getItem("session_id");
    if (!sessionId) {
      sessionId = `session_${secureUuid()}`;
      sessionStorage.setItem("session_id", sessionId);
    }
    return sessionId;
  } catch {
    return undefined;
  }
}
