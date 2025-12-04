/**
 * @fileoverview Activity results grid with filters, sorting controls, and view modes.
 */

"use client";

import type { Activity } from "@schemas/search";
import {
  ArrowUpDownIcon,
  FilterIcon,
  Grid3X3Icon,
  ListIcon,
  MapPinIcon,
  RefreshCwIcon,
} from "lucide-react";
import { useOptimistic, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/components/ui/use-toast";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { cn } from "@/lib/utils";
import { ActivityCard } from "./activity-card";

interface ActivityResultsProps {
  results: Activity[];
  loading?: boolean;
  onSelect: (activity: Activity) => Promise<void>;
  onCompare?: (activities: Activity[]) => void;
  onOpenFilters?: () => void;
  onLoadMore?: () => Promise<void>;
  hasMore?: boolean;
  className?: string;
}

/** Activity results component */
export function ActivityResults({
  results,
  loading = false,
  onSelect,
  onCompare,
  onOpenFilters,
  onLoadMore,
  hasMore = false,
  className,
}: ActivityResultsProps) {
  const [isPending, startTransition] = useTransition();
  const [viewMode, setViewMode] = useState<"list" | "grid">("grid");
  const [sortBy, setSortBy] = useState<"price" | "rating" | "duration">("rating");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [selectedForComparison, setSelectedForComparison] = useState<Set<string>>(
    new Set()
  );
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const { toast } = useToast();

  // Optimistic selection state
  const [optimisticSelecting, setOptimisticSelecting] = useOptimistic(
    "",
    (_state, activityId: string) => activityId
  );

  /** Handle activity selection */
  const handleActivitySelect = (activity: Activity) => {
    startTransition(async () => {
      setOptimisticSelecting(activity.id);
      try {
        await onSelect(activity);
      } catch (error) {
        recordClientErrorOnActiveSpan(
          error instanceof Error ? error : new Error(String(error)),
          {
            action: "handleActivitySelect",
            activityId: activity.id,
            context: "ActivityResults",
          }
        );
      }
    });
  };

  /** Handle activity comparison */
  const handleCompare = (activity: Activity) => {
    setSelectedForComparison((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(activity.id)) {
        newSet.delete(activity.id);
      } else if (newSet.size < 3) {
        newSet.add(activity.id);
      }
      return newSet;
    });
  };

  /** Sort activities by price, rating, or duration */
  const handleSort = (field: "price" | "rating" | "duration") => {
    if (sortBy === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortDirection(field === "price" ? "asc" : "desc");
    }
  };

  /** Load more activities */
  const handleLoadMore = async () => {
    if (!onLoadMore) return;
    setIsLoadingMore(true);
    try {
      await onLoadMore();
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      recordClientErrorOnActiveSpan(err, {
        action: "handleLoadMore",
        context: "ActivityResults",
      });
      toast({
        description:
          err.message ||
          "An unexpected error occurred while loading activities. Please try again.",
        title: "Unable to load more activities",
        variant: "destructive",
      });
    } finally {
      setIsLoadingMore(false);
    }
  };

  /** Sort activities by price, rating, or duration */
  const sortedResults = [...results].sort((a, b) => {
    const multiplier = sortDirection === "asc" ? 1 : -1;
    switch (sortBy) {
      case "price":
        return (a.price - b.price) * multiplier;
      case "rating":
        return (a.rating - b.rating) * multiplier;
      case "duration":
        return (a.duration - b.duration) * multiplier;
      default:
        return 0;
    }
  });

  /** Render loading state */
  if (loading) {
    return (
      <div
        className={cn(
          viewMode === "grid"
            ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            : "space-y-4"
        )}
      >
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Card key={`activity-skeleton-${i}`} className="overflow-hidden">
            <div className="animate-pulse">
              <div className="h-48 bg-muted" />
              <CardContent className="p-4 space-y-3">
                <div className="h-5 bg-muted rounded w-3/4" />
                <div className="h-4 bg-muted rounded w-1/2" />
                <div className="h-4 bg-muted rounded w-1/4" />
              </CardContent>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  /** Render no activities found state */
  if (results.length === 0) {
    return (
      <Card className="p-12 text-center">
        <MapPinIcon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No activities found</h3>
        <p className="text-muted-foreground mb-4">
          Try adjusting your search criteria or dates
        </p>
        <Button variant="outline">
          <RefreshCwIcon className="h-4 w-4 mr-2" />
          Modify Search
        </Button>
      </Card>
    );
  }

  /** Render activity results */
  return (
    <div className={cn("space-y-4", className)}>
      {/* Search Controls */}
      <Card className="p-4" data-testid="activity-results-controls">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">
              {results.length} activities found
            </span>
            <Separator orientation="vertical" className="h-4" />
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={onOpenFilters}
                disabled={!onOpenFilters}
                aria-label="Open activity filters"
                title={onOpenFilters ? undefined : "Filters unavailable"}
              >
                <FilterIcon className="h-4 w-4 mr-2" />
                Filters
              </Button>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort("price")}
                  className={cn(sortBy === "price" && "bg-accent")}
                >
                  Price
                  {sortBy === "price" && <ArrowUpDownIcon className="h-3 w-3 ml-1" />}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort("rating")}
                  className={cn(sortBy === "rating" && "bg-accent")}
                >
                  Rating
                  {sortBy === "rating" && <ArrowUpDownIcon className="h-3 w-3 ml-1" />}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort("duration")}
                  className={cn(sortBy === "duration" && "bg-accent")}
                >
                  Duration
                  {sortBy === "duration" && (
                    <ArrowUpDownIcon className="h-3 w-3 ml-1" />
                  )}
                </Button>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant={viewMode === "list" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("list")}
            >
              <ListIcon className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === "grid" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("grid")}
            >
              <Grid3X3Icon className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {selectedForComparison.size > 0 && onCompare && (
          <div className="mt-3 pt-3 border-t">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {selectedForComparison.size} activit
                {selectedForComparison.size > 1 ? "ies" : "y"} selected for comparison
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setSelectedForComparison(new Set())}
                >
                  Clear
                </Button>
                <Button
                  size="sm"
                  onClick={() =>
                    onCompare(results.filter((a) => selectedForComparison.has(a.id)))
                  }
                  disabled={selectedForComparison.size < 2}
                >
                  Compare ({selectedForComparison.size})
                </Button>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Activity Results */}
      <div
        className={cn(
          viewMode === "grid"
            ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            : "space-y-4"
        )}
      >
        {sortedResults.map((activity) => (
          <div
            key={activity.id}
            className={cn(
              "relative",
              selectedForComparison.has(activity.id) &&
                "ring-2 ring-blue-500 rounded-lg",
              optimisticSelecting === activity.id && "opacity-75"
            )}
          >
            <ActivityCard
              activity={activity}
              onSelect={() => handleActivitySelect(activity)}
              onCompare={onCompare ? () => handleCompare(activity) : undefined}
            />
            {selectedForComparison.has(activity.id) && (
              <Badge className="absolute top-2 right-2 bg-blue-500">Selected</Badge>
            )}
          </div>
        ))}
      </div>

      {/* Load More */}
      {hasMore && onLoadMore && (
        <Card className="p-4 text-center">
          <Button
            variant="outline"
            disabled={isPending || isLoadingMore}
            onClick={handleLoadMore}
          >
            {isLoadingMore ? "Loading more..." : "Load More Activities"}
          </Button>
        </Card>
      )}
    </div>
  );
}
