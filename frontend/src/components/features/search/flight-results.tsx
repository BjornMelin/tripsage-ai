/**
 * @fileoverview Flight results grid with filters, tags, and sorting controls.
 */

"use client";

import type { FlightResult } from "@schemas/search";
import {
  ArrowUpDownIcon,
  FilterIcon,
  Grid3X3Icon,
  HeartIcon,
  ListIcon,
  MonitorIcon,
  PlaneIcon,
  RefreshCwIcon,
  ShieldIcon,
  StarIcon,
  TrendingUpIcon,
  UtensilsIcon,
  WifiIcon,
  ZapIcon,
} from "lucide-react";
import { useMemo, useOptimistic, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { cn } from "@/lib/utils";
import { formatCurrency, formatDurationMinutes } from "./common/format";

type SortField = "price" | "duration" | "departure" | "emissions";

/** Flight results component props */
interface FlightResultsProps {
  results: FlightResult[];
  loading?: boolean;
  onSelect: (flight: FlightResult) => Promise<void>;
  onCompare: (flights: FlightResult[]) => void;
  className?: string;
}

/** Flight results grid with filters, tags, and sorting controls. */
export function FlightResults({
  results,
  loading = false,
  onSelect,
  onCompare,
  className,
}: FlightResultsProps) {
  const [isPending, startTransition] = useTransition();
  const [selectedForComparison, setSelectedForComparison] = useState<Set<string>>(
    new Set()
  );
  const [sortBy, _setSortBy] = useState<SortField>("price");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");

  // Optimistic selection state
  const [optimisticSelecting, setOptimisticSelecting] = useOptimistic(
    "",
    (_state, flightId: string) => flightId
  );

  const sortedResults = useMemo(() => {
    const cloned = [...results];
    const compare = (first: FlightResult, second: FlightResult) => {
      const direction = sortDirection === "asc" ? 1 : -1;
      switch (sortBy) {
        case "price":
          return direction * (first.price.total - second.price.total);
        case "duration":
          return direction * (first.duration - second.duration);
        case "departure":
          return (
            direction *
            (new Date(`${first.departure.date}T${first.departure.time}`).getTime() -
              new Date(`${second.departure.date}T${second.departure.time}`).getTime())
          );
        case "emissions":
          return direction * (first.emissions.kg - second.emissions.kg);
        default:
          return 0;
      }
    };
    return cloned.sort(compare);
  }, [results, sortBy, sortDirection]);

  /** Handle flight selection */
  const handleFlightSelect = (flight: FlightResult) => {
    startTransition(async () => {
      setOptimisticSelecting(flight.id);
      try {
        await onSelect(flight);
      } catch (error) {
        recordClientErrorOnActiveSpan(
          error instanceof Error ? error : new Error(String(error)),
          {
            action: "handleFlightSelect",
            context: "FlightResults",
            flightId: flight.id,
          }
        );
      } finally {
        setOptimisticSelecting("");
      }
    });
  };

  /** Toggle flight for comparison */
  const toggleComparison = (flightId: string) => {
    setSelectedForComparison((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(flightId)) {
        newSet.delete(flightId);
      } else if (newSet.size < 3) {
        // Max 3 for comparison
        newSet.add(flightId);
      }
      return newSet;
    });
  };

  const toggleSort = () => {
    setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
  };

  /** Get price change icon */
  const getPriceChangeIcon = (change?: "up" | "down" | "stable") => {
    if (change === "down")
      return <TrendingUpIcon className="h-3 w-3 text-green-500 rotate-180" />;
    if (change === "up") return <TrendingUpIcon className="h-3 w-3 text-red-500" />;
    return null;
  };

  const getPredictionBadge = (prediction: FlightResult["prediction"]) => {
    const colors = {
      buy_now: "bg-green-100 text-green-800 border-green-200",
      neutral: "bg-gray-100 text-gray-800 border-gray-200",
      wait: "bg-yellow-100 text-yellow-800 border-yellow-200",
    };

    const text = {
      buy_now: "Book Now",
      neutral: "Monitor",
      wait: "Wait",
    };

    return (
      <Badge variant="outline" className={cn("text-xs", colors[prediction.priceAlert])}>
        {text[prediction.priceAlert]} ({prediction.confidence}%)
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Card key={`flight-skeleton-${i}`} className="p-6">
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
        ))}
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <Card className="p-12 text-center">
        <PlaneIcon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No flights found</h3>
        <p className="text-muted-foreground mb-4">
          Try adjusting your search dates or filters
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
      <Card className="p-4" data-testid="flight-results-controls">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">{results.length} flights found</span>
            <Separator orientation="vertical" className="h-4" />
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm">
                <FilterIcon className="h-4 w-4 mr-2" />
                Filters
              </Button>
              <Button variant="ghost" size="sm" onClick={toggleSort}>
                <ArrowUpDownIcon className="h-4 w-4 mr-2" />
                Sort: {sortBy} ({sortDirection})
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
          </div>
        </div>

        {selectedForComparison.size > 0 && (
          <div className="mt-3 pt-3 border-t">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {selectedForComparison.size} flight
                {selectedForComparison.size > 1 ? "s" : ""} selected for comparison
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
                    onCompare(
                      sortedResults.filter((f) => selectedForComparison.has(f.id))
                    )
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

      {/* Flight Results */}
      <div className="space-y-3">
        {sortedResults.map((flight) => (
          <Card
            key={flight.id}
            className={cn(
              "relative transition-all duration-200 hover:shadow-md",
              selectedForComparison.has(flight.id) && "ring-2 ring-blue-500",
              optimisticSelecting === flight.id && "opacity-75"
            )}
          >
            <CardContent className={cn("p-6", viewMode === "grid" && "p-4")}>
              {/* Promotions Banner */}
              {flight.promotions && (
                <div className="absolute top-0 left-6 transform -translate-y-1/2">
                  <Badge className="bg-red-500 text-white">
                    <ZapIcon className="h-3 w-3 mr-1" />
                    {flight.promotions.description}
                  </Badge>
                </div>
              )}

              <div className="grid grid-cols-12 gap-4 items-center">
                {/* Airline Info */}
                <div className="col-span-2">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center">
                      <PlaneIcon className="h-4 w-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">{flight.airline}</p>
                      <p className="text-xs text-muted-foreground">
                        {flight.flightNumber}
                      </p>
                      {viewMode === "list" && (
                        <p className="text-xs text-muted-foreground">
                          {flight.aircraft}
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Route & Times */}
                <div className="col-span-5">
                  <div className="flex items-center justify-between">
                    <div className="text-center">
                      <p className="font-semibold">{flight.departure.time}</p>
                      <p className="text-sm font-medium">{flight.origin.code}</p>
                      <p className="text-xs text-muted-foreground">
                        {flight.origin.city}
                      </p>
                      {flight.origin.terminal && viewMode === "list" && (
                        <p className="text-xs text-muted-foreground">
                          Terminal {flight.origin.terminal}
                        </p>
                      )}
                    </div>

                    <div className="flex-1 mx-4">
                      <div className="relative">
                        <div className="h-0.5 bg-muted-foreground/30 w-full" />
                        <PlaneIcon className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="text-center mt-2">
                        <p className="text-xs font-medium">
                          {formatDurationMinutes(flight.duration)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {flight.stops.count === 0
                            ? "Direct"
                            : `${flight.stops.count} stop${
                                flight.stops.count > 1 ? "s" : ""
                              }`}
                        </p>
                      </div>
                    </div>

                    <div className="text-center">
                      <p className="font-semibold">{flight.arrival.time}</p>
                      <p className="text-sm font-medium">{flight.destination.code}</p>
                      <p className="text-xs text-muted-foreground">
                        {flight.destination.city}
                      </p>
                      {flight.destination.terminal && viewMode === "list" && (
                        <p className="text-xs text-muted-foreground">
                          Terminal {flight.destination.terminal}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Additional Info for List View */}
                  {viewMode === "list" && (
                    <div className="mt-4 flex items-center justify-center gap-4 text-xs">
                      {flight.amenities.includes("wifi") && (
                        <div className="flex items-center gap-1 text-muted-foreground">
                          <WifiIcon className="h-3 w-3" />
                          WiFi
                        </div>
                      )}
                      {flight.amenities.includes("meals") && (
                        <div className="flex items-center gap-1 text-muted-foreground">
                          <UtensilsIcon className="h-3 w-3" />
                          Meals
                        </div>
                      )}
                      {flight.amenities.includes("entertainment") && (
                        <div className="flex items-center gap-1 text-muted-foreground">
                          <MonitorIcon className="h-3 w-3" />
                          Entertainment
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Price & Actions */}
                <div className="col-span-3">
                  <div className="text-right">
                    <div className="flex items-center justify-end gap-2 mb-1">
                      <span className="text-2xl font-bold">
                        {formatCurrency(flight.price.total)}
                      </span>
                      {getPriceChangeIcon(flight.price.priceChange)}
                    </div>
                    <p className="text-xs text-muted-foreground mb-2">per person</p>

                    {flight.price.dealScore && flight.price.dealScore >= 8 && (
                      <Badge
                        variant="secondary"
                        className="mb-2 bg-green-100 text-green-800"
                      >
                        <StarIcon className="h-3 w-3 mr-1" />
                        Great Deal
                      </Badge>
                    )}

                    {viewMode === "list" && (
                      <div className="space-y-2 mb-3">
                        {getPredictionBadge(flight.prediction)}

                        <div className="flex items-center gap-2 text-xs">
                          <div
                            className={cn(
                              "w-2 h-2 rounded-full",
                              flight.emissions.compared === "low"
                                ? "bg-green-500"
                                : flight.emissions.compared === "average"
                                  ? "bg-yellow-500"
                                  : "bg-red-500"
                            )}
                          />
                          <span className="text-muted-foreground">
                            {flight.emissions.kg}kg CO₂
                          </span>
                        </div>

                        {(flight.flexibility.changeable ||
                          flight.flexibility.refundable) && (
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <ShieldIcon className="h-3 w-3" />
                            {flight.flexibility.refundable
                              ? "Refundable"
                              : "Changeable"}
                          </div>
                        )}
                      </div>
                    )}

                    <div className="space-y-2">
                      <Button
                        onClick={() => handleFlightSelect(flight)}
                        disabled={isPending || optimisticSelecting === flight.id}
                        className="w-full"
                        size={viewMode === "grid" ? "sm" : "default"}
                      >
                        {optimisticSelecting === flight.id
                          ? "Selecting..."
                          : "Select Flight"}
                      </Button>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => toggleComparison(flight.id)}
                        className="w-full"
                      >
                        {selectedForComparison.has(flight.id) ? (
                          <>
                            <HeartIcon className="h-3 w-3 mr-1 fill-current" />
                            Selected
                          </>
                        ) : (
                          <>
                            <HeartIcon className="h-3 w-3 mr-1" />
                            Compare
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Comparison Checkbox */}
                <div className="col-span-2 flex justify-end">
                  <input
                    type="checkbox"
                    checked={selectedForComparison.has(flight.id)}
                    onChange={() => toggleComparison(flight.id)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* AI Prediction Details */}
              {viewMode === "list" && flight.prediction.priceAlert !== "neutral" && (
                <div className="mt-4 pt-4 border-t">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <ZapIcon className="h-3 w-3" />
                    <span>AI Prediction: {flight.prediction.reason}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Load More */}
      {sortedResults.length > 0 && (
        <Card className="p-4 text-center">
          <Button variant="outline">Load More Flights</Button>
        </Card>
      )}
    </div>
  );
}
