/**
 * @fileoverview ICS import endpoint.
 *
 * Parses ICS file/text and returns events payload. Optionally validates
 * without writing to calendar (requires approval for writes).
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import {
  calendarEventSchema,
  type IcsImportRequest,
  icsImportRequestSchema,
} from "@schemas/calendar";
import ICAL from "ical.js";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { RecurringDateGenerator } from "@/lib/dates/recurring-rules";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import { createServerLogger } from "@/lib/telemetry/logger";

/** Parsed ICS event structure from ical.js. */
type ParsedIcsEvent = {
  type: "VEVENT";
  summary?: string;
  description?: string;
  location?: string;
  start?: Date;
  end?: Date;
  rrule?: string;
  attendees?: Array<{ val: string; params?: Record<string, string> }>;
  uid?: string;
  created?: Date;
  lastmodified?: Date;
};

/**
 * Parses raw ICS data into a keyed map of VEVENT entries using ical.js library.
 * Handles RFC 5545 compliance, line folding, property parameters, and timezone handling.
 *
 * @param icsData - Raw ICS document string.
 * @returns Event map keyed by incremental ids.
 */
function parseICS(icsData: string): Record<string, ParsedIcsEvent> {
  const events: Record<string, ParsedIcsEvent> = {};

  try {
    // Parse ICS data into jCal format
    const jcal = ICAL.parse(icsData);
    const component = new ICAL.Component(jcal);
    const vevents = component.getAllSubcomponents("vevent");

    let eventId = 0;
    for (const veventComp of vevents) {
      eventId++;
      const event = new ICAL.Event(veventComp);

      const parsedEvent: ParsedIcsEvent = {
        type: "VEVENT",
      };

      // Extract basic properties
      if (event.summary) {
        parsedEvent.summary = event.summary;
      }
      if (event.description) {
        parsedEvent.description = event.description;
      }
      if (event.location) {
        parsedEvent.location = event.location;
      }
      if (event.uid) {
        parsedEvent.uid = event.uid;
      }

      // Extract dates (ical.js handles timezone conversion)
      if (event.startDate) {
        parsedEvent.start = event.startDate.toJSDate();
      }
      if (event.endDate) {
        parsedEvent.end = event.endDate.toJSDate();
      }

      // Extract RRULE
      const rruleProp = veventComp.getFirstProperty("rrule");
      if (rruleProp) {
        const rrule = rruleProp.getFirstValue();
        if (rrule instanceof ICAL.Recur) {
          parsedEvent.rrule = rrule.toString();
        }
      }

      // Extract CREATED and LAST-MODIFIED
      const createdProp = veventComp.getFirstProperty("created");
      if (createdProp) {
        const created = createdProp.getFirstValue();
        if (created instanceof ICAL.Time) {
          parsedEvent.created = created.toJSDate();
        }
      }

      const lastModifiedProp = veventComp.getFirstProperty("last-modified");
      if (lastModifiedProp) {
        const lastModified = lastModifiedProp.getFirstValue();
        if (lastModified instanceof ICAL.Time) {
          parsedEvent.lastmodified = lastModified.toJSDate();
        }
      }

      // Extract attendees with parameters
      const attendeeProps = veventComp.getAllProperties("attendee");
      if (attendeeProps.length > 0) {
        parsedEvent.attendees = attendeeProps.map((prop) => {
          const params: Record<string, string> = {};
          // Common attendee parameters
          const commonParams = ["cn", "cutype", "role", "partstat", "rsvp"];
          for (const paramName of commonParams) {
            const paramValue = prop.getParameter(paramName);
            if (paramValue) {
              // Parameter names are case-insensitive in ICS, normalize to uppercase
              params[paramName.toUpperCase()] = Array.isArray(paramValue)
                ? paramValue[0]
                : paramValue;
            }
          }
          // Convert value to string (attendee values are typically mailto: URLs)
          const value = prop.getFirstValue();
          const valString = typeof value === "string" ? value : String(value || "");
          return {
            params,
            val: valString,
          };
        });
      }

      events[`event_${eventId}`] = parsedEvent;
    }
  } catch (error) {
    // If parsing fails, throw error to be caught by caller
    throw new Error(
      `Failed to parse ICS: ${error instanceof Error ? error.message : String(error)}`
    );
  }

  return events;
}

/**
 * Validates ICS payloads, performs rudimentary parsing, and returns structured
 * event objects while applying rate limiting and auth guards.
 *
 * @param req - Request containing raw ICS data and validation flag.
 * @param routeContext - Route context from withApiGuards
 * @returns Response containing normalized events or an error payload.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "calendar:ics:import",
  schema: icsImportRequestSchema,
  telemetry: "calendar.ics.import",
})((_req: NextRequest, _context, validated: IcsImportRequest): NextResponse => {
  const logger = createServerLogger("calendar.ics.import");
  // Parse ICS data
  let parsedEvents: ReturnType<typeof parseICS>;
  try {
    parsedEvents = parseICS(validated.icsData);
  } catch (parseError) {
    return errorResponse({
      err: parseError,
      error: "invalid_request",
      reason: "Invalid ICS format",
      status: 400,
    });
  }

  // Convert parsed events to calendar event format
  const events: unknown[] = [];
  for (const [_key, event] of Object.entries(parsedEvents)) {
    if (event.type === "VEVENT") {
      const vevent = event as ParsedIcsEvent;

      if (!vevent.start || !vevent.end) {
        continue; // Skip events without valid dates
      }

      const startDate = vevent.start;
      const endDate = vevent.end;

      const eventData = {
        description: vevent.description,
        end: {
          dateTime: DateUtils.formatForApi(endDate),
        },
        location: vevent.location,
        start: {
          dateTime: DateUtils.formatForApi(startDate),
        },
        summary: vevent.summary || "Untitled Event",
        ...(vevent.rrule
          ? {
              recurrence: [
                RecurringDateGenerator.toRRule(
                  RecurringDateGenerator.parseRRule(vevent.rrule)
                ),
              ],
            }
          : {}),
        ...(vevent.attendees?.length
          ? {
              attendees: vevent.attendees.map((att) => {
                // Strip mailto: prefix from email if present
                const email = att.val.startsWith("mailto:")
                  ? att.val.slice(7)
                  : att.val;
                return {
                  displayName: att.params?.CN?.replace(/^"(.*)"$/, "$1"), // Strip surrounding quotes
                  email,
                };
              }),
            }
          : {}),
        ...(vevent.uid ? { iCalUID: vevent.uid } : {}),
        ...(vevent.created ? { created: vevent.created } : {}),
        ...(vevent.lastmodified ? { updated: vevent.lastmodified } : {}),
      };

      // Validate against schema - use parsed result or skip invalid events
      const parsedEvent = calendarEventSchema.safeParse(eventData);
      if (!parsedEvent.success) {
        // Log validation error but skip invalid events
        logger.warn("ics_import:invalid_event_skipped", {
          errors: parsedEvent.error.issues,
          eventSummary: vevent.summary,
        });
        continue;
      }

      events.push(parsedEvent.data);
    }
  }

  return NextResponse.json({
    count: events.length,
    events,
    validateOnly: validated.validateOnly,
  });
});
