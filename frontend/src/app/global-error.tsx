"use client";

import { useEffect } from "react";
import { MinimalErrorFallback } from "@/components/error/error-fallback";
import { errorService } from "@/lib/error-service";

/**
 * Global error boundary - catches errors in the root layout or template
 * This is a last resort fallback that replaces the entire root layout
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Report the critical error
    const errorReport = errorService.createErrorReport(error, undefined, {
      sessionId: getSessionId(),
      userId: getUserId(),
    });

    errorService.reportError(errorReport);

    // Log critical error
    console.error("CRITICAL: Global error boundary caught error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body>
        <MinimalErrorFallback error={error} reset={reset} />
      </body>
    </html>
  );
}

function getUserId(): string | undefined {
  try {
    const userStore = (
      window as typeof window & { __USER_STORE__?: { user?: { id?: string } } }
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
