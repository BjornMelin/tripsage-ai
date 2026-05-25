/**
 * @fileoverview Root-level error boundary for the Next.js app router.
 */

"use client";

import { useEffect } from "react";
import { PageErrorFallback } from "@/components/error/error-fallback";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";
import { reportRouteErrorBoundaryError } from "@/lib/telemetry/route-error-boundary";

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
    reportRouteErrorBoundaryError(error, {
      context: "RootErrorBoundary",
    });
  }, [error]);

  return (
    <main id={MAIN_CONTENT_ID} className="flex-1" tabIndex={-1}>
      <PageErrorFallback error={error} reset={reset} />
    </main>
  );
}
