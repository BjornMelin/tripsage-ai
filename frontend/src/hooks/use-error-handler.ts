/**
 * @fileoverview React hook for error handling and reporting.
 *
 * Provides error handling utilities with automatic error reporting,
 * user context, and session tracking.
 */

"use client";

import { useCallback } from "react";
import { errorService } from "@/lib/error-service";

// Extend Window interface for custom properties
declare global {
  interface Window {
    userStore?: {
      user?: {
        id?: string;
      };
    };
  }
}

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
    (error: Error, additionalInfo?: Record<string, unknown>) => {
      // Create error report
      const errorReport = errorService.createErrorReport(error, undefined, {
        sessionId: getSessionId(),
        userId: getUserId(),
        ...additionalInfo,
      });

      // Report error
      errorService.reportError(errorReport);

      // Log in development
      if (process.env.NODE_ENV === "development") {
        console.error("Error handled by useErrorHandler:", error, additionalInfo);
      }
    },
    []
  );

  const handleAsyncError = useCallback(
    async <T>(asyncOperation: () => Promise<T>, fallback?: () => void): Promise<T> => {
      try {
        return await asyncOperation();
      } catch (error) {
        handleError(error as Error, { context: "async_operation" });
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

/**
 * Gets the current user ID from the user store.
 *
 * @returns User ID or undefined if not available
 */
function getUserId(): string | undefined {
  try {
    const userStore = window.userStore;
    return userStore?.user?.id;
  } catch {
    return undefined;
  }
}

/**
 * Gets or creates a session ID for error tracking.
 *
 * @returns Session ID or undefined if sessionStorage is unavailable
 */
function getSessionId(): string | undefined {
  try {
    let sessionId = sessionStorage.getItem("session_id");
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem("session_id", sessionId);
    }
    return sessionId;
  } catch {
    return undefined;
  }
}
