/**
 * @fileoverview Flight search results client UI.
 */

"use client";

import { ArrowRightIcon, FilterIcon, PlaneIcon } from "lucide-react";
import Link from "next/link";
import { useCallback, useMemo } from "react";
import { useShallow } from "zustand/react/shallow";
import { SearchLayout } from "@/components/layouts/search-layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useUser } from "@/features/auth/store/auth/auth-core";
import { formatCurrency } from "@/features/search/components/common/format";
import { useSearchResultsStore } from "@/features/search/store/search-results-store";
import { useBaseCurrency } from "@/features/shared/store/currency-store";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import { cn } from "@/lib/utils";

/**
 * Flight results page semantic colors.
 * - Price display: green (indicates value/good deal)
 */
const FLIGHT_RESULTS_COLORS = {
  priceDisplay: "text-success",
} as const;

const formatDuration = (minutes: number): string => {
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  if (remaining === 0) return `${hours}h`;
  if (hours === 0) return `${remaining}m`;
  return `${hours}h ${remaining}m`;
};

/** Props for the FlightResultsClient component. */
export interface FlightResultsClientProps {
  /** The search identifier to load results for, or null if not yet available. */
  searchId: string | null;
}

/**
 * Flight results client component.
 * @param searchId - Identifier for the search whose results should be displayed.
 * @returns A React element rendering the flight search results UI.
 */
