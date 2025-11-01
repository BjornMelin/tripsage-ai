/**
 * @fileoverview Lightweight typed mocks for TanStack Query primitives used in tests.
 */

import type {
  MutateOptions,
  QueryClient,
  UseMutationResult,
} from "@tanstack/react-query";
import { QueryClient as TanStackQueryClient } from "@tanstack/react-query";
import { vi } from "vitest";
import { createMockUseQueryResult } from "@/test/mock-helpers";

type MutationState<TData, TError, TVariables> = {
  data: TData | undefined;
  error: TError | null;
  status: "idle" | "pending" | "success" | "error";
  variables: TVariables | undefined;
};

type QueryState<TData, TError> = {
  data: TData | undefined;
  error: TError | null;
  status: "pending" | "success" | "error";
};

/**
 * Controller that allows tests to drive mutation state transitions manually.
 */
export interface MutationController<TData, TError, TVariables> {
  /** Set the mutation into a pending/loading state. */
  triggerMutate: (variables: TVariables) => void;
  /** Resolve the mutation with data. */
  triggerSuccess: (data: TData) => void;
  /** Reject the mutation with an error. */
  triggerError: (error: TError) => void;
  /** Reset the mutation back to the idle state. */
  reset: () => void;
}

/**
 * Controller that allows tests to drive query state transitions manually.
 */
export interface QueryController<TData, TError> {
  /** Set the query to loading/pending. */
  triggerLoading: () => void;
  /** Resolve the query with data. */
  triggerSuccess: (data: TData) => void;
  /** Reject the query with an error. */
  triggerError: (error: TError) => void;
  /** Invoke the mock refetch handler. */
  triggerRefetch: () => void;
  /** Reset the query back to pending with no data. */
  reset: () => void;
}

/**
 * Create a test QueryClient with retries disabled and zero cache persistence.
 * @returns QueryClient configured for deterministic unit tests.
 */
export const createMockQueryClient = (): QueryClient =>
  new TanStackQueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });

/**
 * Build a controlled mutation result along with its controller helpers.
 * @returns A tuple containing the mutation result and controller.
 */
export function createControlledMutation<
  TData,
  TError = Error,
  TVariables = void,
  TContext = unknown,
>() {
  const state: MutationState<TData, TError, TVariables> = {
    data: undefined,
    error: null,
    status: "idle",
    variables: undefined,
  };

  const mutate = vi.fn(
    (
      variables: TVariables,
      _options?: MutateOptions<TData, TError, TVariables, TContext>
    ) => {
      state.variables = variables;
      state.status = "pending";
      state.error = null;
    }
  );

  const mutateAsync = vi.fn(
    async (
      variables: TVariables,
      options?: MutateOptions<TData, TError, TVariables, TContext>
    ) => {
      mutate(variables, options);
      return state.data as TData;
    }
  );

  const reset = vi.fn(() => {
    state.data = undefined;
    state.error = null;
    state.status = "idle";
    state.variables = undefined;
  });

  const mutation: UseMutationResult<TData, TError, TVariables, TContext> = {
    data: state.data,
    error: state.error,
    failureCount: 0,
    failureReason: null,
    isError: false,
    isIdle: true,
    isPending: false,
    isPaused: false,
    isSuccess: false,
    status: "idle",
    variables: state.variables,
    mutate,
    mutateAsync,
    reset,
    context: undefined as TContext,
    isLoadingError: false,
    isRefetchError: false,
    submittedAt: Date.now(),
    promise: Promise.resolve({ data: state.data, error: state.error }),
  } as UseMutationResult<TData, TError, TVariables, TContext>;

  const controller: MutationController<TData, TError, TVariables> = {
    triggerMutate: (variables: TVariables) => {
      mutate(variables);
      Object.assign(mutation, {
        status: "pending" as const,
        isPending: true,
        isIdle: false,
        isError: false,
        isSuccess: false,
        variables,
        error: null,
      });
    },
    triggerSuccess: (data: TData) => {
      state.data = data;
      state.error = null;
      state.status = "success";
      Object.assign(mutation, {
        data,
        error: null,
        status: "success" as const,
        isPending: false,
        isSuccess: true,
        isError: false,
        isIdle: false,
      });
    },
    triggerError: (error: TError) => {
      state.data = undefined;
      state.error = error;
      state.status = "error";
      Object.assign(mutation, {
        data: undefined,
        error,
        status: "error" as const,
        isPending: false,
        isSuccess: false,
        isError: true,
        isIdle: false,
        failureReason: error,
        failureCount: 1,
      });
    },
    reset: () => {
      reset();
      Object.assign(mutation, {
        data: undefined,
        error: null,
        status: "idle" as const,
        isPending: false,
        isSuccess: false,
        isError: false,
        isIdle: true,
        variables: undefined,
      });
    },
  };

  return { mutation, controller };
}

