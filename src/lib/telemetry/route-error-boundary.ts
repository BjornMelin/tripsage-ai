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
 *
 * @param error - Error value thrown by the route-level boundary.
 * @param options - Route boundary reporting options.
 * @param options.context - Telemetry context name for the boundary.
 * @param options.includeUserId - Whether to include the current user ID.
 * @returns Nothing.
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
