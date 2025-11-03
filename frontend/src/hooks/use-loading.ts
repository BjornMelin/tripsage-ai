/**
 * @fileoverview React hooks for managing loading states.
 *
 * Provides hooks for loading state management with timeout, progress tracking,
 * debouncing, and async operation handling.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Loading state interface
 */
export interface UseLoadingState {
  isLoading: boolean;
  message?: string;
  progress?: number;
  error?: string;
}

/**
 * Loading hook options
 */
export interface UseLoadingOptions {
  initialLoading?: boolean;
  initialMessage?: string;
  timeout?: number; // Auto-stop loading after timeout
  onTimeout?: () => void;
}

/**
 * Loading hook return type
 */
export interface UseLoadingReturn {
  isLoading: boolean;
  message?: string;
  progress?: number;
  error?: string;
  startLoading: (message?: string) => void;
  stopLoading: () => void;
  setProgress: (progress: number) => void;
  setMessage: (message: string) => void;
  setError: (error: string) => void;
  clearError: () => void;
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
 * Hook for managing async operations with loading states.
 *
 * @template T - Return type of the async function
 * @param asyncFn - Async function to execute
 * @returns Loading state and execution function
 */
export interface UseAsyncLoadingReturn<T> {
  data?: T;
  isLoading: boolean;
  error?: string;
  execute: (...args: any[]) => Promise<T>;
  reset: () => void;
}

export function useAsyncLoading<T>(
  asyncFn: (...args: any[]) => Promise<T>
): UseAsyncLoadingReturn<T> {
  const [data, setData] = useState<T>();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>();

  const execute = useCallback(
    async (...args: any[]): Promise<T> => {
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
 * Hook for managing loading state with debounced updates.
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
