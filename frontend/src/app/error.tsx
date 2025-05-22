"use client";

import { useEffect } from "react";
import { PageErrorFallback } from "@/components/error/error-fallback";
import { errorService } from "@/lib/error-service";

/**
 * Root-level error boundary for the app directory
 * This catches errors in the root layout and pages
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Report the error
    const errorReport = errorService.createErrorReport(error, undefined, {
      userId: getUserId(),
      sessionId: getSessionId(),
    });

    errorService.reportError(errorReport);

    // Log error in development
    if (process.env.NODE_ENV === "development") {
      console.error("Root error boundary caught error:", error);
    }
  }, [error]);

  return <PageErrorFallback error={error} reset={reset} />;
}

function getUserId(): string | undefined {
  try {
    const userStore = (window as any).__USER_STORE__;
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
