/**
 * @fileoverview Loading skeleton component for search results.
 *
 * Provides consistent loading states across flight, hotel, and activity
 * result views with configurable skeleton layouts.
 */

"use client";

import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/** Skeleton variant for different result types. */
export type SkeletonVariant = "flight" | "hotel" | "activity";

/** Props for the ResultsLoadingSkeleton component. */
export interface ResultsLoadingSkeletonProps {
  /** Number of skeleton items to display. */
  count?: number;
  /** Skeleton layout variant. */
  variant: SkeletonVariant;
  /** Additional CSS classes. */
  className?: string;
  /** Test ID for the container. */
  testId?: string;
}

/** Flight skeleton layout. */
function FlightSkeleton() {
  return (
    <Card className="p-6">
      <div className="animate-pulse space-y-4">
        <div className="flex justify-between">
          <div className="space-y-2">
            <div className="h-4 bg-muted rounded w-32" />
            <div className="h-3 bg-muted rounded w-24" />
          </div>
          <div className="h-6 bg-muted rounded w-20" />
        </div>
        <div className="h-2 bg-muted rounded" />
      </div>
    </Card>
  );
}

/** Hotel skeleton layout. */
function HotelSkeleton() {
  return (
    <Card className="p-6">
      <div className="animate-pulse flex gap-4">
        <div className="w-48 h-32 bg-muted rounded-lg" />
        <div className="flex-1 space-y-4">
          <div className="space-y-2">
            <div className="h-4 bg-muted rounded w-3/4" />
            <div className="h-3 bg-muted rounded w-1/2" />
          </div>
          <div className="h-2 bg-muted rounded" />
          <div className="flex gap-2">
            <div className="h-6 bg-muted rounded w-16" />
            <div className="h-6 bg-muted rounded w-16" />
          </div>
        </div>
        <div className="w-32 space-y-2">
          <div className="h-6 bg-muted rounded" />
          <div className="h-8 bg-muted rounded" />
        </div>
      </div>
    </Card>
  );
}

/** Activity skeleton layout. */
function ActivitySkeleton() {
  return (
    <Card className="overflow-hidden">
      <div className="animate-pulse">
        <div className="h-48 bg-muted" />
        <CardContent className="p-4 space-y-3">
          <div className="h-5 bg-muted rounded w-3/4" />
          <div className="h-4 bg-muted rounded w-1/2" />
          <div className="h-4 bg-muted rounded w-1/4" />
        </CardContent>
      </div>
    </Card>
  );
}

/** Map of variant to skeleton component. */
const SKELETON_MAP: Record<SkeletonVariant, () => ReactNode> = {
  activity: ActivitySkeleton,
  flight: FlightSkeleton,
  hotel: HotelSkeleton,
};

/**
 * Loading skeleton component for search results.
 *
 * Displays placeholder skeletons while results are loading,
 * with variant-specific layouts for flights, hotels, and activities.
 *
 * @example
 * ```tsx
 * <ResultsLoadingSkeleton
 *   variant="flight"
 *   count={3}
 *   testId="flight-results-loading"
 * />
 * ```
 */
export function ResultsLoadingSkeleton({
  count = 3,
  variant,
  className,
  testId,
}: ResultsLoadingSkeletonProps) {
  const SkeletonComponent = SKELETON_MAP[variant];
  const isGridLayout = variant === "activity";

  return (
    <div
      className={cn(
        isGridLayout
          ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          : "space-y-4",
        className
      )}
      data-testid={testId}
    >
      {Array.from({ length: count }, (_, i) => (
        <SkeletonComponent key={`${variant}-skeleton-${i + 1}`} />
      ))}
    </div>
  );
}
