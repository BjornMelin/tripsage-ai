/**
 * @fileoverview Upcoming flights dashboard component.
 *
 * Displays a card-based list of upcoming flights with departure/arrival times,
 * flight status, duration, and pricing information. Integrates with trip data
 * and provides links to associated trips and flight search functionality.
 */

"use client";

import { Clock, Plane } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { type UpcomingFlight, useUpcomingFlights } from "@/hooks/use-trips";
import { DateUtils } from "@/lib/dates/unified-date-utils";

/**
 * Props for the UpcomingFlights component.
 *
 * @interface UpcomingFlightsProps
 */
interface UpcomingFlightsProps {
  /** Maximum number of flights to display. Defaults to 3. */
  limit?: number;
  /** Whether to show an empty state when no flights are available. Defaults to true. */
  showEmpty?: boolean;
}

/**
 * Skeleton loading component for flight cards.
 *
 * Displays placeholder content while flight data is loading.
 *
 * @returns A skeleton flight card component.
 */
function FlightCardSkeleton() {
  return (
    <div className="p-3 border border-border rounded-lg" data-testid="flight-skeleton">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-5 w-16" />
      </div>
      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <Skeleton className="h-3 w-16 mb-1" />
          <Skeleton className="h-4 w-20" />
        </div>
        <div>
          <Skeleton className="h-3 w-16 mb-1" />
          <Skeleton className="h-4 w-20" />
        </div>
      </div>
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-3 w-16" />
      </div>
    </div>
  );
}

/**
 * Individual flight card component.
 *
 * Displays detailed information about a single upcoming flight including
 * departure/arrival times, status, duration, price, and associated trip links.
 *
 * @param props - Component props.
 * @param props.flight - The flight data to display.
 * @returns A formatted flight card component.
 */
function FlightCard({ flight }: { flight: UpcomingFlight }) {
  /**
   * Formats a time string to HH:mm format.
   *
   * @param timeString - ISO time string to format.
   * @returns Formatted time string.
   */
  const formatTime = (timeString: string) => {
    try {
      const date = DateUtils.parse(timeString);
      return DateUtils.format(date, "HH:mm");
    } catch {
      return "Invalid time";
    }
  };

  /**
   * Formats a time string to MMM d format.
   *
   * @param timeString - ISO time string to format.
   * @returns Formatted date string.
   */
  const formatDate = (timeString: string) => {
    try {
      const date = DateUtils.parse(timeString);
      return DateUtils.format(date, "MMM d");
    } catch {
      return "Invalid date";
    }
  };

  /**
   * Returns the appropriate badge variant for a flight status.
   *
   * @param status - The flight status.
   * @returns Badge variant name.
   */
  const getStatusColor = (status: UpcomingFlight["status"]) => {
    switch (status) {
      case "upcoming":
        return "default";
      case "boarding":
        return "secondary";
      case "delayed":
        return "destructive";
      case "cancelled":
        return "destructive";
      default:
        return "outline";
    }
  };

  /**
   * Formats flight duration in minutes to "Xh Ym" format.
   *
   * @returns Formatted duration string.
   */
  const getDuration = () => {
    const hours = Math.floor(flight.duration / 60);
    const minutes = flight.duration % 60;
    return `${hours}h ${minutes}m`;
  };

  return (
    <div
      className="p-3 border border-border rounded-lg hover:bg-accent/50 transition-colors"
      data-testid="flight-card"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Plane className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">
            {flight.airlineName} {flight.flightNumber}
          </span>
        </div>
        <Badge variant={getStatusColor(flight.status)} className="text-xs">
          {flight.status}
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <p className="text-xs text-muted-foreground mb-1">Departure</p>
          <p className="font-medium text-sm">{flight.origin}</p>
          <p className="text-xs text-muted-foreground">
            {formatTime(flight.departureTime)} • {formatDate(flight.departureTime)}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">Arrival</p>
          <p className="font-medium text-sm">{flight.destination}</p>
          <p className="text-xs text-muted-foreground">
            {formatTime(flight.arrivalTime)} • {formatDate(flight.arrivalTime)}
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{getDuration()}</span>
          </div>
          {flight.stops > 0 && (
            <span>
              {flight.stops} stop{flight.stops > 1 ? "s" : ""}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <span className="font-medium">
            {flight.currency && flight.currency.trim().length > 0
              ? new Intl.NumberFormat("en-US", {
                  currency: flight.currency,
                  style: "currency",
                }).format(flight.price)
              : `$${flight.price}`}
          </span>
        </div>
      </div>

      {flight.tripName && (
        <div className="mt-2 pt-2 border-t border-border">
          <p className="text-xs text-muted-foreground">
            Part of:{" "}
            <Link
              href={`/dashboard/trips/${flight.tripId}`}
              className="text-primary hover:underline"
            >
              {flight.tripName}
            </Link>
          </p>
        </div>
      )}

      {(flight.terminal || flight.gate) && (
        <div className="mt-2 pt-2 border-t border-border">
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            {flight.terminal && <span>Terminal {flight.terminal}</span>}
            {flight.gate && <span>Gate {flight.gate}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Empty state component for when no upcoming flights are available.
 *
 * Displays a message with a call-to-action to search for flights.
 *
 * @returns An empty state component with flight search CTA.
 */
function EmptyState() {
  return (
    <div className="text-center py-8">
      <div className="mx-auto w-12 h-12 bg-muted rounded-full flex items-center justify-center mb-4">
        <Plane className="h-6 w-6 text-muted-foreground" />
      </div>
      <p className="text-sm text-muted-foreground mb-4">No upcoming flights.</p>
      <Button asChild size="sm">
        <Link href="/dashboard/search/flights">Search Flights</Link>
      </Button>
    </div>
  );
}

/**
 * Renders the upcoming flights dashboard widget with loading and empty states.
 *
 * @param props - Component configuration such as max flights and empty-state
 * preference.
 * @returns Card containing fetched flights or fallback UIs.
 */
export function UpcomingFlights({ limit = 3, showEmpty = true }: UpcomingFlightsProps) {
  const { data: upcomingFlights = [], isLoading } = useUpcomingFlights({
    limit: limit,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Upcoming Flights</CardTitle>
          <CardDescription>Your next departures</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <FlightCardSkeleton key="flight-skeleton-1" />
          <FlightCardSkeleton key="flight-skeleton-2" />
        </CardContent>
        <CardFooter>
          <Skeleton className="h-9 w-full" />
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upcoming Flights</CardTitle>
        <CardDescription>Your next departures</CardDescription>
      </CardHeader>
      <CardContent>
        {upcomingFlights.length === 0 ? (
          showEmpty ? (
            <EmptyState />
          ) : (
            <p className="text-center py-4 text-sm text-muted-foreground">
              No upcoming flights.
            </p>
          )
        ) : (
          <div className="space-y-3">
            {upcomingFlights.map((flight) => (
              <FlightCard key={flight.id} flight={flight} />
            ))}
          </div>
        )}
      </CardContent>
      {upcomingFlights.length > 0 && (
        <CardFooter>
          <Button className="w-full" variant="outline" asChild>
            <Link href="/dashboard/search/flights">Search More Flights</Link>
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
