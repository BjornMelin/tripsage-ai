/**
 * @fileoverview Global error boundary for the app.
 * This catches errors in the root layout or template.
 */

"use client";

import { useEffect } from "react";
import { MinimalErrorFallback } from "@/components/error/error-fallback";
import { getSessionId } from "@/lib/client/session";
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
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Report the critical error
    const errorReport = errorService.createErrorReport(error, undefined, {
      sessionId: getSessionId(),
      userId: getUserId(),
    });

    fireAndForget(errorService.reportError(errorReport));

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

/**
 * Gets the current user ID from the user store.
 *
 * @returns User ID or undefined if not available
 */
function getUserId(): string | undefined {
  try {
    const userStore = (
      window as typeof window & { userStore?: { user?: { id?: string } } }
    ).userStore;
    return userStore?.user?.id;
  } catch {
    return undefined;
  }
}
