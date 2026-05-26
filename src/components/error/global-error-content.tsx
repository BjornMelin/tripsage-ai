/**
 * @fileoverview Renderable content for the root global error document fallback.
 */

"use client";

import { useEffect } from "react";
import { MinimalErrorFallback } from "@/components/error/error-fallback";
import { reportRouteErrorBoundaryError } from "@/lib/telemetry/route-error-boundary";

interface GlobalErrorContentProps {
  error: unknown;
  reset: () => void;
}

/**
 * Global error fallback content without the Next.js document wrapper.
 *
 * @param props - Global error boundary props.
 * @param props.error - Error captured by the root error boundary.
 * @param props.reset - Callback that retries rendering the failed route segment.
 * @returns Minimal error fallback UI with telemetry reporting.
 */
export function GlobalErrorContent({ error, reset }: GlobalErrorContentProps) {
  useEffect(() => {
    reportRouteErrorBoundaryError(error, {
      context: "GlobalErrorBoundary",
    });
  }, [error]);

  return <MinimalErrorFallback error={error} reset={reset} />;
}
