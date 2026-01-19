/**
 * @fileoverview React hook for error handling and reporting.
 */

"use client";

import { useCallback } from "react";
import { getSessionId } from "@/lib/client/session";
import { getUserIdFromUserStore } from "@/lib/client/user-store";
import { errorService } from "@/lib/error-service";
import { fireAndForget } from "@/lib/utils";

/**
 * Hook for handling errors in React components with automatic reporting.
 *
 * Provides utilities for consistent error handling across the application,
 * including automatic error reporting, user context tracking, and session
 * information collection.
 *
 * @returns Object containing error handling functions
 */
export function useErrorHandler() {
  const handleError = useCallback(
    (error: unknown, additionalInfo?: Record<string, unknown>) => {
      // Create error report
      const errorReport = errorService.createErrorReport(error, undefined, {
        sessionId: getSessionId(),
        userId: getUserIdFromUserStore(),
        ...additionalInfo,
      });

      // Report error
      fireAndForget(errorService.reportError(errorReport));
    },
    []
  );

  const handleAsyncError = useCallback(
    async <T>(asyncOperation: () => Promise<T>, fallback?: () => void): Promise<T> => {
      try {
        return await asyncOperation();
      } catch (error) {
        handleError(error, { context: "async_operation" });
        if (fallback) {
          fallback();
        }
        throw error; // Re-throw to allow component-level handling
      }
    },
    [handleError]
  );

  return {
    handleAsyncError,
    handleError,
  };
}
