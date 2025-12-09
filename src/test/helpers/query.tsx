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
import { createMockUseQueryResult } from "./mock";

type MutationState<T, E, V> = {
  data: T | undefined;
  error: E | null;
  status: "idle" | "pending" | "success" | "error";
  variables: V | undefined;
};

type QueryState<T, E> = {
  data: T | undefined;
  error: E | null;
  status: "pending" | "success" | "error";
};

/**
 * Controller that allows tests to drive mutation state transitions manually.
 */
export interface MutationController<T, E, V> {
  /** Set the mutation into a pending/loading state. */
  triggerMutate: (variables: V) => void;
  /** Resolve the mutation with data. */
  triggerSuccess: (data: T) => void;
  /** Reject the mutation with an error. */
  triggerError: (error: E) => void;
  /** Reset the mutation back to the idle state. */
  reset: () => void;
}

/**
 * Controller that allows tests to drive query state transitions manually.
 */
export interface QueryController<T, E> {
  /** Set the query to loading/pending. */
  triggerLoading: () => void;
  /** Resolve the query with data. */
  triggerSuccess: (data: T) => void;
  /** Reject the query with an error. */
  triggerError: (error: E) => void;
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
export function createControlledMutation<T, E = Error, V = void, C = unknown>() {
  const state: MutationState<T, E, V> = {
    data: undefined,
    error: null,
    status: "idle",
    variables: undefined,
  };

  const mutate = vi.fn((variables: V, _options?: MutateOptions<T, E, V, C>) => {
    state.variables = variables;
    state.status = "pending";
    state.error = null;
  });

  const mutateAsync = vi.fn((variables: V, options?: MutateOptions<T, E, V, C>) => {
    mutate(variables, options);
    return state.data as T;
  });

  const reset = vi.fn(() => {
    state.data = undefined;
    state.error = null;
    state.status = "idle";
    state.variables = undefined;
  });

  const mutation: UseMutationResult<T, E, V, C> = {
    context: undefined as C,
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
  } as UseMutationResult<T, E, V, C>;

  const controller: MutationController<T, E, V> = {
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
    triggerError: (error: E) => {
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
    triggerMutate: (variables: V) => {
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
    triggerSuccess: (data: T) => {
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
export function mockUseMutation<T, E, V, C = unknown>() {
  return createControlledMutation<T, E, V, C>();
}

/**
 * Build a controlled query result together with a controller.
 * @returns A tuple containing the query result and controller.
 */
export function createControlledQuery<T, E = Error>() {
  const state: QueryState<T, E> = {
    data: undefined,
    error: null,
    status: "pending",
  };

  const query = createMockUseQueryResult<T, E>(null, null, true, false);
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

  const controller: QueryController<T, E> = {
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
    triggerError: (error: E) => {
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
      query.refetch();
    },
    triggerSuccess: (data: T) => {
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
export function mockUseQuery<T, E>(initialData?: T, initialError?: E) {
  const { query, controller } = createControlledQuery<T, E>();

  if (initialData !== undefined) {
    controller.triggerSuccess(initialData);
  }

  if (initialError !== undefined) {
    controller.triggerError(initialError);
  }

  return { controller, query };
}
