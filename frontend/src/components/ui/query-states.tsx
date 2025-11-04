/**
 * @fileoverview React Query state management components.
 * Provides reusable components for handling loading, error, and empty states
 * in React Query operations.
 */

"use client";

import type {
  UseInfiniteQueryResult,
  UseMutationResult,
  UseQueryResult,
} from "@tanstack/react-query";
import { AlertCircle, Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { InlineQueryError } from "@/components/providers/query-error-boundary";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Props for the QueryStateHandler component.
 */
interface QueryStateHandlerProps<TData = unknown, TError = Error> {
  /** The React Query result object to handle. */
  query: UseQueryResult<TData, TError>;
  /** Render function that receives the query data when available. */
  children: (data: TData) => ReactNode;
  /** Optional fallback component to show during loading state. */
  loadingFallback?: ReactNode;
  /** Optional error fallback that receives error and retry function. */
  errorFallback?: (error: TError, retry: () => void) => ReactNode;
  /** Optional fallback component to show when data is empty. */
  emptyFallback?: ReactNode;
  /** Optional function to determine if data should be considered empty. */
  isEmpty?: (data: TData) => boolean;
}

/**
 * Query state handler component that manages loading, error, and empty states.
 *
 * @param query - The React Query result object to handle.
 * @param children - Render function for successful data state.
 * @param loadingFallback - Optional loading state fallback.
 * @param errorFallback - Optional error state fallback.
 * @param emptyFallback - Optional empty state fallback.
 * @param isEmpty - Optional function to check if data is empty.
 * @returns The appropriate component based on query state.
 */
export function QueryStateHandler<TData = unknown, TError = Error>({
  query,
  children,
  loadingFallback,
  errorFallback,
  emptyFallback,
  isEmpty,
}: QueryStateHandlerProps<TData, TError>) {
  const { data, error, isPending, isError, refetch } = query;

  // Loading state
  if (isPending) {
    return <>{loadingFallback || <DefaultLoadingSkeleton />}</>;
  }

  // Error state
  if (isError && error) {
    if (errorFallback) {
      return <>{errorFallback(error, refetch)}</>;
    }
    // Convert error to Error type for InlineQueryError
    const errorObject =
      error instanceof Error
        ? error
        : new Error(typeof error === "string" ? error : "An error occurred");
    return <InlineQueryError error={errorObject} retry={refetch} />;
  }

  // Empty state
  if (data && isEmpty?.(data)) {
    return <>{emptyFallback || <DefaultEmptyState />}</>;
  }

  // Success state
  if (data) {
    return <>{children(data)}</>;
  }

  // Fallback
  return <DefaultLoadingSkeleton />;
}

/**
 * Props for the MutationStateHandler component.
 */
interface MutationStateHandlerProps<
  TData = unknown,
  TError = Error,
  TVariables = unknown,
> {
  /** The React Query mutation result object to handle. */
  mutation: UseMutationResult<TData, TError, TVariables>;
  /** Child components to render alongside mutation state indicators. */
  children: ReactNode;
  /** Whether to show success message after successful mutation. */
  showSuccess?: boolean;
  /** Success message to display. Defaults to "Success!". */
  successMessage?: string;
  /** Duration in milliseconds to show success message. Defaults to 3000. */
  successDuration?: number;
}

/**
 * Mutation state handler component for form submissions and actions.
 *
 * @param mutation - The React Query mutation result object to handle.
 * @param children - Child components to render.
 * @param showSuccess - Whether to show success message. Defaults to false.
 * @param successMessage - Success message text. Defaults to "Success!".
 * @param successDuration - How long to show success message. Defaults to 3000.
 * @returns Component with mutation state indicators.
 */
export function MutationStateHandler<
  TData = unknown,
  TError = Error,
  TVariables = unknown,
>({
  mutation,
  children,
  showSuccess = false,
  successMessage = "Success!",
  successDuration: _successDuration = 3000,
}: MutationStateHandlerProps<TData, TError, TVariables>) {
  const { isPending, isError, isSuccess, error } = mutation;

  return (
    <div className="space-y-3">
      {children}

      {/* Loading state */}
      {isPending && (
        <div className="flex items-center gap-2 text-sm text-blue-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          Processing...
        </div>
      )}

      {/* Error state */}
      {isError && error && (
        <InlineQueryError
          error={
            error instanceof Error
              ? error
              : new Error(typeof error === "string" ? error : "An error occurred")
          }
        />
      )}

      {/* Success state */}
      {showSuccess && isSuccess && (
        <div className="flex items-center gap-2 text-sm text-green-600 p-2 bg-green-50 rounded border border-green-200">
          <AlertCircle className="h-4 w-4" />
          {successMessage}
        </div>
      )}
    </div>
  );
}

/**
 * Default loading skeleton component.
 *
 * @returns A simple skeleton with three lines of varying widths.
 */
function DefaultLoadingSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}

/**
 * Default empty state component.
 *
 * @returns A centered empty state with icon and message.
 */
function DefaultEmptyState() {
  return (
    <div className="text-center py-8 text-gray-500">
      <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
      <p>No data available</p>
    </div>
  );
}

/**
 * Card-based loading skeleton for lists.
 *
 * @param count - Number of skeleton cards to display. Defaults to 3.
 * @returns A list of skeleton cards mimicking content cards.
 */
