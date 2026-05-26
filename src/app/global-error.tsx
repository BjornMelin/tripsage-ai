/**
 * @fileoverview Global error boundary for the app. This catches errors in the root layout or template.
 */

"use client";

import { GlobalErrorContent } from "@/components/error/global-error-content";

/**
 * Global error boundary for the app.
 * Catches errors in the root layout or template.
 * This is a last resort fallback that replaces the entire root layout
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: unknown;
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body>
        <GlobalErrorContent error={error} reset={reset} />
      </body>
    </html>
  );
}
