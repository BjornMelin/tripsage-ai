/**
 * @fileoverview Server Component for displaying calendar events list.
 */

import { format } from "date-fns";
import { Calendar, Clock, MapPin } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/**
 * Props for CalendarEventList component.
 */
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
 * CalendarEventList component.
 *
 * Server Component that fetches and displays calendar events.
 */
export async function CalendarEventList({
  calendarId = "primary",
  timeMin,
  timeMax,
  className,
}: CalendarEventListProps) {
  // Build query parameters
  const params = new URLSearchParams({
    calendarId,
  });

  if (timeMin) {
    params.set("timeMin", timeMin.toISOString());
  }
  if (timeMax) {
    params.set("timeMax", timeMax.toISOString());
  }

  // Fetch events
  let events: Array<{
    id: string;
    summary: string;
    description?: string;
    location?: string;
    start: { dateTime?: string; date?: string };
    end: { dateTime?: string; date?: string };
    htmlLink?: string;
  }> = [];

  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"}/api/calendar/events?${params.toString()}`,
      {
        cache: "no-store",
      }
    );
    if (response.ok) {
      const data = await response.json();
      events = data.items || [];
    }
  } catch (error) {
    console.error("Failed to fetch calendar events:", error);
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calendar className="h-5 w-5" />
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
              const startDate = event.start.dateTime
                ? new Date(event.start.dateTime)
                : event.start.date
                  ? new Date(event.start.date)
                  : null;
              const endDate = event.end.dateTime
                ? new Date(event.end.dateTime)
                : event.end.date
                  ? new Date(event.end.date)
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
                          <Clock className="h-4 w-4" />
                          {format(startDate, "MMM d, yyyy h:mm a")}
                          {endDate && ` - ${format(endDate, "h:mm a")}`}
                        </div>
                      )}
                      {event.location && (
                        <div className="flex items-center gap-1">
                          <MapPin className="h-4 w-4" />
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
