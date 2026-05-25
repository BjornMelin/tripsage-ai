/**
 * @fileoverview Dashboard-level error boundary for the dashboard directory. This catches errors within the dashboard layout and pages.
 */

"use client";

import { useEffect } from "react";
import { ErrorFallback } from "@/components/error/error-fallback";
import { reportRouteErrorBoundaryError } from "@/lib/telemetry/route-error-boundary";

/**
 * Dashboard-level error boundary
 * Catches errors within the dashboard layout and pages
 */
export default function DashboardError({
  error,
  reset,
}: {
  error: unknown;
  reset: () => void;
}) {
  useEffect(() => {
    reportRouteErrorBoundaryError(error, {
      context: "DashboardErrorBoundary",
    });
  }, [error]);

  return <ErrorFallback error={error} reset={reset} />;
}