/**
 * Convenience helper returning only the mutation result for simple tests.
 * @returns A mocked mutation result along with its controller.
 */
export function mockUseMutation<TData, TError, TVariables, TContext = unknown>() {
  return createControlledMutation<TData, TError, TVariables, TContext>();
}

/**
 * Build a controlled query result together with a controller.
 * @returns A tuple containing the query result and controller.
 */
export function createControlledQuery<TData, TError = Error>() {
  const state: QueryState<TData, TError> = {
    data: undefined,
    error: null,
    status: "pending",
  };

  const query = createMockUseQueryResult<TData, TError>(null, null, true, false);
  query.status = "pending";
  query.fetchStatus = "idle";
  query.isPending = true;
  query.isInitialLoading = true;
  query.isLoading = true;
  query.isFetching = false;
  query.isSuccess = false;
  query.isError = false;
  query.data = undefined;
  query.error = null;

  const controller: QueryController<TData, TError> = {
    triggerLoading: () => {
      state.status = "pending";
      Object.assign(query, {
        status: "pending" as const,
        isPending: true,
        isLoading: true,
        isFetching: true,
        isSuccess: false,
        isError: false,
      });
    },
    triggerSuccess: (data: TData) => {
      state.data = data;
      state.error = null;
      state.status = "success";
      Object.assign(query, {
        data,
        error: null,
        status: "success" as const,
        isPending: false,
        isLoading: false,
        isFetching: false,
        isFetched: true,
        isFetchedAfterMount: true,
        isSuccess: true,
        isError: false,
      });
    },
    triggerError: (error: TError) => {
      state.data = undefined;
      state.error = error;
      state.status = "error";
      Object.assign(query, {
        data: undefined,
        error,
        status: "error" as const,
        isPending: false,
        isLoading: false,
        isFetching: false,
        isSuccess: false,
        isError: true,
        isLoadingError: true,
      });
    },
    triggerRefetch: () => {
      void query.refetch();
    },
    reset: () => {
      state.data = undefined;
      state.error = null;
      state.status = "pending";
      Object.assign(query, {
        data: undefined,
        error: null,
        status: "pending" as const,
        isPending: true,
        isLoading: true,
        isFetching: false,
        isSuccess: false,
        isError: false,
        isLoadingError: false,
        isFetched: false,
        isFetchedAfterMount: false,
      });
    },
  };

  return { query, controller };
}

/**
 * Simplified query mock for components that only need success/error toggling.
 * @param initialData Optional data to seed the query with.
 * @param initialError Optional error to seed the query with.
 * @returns The mocked query result and controller.
 */
export function mockUseQuery<TData, TError>(
  initialData?: TData,
  initialError?: TError
) {
  const { query, controller } = createControlledQuery<TData, TError>();

  if (initialData !== undefined) {
    controller.triggerSuccess(initialData);
  }

  if (initialError !== undefined) {
    controller.triggerError(initialError);
  }

  return { query, controller };
}
