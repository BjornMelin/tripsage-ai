"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  ArrowUpDown,
  Calendar,
  Clock,
  Coffee,
  Filter,
  Heart,
  MapPin,
  Monitor,
  Plane,
  RefreshCw,
  Shield,
  Star,
  TrendingUp,
  Users,
  Utensils,
  Wifi,
  Zap,
} from "lucide-react";
import { useOptimistic, useState, useTransition } from "react";

// Modern flight result types with 2025 travel patterns
interface ModernFlightResult {
  id: string;
  airline: string;
  flightNumber: string;
  aircraft: string;
  origin: {
    code: string;
    city: string;
    terminal?: string;
  };
  destination: {
    code: string;
    city: string;
    terminal?: string;
  };
  departure: {
    time: string;
    date: string;
  };
  arrival: {
    time: string;
    date: string;
  };
  duration: number; // minutes
  stops: {
    count: number;
    cities?: string[];
    duration?: number;
  };
  price: {
    base: number;
    total: number;
    currency: string;
    priceChange?: "up" | "down" | "stable";
    dealScore?: number; // 1-10
  };
  amenities: string[];
  emissions: {
    kg: number;
    compared: "low" | "average" | "high";
  };
  flexibility: {
    changeable: boolean;
    refundable: boolean;
    cost?: number;
  };
  prediction: {
    priceAlert: "buy_now" | "wait" | "neutral";
    confidence: number; // 0-100
    reason: string;
  };
  promotions?: {
    type: "flash_deal" | "early_bird" | "limited_time";
    description: string;
    savings: number;
  };
}

interface ModernFlightResultsProps {
  results: ModernFlightResult[];
  loading?: boolean;
  onSelect: (flight: ModernFlightResult) => Promise<void>;
  onCompare: (flights: ModernFlightResult[]) => void;
  className?: string;
}

