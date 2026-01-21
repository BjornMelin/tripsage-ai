/**
 * @fileoverview Defensive patch for `performance.measure()` to avoid browser errors
 * in prerender-related flows.
 */

"use client";

let didPatch = false;

export function patchPerformanceMeasureForPrerender(): void {
  if (didPatch) return;
  if (typeof performance === "undefined") return;

  didPatch = true;

  const originalMeasure = performance.measure.bind(performance);

  performance.measure = ((
    name: string,
    startOrOptions?: string | PerformanceMeasureOptions,
    endMark?: string
  ) => {
    try {
      if (startOrOptions && typeof startOrOptions === "object") {
        const sanitized: PerformanceMeasureOptions = {
          ...startOrOptions,
          duration:
            typeof startOrOptions.duration === "number"
              ? Math.max(0, startOrOptions.duration)
              : startOrOptions.duration,
          end:
            typeof startOrOptions.end === "number"
              ? Math.max(0, startOrOptions.end)
              : startOrOptions.end,
          start:
            typeof startOrOptions.start === "number"
              ? Math.max(0, startOrOptions.start)
              : startOrOptions.start,
        };

        return originalMeasure(name, sanitized);
      }

      if (typeof startOrOptions === "string" || startOrOptions === undefined) {
        return originalMeasure(name, startOrOptions, endMark);
      }

      return originalMeasure(name);
    } catch (error) {
      // Some browsers throw during prerender-related measurements. We treat those
      // as non-fatal and fall back to a best-effort measure to avoid noisy console
      // errors and unhandled exceptions in the app shell.
      if (error instanceof Error && error.message.includes("negative time stamp")) {
        return originalMeasure(name);
      }
      throw error;
    }
  }) satisfies Performance["measure"];
}
