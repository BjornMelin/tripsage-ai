/**
 * @fileoverview Client telemetry helper for Next.js route error boundaries.
 */

"use client";

import { normalizeThrownError } from "@/lib/client/normalize-thrown-error";
import { getSessionId } from "@/lib/client/session";
import { getUserIdFromUserStore } from "@/lib/client/user-store";
import { errorService } from "@/lib/error-service";
import { fireAndForget } from "@/lib/utils";

interface RouteErrorBoundaryReportOptions {
  context: string;
  includeUserId?: boolean;
}

/**
 * Reports an App Router route-level boundary error to durable error reporting
 * and the currently active client span.
 */
export function reportRouteErrorBoundaryError(
  error: unknown,
  { context, includeUserId = true }: RouteErrorBoundaryReportOptions
): void {
  const normalized = normalizeThrownError(error);
  const metadata = {
    sessionId: getSessionId(),
    ...(includeUserId ? { userId: getUserIdFromUserStore() } : {}),
  };
  const errorReport = errorService.createErrorReport(normalized, undefined, metadata);

  fireAndForget(
    errorService.reportError(errorReport, {
      action: "render",
      context,
    })
  );
}
