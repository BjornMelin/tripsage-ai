/**
 * @fileoverview Root-level error boundary for the app directory.
 * This catches errors in the root layout and pages.
 */

"use client";

import { useEffect } from "react";
import { PageErrorFallback } from "@/components/error/error-fallback";
import { errorService } from "@/lib/error-service";
import { fireAndForget, getSessionId } from "@/lib/utils";

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

    fireAndForget(errorService.reportError(errorReport));

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
