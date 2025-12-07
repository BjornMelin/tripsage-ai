/**
 * @fileoverview Reusable flight card component for flight results display.
 */

"use client";

import type { FlightResult } from "@schemas/search";
import {
  HeartIcon,
  MonitorIcon,
  PlaneIcon,
  ShieldIcon,
  StarIcon,
  TrendingUpIcon,
  UtensilsIcon,
  WifiIcon,
  ZapIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { formatCurrency, formatDurationMinutes } from "../common/format";

/**
 * Flight-specific semantic colors aligned with statusVariants.
 * - Price trends: green (down/good), red (up/bad)
 * - Deal indicators: green (success/active)
 * - Emissions: green (low), amber (average), red (high)
 * - UI accents: blue (info), red (urgent)
 */
export const FLIGHT_COLORS = {
  airlineIcon: "bg-blue-50 text-blue-700",
  dealBadge: "bg-green-50 text-green-700",
  emissionHigh: "bg-red-500",
  emissionLow: "bg-green-500",
  emissionMedium: "bg-amber-500",
  priceTrendDown: "text-green-700",
  priceTrendUp: "text-red-700",
  promotionBadge: "bg-red-600 text-white",
} as const;

/** Price change icon component */
export function PriceChangeIcon({ change }: { change?: "up" | "down" | "stable" }) {
  if (change === "down")
    return (
      <TrendingUpIcon
        className={cn("h-3 w-3 rotate-180", FLIGHT_COLORS.priceTrendDown)}
      />
    );
  if (change === "up")
    return <TrendingUpIcon className={cn("h-3 w-3", FLIGHT_COLORS.priceTrendUp)} />;
  return null;
}

/** Prediction badge for flight booking recommendation */
export function PredictionBadge({
  prediction,
}: {
  prediction: FlightResult["prediction"];
}) {
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
}

/** Flight card component props */
export interface FlightCardProps {
  flight: FlightResult;
  viewMode: "list" | "grid";
  isSelected: boolean;
  isOptimisticSelecting: boolean;
  isPending: boolean;
  onSelect: () => void;
  onToggleComparison: () => void;
}

/** Individual flight card for results display */
export function FlightCard({
  flight,
  viewMode,
  isSelected,
  isOptimisticSelecting,
  isPending,
  onSelect,
  onToggleComparison,
}: FlightCardProps) {
  return (
    <Card
      data-testid={`flight-card-${flight.id}`}
      className={cn(
        "relative transition-all duration-200 hover:shadow-md",
        isSelected && "ring-2 ring-blue-500",
        isOptimisticSelecting && "opacity-75"
      )}
    >
      <CardContent className={cn("p-6", viewMode === "grid" && "p-4")}>
        {/* Promotions Banner */}
        {flight.promotions && (
          <div className="absolute top-0 left-6 transform -translate-y-1/2">
            <Badge className={FLIGHT_COLORS.promotionBadge}>
              <ZapIcon className="h-3 w-3 mr-1" />
              {flight.promotions.description}
            </Badge>
          </div>
        )}

        <div className="grid grid-cols-12 gap-4 items-center">
          {/* Airline Info */}
          <div className="col-span-2">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  "w-8 h-8 rounded flex items-center justify-center",
                  FLIGHT_COLORS.airlineIcon
                )}
              >
                <PlaneIcon className="h-4 w-4" />
              </div>
              <div>
                <p className="font-medium text-sm">{flight.airline}</p>
                <p className="text-xs text-muted-foreground">{flight.flightNumber}</p>
                {viewMode === "list" && (
                  <p className="text-xs text-muted-foreground">{flight.aircraft}</p>
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
                <p className="text-xs text-muted-foreground">{flight.origin.city}</p>
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
                <PriceChangeIcon change={flight.price.priceChange} />
              </div>
              <p className="text-xs text-muted-foreground mb-2">per person</p>

              {flight.price.dealScore && flight.price.dealScore >= 8 && (
                <Badge
                  variant="secondary"
                  className={cn("mb-2", FLIGHT_COLORS.dealBadge)}
                >
                  <StarIcon className="h-3 w-3 mr-1" />
                  Great Deal
                </Badge>
              )}

              {viewMode === "list" && (
                <div className="space-y-2 mb-3">
                  <PredictionBadge prediction={flight.prediction} />

                  <div className="flex items-center gap-2 text-xs">
                    <div
                      className={cn(
                        "w-2 h-2 rounded-full",
                        flight.emissions.compared === "low"
                          ? FLIGHT_COLORS.emissionLow
                          : flight.emissions.compared === "average"
                            ? FLIGHT_COLORS.emissionMedium
                            : FLIGHT_COLORS.emissionHigh
                      )}
                    />
                    <span className="text-muted-foreground">
                      {flight.emissions.kg}kg CO2
                    </span>
                  </div>

                  {(flight.flexibility.changeable || flight.flexibility.refundable) && (
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <ShieldIcon className="h-3 w-3" />
                      {flight.flexibility.refundable ? "Refundable" : "Changeable"}
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-2">
                <Button
                  onClick={onSelect}
                  disabled={isPending || isOptimisticSelecting}
                  className="w-full"
                  size={viewMode === "grid" ? "sm" : "default"}
                >
                  {isOptimisticSelecting ? "Selecting..." : "Select Flight"}
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={onToggleComparison}
                  className="w-full"
                >
                  {isSelected ? (
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
              checked={isSelected}
              onChange={onToggleComparison}
              aria-label="Compare this flight"
              data-testid="compare-checkbox"
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
  );
}
