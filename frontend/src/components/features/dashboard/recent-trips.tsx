/**
 * @fileoverview RecentTrips dashboard widget.
 * Renders recent trip cards using data from useTrips with resilient parsing
 * for items/data.items shapes. Includes accessible links and stable date text.
 */

"use client";

import { Calendar, Clock, MapPin } from "lucide-react";
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
import { useTrips } from "@/hooks/use-trips";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import type { Trip } from "@/stores/trip-store";

interface RecentTripsProps {
  limit?: number;
  showEmpty?: boolean;
}

function TripCardSkeleton() {
  return (
    <div className="p-3 border border-border rounded-lg">
      <div className="flex items-start justify-between mb-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-5 w-16" />
      </div>
      <div className="flex items-center gap-4 text-sm text-muted-foreground mb-2">
        <div className="flex items-center gap-1">
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-3 w-20" />
        </div>
        <div className="flex items-center gap-1">
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-3 w-16" />
        </div>
      </div>
      <Skeleton className="h-3 w-full mb-1" />
      <Skeleton className="h-3 w-3/4" />
    </div>
  );
}

/**
 * Render a single trip card.
 * @param trip - Trip object to render.
 */
function TripCard({ trip }: { trip: Trip }) {
  /**
   * Format an ISO date string to e.g. "Jun 15, 2024" in UTC to avoid TZ drift.
   */
  const formatDate = (dateString?: string) => {
    if (!dateString) return "Not set";
    const date = DateUtils.parse(dateString);
    return DateUtils.format(date, "MMM d, yyyy");
  };

  /**
   * Build destination summary (e.g., "Paris (+1 more)").
   */
  const getDestinationText = () => {
    if (!trip.destinations || trip.destinations.length === 0) return "No destinations";
    if (trip.destinations.length === 1) return trip.destinations[0].name;
    return `${trip.destinations[0].name} (+${trip.destinations.length - 1} more)`;
  };

  /**
   * Compute duration in days from start/end.
   */
  const getTripDuration = () => {
    if (!trip.startDate || !trip.endDate) return null;
    const start = DateUtils.parse(trip.startDate);
    const end = DateUtils.parse(trip.endDate);
    const diffDays = Math.max(1, Math.abs(DateUtils.difference(end, start, "days")));
    return `${diffDays} day${diffDays !== 1 ? "s" : ""}`;
  };

  /**
   * Compute trip status relative to now.
   */
  const getTripStatus = () => {
    if (!trip.startDate || !trip.endDate) return "draft";
    const now = new Date();
    const start = DateUtils.parse(trip.startDate);
    const end = DateUtils.parse(trip.endDate);
    const nowTs = now.getTime();

    if (start.getTime() > nowTs) {
      return "upcoming";
    }
    if (end.getTime() < nowTs) {
      return "completed";
    }
    return "ongoing";
  };

  const status = getTripStatus();
  const duration = getTripDuration();

  return (
    <Link
      href={`/dashboard/trips/${trip.id}`}
      className="block p-3 border border-border rounded-lg hover:bg-accent/50 transition-colors"
    >
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-medium text-sm truncate pr-2">{trip.title}</h4>
        <Badge
          variant={
            status === "upcoming"
              ? "default"
              : status === "ongoing"
                ? "secondary"
                : status === "completed"
                  ? "outline"
                  : "outline"
          }
          className="text-xs whitespace-nowrap"
        >
          {status}
        </Badge>
      </div>

      <div className="flex items-center gap-4 text-sm text-muted-foreground mb-2">
        <div className="flex items-center gap-1">
          <MapPin className="h-3 w-3" />
          <span className="truncate">{getDestinationText()}</span>
        </div>
        {duration && (
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{duration}</span>
          </div>
        )}
      </div>

      {trip.startDate && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Calendar className="h-3 w-3" />
          <span>
            {formatDate(trip.startDate)}
            {trip.endDate && ` - ${formatDate(trip.endDate)}`}
          </span>
        </div>
      )}

      {trip.description && (
        <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
          {trip.description}
        </p>
      )}
    </Link>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-8">
      <div className="mx-auto w-12 h-12 bg-muted rounded-full flex items-center justify-center mb-4">
        <MapPin className="h-6 w-6 text-muted-foreground" />
      </div>
      <p className="text-sm text-muted-foreground mb-4">No recent trips yet.</p>
      <Button asChild size="sm">
        <Link href="/dashboard/trips">Create your first trip</Link>
      </Button>
    </div>
  );
}

/**
 * Renders a dashboard widget listing the most recently updated trips.
 *
 * @param props - Component configuration including list limit and whether to
 * show the empty state.
 * @returns Recent trip grid with skeleton fallback.
 */
export function RecentTrips({ limit = 5, showEmpty = true }: RecentTripsProps) {
  const { data: tripsResponse, isLoading } = useTrips();

  // Extract trips from the response and sort by updatedAt/createdAt, take the most recent ones
  let tripsData: Trip[] = [];
  if (Array.isArray(tripsResponse)) {
    tripsData = tripsResponse;
  } else if (tripsResponse && typeof tripsResponse === "object") {
    const anyResp = tripsResponse as {
      items?: Trip[];
      data?: Trip[] | { items?: Trip[] };
    };
    if (Array.isArray(anyResp.items)) {
      tripsData = anyResp.items;
    } else if (anyResp.data) {
      if (Array.isArray(anyResp.data)) tripsData = anyResp.data;
      else if (Array.isArray(anyResp.data.items)) tripsData = anyResp.data.items;
    }
  }
  const recentTrips = tripsData
    .sort((a: Trip, b: Trip) => {
      const aUpdated = (a as unknown as { updatedAt?: string }).updatedAt;
      const aCreated = (a as unknown as { createdAt?: string }).createdAt;
      const bUpdated = (b as unknown as { updatedAt?: string }).updatedAt;
      const bCreated = (b as unknown as { createdAt?: string }).createdAt;
      const dateA = new Date(aUpdated || aCreated || "1970-01-01T00:00:00Z");
      const dateB = new Date(bUpdated || bCreated || "1970-01-01T00:00:00Z");
      return dateB.getTime() - dateA.getTime();
    })
    .slice(0, limit);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Trips</CardTitle>
          <CardDescription>Your latest travel plans</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {["a", "b", "c"].map((k) => (
            <TripCardSkeleton key={`trip-skeleton-${k}`} />
          ))}
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
        <CardTitle>Recent Trips</CardTitle>
        <CardDescription>Your latest travel plans</CardDescription>
      </CardHeader>
      <CardContent>
        {recentTrips.length === 0 ? (
          showEmpty ? (
            <EmptyState />
          ) : (
            <p className="text-center py-4 text-sm text-muted-foreground">
              No recent trips yet.
            </p>
          )
        ) : (
          <div className="space-y-3">
            {recentTrips.map((trip: Trip) => (
              <TripCard key={trip.id} trip={trip} />
            ))}
          </div>
        )}
      </CardContent>
      {recentTrips.length > 0 && (
        <CardFooter>
          <Button className="w-full" variant="outline" asChild>
            <Link href="/dashboard/trips">View All Trips</Link>
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
