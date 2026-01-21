/**
 * @fileoverview Client Component for displaying calendar events list.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { CalendarIcon, ClockIcon, MapPinIcon } from "lucide-react";
import { z } from "zod";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCurrentUserId } from "@/hooks/use-current-user-id";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import { keys } from "@/lib/keys";

const CalendarEventListItemSchema = z.looseObject({
  description: z.string().max(8192).optional(),
  end: z
    .looseObject({
      date: z
        .string()
        .regex(/^\d{4}-\d{2}-\d{2}$/, { error: "Date must be YYYY-MM-DD" })
        .optional(),
      dateTime: z.iso.datetime().optional(),
    })
    .refine((data) => data.date || data.dateTime, {
      error: "end.date or end.dateTime is required",
      path: ["end"],
    }),
  htmlLink: z.url().optional(),
  id: z.string().min(1, { error: "id is required" }),
  location: z.string().max(1024).optional(),
  start: z
    .looseObject({
      date: z
        .string()
        .regex(/^\d{4}-\d{2}-\d{2}$/, { error: "Date must be YYYY-MM-DD" })
        .optional(),
      dateTime: z.iso.datetime().optional(),
    })
    .refine((data) => data.date || data.dateTime, {
      error: "start.date or start.dateTime is required",
      path: ["start"],
    }),
  summary: z.string().min(1).max(1024).default("Untitled"),
});

type CalendarEventListItem = z.infer<typeof CalendarEventListItemSchema>;

const CalendarEventsApiResponseSchema = z.looseObject({
  items: z.array(CalendarEventListItemSchema).default([]),
});

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
  const userId = useCurrentUserId();
  const timeMinIso = timeMin?.toISOString() ?? null;
  const timeMaxIso = timeMax?.toISOString() ?? null;

  const {
    data: events = [],
    error,
    isError,
    isPending,
  } = useQuery<CalendarEventListItem[]>({
    enabled: Boolean(userId),
    queryFn: async ({ signal }) => {
      const params = new URLSearchParams();
      params.set("calendarId", calendarId);
      params.set("maxResults", "250");
      if (timeMinIso) {
        params.set("timeMin", timeMinIso);
      }
      if (timeMaxIso) {
        params.set("timeMax", timeMaxIso);
      }

      const response = await fetch(`/api/calendar/events?${params}`, { signal });
      if (!response.ok) {
        throw new Error(`Failed to fetch events: ${response.statusText}`);
      }

      const json: unknown = await response.json();
      const parsed = CalendarEventsApiResponseSchema.safeParse(json);
      if (!parsed.success) {
        if (process.env.NODE_ENV === "development") {
          console.error("Calendar events validation error:", parsed.error);
        }
        throw new Error("Invalid calendar events response");
      }

      return parsed.data.items;
    },
    queryKey: userId
      ? keys.calendar.events(userId, {
          calendarId,
          timeMaxIso,
          timeMinIso,
        })
      : keys.calendar.eventsDisabled(),
  });

  if (isPending) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarIcon className="h-5 w-5" />
            Upcoming Events
          </CardTitle>
          <CardDescription>Loading events…</CardDescription>
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

  if (isError) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarIcon className="h-5 w-5" />
            Upcoming Events
          </CardTitle>
          <CardDescription className="text-destructive">
            Failed to load events: {message}
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
              const isAllDay = Boolean(event.start?.date && !event.start?.dateTime);
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
                          {isAllDay ? (
                            <>{DateUtils.format(startDate, "MMM d, yyyy")} - All day</>
                          ) : (
                            <>
                              {DateUtils.format(startDate, "MMM d, yyyy h:mm a")}
                              {endDate && ` - ${DateUtils.format(endDate, "h:mm a")}`}
                            </>
                          )}
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
                        className="text-sm text-primary hover:underline"
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