export default function FlightResultsClient({ searchId }: FlightResultsClientProps) {
  const authUser = useUser();
  const baseCurrency = useBaseCurrency();
  const { currentContext, results, resultsBySearch, searchProgress, status } =
    useSearchResultsStore(
      useShallow((state) => ({
        currentContext: state.currentContext,
        results: state.results,
        resultsBySearch: state.resultsBySearch,
        searchProgress: state.searchProgress,
        status: state.status,
      }))
    );

  const contextCurrency =
    typeof currentContext?.searchParams?.currency === "string"
      ? currentContext.searchParams.currency
      : undefined;
  const preferredLanguage = authUser?.preferences?.language;
  const preferredTimeFormat = authUser?.preferences?.timeFormat;
  const currency = contextCurrency ?? authUser?.preferences?.currency ?? baseCurrency;
  const locale = useMemo(
    () =>
      preferredLanguage ??
      (typeof navigator !== "undefined" ? navigator.language : "en"),
    [preferredLanguage]
  );
  const timeFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(locale, {
        hour: "2-digit",
        hour12: preferredTimeFormat ? preferredTimeFormat === "12h" : undefined,
        minute: "2-digit",
      }),
    [locale, preferredTimeFormat]
  );
  const formatPrice = useCallback(
    (value: number) => formatCurrency(value, currency, locale),
    [currency, locale]
  );
  const formatTime = useCallback(
    (value: string): string => {
      try {
        return timeFormatter.format(DateUtils.parse(value));
      } catch {
        return value;
      }
    },
    [timeFormatter]
  );

  const flights = useMemo(() => {
    if (!searchId) return [];
    return resultsBySearch[searchId]?.flights ?? results.flights ?? [];
  }, [results.flights, resultsBySearch, searchId]);

  const priceRange = useMemo(() => {
    if (flights.length === 0) return null;
    let min = flights[0].price;
    let max = min;
    for (let i = 1; i < flights.length; i += 1) {
      const price = flights[i].price;
      if (price < min) min = price;
      if (price > max) max = price;
    }
    return {
      max,
      min,
    };
  }, [flights]);

  const airlineCounts = useMemo(() => {
    const counts = new Map<string, number>();
    flights.forEach((flight) => {
      counts.set(flight.airline, (counts.get(flight.airline) ?? 0) + 1);
    });
    return Array.from(counts.entries());
  }, [flights]);

  const stopCounts = useMemo(() => {
    return flights.reduce(
      (acc, flight) => {
        if (flight.stops === 0) {
          acc.direct += 1;
        } else {
          acc.withStops += 1;
        }
        return acc;
      },
      { direct: 0, withStops: 0 }
    );
  }, [flights]);

  if (!searchId) {
    return (
      <SearchLayout>
        <Card>
          <CardHeader>
            <CardTitle>Invalid Search</CardTitle>
            <CardDescription>No search ID provided.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link href="/dashboard/search/flights">Start New Search</Link>
            </Button>
          </CardContent>
        </Card>
      </SearchLayout>
    );
  }

  return (
    <SearchLayout>
      <div className="space-y-6">
        {/* Search Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlaneIcon aria-hidden="true" className="h-5 w-5" />
              Flight Search Results
            </CardTitle>
            <CardDescription>
              {currentContext
                ? `Searching flights from ${currentContext.searchParams?.from || "Unknown"} to ${currentContext.searchParams?.to || "Unknown"}`
                : `Search ID: ${searchId}`}
            </CardDescription>
          </CardHeader>
          {currentContext && (
            <CardContent>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">
                  {(() => {
                    const passengers =
                      Number(currentContext.searchParams?.passengers) || 1;
                    return `${passengers} passenger${passengers > 1 ? "s" : ""}`;
                  })()}
                </Badge>
                <Badge variant="outline">
                  {String(currentContext.searchParams?.class || "Economy")}
                </Badge>
                <Badge variant="outline">
                  {String(currentContext.searchParams?.tripType || "Round trip")}
                </Badge>
              </div>
            </CardContent>
          )}
        </Card>

        {/* Search Status */}
        {status === "searching" ? (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <span>Searching for flights…</span>
                <span>{searchProgress}%</span>
              </div>
            </CardContent>
          </Card>
        ) : null}

        {/* Results */}
        <div className="flex flex-col gap-6 lg:flex-row">
          {/* Filters Sidebar */}
          <div className="w-full space-y-4 lg:w-64">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <FilterIcon aria-hidden="true" className="h-4 w-4" />
                  Filters
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-medium mb-2">Price Range</h4>
                  <div className="text-sm text-muted-foreground">
                    {priceRange
                      ? `${formatPrice(priceRange.min)} - ${formatPrice(priceRange.max)}`
                      : "No results yet"}
                  </div>
                </div>
                <Separator />
                <div>
                  <h4 className="font-medium mb-2">Airlines</h4>
                  <div className="space-y-1 text-sm">
                    {airlineCounts.length === 0 ? (
                      <div className="text-muted-foreground">No results yet</div>
                    ) : (
                      airlineCounts.map(([airline, count]) => (
                        <div key={airline}>
                          {airline} ({count})
                        </div>
                      ))
                    )}
                  </div>
                </div>
                <Separator />
                <div>
                  <h4 className="font-medium mb-2">Stops</h4>
                  <div className="text-sm">
                    {flights.length === 0 ? (
                      <div className="text-muted-foreground">No results yet</div>
                    ) : (
                      <>
                        <div>Direct ({stopCounts.direct})</div>
                        <div>With stops ({stopCounts.withStops})</div>
                      </>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Flight Results */}
          <div className="flex-1 space-y-4">
            {flights.length === 0 && status !== "searching" ? (
              <Card>
                <CardHeader>
                  <CardTitle>No flights yet</CardTitle>
                  <CardDescription>
                    Run a search to see available flight options.
                  </CardDescription>
                </CardHeader>
              </Card>
            ) : null}

            {flights.map((flight) => (
              <Card key={flight.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-6">
                      {/* Airline Info */}
                      <div>
                        <div className="font-semibold">{flight.airline}</div>
                        <div className="text-sm text-muted-foreground">
                          {flight.flightNumber}
                        </div>
                      </div>

                      {/* Flight Route */}
                      <div className="flex items-center gap-4">
                        <div className="text-center">
                          <div className="font-semibold text-lg">
                            {formatTime(flight.departureTime)}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {flight.origin}
                          </div>
                        </div>

                        <div className="flex flex-col items-center gap-1">
                          <div className="text-xs text-muted-foreground">
                            {formatDuration(flight.duration)}
                          </div>
                          <div className="flex items-center">
                            <div className="w-16 h-px bg-border" />
                            <ArrowRightIcon
                              aria-hidden="true"
                              className="h-3 w-3 mx-1 text-muted-foreground"
                            />
                            <div className="w-16 h-px bg-border" />
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {flight.stops === 0
                              ? "Direct"
                              : `${flight.stops} stop${flight.stops > 1 ? "s" : ""}`}
                          </div>
                        </div>

                        <div className="text-center">
                          <div className="font-semibold text-lg">
                            {formatTime(flight.arrivalTime)}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {flight.destination}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Price and Book */}
                    <div className="text-right">
                      <div
                        className={cn(
                          "text-2xl font-bold",
                          FLIGHT_RESULTS_COLORS.priceDisplay
                        )}
                      >
                        {formatPrice(flight.price)}
                      </div>
                      <div className="text-sm text-muted-foreground mb-3">
                        per person
                      </div>
                      <Button
                        className="w-24"
                        disabled
                        title="Flight selection is not available yet."
                      >
                        Select
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {/* Load More */}
            <div className="text-center pt-4">
              <Button
                disabled
                title="Pagination is not available yet."
                variant="outline"
              >
                Load More Results
              </Button>
            </div>
          </div>
        </div>
      </div>
    </SearchLayout>
  );
}
