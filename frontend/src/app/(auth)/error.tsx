"use client";

import { ErrorFallback } from "@/components/error/error-fallback";
import { errorService } from "@/lib/error-service";
import { useEffect } from "react";

/**
 * Authentication-level error boundary
 * Catches errors within the auth layout and pages
 */
export default function AuthError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Report the auth error
    const errorReport = errorService.createErrorReport(error, undefined, {
      sessionId: getSessionId(),
    });

    errorService.reportError(errorReport);

    // Log error in development
    if (process.env.NODE_ENV === "development") {
      console.error("Auth error boundary caught error:", error);
    }
  }, [error]);

  return <ErrorFallback error={error} reset={reset} />;
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