export function ModernFlightResults({
  results,
  loading = false,
  onSelect,
  onCompare,
  className,
}: ModernFlightResultsProps) {
  const [isPending, startTransition] = useTransition();
  const [selectedForComparison, setSelectedForComparison] = useState<Set<string>>(
    new Set()
  );
  const [sortBy, setSortBy] = useState<
    "price" | "duration" | "departure" | "emissions"
  >("price");
  const [viewMode, setViewMode] = useState<"comfortable" | "compact">("comfortable");

  // Optimistic selection state
  const [optimisticSelecting, setOptimisticSelecting] = useOptimistic(
    "",
    (state, flightId: string) => flightId
  );

  const handleFlightSelect = (flight: ModernFlightResult) => {
    startTransition(async () => {
      setOptimisticSelecting(flight.id);
      try {
        await onSelect(flight);
      } catch (error) {
        console.error("Flight selection failed:", error);
      } finally {
        setOptimisticSelecting("");
      }
    });
  };

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

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const getPriceChangeIcon = (change?: "up" | "down" | "stable") => {
    if (change === "down")
      return <TrendingUp className="h-3 w-3 text-green-500 rotate-180" />;
    if (change === "up") return <TrendingUp className="h-3 w-3 text-red-500" />;
    return null;
  };

  const getPredictionBadge = (prediction: ModernFlightResult["prediction"]) => {
    const colors = {
      buy_now: "bg-green-100 text-green-800 border-green-200",
      wait: "bg-yellow-100 text-yellow-800 border-yellow-200",
      neutral: "bg-gray-100 text-gray-800 border-gray-200",
    };

    const text = {
      buy_now: "Book Now",
      wait: "Wait",
      neutral: "Monitor",
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
        <Plane className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No flights found</h3>
        <p className="text-muted-foreground mb-4">
          Try adjusting your search dates or filters
        </p>
        <Button variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
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
            <span className="text-sm font-medium">{results.length} flights found</span>
            <Separator orientation="vertical" className="h-4" />
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm">
                <Filter className="h-4 w-4 mr-2" />
                Filters
              </Button>
              <Button variant="ghost" size="sm">
                <ArrowUpDown className="h-4 w-4 mr-2" />
                Sort: {sortBy}
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant={viewMode === "comfortable" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("comfortable")}
            >
              Comfortable
            </Button>
            <Button
              variant={viewMode === "compact" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("compact")}
            >
              Compact
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
                    onCompare(results.filter((f) => selectedForComparison.has(f.id)))
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
        {results.map((flight) => (
          <Card
            key={flight.id}
            className={cn(
              "relative transition-all duration-200 hover:shadow-md",
              selectedForComparison.has(flight.id) && "ring-2 ring-blue-500",
              optimisticSelecting === flight.id && "opacity-75"
            )}
          >
            <CardContent className={cn("p-6", viewMode === "compact" && "p-4")}>
              {/* Promotions Banner */}
              {flight.promotions && (
                <div className="absolute top-0 left-6 transform -translate-y-1/2">
                  <Badge className="bg-red-500 text-white">
                    <Zap className="h-3 w-3 mr-1" />
                    {flight.promotions.description}
                  </Badge>
                </div>
              )}

              <div className="grid grid-cols-12 gap-4 items-center">
                {/* Airline Info */}
                <div className="col-span-2">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center">
                      <Plane className="h-4 w-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">{flight.airline}</p>
                      <p className="text-xs text-muted-foreground">
                        {flight.flightNumber}
                      </p>
                      {viewMode === "comfortable" && (
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
                      {flight.origin.terminal && viewMode === "comfortable" && (
                        <p className="text-xs text-muted-foreground">
                          Terminal {flight.origin.terminal}
                        </p>
                      )}
                    </div>

                    <div className="flex-1 mx-4">
                      <div className="relative">
                        <div className="h-0.5 bg-muted-foreground/30 w-full" />
                        <Plane className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="text-center mt-2">
                        <p className="text-xs font-medium">
                          {formatDuration(flight.duration)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {flight.stops.count === 0
                            ? "Direct"
                            : `${flight.stops.count} stop${flight.stops.count > 1 ? "s" : ""}`}
                        </p>
                      </div>
                    </div>

                    <div className="text-center">
                      <p className="font-semibold">{flight.arrival.time}</p>
                      <p className="text-sm font-medium">{flight.destination.code}</p>
                      <p className="text-xs text-muted-foreground">
                        {flight.destination.city}
                      </p>
                      {flight.destination.terminal && viewMode === "comfortable" && (
                        <p className="text-xs text-muted-foreground">
                          Terminal {flight.destination.terminal}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Additional Info for Comfortable View */}
                  {viewMode === "comfortable" && (
                    <div className="mt-4 flex items-center justify-center gap-4 text-xs">
                      {flight.amenities.includes("wifi") && (
                        <div className="flex items-center gap-1 text-muted-foreground">
                          <Wifi className="h-3 w-3" />
                          WiFi
                        </div>
                      )}
                      {flight.amenities.includes("meals") && (
                        <div className="flex items-center gap-1 text-muted-foreground">
                          <Utensils className="h-3 w-3" />
                          Meals
                        </div>
                      )}
                      {flight.amenities.includes("entertainment") && (
                        <div className="flex items-center gap-1 text-muted-foreground">
                          <Monitor className="h-3 w-3" />
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
                      <span className="text-2xl font-bold">${flight.price.total}</span>
                      {getPriceChangeIcon(flight.price.priceChange)}
                    </div>
                    <p className="text-xs text-muted-foreground mb-2">per person</p>

                    {flight.price.dealScore && flight.price.dealScore >= 8 && (
                      <Badge
                        variant="secondary"
                        className="mb-2 bg-green-100 text-green-800"
                      >
                        <Star className="h-3 w-3 mr-1" />
                        Great Deal
                      </Badge>
                    )}

                    {viewMode === "comfortable" && (
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
                            <Shield className="h-3 w-3" />
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
                        size={viewMode === "compact" ? "sm" : "default"}
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
                            <Heart className="h-3 w-3 mr-1 fill-current" />
                            Selected
                          </>
                        ) : (
                          <>
                            <Heart className="h-3 w-3 mr-1" />
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
              {viewMode === "comfortable" &&
                flight.prediction.priceAlert !== "neutral" && (
                  <div className="mt-4 pt-4 border-t">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Zap className="h-3 w-3" />
                      <span>AI Prediction: {flight.prediction.reason}</span>
                    </div>
                  </div>
                )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Load More */}
      {results.length > 0 && (
        <Card className="p-4 text-center">
          <Button variant="outline">Load More Flights</Button>
        </Card>
      )}
    </div>
  );
}
