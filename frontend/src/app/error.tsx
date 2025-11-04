/**
 * @fileoverview Root-level error boundary for the app directory.
 * This catches errors in the root layout and pages.
 */

"use client";

import { useEffect } from "react";
import { PageErrorFallback } from "@/components/error/error-fallback";
import { errorService } from "@/lib/error-service";
import { secureUUID } from "@/lib/security/random";

/**
 * Root-level error boundary for the app directory
 * This catches errors in the root layout and pages
 */
export default function RootErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Report the error
    const errorReport = errorService.createErrorReport(error, undefined, {
      sessionId: getSessionId(),
      userId: getUserId(),
    });

    errorService.reportError(errorReport);

    // Log error in development
    if (process.env.NODE_ENV === "development") {
      console.error("Root error boundary caught error:", error);
    }
  }, [error]);

  return <PageErrorFallback error={error} reset={reset} />;
}

/**
 * Gets the current user ID from the user store.
 *
 * @returns User ID or undefined if not available
 */
function getUserId(): string | undefined {
  try {
    interface UserStore {
      user?: {
        id?: string;
      };
    }
    const userStore = (window as unknown as { userStore?: UserStore }).userStore;
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
      sessionId = `session_${secureUUID()}`;
      sessionStorage.setItem("session_id", sessionId);
    }
    return sessionId;
  } catch {
    return undefined;
  }
}
