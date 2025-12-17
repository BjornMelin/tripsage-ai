/**
 * Pure ICS (iCalendar) generation utilities.
 *
 * Extracts calendar event data into RFC 5545 compliant ICS format.
 * Used by both the API route handler and AI tools to ensure consistent output.
 */

import type { CalendarEvent } from "@schemas/calendar";
import ical from "ical-generator";
import { RecurringDateGenerator } from "@/lib/dates/recurring-rules";
import { DateUtils } from "@/lib/dates/unified-date-utils";

/**
 * Options for ICS generation.
 */
export interface GenerateIcsOptions {
  /** Name for the calendar in the ICS file. */
  calendarName: string;
  /** Events to include in the calendar. */
  events: CalendarEvent[];
  /** Timezone for the calendar (defaults to UTC). */
  timezone?: string;
}

/**
 * Result of ICS generation.
 */
export interface GenerateIcsResult {
  /** Generated ICS string content. */
  icsString: string;
  /** Number of events included. */
  eventCount: number;
}

/**
 * Converts an attendee response status to the canonical iCal constant.
 *
 * @param status - Google Calendar style attendee status.
 * @returns iCal attendee status string.
 */
function eventAttendeeStatusToIcal(
  status: string
): "ACCEPTED" | "DECLINED" | "TENTATIVE" | "NEEDS-ACTION" {
  switch (status) {
    case "accepted":
      return "ACCEPTED";
    case "declined":
      return "DECLINED";
    case "tentative":
      return "TENTATIVE";
    default:
      return "NEEDS-ACTION";
  }
}

/**
 * Normalizes reminder methods to the subset supported by iCal alarms.
 *
 * @param method - Notification channel provided by Google events.
 * @returns Alarm type accepted by ical-generator.
 */
function reminderMethodToIcal(method: string): "display" | "email" | "audio" {
  switch (method) {
    case "email":
      return "email";
    default:
      return "display";
  }
}

/**
 * Generates an ICS (iCalendar) string from calendar events.
 *
 * This is a pure function with no side effects - it takes event data
 * and produces an ICS string. No authentication, HTTP calls, or I/O.
 *
 * @param options - Calendar name, events, and optional timezone.
 * @returns Generated ICS string and event count.
 *
 * @example
 * ```typescript
 * const { icsString, eventCount } = generateIcsFromEvents({
 *   calendarName: "My Trip",
 *   events: [{ summary: "Flight", start: {...}, end: {...} }],
 *   timezone: "America/New_York",
 * });
 * ```
 */
export function generateIcsFromEvents(options: GenerateIcsOptions): GenerateIcsResult {
  const { calendarName, events, timezone = "UTC" } = options;

  // Create calendar
  const calendar = ical({
    name: calendarName,
    timezone,
  });

  // Add events
  for (const event of events) {
    const startDate =
      event.start.dateTime instanceof Date
        ? event.start.dateTime
        : event.start.date
          ? DateUtils.parse(event.start.date)
          : new Date();

    const endDate =
      event.end.dateTime instanceof Date
        ? event.end.dateTime
        : event.end.date
          ? DateUtils.parse(event.end.date)
          : DateUtils.add(startDate, 1, "hours"); // Default 1 hour

    const eventData = {
      description: event.description,
      end: endDate,
      location: event.location,
      start: startDate,
      summary: event.summary,
      ...(event.recurrence?.length
        ? {
            recurrence: [
              RecurringDateGenerator.toRRule(
                RecurringDateGenerator.parseRRule(event.recurrence[0])
              ),
            ],
          }
        : {}),
      ...(event.iCalUID ? { uid: event.iCalUID } : {}),
      ...(event.created ? { created: event.created } : {}),
      ...(event.updated ? { lastModified: event.updated } : {}),
    };

    const ev = calendar.createEvent(eventData);

    if (event.attendees?.length) {
      for (const att of event.attendees) {
        ev.createAttendee({
          email: att.email,
          name: att.displayName,
          rsvp: !att.optional,
          // biome-ignore lint/suspicious/noExplicitAny: third-party type casting for ical types
          status: eventAttendeeStatusToIcal(att.responseStatus) as unknown as any,
        });
      }
    }

    if (event.reminders?.overrides?.length) {
      for (const rem of event.reminders.overrides) {
        ev.createAlarm({
          trigger: rem.minutes * 60, // seconds
          // biome-ignore lint/suspicious/noExplicitAny: third-party type casting for ical types
          type: reminderMethodToIcal(rem.method) as unknown as any,
        });
      }
    }
  }

  return {
    eventCount: events.length,
    icsString: calendar.toString(),
  };
}

/**
 * Sanitizes a calendar name for use as a filename.
 *
 * Replaces non-alphanumeric characters with underscores.
 *
 * @param name - Calendar name to sanitize.
 * @returns Sanitized filename (without extension).
 */
export function sanitizeCalendarFilename(name: string): string {
  return name.replace(/[^a-z0-9]/gi, "_");
}