export function CardLoadingSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={`card-skeleton-${index}`} className="border rounded-lg p-4 space-y-3">
          <Skeleton className="h-5 w-1/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <div className="flex gap-2">
            <Skeleton className="h-8 w-16" />
            <Skeleton className="h-8 w-20" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Table loading skeleton component.
 *
 * @param rows - Number of skeleton rows to display. Defaults to 5.
 * @param columns - Number of skeleton columns to display. Defaults to 4.
 * @returns A skeleton component mimicking a table layout.
 */
export function TableLoadingSkeleton({
  rows = 5,
  columns = 4,
}: {
  rows?: number;
  columns?: number;
}) {
  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="grid grid-cols-4 gap-4 p-2">
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={`table-header-${index}`} className="h-4" />
        ))}
      </div>

      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={`table-row-${rowIndex}`} className="grid grid-cols-4 gap-4 p-2">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={`table-cell-${rowIndex}-${colIndex}`} className="h-4" />
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * Props for the SuspenseQuery component.
 */
interface SuspenseQueryProps<TData = unknown, TError = Error> {
  /** The React Query result object to handle. */
  query: UseQueryResult<TData, TError>;
  /** Render function that receives the query data. */
  children: (data: TData) => ReactNode;
  /** Optional fallback component to show during loading. */
  fallback?: ReactNode;
  /** Optional placeholder data to show while loading. */
  placeholderData?: TData;
}

/**
 * Suspense-like query wrapper with enhanced loading states.
 *
 * @param query - The React Query result object to handle.
 * @param children - Render function for the data.
 * @param fallback - Optional loading fallback component.
 * @param placeholderData - Optional placeholder data for loading state.
 * @returns Component that handles query states with placeholder support.
 */
export function SuspenseQuery<TData = unknown, TError = Error>({
  query,
  children,
  fallback,
  placeholderData,
}: SuspenseQueryProps<TData, TError>) {
  const { data, isPending, isError, error } = query;

  // Show placeholder data while loading if available
  if (isPending && placeholderData) {
    return (
      <div className="relative opacity-75">
        {children(placeholderData)}
        <div className="absolute inset-0 bg-white/50 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
        </div>
      </div>
    );
  }

  if (isPending) {
    return <>{fallback || <DefaultLoadingSkeleton />}</>;
  }

  if (isError) {
    throw error; // Let error boundary handle this
  }

  if (data) {
    return <>{children(data)}</>;
  }

  return <>{fallback || <DefaultLoadingSkeleton />}</>;
}

/**
 * Props for the InfiniteQueryStateHandler component.
 */
interface InfiniteQueryStateHandlerProps<TData = unknown> {
  /** The React Query infinite result object to handle. */
  query: UseInfiniteQueryResult<TData, Error>;
  /** Render function that receives flattened array of all pages data. */
  children: (data: TData[]) => ReactNode;
  /** Optional fallback component to show during loading. */
  loadingFallback?: ReactNode;
  /** Optional fallback component to show when no data is available. */
  emptyFallback?: ReactNode;
  /** Optional custom load more button component. */
  loadMoreButton?: ReactNode;
}

/**
 * Infinite query state handler component.
 *
 * @param query - The React Query infinite result object to handle.
 * @param children - Render function for the flattened data array.
 * @param loadingFallback - Optional loading state fallback.
 * @param emptyFallback - Optional empty state fallback.
 * @param loadMoreButton - Optional custom load more button.
 * @returns Component that handles infinite query states with load more functionality.
 */
export function InfiniteQueryStateHandler<TData = unknown>({
  query,
  children,
  loadingFallback,
  emptyFallback,
  loadMoreButton,
}: InfiniteQueryStateHandlerProps<TData>) {
  const {
    data,
    error,
    isPending,
    isError,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
    refetch,
  } = query;

  // Type assertion for infinite query data structure
  const infiniteData = data as { pages?: TData[] } | undefined;

  if (isPending) {
    return <>{loadingFallback || <DefaultLoadingSkeleton />}</>;
  }

  if (isError && error) {
    // Convert error to Error type for InlineQueryError
    const errorObject =
      error instanceof Error
        ? error
        : new Error(typeof error === "string" ? error : "An error occurred");
    return <InlineQueryError error={errorObject} retry={refetch} />;
  }

  // Extract data from infinite query pages structure
  const allData = (infiniteData?.pages?.flatMap((page) =>
    Array.isArray(page) ? page : (page as { data?: unknown[] })?.data || page
  ) || []) as TData[];

  if (allData.length === 0) {
    return <>{emptyFallback || <DefaultEmptyState />}</>;
  }

  return (
    <div className="space-y-4">
      {children(allData)}

      {/* Load more button */}
      {hasNextPage && (
        <div className="text-center">
          {loadMoreButton || (
            <Button
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              variant="outline"
            >
              {isFetchingNextPage ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Loading...
                </>
              ) : (
                "Load More"
              )}
            </Button>
          )}
        </div>
      )}

      {/* Loading indicator for next page */}
      {isFetchingNextPage && (
        <div className="text-center">
          <Loader2 className="h-5 w-5 animate-spin mx-auto text-blue-500" />
        </div>
      )}
    </div>
  );
}
