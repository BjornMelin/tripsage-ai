/**
 * Pure ICS (iCalendar) generation utilities.
 *
 * Extracts calendar event data into RFC 5545 compliant ICS format.
 * Used by both the API route handler and AI tools to ensure consistent output.
 */

import type { CalendarEvent } from "@schemas/calendar";
import ical, { ICalAlarmType, ICalAttendeeStatus } from "ical-generator";
import { RecurringDateGenerator } from "@/lib/dates/recurring-rules";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import { createServerLogger } from "@/lib/telemetry/logger";

/** Logger for ICS generation operations. */
const logger = createServerLogger("calendar.ics");

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
 * @returns iCal attendee status enum value.
 */
function eventAttendeeStatusToIcal(status: string): ICalAttendeeStatus {
  switch (status) {
    case "accepted":
      return ICalAttendeeStatus.ACCEPTED;
    case "declined":
      return ICalAttendeeStatus.DECLINED;
    case "tentative":
      return ICalAttendeeStatus.TENTATIVE;
    default:
      return ICalAttendeeStatus.NEEDSACTION;
  }
}

/**
 * Normalizes reminder methods to the subset supported by iCal alarms.
 *
 * @param method - Notification channel provided by Google events.
 * @returns Alarm type enum value accepted by ical-generator.
 */
function reminderMethodToIcal(method: string): ICalAlarmType {
  switch (method) {
    case "email":
      return ICalAlarmType.email;
    default:
      return ICalAlarmType.display;
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
    let startDate: Date;
    if (event.start.dateTime instanceof Date) {
      startDate = event.start.dateTime;
    } else if (event.start.date) {
      startDate = DateUtils.parse(event.start.date);
    } else {
      logger.warn("Event missing start date, using current time", {
        eventId: event.id,
        eventSummary: event.summary,
      });
      startDate = new Date();
    }

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
          status: eventAttendeeStatusToIcal(att.responseStatus),
        });
      }
    }

    if (event.reminders?.overrides?.length) {
      for (const rem of event.reminders.overrides) {
        ev.createAlarm({
          trigger: rem.minutes * 60, // seconds
          type: reminderMethodToIcal(rem.method),
        });
      }
    }
  }

  return {
    eventCount: events.length,
    icsString: calendar.toString(),
  };
}

/** Default filename used when input produces empty result. */
const DEFAULT_CALENDAR_FILENAME = "calendar";

/** Maximum filename length for filesystem safety. */
const MAX_FILENAME_LENGTH = 200;

/**
 * Sanitizes a calendar name for use as a filename.
 *
 * Replaces non-alphanumeric characters with underscores, collapses consecutive
 * underscores, trims leading/trailing underscores, and enforces length limits.
 *
 * @param name - Calendar name to sanitize.
 * @returns Sanitized filename (without extension), or "calendar" if empty.
 */
export function sanitizeCalendarFilename(name: string): string {
  const sanitized = name
    .replace(/[^a-z0-9]/gi, "_") // Replace non-alphanumeric with underscores
    .replace(/_+/g, "_") // Collapse consecutive underscores
    .replace(/^_|_$/g, ""); // Trim leading/trailing underscores

  // Return default for empty/all-special-char names
  if (!sanitized) {
    return DEFAULT_CALENDAR_FILENAME;
  }

  // Enforce length limit for filesystem safety
  return sanitized.slice(0, MAX_FILENAME_LENGTH);
}
