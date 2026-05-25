/**
 * @fileoverview Global error boundary for the app. This catches errors in the root layout or template.
 */

"use client";

import { useEffect } from "react";
import { MinimalErrorFallback } from "@/components/error/error-fallback";
import { reportRouteErrorBoundaryError } from "@/lib/telemetry/route-error-boundary";

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
    reportRouteErrorBoundaryError(error, {
      context: "GlobalErrorBoundary",
    });
  }, [error]);

  return (
    <html lang="en">
      <body>
        <MinimalErrorFallback error={error} reset={reset} />
      </body>
    </html>
  );
}
