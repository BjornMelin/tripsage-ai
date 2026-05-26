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
 */
export function GlobalErrorContent({ error, reset }: GlobalErrorContentProps) {
  useEffect(() => {
    reportRouteErrorBoundaryError(error, {
      context: "GlobalErrorBoundary",
    });
  }, [error]);

  return <MinimalErrorFallback error={error} reset={reset} />;
}
