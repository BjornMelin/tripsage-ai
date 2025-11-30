/**
 * @fileoverview Client-side logger for Zustand stores.
 *
 * Provides a structured logging interface for client-side stores that
 * integrates with OTEL tracing for error recording. Warnings and info
 * are no-op in production to avoid console pollution.
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
 * Falls back to no-op in production for non-errors.
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
     * Log an info message. Development-only logging.
     *
     * @param message - Info message
     * @param details - Additional context
     */
    info(message: string, details?: StoreLogDetails) {
      if (process.env.NODE_ENV === "development") {
        try {
          if (details !== undefined) {
            const safeDetails =
              typeof details === "object" ? JSON.stringify(details) : String(details);
            console.log(`[${storeName}] ${message}`, safeDetails);
          } else {
            console.log(`[${storeName}] ${message}`);
          }
        } catch {
          // Ignore stringification errors
        }
      }
    },

    /**
     * Log a warning. Development-only logging.
     *
     * @param message - Warning message
     * @param details - Additional context
     */
    warn(message: string, details?: StoreLogDetails) {
      if (process.env.NODE_ENV === "development") {
        try {
          if (details !== undefined) {
            const safeDetails =
              typeof details === "object" ? JSON.stringify(details) : String(details);
            console.warn(`[${storeName}] ${message}`, safeDetails);
          } else {
            console.warn(`[${storeName}] ${message}`);
          }
        } catch {
          // Ignore stringification errors
        }
      }
    },
  };
}
