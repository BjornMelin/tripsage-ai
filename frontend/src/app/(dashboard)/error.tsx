"use client";

import { useEffect } from "react";
import { ErrorFallback } from "@/components/error/error-fallback";
import { errorService } from "@/lib/error-service";

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
      userId: getUserId(),
      sessionId: getSessionId(),
    });

    errorService.reportError(errorReport);

    // Log error in development
    if (process.env.NODE_ENV === "development") {
      console.error("Dashboard error boundary caught error:", error);
    }
  }, [error]);

  return <ErrorFallback error={error} reset={reset} />;
}

function getUserId(): string | undefined {
  try {
    const userStore = (
      window as Window & { __USER_STORE__?: { user?: { id?: string } } }
    ).__USER_STORE__;
    return userStore?.user?.id;
  } catch {
    return undefined;
  }
}

function getSessionId(): string | undefined {
  try {
    let sessionId = sessionStorage.getItem("session_id");
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem("session_id", sessionId);
    }
    return sessionId;
  } catch {
    return undefined;
  }
}
