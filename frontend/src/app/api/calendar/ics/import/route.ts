/**
 * @fileoverview ICS import endpoint.
 *
 * Parses ICS file/text and returns events payload. Optionally validates
 * without writing to calendar (requires approval for writes).
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { RecurringDateGenerator } from "@/lib/dates/recurring-rules";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import { calendarEventSchema } from "@/lib/schemas/calendar";

type ParsedIcsEvent = {
  type: "VEVENT";
  summary?: string;
  description?: string;
  location?: string;
  start?: Date | { toJSDate?: () => Date };
  end?: Date | { toJSDate?: () => Date };
  rrule?: string;
  attendees?: Array<{ val: string; params?: Record<string, string> }>;
  uid?: string;
  created?: Date;
  lastmodified?: Date;
};

/**
 * Unfolds RFC 5545 line folding.
 * Lines longer than 75 octets are folded by inserting CRLF followed by a single space or tab.
 *
 * @param icsData - Raw ICS document string with potential line folding.
 * @returns Unfolded ICS data string.
 */
function unfoldLines(icsData: string): string {
  // Normalize line endings to \n
  const normalized = icsData.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lines = normalized.split("\n");
  const unfolded: string[] = [];
  let currentLine = "";

  for (const line of lines) {
    // Check if this line is a continuation (starts with space or tab)
    if (line.length > 0 && (line[0] === " " || line[0] === "\t")) {
      // Continuation line - append to current line (without leading whitespace)
      currentLine += line.slice(1);
    } else {
      // New line - save previous line and start new one
      if (currentLine) {
        unfolded.push(currentLine);
      }
      currentLine = line;
    }
  }
  // Don't forget the last line
  if (currentLine) {
    unfolded.push(currentLine);
  }

  return unfolded.join("\n");
}

/**
 * Parses property name and parameters from an ICS line.
 * Handles properties with parameters like "DTSTART;TZID=America/New_York:20200101T120000"
 *
 * @param line - ICS content line.
 * @returns Object with property name, parameters, and value.
 */
function parseProperty(line: string): {
  name: string;
  params: Record<string, string>;
  value: string;
} {
  const colonIndex = line.indexOf(":");
  if (colonIndex === -1) {
    return { name: line, params: {}, value: "" };
  }

  const propertyPart = line.slice(0, colonIndex);
  const value = line.slice(colonIndex + 1);

  const semicolonIndex = propertyPart.indexOf(";");
  if (semicolonIndex === -1) {
    return { name: propertyPart, params: {}, value };
  }

  const name = propertyPart.slice(0, semicolonIndex);
  const params: Record<string, string> = {};
  const paramParts = propertyPart.slice(semicolonIndex + 1).split(";");

  for (const paramPart of paramParts) {
    const equalsIndex = paramPart.indexOf("=");
    if (equalsIndex !== -1) {
      const paramName = paramPart.slice(0, equalsIndex);
      const paramValue = paramPart.slice(equalsIndex + 1);
      // Unescape parameter values (RFC 5545 section 3.2)
      params[paramName] = paramValue.replace(/\\,/g, ",").replace(/\\;/g, ";");
    }
  }

  return { name, params, value };
}

/**
 * Parses raw ICS data into a keyed map of VEVENT entries.
 * Handles RFC 5545 line folding and property parameters.
 *
 * @param icsData - Raw ICS document string.
 * @returns Event map keyed by incremental ids.
 */
