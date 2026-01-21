/**
 * @fileoverview Root-level error boundary for the Next.js app router.
 */

"use client";

import { useEffect } from "react";
import { PageErrorFallback } from "@/components/error/error-fallback";
import { normalizeThrownError } from "@/lib/client/normalize-thrown-error";
import { getSessionId } from "@/lib/client/session";
import { getUserIdFromUserStore } from "@/lib/client/user-store";
import { errorService } from "@/lib/error-service";
import { fireAndForget } from "@/lib/utils";

/**
 * Root-level error boundary for the app directory
 * This catches errors in the root layout and pages
 */
export default function RootErrorBoundary({
  error,
  reset,
}: {
  error: unknown;
  reset: () => void;
}) {
  useEffect(() => {
    const normalized = normalizeThrownError(error);
    // Report the error
    const errorReport = errorService.createErrorReport(normalized, undefined, {
      sessionId: getSessionId(),
      userId: getUserIdFromUserStore(),
    });

    fireAndForget(errorService.reportError(errorReport));

    // Log error in development
    if (process.env.NODE_ENV === "development") {
      console.error("Root error boundary caught error:", normalized);
    }
  }, [error]);

  return <PageErrorFallback error={error} reset={reset} />;
}
