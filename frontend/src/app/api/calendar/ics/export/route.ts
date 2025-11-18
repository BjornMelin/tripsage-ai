/**
 * @fileoverview ICS export endpoint.
 *
 * Generates ICS file from events payload. Supports caching for performance.
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import ical from "ical-generator";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { RecurringDateGenerator } from "@/lib/dates/recurring-rules";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import { type IcsExportRequest, icsExportRequestSchema } from "@/lib/schemas/calendar";

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
})(
  async (
    req: NextRequest,
    _context,
    validated: IcsExportRequest
  ): Promise<NextResponse> => {
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

    // Generate ICS string
    const icsString = calendar.toString();

    return new NextResponse(icsString, {
      headers: {
        "Content-Disposition": `attachment; filename="${validated.calendarName.replace(/[^a-z0-9]/gi, "_")}.ics"`,
        "Content-Type": "text/calendar; charset=utf-8",
      },
      status: 200,
    });
  }
);
