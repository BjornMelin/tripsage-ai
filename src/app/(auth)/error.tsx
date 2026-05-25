/**
 * @fileoverview Authentication-level error boundary for the auth directory. This catches errors within the auth layout and pages.
 */

"use client";

import { useEffect } from "react";
import { ErrorFallback } from "@/components/error/error-fallback";
import { reportRouteErrorBoundaryError } from "@/lib/telemetry/route-error-boundary";

/**
 * Authentication-level error boundary
 * Catches errors within the auth layout and pages
 */
export default function AuthError({
  error,
  reset,
}: {
  error: unknown;
  reset: () => void;
}) {
  useEffect(() => {
    reportRouteErrorBoundaryError(error, {
      context: "AuthErrorBoundary",
      includeUserId: false,
    });
  }, [error]);

  return <ErrorFallback error={error} reset={reset} />;
}
