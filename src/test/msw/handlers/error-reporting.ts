/**
 * @fileoverview MSW handlers for client-side error reporting.
 *
 * Provides reusable handler factories for the ErrorService tests so suites can
 * capture posted payloads or simulate flaky network conditions without
 * hand-rolling inline MSW handlers.
 */

import type { ErrorReport } from "@schemas/errors";
import type { HttpHandler } from "msw";
import { HttpResponse, http } from "msw";

/** Default endpoint used by ErrorService in tests. */
export const ERROR_REPORTING_ENDPOINT = "https://api.example.com/errors";

export interface RecordedErrorReport {
  body: ErrorReport;
  headers: Headers;
}

/**
 * Create a handler that records every posted error report.
 *
 * @param endpoint - Error reporting endpoint to intercept.
 * @returns MSW handler and an array that accumulates captured requests.
 */
export function createErrorReportingRecorder(endpoint = ERROR_REPORTING_ENDPOINT): {
  handler: HttpHandler;
  requests: RecordedErrorReport[];
} {
  const requests: RecordedErrorReport[] = [];

  return {
    handler: http.post(endpoint, async ({ request }) => {
      const body = (await request.json()) as ErrorReport;
      requests.push({ body, headers: request.headers });
      return HttpResponse.json({ success: true });
    }),
    requests,
  };
}

/**
 * Create a handler that fails a configurable number of times before succeeding.
 *
 * Useful for exercising retry logic without duplicating inline handlers.
 *
 * @param options.failTimes - Number of initial calls that should throw.
 * @param options.endpoint - Endpoint to intercept.
 * @returns MSW handler plus a getter for total call count.
 */
export function createFlakyErrorReportingHandler(options?: {
  failTimes?: number;
  endpoint?: string;
}): { handler: HttpHandler; callCount: () => number } {
  const endpoint = options?.endpoint ?? ERROR_REPORTING_ENDPOINT;
  const failTimes = options?.failTimes ?? 1;
  let calls = 0;

  return {
    callCount: () => calls,
    handler: http.post(endpoint, () => {
      calls += 1;
      if (calls <= failTimes) {
        throw new Error("Network error");
      }
      return HttpResponse.json({ success: true });
    }),
  };
}

/**
 * Default happy-path handler for error reporting.
 *
 * Added to the global server so unmocked error posts are still intercepted.
 */
export const errorReportingHandlers: HttpHandler[] = [
  http.post(ERROR_REPORTING_ENDPOINT, () => HttpResponse.json({ success: true })),
];