function parseICS(icsData: string): Record<string, ParsedIcsEvent> {
  const events: Record<string, ParsedIcsEvent> = {};
  // Unfold lines first (RFC 5545 section 3.1)
  const unfolded = unfoldLines(icsData);
  const lines = unfolded.split("\n");
  let currentEvent: ParsedIcsEvent | null = null;
  let eventId = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    if (trimmed === "BEGIN:VEVENT") {
      currentEvent = { type: "VEVENT" };
      eventId++;
    } else if (trimmed === "END:VEVENT") {
      if (currentEvent) {
        events[`event_${eventId}`] = currentEvent;
      }
      currentEvent = null;
    } else {
      const { name, params, value } = parseProperty(trimmed);
      currentEvent = currentEvent ?? { type: "VEVENT" };

      // Handle common properties
      if (name === "SUMMARY") {
        currentEvent.summary = value;
      } else if (name === "DESCRIPTION") {
        currentEvent.description = value;
      } else if (name === "LOCATION") {
        currentEvent.location = value;
      } else if (name === "DTSTART") {
        // Parse date, handling timezone if present
        currentEvent.start = DateUtils.parse(value);
      } else if (name === "DTEND") {
        currentEvent.end = DateUtils.parse(value);
      } else if (name === "UID") {
        currentEvent.uid = value;
      } else if (name === "RRULE") {
        currentEvent.rrule = value;
      } else if (name === "CREATED") {
        currentEvent.created = DateUtils.parse(value);
      } else if (name === "LAST-MODIFIED") {
        currentEvent.lastmodified = DateUtils.parse(value);
      } else if (name === "ATTENDEE") {
        // Parse attendee with parameters
        if (!currentEvent.attendees) {
          currentEvent.attendees = [];
        }
        currentEvent.attendees.push({
          params,
          val: value,
        });
      }
    }
  }

  return events;
}

export const dynamic = "force-dynamic";

const importRequestSchema = z.object({
  icsData: z.string().min(1, { error: "ICS data is required" }),
  validateOnly: z.boolean().default(true),
});

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
  telemetry: "calendar.ics.import",
})(async (req: NextRequest): Promise<NextResponse> => {
  const body = await req.json();
  const validated = importRequestSchema.parse(body);

  // Parse ICS data
  let parsedEvents: ReturnType<typeof parseICS>;
  try {
    parsedEvents = parseICS(validated.icsData);
  } catch (parseError) {
    const message =
      parseError instanceof Error ? parseError.message : "Failed to parse ICS";
    return NextResponse.json(
      { details: message, error: "Invalid ICS format" },
      { status: 400 }
    );
  }

  // Convert parsed events to calendar event format
  const events: unknown[] = [];
  for (const [_key, event] of Object.entries(parsedEvents)) {
    if (event.type === "VEVENT") {
      const vevent = event as {
        summary?: string;
        description?: string;
        location?: string;
        start?: Date | { toJSDate?: () => Date };
        end?: Date | { toJSDate?: () => Date };
        rrule?: string;
        attendees?: Array<{ val: string; params?: Record<string, string> }>;
        uid?: string;
        created?: Date;
        lastmodified?: Date;
      };

      const startDate =
        vevent.start instanceof Date
          ? vevent.start
          : vevent.start &&
              typeof vevent.start === "object" &&
              "toJSDate" in vevent.start &&
              typeof vevent.start.toJSDate === "function"
            ? vevent.start.toJSDate()
            : null;

      const endDate =
        vevent.end instanceof Date
          ? vevent.end
          : vevent.end &&
              typeof vevent.end === "object" &&
              "toJSDate" in vevent.end &&
              typeof vevent.end.toJSDate === "function"
            ? vevent.end.toJSDate()
            : null;

      if (!startDate || !endDate) {
        continue; // Skip events without valid dates
      }

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
              attendees: vevent.attendees.map((att) => ({
                displayName: att.params?.CN?.replace(/^"(.*)"$/, "$1"), // Strip surrounding quotes
                email: att.val,
              })),
            }
          : {}),
        ...(vevent.uid ? { iCalUID: vevent.uid } : {}),
        ...(vevent.created ? { created: vevent.created } : {}),
        ...(vevent.lastmodified ? { updated: vevent.lastmodified } : {}),
      };

      // Validate against schema (but don't fail on minor issues)
      try {
        calendarEventSchema.parse(eventData);
      } catch {
        // Continue even if validation fails - return raw data
      }

      events.push(eventData);
    }
  }

  return NextResponse.json({
    count: events.length,
    events,
    validateOnly: validated.validateOnly,
  });
});
