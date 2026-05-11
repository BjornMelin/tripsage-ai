/**
 * @fileoverview Lazy loader for the Web Vitals reporter client island.
 */

"use client";

import dynamic from "next/dynamic";

const WebVitalsReporterClient = dynamic(
  () => import("./web-vitals-reporter").then((mod) => mod.WebVitalsReporter),
  { ssr: false }
);

/**
 * Loads Web Vitals reporting after hydration so the compiled reporter stays out of
 * the shared root client chunk.
 *
 * @returns A lazily loaded Web Vitals reporter.
 */
export function WebVitalsReporterLoader() {
  return <WebVitalsReporterClient />;
}
