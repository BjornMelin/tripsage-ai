import type {
  QueryClient,
  UseInfiniteQueryResult,
  UseMutationResult,
  UseQueryResult,
} from "@tanstack/react-query";

// MutationContext type matching the one from use-api-query.ts
interface MutationContext<TVariables = unknown> {
  previousData?: unknown;
  optimisticData?: unknown;
  variables?: TVariables;
}
/**
 * React Query mock utilities for testing React Query v5
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

// Helper to manually trigger query lifecycle
export interface QueryController<TData = unknown, TError = Error> {
  triggerLoading: () => void;
  triggerSuccess: (data: TData) => void;
  triggerError: (error: TError) => void;
  triggerRefetch: () => void;
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
    submittedAt: 0,
    promise: Promise.resolve({
      data: currentData,
      error: currentError,
    }),
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
  TContext = MutationContext<TVariables>,
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

/**
 * Create a controlled mock query for testing
 */
export function createControlledQuery<TData = unknown, TError = Error>(): {
  query: UseQueryResult<TData, TError>;
  controller: QueryController<TData, TError>;
} {
  let currentData: TData | undefined;
  let currentError: TError | null = null;
  let isPending = true;
  let isError = false;
  let isSuccess = false;
  let isLoading = true;
  let isFetching = false;

  const refetch = vi.fn(() =>
    Promise.resolve({
      data: currentData,
      error: currentError,
      status: isPending ? "pending" : isError ? "error" : "success",
      fetchStatus: isFetching ? "fetching" : "idle",
      isPending,
      isError,
      isSuccess,
      isLoading,
      isFetching,
      isLoadingError: false,
      isRefetchError: false,
      isFetched: !isPending,
      isFetchedAfterMount: !isPending,
      isRefetching: false,
      isStale: false,
      isPlaceholderData: false,
      failureCount: 0,
      failureReason: currentError,
      errorUpdatedAt: 0,
      dataUpdatedAt: Date.now(),
      errorUpdateCount: 0,
      isInitialLoading: isPending,
      isPaused: false,
      refetch,
      promise: Promise.resolve({
        data: currentData,
        error: currentError,
      } as any),
    } as UseQueryResult<TData, TError>)
  );

  const query = {
    data: currentData,
    error: currentError,
    isError,
    isPending,
    isLoading,
    isSuccess,
    isFetching,
    isLoadingError: false,
    isRefetchError: false,
    isFetched: !isPending,
    isFetchedAfterMount: !isPending,
    isRefetching: false,
    isStale: false,
    isPlaceholderData: false,
    status: isPending ? "pending" : isError ? "error" : "success",
    fetchStatus: isFetching ? "fetching" : "idle",
    refetch,
    failureCount: 0,
    failureReason: currentError,
    errorUpdatedAt: 0,
    dataUpdatedAt: Date.now(),
    errorUpdateCount: 0,
    isInitialLoading: isPending,
    isPaused: false,
    promise: Promise.resolve({
      data: currentData,
      error: currentError,
    } as any),
  } as UseQueryResult<TData, TError>;

  const controller: QueryController<TData, TError> = {
    triggerLoading: () => {
      isPending = true;
      isLoading = true;
      isFetching = true;
      isError = false;
      isSuccess = false;
      currentError = null;

      Object.assign(query, {
        isPending,
        isLoading,
        isFetching,
        isError,
        isSuccess,
        error: currentError,
        status: "pending",
        fetchStatus: "fetching",
      });
    },
    triggerSuccess: (data: TData) => {
      currentData = data;
      currentError = null;
      isPending = false;
      isLoading = false;
      isFetching = false;
      isError = false;
      isSuccess = true;

      Object.assign(query, {
        data: currentData,
        error: currentError,
        isPending,
        isLoading,
        isFetching,
        isError,
        isSuccess,
        status: "success",
        fetchStatus: "idle",
        isFetched: true,
        isFetchedAfterMount: true,
        dataUpdatedAt: Date.now(),
      });
    },
    triggerError: (error: TError) => {
      currentData = undefined;
      currentError = error;
      isPending = false;
      isLoading = false;
      isFetching = false;
      isError = true;
      isSuccess = false;

      Object.assign(query, {
        data: currentData,
        error: currentError,
        isPending,
        isLoading,
        isFetching,
        isError,
        isSuccess,
        status: "error",
        fetchStatus: "idle",
        failureReason: error,
        errorUpdatedAt: Date.now(),
      });
    },
    triggerRefetch: () => {
      isFetching = true;
      Object.assign(query, {
        isFetching,
        fetchStatus: "fetching",
      });
    },
    reset: () => {
      currentData = undefined;
      currentError = null;
      isPending = true;
      isLoading = true;
      isFetching = false;
      isError = false;
      isSuccess = false;

      Object.assign(query, {
        data: undefined,
        error: null,
        isPending: true,
        isLoading: true,
        isFetching: false,
        isError: false,
        isSuccess: false,
        status: "pending",
        fetchStatus: "idle",
      });
    },
  };

  return { query, controller };
}

/**
 * Create a mock QueryClient for testing
 */
