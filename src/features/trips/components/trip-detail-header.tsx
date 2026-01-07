/**
 * @fileoverview Trip detail header with summary metadata and top-level actions.
 */

"use client";

import type { UiTrip } from "@schemas/trips";
import {
  CalendarIcon,
  ChevronLeftIcon,
  MessageSquareIcon,
  Trash2Icon,
  UsersIcon,
} from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatTripDates } from "@/lib/trips/trip-detail-utils";

type TripDetailHeaderProps = {
  trip: UiTrip;
  collaboratorCount: number;
  isDeleting: boolean;
  onDeleteClick: () => void;
};

export function TripDetailHeader({
  trip,
  collaboratorCount,
  isDeleting,
  onDeleteClick,
}: TripDetailHeaderProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="space-y-2">
        <Button asChild variant="ghost" size="sm" className="-ml-2 w-fit">
          <Link href="/dashboard/trips">
            <ChevronLeftIcon className="mr-1 h-4 w-4" />
            Trips
          </Link>
        </Button>

        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">{trip.title}</h1>
          {trip.destination ? (
            <Badge variant="outline" className="border-dashed">
              {trip.destination}
            </Badge>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-2">
            <CalendarIcon className="h-4 w-4" />
            {formatTripDates(trip)}
          </span>
          <span className="text-muted-foreground/60">•</span>
          <span className="inline-flex items-center gap-2">
            <UsersIcon className="h-4 w-4" />
            {collaboratorCount} collaborator{collaboratorCount === 1 ? "" : "s"}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button asChild variant="outline">
          <Link href="/chat">
            <MessageSquareIcon className="mr-2 h-4 w-4" />
            Ask TripSage
          </Link>
        </Button>

        <Button
          type="button"
          variant="destructive"
          onClick={onDeleteClick}
          disabled={isDeleting}
        >
          <Trash2Icon className="mr-2 h-4 w-4" />
          Delete
        </Button>
      </div>
    </div>
  );
}
