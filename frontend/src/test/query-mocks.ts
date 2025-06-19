import type { UseMutationResult } from "@tanstack/react-query";
/**
 * React Query mock utilities for testing
 */
import { vi } from "vitest";

// Helper to manually trigger mutation lifecycle
export interface MutationController<
  TData = unknown,
  TError = Error,
  TVariables = unknown,
> {
  triggerMutate: (variables: TVariables) => void;
  triggerSuccess: (data: TData) => void;
  triggerError: (error: TError) => void;
  reset: () => void;
}

// Create a controlled mock mutation
export function createControlledMutation<
  TData = unknown,
  TError = Error,
  TVariables = unknown,
  TContext = unknown,
>(): {
  mutation: UseMutationResult<TData, TError, TVariables, TContext>;
  controller: MutationController<TData, TError, TVariables>;
} {
  let currentData: TData | undefined;
  let currentError: TError | null = null;
  let isPending = false;
  let isError = false;
  let isSuccess = false;
  let variables: TVariables | undefined;

  // Callbacks
  let onMutateCallback: ((vars: TVariables) => void) | undefined;
  let onSuccessCallback: ((data: TData, vars: TVariables) => void) | undefined;
  let onErrorCallback: ((error: TError, vars: TVariables) => void) | undefined;

  const mutate = vi.fn((vars: TVariables, options?: any) => {
    variables = vars;
    isPending = true;
    isError = false;
    isSuccess = false;
    currentError = null;

    // Call onMutate if provided
    if (onMutateCallback) {
      onMutateCallback(vars);
    }

    if (options?.onMutate) {
      options.onMutate(vars);
    }
  });

  const mutateAsync = vi.fn((vars: TVariables) => {
    mutate(vars);
    return new Promise<TData>((resolve, reject) => {
      // Store resolve/reject for manual control
      (mutateAsync as any)._resolve = resolve;
      (mutateAsync as any)._reject = reject;
    });
  });

  const reset = vi.fn(() => {
    currentData = undefined;
    currentError = null;
    isPending = false;
    isError = false;
    isSuccess = false;
    variables = undefined;
  });

  const mutation: UseMutationResult<TData, TError, TVariables, TContext> = {
    data: currentData,
    error: currentError,
    isError,
    isIdle: !isPending && !isError && !isSuccess,
    isPending,
    isSuccess,
    failureCount: 0,
    failureReason: currentError,
    isPaused: false,
    variables,
    status: isPending ? "pending" : isError ? "error" : isSuccess ? "success" : "idle",
    mutate,
    mutateAsync,
    reset,
    context: undefined as TContext,
    isLoadingError: false,
    isRefetchError: false,
    promise: Promise.resolve(currentData as TData),
  } as UseMutationResult<TData, TError, TVariables, TContext>;

  // Controller functions
  const controller: MutationController<TData, TError, TVariables> = {
    triggerMutate: (vars: TVariables) => {
      mutate(vars);
    },
    triggerSuccess: (data: TData) => {
      currentData = data;
      currentError = null;
      isPending = false;
      isError = false;
      isSuccess = true;

      // Update mutation object
      Object.assign(mutation, {
        data: currentData,
        error: currentError,
        isError,
        isPending,
        isSuccess,
        status: "success",
      });

      // Call success callbacks
      if (onSuccessCallback && variables) {
        onSuccessCallback(data, variables);
      }

      // Resolve async promise if exists
      if ((mutateAsync as any)._resolve) {
        (mutateAsync as any)._resolve(data);
      }
    },
    triggerError: (error: TError) => {
      currentData = undefined;
      currentError = error;
      isPending = false;
      isError = true;
      isSuccess = false;

      // Update mutation object
      Object.assign(mutation, {
        data: currentData,
        error: currentError,
        isError,
        isPending,
        isSuccess,
        status: "error",
        failureReason: error,
      });

      // Call error callbacks
      if (onErrorCallback && variables) {
        onErrorCallback(error, variables);
      }

      // Reject async promise if exists
      if ((mutateAsync as any)._reject) {
        (mutateAsync as any)._reject(error);
      }
    },
    reset: () => {
      reset();
      Object.assign(mutation, {
        data: undefined,
        error: null,
        isError: false,
        isPending: false,
        isSuccess: false,
        status: "idle",
        variables: undefined,
      });
    },
  };

  // Store callbacks on mutation for use by controller
  (mutation as any)._setCallbacks = (callbacks: {
    onMutate?: (vars: TVariables) => void;
    onSuccess?: (data: TData, vars: TVariables) => void;
    onError?: (error: TError, vars: TVariables) => void;
  }) => {
    onMutateCallback = callbacks.onMutate;
    onSuccessCallback = callbacks.onSuccess;
    onErrorCallback = callbacks.onError;
  };

  return { mutation, controller };
}

// Mock useMutation hook
export function mockUseMutation<
  TData = unknown,
  TError = Error,
  TVariables = unknown,
  TContext = unknown,
>(options?: {
  onMutate?: (variables: TVariables) => void;
  onSuccess?: (data: TData, variables: TVariables) => void;
  onError?: (error: TError, variables: TVariables) => void;
}) {
  const { mutation, controller } = createControlledMutation<
    TData,
    TError,
    TVariables,
    TContext
  >();

  // Store callbacks
  if (options) {
    (mutation as any)._setCallbacks(options);
  }

  return { mutation, controller };
}

// Helper to wait for React updates
export async function waitForReactUpdate() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}
