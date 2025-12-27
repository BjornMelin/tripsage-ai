/**
 * @fileoverview Trip collaboration activity feed UI.
 */

"use client";

import {
  CheckCircleIcon,
  CrownIcon,
  EditIcon,
  UserMinusIcon,
  UserPlusIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type {
  TripActivityItem,
  TripActivityKind,
} from "@/hooks/use-trip-activity-feed";
import { cn } from "@/lib/utils";

function ActivityIcon(kind: TripActivityKind) {
  switch (kind) {
    case "collaborator_invited":
      return UserPlusIcon;
    case "collaborator_removed":
      return UserMinusIcon;
    case "collaborator_role_updated":
      return CrownIcon;
    case "trip_updated":
      return EditIcon;
  }
}

function ActivityTone(kind: TripActivityKind) {
  switch (kind) {
    case "collaborator_invited":
      return "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
    case "collaborator_removed":
      return "bg-rose-500/10 text-rose-700 dark:text-rose-300";
    case "collaborator_role_updated":
      return "bg-amber-500/10 text-amber-700 dark:text-amber-300";
    case "trip_updated":
      return "bg-sky-500/10 text-sky-700 dark:text-sky-300";
  }
}

export function TripActivityFeed(props: {
  events: TripActivityItem[];
  connectionStatus: string;
}) {
  const { events, connectionStatus } = props;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Badge
          variant="outline"
          className={cn(
            connectionStatus === "subscribed"
              ? "border-emerald-500/40 text-emerald-600 dark:text-emerald-300"
              : "border-border text-muted-foreground"
          )}
        >
          <CheckCircleIcon className="mr-1 h-3 w-3" />
          {connectionStatus === "subscribed" ? "Live" : "Offline"}
        </Badge>

        <span className="text-xs text-muted-foreground">
          {events.length > 0 ? `${events.length} events` : "No events yet"}
        </span>
      </div>

      {events.length === 0 ? (
        <div className="rounded-lg border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
          Activity will appear here as collaborators join and edits happen.
        </div>
      ) : (
        <div className="space-y-2">
          {events.map((event) => {
            const Icon = ActivityIcon(event.kind);
            return (
              <div
                key={event.id}
                className="flex items-start justify-between gap-3 rounded-lg border bg-background px-3 py-2"
              >
                <div className="flex min-w-0 items-start gap-2">
                  <span
                    className={cn(
                      "mt-0.5 inline-flex h-7 w-7 items-center justify-center rounded-md",
                      ActivityTone(event.kind)
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">{event.message}</div>
                    <div className="text-xs text-muted-foreground">
                      {new Date(event.at).toLocaleTimeString()} •{" "}
                      {event.source === "local" ? "You" : "Collaborator"}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
