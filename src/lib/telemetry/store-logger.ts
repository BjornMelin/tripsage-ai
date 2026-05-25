/**
 * @fileoverview Client-side logger for Zustand stores.
 */

"use client";

import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

export type StoreLogLevel = "error" | "warn" | "info";

export interface StoreLogOptions {
  storeName: string;
  metadata?: Record<string, unknown>;
}

interface StoreLogDetails {
  [key: string]: unknown;
}

/**
 * Client-side logger for Zustand stores.
 *
 * Records errors to the active OTEL span when available.
 * Non-error store events are no-ops; use explicit telemetry for durable diagnostics.
 *
 * @param options - Configuration options including store name
 * @returns Logger object with error, warn, and info methods
 */
export function createStoreLogger(options: StoreLogOptions) {
  const { storeName, metadata = {} } = options;

  return {
    /**
     * Log an error and record it on the active OTEL span.
     *
     * @param message - Error message
     * @param details - Additional context to include with the error
     */
    error(message: string, details?: StoreLogDetails) {
      const error = new Error(`[${storeName}] ${message}`);

      // Always attach context details to the error
      const errorDetails = { ...metadata, ...(details || {}), storeName };
      Object.assign(error, { details: errorDetails });

      recordClientErrorOnActiveSpan(error);
    },

    /**
     * Ignore non-error informational store events.
     *
     * @param message - Info message
     * @param details - Additional context
     */
    info(_message: string, _details?: StoreLogDetails) {
      // Non-error store events should not emit raw browser console diagnostics.
    },

    /**
     * Ignore non-error warning store events.
     *
     * @param message - Warning message
     * @param details - Additional context
     */
    warn(_message: string, _details?: StoreLogDetails) {
      // Non-error store events should not emit raw browser console diagnostics.
    },
  };
}
