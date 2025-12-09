/**
 * @fileoverview Hotel results grid with filters, badges, and sorting controls.
 */

"use client";

import type { HotelResult } from "@schemas/search";
import {
  ArrowUpDownIcon,
  Building2Icon,
  FilterIcon,
  Grid3X3Icon,
  ListIcon,
  MapIcon,
  RefreshCwIcon,
} from "lucide-react";
import { useMemo, useOptimistic, useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { type Coordinates, calculateDistanceKm } from "@/lib/geo";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { cn } from "@/lib/utils";
import { HotelCard } from "../cards/hotel-card";

/** Hotel results props */
interface HotelResultsProps {
  results: HotelResult[];
  loading?: boolean;
  onSelect: (hotel: HotelResult) => Promise<void>;
  onSaveToWishlist: (hotelId: string) => void;
  className?: string;
  showMap?: boolean;
  /** Search center coordinates for distance calculation. */
  searchCenter?: Coordinates;
}

/** Hotel results component */
export function HotelResults({
  results,
  loading = false,
  onSelect,
  onSaveToWishlist,
  className,
  showMap = true,
  searchCenter,
}: HotelResultsProps) {
  const [isPending, startTransition] = useTransition();
  const [viewMode, setViewMode] = useState<"list" | "grid" | "map">("list");
  const [savedHotels, setSavedHotels] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<"ai" | "price" | "rating" | "distance">("ai");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  // Optimistic selection state
  const [optimisticSelecting, setOptimisticSelecting] = useOptimistic(
    "",
    (_state, hotelId: string) => hotelId
  );

  /** Handle hotel selection */
  const handleHotelSelect = (hotel: HotelResult) => {
    startTransition(async () => {
      setOptimisticSelecting(hotel.id);
      try {
        await onSelect(hotel);
      } catch (error) {
        recordClientErrorOnActiveSpan(
          error instanceof Error ? error : new Error(String(error)),
          {
            action: "handleHotelSelect",
            context: "HotelResults",
            hotelId: hotel.id,
          }
        );
      } finally {
        setOptimisticSelecting("");
      }
    });
  };

  /** Toggle hotel for comparison */
  const toggleWishlist = (hotelId: string) => {
    setSavedHotels((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(hotelId)) {
        newSet.delete(hotelId);
      } else {
        newSet.add(hotelId);
      }
      onSaveToWishlist(hotelId);
      return newSet;
    });
  };

  /** Check if distance sorting is available. */
  const canSortByDistance = searchCenter !== undefined;

  const sortedResults = useMemo(() => {
    /** Calculate distance from search center for a hotel. */
    const getDistance = (hotel: HotelResult): number =>
      searchCenter && hotel.location.coordinates
        ? calculateDistanceKm(searchCenter, hotel.location.coordinates)
        : Number.MAX_VALUE;

    const clones = [...results];
    const direction = sortDirection === "asc" ? 1 : -1;
    const comparator = (first: HotelResult, second: HotelResult) => {
      switch (sortBy) {
        case "price":
          return direction * (first.pricing.totalPrice - second.pricing.totalPrice);
        case "rating":
          return direction * ((first.starRating ?? 0) - (second.starRating ?? 0));
        case "distance":
          return direction * (getDistance(first) - getDistance(second));
        default:
          return (
            direction *
            ((first.ai?.recommendation ?? 0) - (second.ai?.recommendation ?? 0))
          );
      }
    };
    return clones.sort(comparator);
  }, [results, sortBy, sortDirection, searchCenter]);

  const cycleSort = () => {
    const order: Array<typeof sortBy> = canSortByDistance
      ? ["ai", "price", "rating", "distance"]
      : ["ai", "price", "rating"];
    const currentIndex = order.indexOf(sortBy);
    const next = order[(currentIndex + 1) % order.length];
    setSortBy(next);
  };

  const toggleDirection = () => {
    setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
  };

  const formatSortLabel = (sort: typeof sortBy) => {
    const labels: Record<typeof sortBy, string> = {
      ai: "AI Recommended",
      distance: "Distance",
      price: "Price",
      rating: "Rating",
    };
    return labels[sort];
  };

  const formatDirectionLabel = (direction: typeof sortDirection) =>
    direction === "asc" ? "↑" : "↓";

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={`hotel-skeleton-${i}`} className="p-6">
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
        ))}
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <Card className="p-12 text-center">
        <Building2Icon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No hotels found</h3>
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

  return (
    <div className={cn("space-y-4", className)}>
      {/* Search Controls */}
      <Card className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">{results.length} hotels found</span>
            <Separator orientation="vertical" className="h-4" />
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm">
                <FilterIcon className="h-4 w-4 mr-2" />
                Filters
              </Button>
              <Button variant="ghost" size="sm" onClick={toggleDirection}>
                <ArrowUpDownIcon className="h-4 w-4 mr-2" />
                Sort: {formatSortLabel(sortBy)} ({formatDirectionLabel(sortDirection)})
              </Button>
              <Button variant="outline" size="sm" onClick={cycleSort}>
                Change Sort
              </Button>
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
            {showMap && (
              <Button
                variant={viewMode === "map" ? "default" : "outline"}
                size="sm"
                onClick={() => setViewMode("map")}
              >
                <MapIcon className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Hotel Results */}
      <div
        className={cn(
          viewMode === "grid"
            ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
            : "space-y-4"
        )}
      >
        {sortedResults.map((hotel) => (
          <HotelCard
            key={hotel.id}
            hotel={hotel}
            viewMode={viewMode}
            isSaved={savedHotels.has(hotel.id)}
            isOptimisticSelecting={optimisticSelecting === hotel.id}
            isPending={isPending}
            onSelect={() => handleHotelSelect(hotel)}
            onToggleWishlist={() => toggleWishlist(hotel.id)}
          />
        ))}
      </div>

      {/* Load More */}
      {results.length > 0 && (
        <Card className="p-4 text-center">
          <Button variant="outline">Load More Hotels</Button>
        </Card>
      )}
    </div>
  );
}
