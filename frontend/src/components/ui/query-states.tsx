"use client";

import { type UseQueryResult, type UseMutationResult } from "@tanstack/react-query";
import { ReactNode } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { InlineQueryError } from "@/components/providers/query-error-boundary";
import { Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface QueryStateHandlerProps<TData = unknown, TError = Error> {
  query: UseQueryResult<TData, TError>;
  children: (data: TData) => ReactNode;
  loadingFallback?: ReactNode;
  errorFallback?: (error: TError, retry: () => void) => ReactNode;
  emptyFallback?: ReactNode;
  isEmpty?: (data: TData) => boolean;
}

/**
 * Comprehensive query state handler with loading, error, and empty states
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
    return <InlineQueryError error={error as Error} retry={refetch} />;
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
 * Mutation state handler for form submissions and actions
 */
interface MutationStateHandlerProps<
  TData = unknown,
  TError = Error,
  TVariables = unknown,
> {
  mutation: UseMutationResult<TData, TError, TVariables>;
  children: ReactNode;
  showSuccess?: boolean;
  successMessage?: string;
  successDuration?: number;
}

export function MutationStateHandler<
  TData = unknown,
  TError = Error,
  TVariables = unknown,
>({
  mutation,
  children,
  showSuccess = false,
  successMessage = "Success!",
  successDuration = 3000,
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
      {isError && error && <InlineQueryError error={error as Error} />}

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
 * Default loading skeleton
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
 * Default empty state
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
 * Card-based loading skeleton for lists
 */
export function CardLoadingSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="border rounded-lg p-4 space-y-3">
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
 * Table loading skeleton
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
          <Skeleton key={index} className="h-4" />
        ))}
      </div>

      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="grid grid-cols-4 gap-4 p-2">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-4" />
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * Suspense-like query wrapper with enhanced loading states
 */
interface SuspenseQueryProps<TData = unknown, TError = Error> {
  query: UseQueryResult<TData, TError>;
  children: (data: TData) => ReactNode;
  fallback?: ReactNode;
  placeholderData?: TData;
}

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
 * Infinite query state handler
 */
interface InfiniteQueryStateHandlerProps<TData = unknown> {
  query: any; // UseInfiniteQueryResult type is complex
  children: (data: TData[]) => ReactNode;
  loadingFallback?: ReactNode;
  emptyFallback?: ReactNode;
  LoadMoreButton?: ReactNode;
}

export function InfiniteQueryStateHandler<TData = unknown>({
  query,
  children,
  loadingFallback,
  emptyFallback,
  LoadMoreButton,
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

  if (isPending) {
    return <>{loadingFallback || <DefaultLoadingSkeleton />}</>;
  }

  if (isError && error) {
    return <InlineQueryError error={error as Error} retry={refetch} />;
  }

  const allData = data?.pages?.flatMap((page: any) => page.data || page) || [];

  if (allData.length === 0) {
    return <>{emptyFallback || <DefaultEmptyState />}</>;
  }

  return (
    <div className="space-y-4">
      {children(allData)}

      {/* Load more button */}
      {hasNextPage && (
        <div className="text-center">
          {LoadMoreButton || (
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
