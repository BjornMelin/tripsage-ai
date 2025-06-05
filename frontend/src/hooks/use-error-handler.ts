"use client";

import { errorService } from "@/lib/error-service";
import { useCallback } from "react";

/**
 * Hook for handling errors in components
 */
export function useErrorHandler() {
  const handleError = useCallback(
    (error: Error, additionalInfo?: Record<string, any>) => {
      // Create error report
      const errorReport = errorService.createErrorReport(error, undefined, {
        userId: getUserId(),
        sessionId: getSessionId(),
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
    async (asyncOperation: () => Promise<any>, fallback?: () => void) => {
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
    handleError,
    handleAsyncError,
  };
}

function getUserId(): string | undefined {
  try {
    const userStore = (window as any).__USER_STORE__;
    return userStore?.user?.id;
  } catch {
    return undefined;
  }
}

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
