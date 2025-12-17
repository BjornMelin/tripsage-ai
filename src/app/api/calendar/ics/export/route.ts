/**
 * @fileoverview POST /api/calendar/ics/export generates an ICS file from a validated events payload.
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import { type IcsExportRequest, icsExportRequestSchema } from "@schemas/calendar";
import ical, { ICalAlarmType, ICalAttendeeStatus } from "ical-generator";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { RecurringDateGenerator } from "@/lib/dates/recurring-rules";
import { DateUtils } from "@/lib/dates/unified-date-utils";

/**
 * Converts an attendee response status to the canonical iCal constant.
 *
 * @param status - Google Calendar style attendee status.
 * @returns iCal attendee status string.
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
 * @returns Alarm type accepted by ical-generator.
 */
function reminderMethodToIcal(
  method: "email" | "popup" | "sms" | string
): ICalAlarmType {
  switch (method) {
    case "email":
      return ICalAlarmType.email;
    default:
      return ICalAlarmType.display;
  }
}

/**
 * Handles the ICS export request by validating payloads, enforcing rate
 * limits, and returning the generated calendar file.
 *
 * @param req - HTTP request containing calendar metadata and Google-style events.
 * @param routeContext - Route context from withApiGuards
 * @returns Response with the ICS attachment or JSON error payload.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "calendar:ics:export",
  schema: icsExportRequestSchema,
  telemetry: "calendar.ics.export",
})((_req: NextRequest, _context, validated: IcsExportRequest): NextResponse => {
  // Create calendar
  const calendar = ical({
    name: validated.calendarName,
    timezone: validated.timezone || "UTC",
  });

  // Add events
  for (const event of validated.events) {
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

  // Generate ICS string
  const icsString = calendar.toString();

  return new NextResponse(icsString, {
    headers: {
      "Content-Disposition": `attachment; filename="${validated.calendarName.replace(/[^a-z0-9]/gi, "_")}.ics"`,
      "Content-Type": "text/calendar; charset=utf-8",
    },
    status: 200,
  });
});
