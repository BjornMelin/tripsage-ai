/**
 * @fileoverview Calendar test data factories.
 */

import type { CalendarEvent } from "@schemas/calendar";
import { calendarEventSchema } from "@schemas/calendar";

let eventIdCounter = 1;

export const createCalendarEvent = (
  overrides: Partial<CalendarEvent> = {}
): CalendarEvent => {
  const now = new Date();
  const start = overrides.start ?? { dateTime: now };
  const end = overrides.end ?? { dateTime: new Date(now.getTime() + 3_600_000) };
  const base: CalendarEvent = {
    attendees: [],
    attendeesOmitted: false,
    created: now,
    end,
    endTimeUnspecified: false,
    htmlLink: "https://example.com/calendar/event",
    iCalUID: `ical-${eventIdCounter}`,
    id: overrides.id ?? `event-${eventIdCounter++}`,
    organizer: { displayName: "TripSage", email: "events@tripsage.ai", self: true },
    reminders: { useDefault: true },
    sequence: 0,
    start,
    status: "confirmed",
    summary: overrides.summary ?? "Test Event",
    transparency: "opaque",
    updated: now,
    visibility: "default",
    ...overrides,
  };
  return calendarEventSchema.parse(base);
};

export const resetCalendarFactory = () => {
  eventIdCounter = 1;
};