export function createMockQueryClient(): QueryClient {
  const mockClient = {
    getQueryData: vi.fn(),
    setQueryData: vi.fn(),
    invalidateQueries: vi.fn(),
    removeQueries: vi.fn(),
    prefetchQuery: vi.fn(),
    fetchQuery: vi.fn(),
    cancelQueries: vi.fn(),
    resetQueries: vi.fn(),
    clear: vi.fn(),
    mount: vi.fn(),
    unmount: vi.fn(),
    isFetching: vi.fn(() => 0),
    isMutating: vi.fn(() => 0),
    getDefaultOptions: vi.fn(() => ({})),
    setDefaultOptions: vi.fn(),
    setQueryDefaults: vi.fn(),
    getQueryDefaults: vi.fn(),
    setMutationDefaults: vi.fn(),
    getMutationDefaults: vi.fn(),
    getQueryCache: vi.fn(),
    getMutationCache: vi.fn(),
    resumePausedMutations: vi.fn(),
  } as unknown as QueryClient;

  return mockClient;
}

/**
 * Create a mock infinite query
 */
export function createControlledInfiniteQuery<TData = unknown, TError = Error>(): {
  query: UseInfiniteQueryResult<any, TError>;
  controller: {
    triggerLoading: () => void;
    triggerSuccess: (pages: TData[][]) => void;
    triggerError: (error: TError) => void;
    triggerFetchNextPage: () => void;
    reset: () => void;
  };
} {
  let pages: TData[][] = [];
  let currentError: TError | null = null;
  let isPending = true;
  let isError = false;
  let isSuccess = false;
  let hasNextPage = false;
  let isFetchingNextPage = false;

  const fetchNextPage = vi.fn();
  const fetchPreviousPage = vi.fn();

  const query = {
    data: pages.length > 0 ? { pages, pageParams: [] } : undefined,
    error: currentError,
    isError,
    isPending,
    isLoading: isPending,
    isSuccess,
    isFetching: isPending,
    isFetchingNextPage,
    isFetchingPreviousPage: false,
    hasNextPage,
    hasPreviousPage: false,
    fetchNextPage,
    fetchPreviousPage,
    isLoadingError: false,
    isRefetchError: false,
    isFetched: !isPending,
    isFetchedAfterMount: !isPending,
    isRefetching: false,
    isStale: false,
    isPlaceholderData: false,
    status: isPending ? "pending" : isError ? "error" : "success",
    fetchStatus: isPending ? "fetching" : "idle",
    refetch: vi.fn(),
    failureCount: 0,
    failureReason: currentError,
    errorUpdatedAt: 0,
    dataUpdatedAt: Date.now(),
    isFetchNextPageError: false,
    isFetchPreviousPageError: false,
    errorUpdateCount: 0,
    isInitialLoading: isPending,
    isPaused: false,
    promise: Promise.resolve({
      data: pages.length > 0 ? { pages, pageParams: [] } : undefined,
      error: currentError,
    }),
  } as UseInfiniteQueryResult<any, TError>;

  const controller = {
    triggerLoading: () => {
      isPending = true;
      isError = false;
      isSuccess = false;
      currentError = null;
      Object.assign(query, {
        isPending,
        isLoading: true,
        isFetching: true,
        isError,
        isSuccess,
        error: currentError,
        status: "pending",
      });
    },
    triggerSuccess: (newPages: TData[][]) => {
      pages = newPages;
      currentError = null;
      isPending = false;
      isError = false;
      isSuccess = true;
      hasNextPage = true; // Assume there's more data

      Object.assign(query, {
        data: { pages, pageParams: [] },
        error: currentError,
        isPending,
        isLoading: false,
        isFetching: false,
        isError,
        isSuccess,
        hasNextPage,
        status: "success",
      });
    },
    triggerError: (error: TError) => {
      currentError = error;
      isPending = false;
      isError = true;
      isSuccess = false;

      Object.assign(query, {
        error: currentError,
        isPending,
        isLoading: false,
        isFetching: false,
        isError,
        isSuccess,
        status: "error",
      });
    },
    triggerFetchNextPage: () => {
      isFetchingNextPage = true;
      Object.assign(query, {
        isFetchingNextPage,
      });
    },
    reset: () => {
      pages = [];
      currentError = null;
      isPending = true;
      isError = false;
      isSuccess = false;
      hasNextPage = false;
      isFetchingNextPage = false;

      Object.assign(query, {
        data: undefined,
        error: null,
        isPending: true,
        isLoading: true,
        isFetching: false,
        isError: false,
        isSuccess: false,
        hasNextPage: false,
        isFetchingNextPage: false,
        status: "pending",
      });
    },
  };

  return { query, controller };
}

/**
 * Mock useQuery hook with enhanced v5 features
 */
export function mockUseQuery<TData = unknown, TError = Error>(
  initialData?: TData,
  initialError?: TError
) {
  const { query, controller } = createControlledQuery<TData, TError>();

  if (initialData) {
    controller.triggerSuccess(initialData);
  }

  if (initialError) {
    controller.triggerError(initialError);
  }

  return { query, controller };
}

/**
 * Mock useInfiniteQuery hook
 */
export function mockUseInfiniteQuery<TData = unknown, TError = Error>(
  initialPages?: TData[][]
) {
  const { query, controller } = createControlledInfiniteQuery<TData, TError>();

  if (initialPages) {
    controller.triggerSuccess(initialPages);
  }

  return { query, controller };
}

/**
 * Utility to create query test wrapper
 */
export function createQueryTestWrapper(queryClient?: QueryClient) {
  const _client = queryClient || createMockQueryClient();

  return ({ children }: { children: React.ReactNode }) => (
    <div data-testid="query-wrapper">{children}</div>
  );
}

// Helper to wait for React updates
export async function waitForReactUpdate() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

/**
 * Helper to wait for query state changes
 */
export async function waitForQueryUpdate(controller: QueryController<any, any>) {
  await waitForReactUpdate();
  return controller;
}

/**
 * Helper to simulate network delay in tests
 */
export function simulateNetworkDelay(ms = 100) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
