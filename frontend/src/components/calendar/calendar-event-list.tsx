/**
 * @fileoverview Server Component for displaying calendar events list.
 */

import { Calendar, Clock, MapPin } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { listEvents } from "@/lib/calendar/google";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import { createServerLogger } from "@/lib/telemetry/logger";

const CalendarEventLogger = createServerLogger("component.calendar-event-list");

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
 * Fetches Calendar events server-side and renders a summarized list in a card.
 *
 * @param props - Optional calendar id and time range plus styling hook.
 * @returns Server component output with event list.
 */
export async function CalendarEventList({
  calendarId = "primary",
  timeMin,
  timeMax,
  className,
}: CalendarEventListProps) {
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
    const result = await listEvents({
      calendarId,
      timeMax,
      timeMin,
    });
    events = result.items || [];
  } catch (error) {
    CalendarEventLogger.error("Failed to fetch calendar events", {
      calendarId,
      error: error instanceof Error ? error.message : String(error),
      timeMax: timeMax?.toISOString(),
      timeMin: timeMin?.toISOString(),
    });
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
                ? DateUtils.parse(event.start.dateTime)
                : event.start.date
                  ? DateUtils.parse(event.start.date)
                  : null;
              const endDate = event.end.dateTime
                ? DateUtils.parse(event.end.dateTime)
                : event.end.date
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
                          <Clock className="h-4 w-4" />
                          {DateUtils.format(startDate, "MMM d, yyyy h:mm a")}
                          {endDate && ` - ${DateUtils.format(endDate, "h:mm a")}`}
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
