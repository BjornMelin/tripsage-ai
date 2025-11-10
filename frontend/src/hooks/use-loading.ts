/**
 * @fileoverview React hooks for managing loading states.
 *
 * Provides hooks for loading state management with timeout, progress tracking,
 * debouncing, and async operation handling.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Represents the current state of a loading operation.
 */
export interface UseLoadingState {
  /** Whether a loading operation is currently in progress. */
  isLoading: boolean;
  /** Optional message describing the current loading operation. */
  message?: string;
  /** Optional progress percentage (0-100) for the loading operation. */
  progress?: number;
  /** Optional error message if the loading operation failed. */
  error?: string;
}

/**
 * Configuration options for the useLoading hook.
 */
export interface UseLoadingOptions {
  /** Whether loading should start immediately when the hook initializes. */
  initialLoading?: boolean;
  /** Initial message to display when loading starts. */
  initialMessage?: string;
  /** Timeout in milliseconds after which loading automatically stops. */
  timeout?: number;
  /** Callback function called when the timeout expires. */
  onTimeout?: () => void;
}

/**
 * Return type of the useLoading hook containing state and control functions.
 */
export interface UseLoadingReturn {
  /** Whether a loading operation is currently in progress. */
  isLoading: boolean;
  /** Current loading message. */
  message?: string;
  /** Current progress percentage (0-100). */
  progress?: number;
  /** Current error message, if any. */
  error?: string;
  /** Starts a loading operation with an optional message. */
  startLoading: (message?: string) => void;
  /** Stops the current loading operation. */
  stopLoading: () => void;
  /** Sets the progress percentage (clamped between 0-100). */
  setProgress: (progress: number) => void;
  /** Sets the loading message. */
  setMessage: (message: string) => void;
  /** Sets an error message and stops loading. */
  setError: (error: string) => void;
  /** Clears the current error message. */
  clearError: () => void;
  /** Resets all loading state to initial values. */
  reset: () => void;
}

/**
 * Hook for managing loading states with optional timeout.
 *
 * @param options - Configuration options
 * @returns Loading state and control functions
 */
export function useLoading(options: UseLoadingOptions = {}): UseLoadingReturn {
  const { initialLoading = false, initialMessage, timeout, onTimeout } = options;

  const [state, setState] = useState<UseLoadingState>({
    error: undefined,
    isLoading: initialLoading,
    message: initialMessage,
    progress: undefined,
  });

  const timeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

  // Clear timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const startLoading = useCallback(
    (message?: string) => {
      setState((prev) => ({
        ...prev,
        error: undefined,
        isLoading: true,
        message,
      }));

      // Set timeout if specified
      if (timeout) {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }

        timeoutRef.current = setTimeout(() => {
          setState((prev) => ({ ...prev, isLoading: false }));
          onTimeout?.();
        }, timeout);
      }
    },
    [timeout, onTimeout]
  );

  const stopLoading = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    setState((prev) => ({ ...prev, isLoading: false }));
  }, []);

  const setProgress = useCallback((progress: number) => {
    setState((prev) => ({
      ...prev,
      progress: Math.min(100, Math.max(0, progress)),
    }));
  }, []);

  const setMessage = useCallback((message: string) => {
    setState((prev) => ({ ...prev, message }));
  }, []);

  const setError = useCallback((error: string) => {
    setState((prev) => ({
      ...prev,
      error,
      isLoading: false,
    }));

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
  }, []);

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: undefined }));
  }, []);

  const reset = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    setState({
      error: undefined,
      isLoading: false,
      message: undefined,
      progress: undefined,
    });
  }, []);

  return {
    clearError,
    error: state.error,
    isLoading: state.isLoading,
    message: state.message,
    progress: state.progress,
    reset,
    setError,
    setMessage,
    setProgress,
    startLoading,
    stopLoading,
  };
}

/**
 * Return type of the useAsyncLoading hook for managing async operations.
 *
 * @template T - The return type of the async function
 * @template P - The parameters tuple type of the async function
 */
export interface UseAsyncLoadingReturn<
  T,
  P extends readonly unknown[] = readonly unknown[],
> {
  /** The result data from the last successful async operation. */
  data?: T;
  /** Whether an async operation is currently in progress. */
  isLoading: boolean;
  /** Error message from the last failed async operation. */
  error?: string;
  /** Executes the async function with the provided arguments. */
  execute: (...args: P) => Promise<T>;
  /** Resets the hook state to initial values. */
  reset: () => void;
}

export function useAsyncLoading<T, P extends readonly unknown[]>(
  asyncFn: (...args: P) => Promise<T>
): UseAsyncLoadingReturn<T, P> {
  const [data, setData] = useState<T>();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>();

  const execute = useCallback(
    async (...args: P): Promise<T> => {
      setIsLoading(true);
      setError(undefined);

      try {
        const result = await asyncFn(...args);
        setData(result);
        return result;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "An error occurred";
        setError(errorMessage);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [asyncFn]
  );

  const reset = useCallback(() => {
    setData(undefined);
    setIsLoading(false);
    setError(undefined);
  }, []);

  return {
    data,
    error,
    execute,
    isLoading,
    reset,
  };
}

/**
 * Hook for managing loading state with debounced start/stop operations.
 *
 * Useful for preventing rapid loading state changes in response to frequent
 * user interactions. Both start and stop operations are debounced by the
 * specified delay.
 *
 * @param delay - Debounce delay in milliseconds (default: 300)
 * @returns Loading state with debounced start/stop functions
 */
export function useDebouncedLoading(delay = 300): UseLoadingReturn {
  const loading = useLoading();
  const debounceRef = useRef<NodeJS.Timeout | undefined>(undefined);

  const debouncedStartLoading = useCallback(
    (message?: string) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      debounceRef.current = setTimeout(() => {
        loading.startLoading(message);
      }, delay);
    },
    [loading, delay]
  );

  const debouncedStopLoading = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      loading.stopLoading();
    }, delay);
  }, [loading, delay]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  return {
    ...loading,
    startLoading: debouncedStartLoading,
    stopLoading: debouncedStopLoading,
  };
}
