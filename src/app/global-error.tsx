/**
 * @fileoverview Global error boundary for the app. This catches errors in the root layout or template.
 */

"use client";

import { useEffect } from "react";
import { MinimalErrorFallback } from "@/components/error/error-fallback";
import { normalizeThrownError } from "@/lib/client/normalize-thrown-error";
import { getSessionId } from "@/lib/client/session";
import { getUserIdFromUserStore } from "@/lib/client/user-store";
import { errorService } from "@/lib/error-service";
import { fireAndForget } from "@/lib/utils";

/**
 * Global error boundary for the app.
 * Catches errors in the root layout or template.
 * This is a last resort fallback that replaces the entire root layout
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: unknown;
  reset: () => void;
}) {
  useEffect(() => {
    const normalized = normalizeThrownError(error);
    // Report the critical error
    const errorReport = errorService.createErrorReport(normalized, undefined, {
      sessionId: getSessionId(),
      userId: getUserIdFromUserStore(),
    });

    fireAndForget(errorService.reportError(errorReport));

    // Log critical error in development (production uses errorService only)
    if (process.env.NODE_ENV === "development") {
      console.error("CRITICAL: Global error boundary caught error:", normalized);
    }
  }, [error]);

  return (
    <html lang="en">
      <body>
        <MinimalErrorFallback error={error} reset={reset} />
      </body>
    </html>
  );
}
