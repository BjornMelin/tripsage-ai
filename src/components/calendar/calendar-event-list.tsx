/**
 * @fileoverview Client Component for displaying calendar events list.
 *
 * Fetches events via API route to avoid server/client boundary violations.
 */

"use client";

import { CalendarIcon, ClockIcon, MapPinIcon } from "lucide-react";
import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { DateUtils } from "@/lib/dates/unified-date-utils";

/** Shape of a calendar event from the API. */
interface CalendarEvent {
  id: string;
  summary: string;
  description?: string;
  location?: string;
  start: { dateTime?: string; date?: string };
  end: { dateTime?: string; date?: string };
  htmlLink?: string;
}

/** Props for CalendarEventList component. */
export interface CalendarEventListProps {
  /** Calendar ID to fetch events from (default: "primary") */
  calendarId?: string;
  /** Start date for event query */
  timeMin?: Date;
  /** End date for event query */
  timeMax?: Date;
  /** Optional className */
  className?: string;
}

/**
 * Fetches Calendar events via API and renders a summarized list in a card.
 *
 * @param props - Optional calendar id and time range plus styling hook.
 * @returns Client component output with event list.
 */
export function CalendarEventList({
  calendarId = "primary",
  timeMin,
  timeMax,
  className,
}: CalendarEventListProps) {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    (async () => {
      setIsLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();
        params.set("calendarId", calendarId);
        params.set("maxResults", "250");
        if (timeMin) {
          params.set("timeMin", timeMin.toISOString());
        }
        if (timeMax) {
          params.set("timeMax", timeMax.toISOString());
        }

        const response = await fetch(`/api/calendar/events?${params}`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch events: ${response.statusText}`);
        }

        const data = await response.json();
        const items = (data.items || []).filter(
          (event: Partial<CalendarEvent>): event is CalendarEvent =>
            Boolean(event.id && event.start && event.end)
        );
        setEvents(items);
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        if (process.env.NODE_ENV === "development") {
          console.error("Failed to fetch calendar events:", err);
        }
      } finally {
        setIsLoading(false);
      }
    })();

    return () => {
      controller.abort();
    };
  }, [calendarId, timeMin, timeMax]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-48 mt-2" />
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="p-4 border rounded-lg space-y-2">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarIcon className="h-5 w-5" />
            Upcoming Events
          </CardTitle>
          <CardDescription className="text-destructive">
            Failed to load events: {error}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CalendarIcon className="h-5 w-5" />
          Upcoming Events
        </CardTitle>
        <CardDescription>
          {events.length > 0
            ? `${events.length} event${events.length !== 1 ? "s" : ""} found`
            : "No upcoming events"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {events.length > 0 ? (
          <ul className="space-y-4">
            {events.map((event) => {
              const startDate = event.start?.dateTime
                ? DateUtils.parse(event.start.dateTime)
                : event.start?.date
                  ? DateUtils.parse(event.start.date)
                  : null;
              const endDate = event.end?.dateTime
                ? DateUtils.parse(event.end.dateTime)
                : event.end?.date
                  ? DateUtils.parse(event.end.date)
                  : null;

              return (
                <li
                  key={event.id}
                  className="p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="space-y-2">
                    <h3 className="font-semibold">{event.summary}</h3>
                    {event.description && (
                      <p className="text-sm text-muted-foreground">
                        {event.description}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                      {startDate && (
                        <div className="flex items-center gap-1">
                          <ClockIcon className="h-4 w-4" />
                          {DateUtils.format(startDate, "MMM d, yyyy h:mm a")}
                          {endDate && ` - ${DateUtils.format(endDate, "h:mm a")}`}
                        </div>
                      )}
                      {event.location && (
                        <div className="flex items-center gap-1">
                          <MapPinIcon className="h-4 w-4" />
                          {event.location}
                        </div>
                      )}
                    </div>
                    {event.htmlLink && (
                      <a
                        href={event.htmlLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:underline"
                      >
                        View in Google Calendar
                      </a>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">
            No events found in this time range.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
