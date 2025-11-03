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
      mutations: { retry: false },
      queries: { gcTime: 0, retry: false, staleTime: 0 },
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
    context: undefined as TContext,
    data: state.data,
    error: state.error,
    failureCount: 0,
    failureReason: null,
    isError: false,
    isIdle: true,
    isLoadingError: false,
    isPaused: false,
    isPending: false,
    isRefetchError: false,
    isSuccess: false,
    mutate,
    mutateAsync,
    promise: Promise.resolve({ data: state.data, error: state.error }),
    reset,
    status: "idle",
    submittedAt: Date.now(),
    variables: state.variables,
  } as UseMutationResult<TData, TError, TVariables, TContext>;

  const controller: MutationController<TData, TError, TVariables> = {
    reset: () => {
      reset();
      Object.assign(mutation, {
        data: undefined,
        error: null,
        isError: false,
        isIdle: true,
        isPending: false,
        isSuccess: false,
        status: "idle" as const,
        variables: undefined,
      });
    },
    triggerError: (error: TError) => {
      state.data = undefined;
      state.error = error;
      state.status = "error";
      Object.assign(mutation, {
        data: undefined,
        error,
        failureCount: 1,
        failureReason: error,
        isError: true,
        isIdle: false,
        isPending: false,
        isSuccess: false,
        status: "error" as const,
      });
    },
    triggerMutate: (variables: TVariables) => {
      mutate(variables);
      Object.assign(mutation, {
        error: null,
        isError: false,
        isIdle: false,
        isPending: true,
        isSuccess: false,
        status: "pending" as const,
        variables,
      });
    },
    triggerSuccess: (data: TData) => {
      state.data = data;
      state.error = null;
      state.status = "success";
      Object.assign(mutation, {
        data,
        error: null,
        isError: false,
        isIdle: false,
        isPending: false,
        isSuccess: true,
        status: "success" as const,
      });
    },
  };

  return { controller, mutation };
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
    reset: () => {
      state.data = undefined;
      state.error = null;
      state.status = "pending";
      Object.assign(query, {
        data: undefined,
        error: null,
        isError: false,
        isFetched: false,
        isFetchedAfterMount: false,
        isFetching: false,
        isLoading: true,
        isLoadingError: false,
        isPending: true,
        isSuccess: false,
        status: "pending" as const,
      });
    },
    triggerError: (error: TError) => {
      state.data = undefined;
      state.error = error;
      state.status = "error";
      Object.assign(query, {
        data: undefined,
        error,
        isError: true,
        isFetching: false,
        isLoading: false,
        isLoadingError: true,
        isPending: false,
        isSuccess: false,
        status: "error" as const,
      });
    },
    triggerLoading: () => {
      state.status = "pending";
      Object.assign(query, {
        isError: false,
        isFetching: true,
        isLoading: true,
        isPending: true,
        isSuccess: false,
        status: "pending" as const,
      });
    },
    triggerRefetch: () => {
      void query.refetch();
    },
    triggerSuccess: (data: TData) => {
      state.data = data;
      state.error = null;
      state.status = "success";
      Object.assign(query, {
        data,
        error: null,
        isError: false,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isLoading: false,
        isPending: false,
        isSuccess: true,
        status: "success" as const,
      });
    },
  };

  return { controller, query };
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

  return { controller, query };
}
