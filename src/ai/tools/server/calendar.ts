/**
 * @fileoverview Calendar tools for AI SDK v6.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import {
  calendarEventSchema,
  createCalendarEventInputSchema,
  createCalendarEventOutputSchema,
  createEventRequestSchema,
  type EventDateTime,
  exportItineraryToIcsInputSchema,
  exportItineraryToIcsOutputSchema,
  freeBusyToolInputSchema,
  getAvailabilityOutputSchema,
} from "@schemas/calendar";
import { createEvent, queryFreeBusy } from "@/lib/calendar/google";
import { generateIcsFromEvents } from "@/lib/calendar/ics";

function parseDateOrUndefined(value?: string): Date | undefined {
  if (!value) return undefined;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`Invalid date string: ${value}`);
  }
  return parsed;
}

/**
 * Normalizes tool input date/time to EventDateTime format.
 */
function normalizeEventDateTime(value: {
  date?: string;
  dateTime?: string;
  timeZone?: string;
}): EventDateTime {
  return {
    date: value.date,
    dateTime: parseDateOrUndefined(value.dateTime),
    timeZone: value.timeZone,
  };
}

/**
 * Creates calendar events in Google Calendar.
 */
export const createCalendarEvent = createAiTool({
  description: "Create a calendar event in the user's Google Calendar.",
  execute: async (params) => {
    try {
      const payload = {
        ...params,
        end: normalizeEventDateTime(params.end),
        start: normalizeEventDateTime(params.start),
      };
      const toIsoDateTime = (value: EventDateTime): string => {
        if (value.dateTime) {
          return value.dateTime instanceof Date
            ? value.dateTime.toISOString()
            : value.dateTime;
        }
        if (value.date) {
          const parsed = parseDateOrUndefined(value.date);
          if (!parsed) {
            throw new Error("calendar_event_missing_datetime");
          }
          return parsed.toISOString();
        }
        throw new Error("calendar_event_missing_datetime");
      };
      const { calendarId, ...eventData } = payload;
      const parsedEventData = createEventRequestSchema.parse(eventData);
      const result = await createEvent(parsedEventData, calendarId);
      if (!result.id) {
        return { error: "calendar_event_missing_id", success: false } as const;
      }
      return {
        end: toIsoDateTime(result.end),
        eventId: result.id,
        htmlLink: result.htmlLink,
        start: toIsoDateTime(result.start),
        success: true,
        summary: result.summary,
      } as const;
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : "Unknown error",
        success: false,
      } as const;
    }
  },
  guardrails: {
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 10,
      window: "1 m",
    },
  },
  inputSchema: createCalendarEventInputSchema,
  name: "createCalendarEvent",
  outputSchema: createCalendarEventOutputSchema,
  validateOutput: true,
});

/**
 * Checks calendar availability and free/busy status.
 */
export const getAvailability = createAiTool({
  description: "Check calendar availability (free/busy) for specified calendars.",
  execute: async (params) => {
    try {
      const result = await queryFreeBusy({
        ...params,
        timeMax: new Date(params.timeMax),
        timeMin: new Date(params.timeMin),
      });
      return {
        calendars: Object.entries(result.calendars).map(([id, data]) => ({
          busy: (data as { busy?: Array<{ start: string; end: string }> }).busy || [],
          calendarId: id,
        })),
        success: true,
        timeMax: result.timeMax.toISOString(),
        timeMin: result.timeMin.toISOString(),
      } as const;
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : "Unknown error",
        success: false,
      } as const;
    }
  },
  guardrails: {
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 20,
      window: "1 m",
    },
  },
  inputSchema: freeBusyToolInputSchema,
  name: "getAvailability",
  outputSchema: getAvailabilityOutputSchema,
  validateOutput: true,
});

/**
 * Exports calendar events to ICS format.
 */
export const exportItineraryToIcs = createAiTool({
  description: "Export a list of calendar events to ICS (iCalendar) format.",
  // biome-ignore lint/suspicious/useAwait: createAiTool requires Promise return type
  execute: async (params) => {
    try {
      const normalizedEvents = params.events.map((event) =>
        calendarEventSchema.parse({
          ...event,
          created: parseDateOrUndefined(event.created),
          end: normalizeEventDateTime(event.end),
          start: normalizeEventDateTime(event.start),
          updated: parseDateOrUndefined(event.updated),
        })
      );

      const { icsString, eventCount } = generateIcsFromEvents({
        calendarName: params.calendarName,
        events: normalizedEvents,
        timezone: params.timezone ?? undefined,
      });

      return {
        calendarName: params.calendarName,
        eventCount,
        icsContent: icsString,
        success: true,
      } as const;
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : "Unknown error",
        success: false,
      } as const;
    }
  },
  guardrails: {
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 5,
      window: "1 m",
    },
  },
  inputSchema: exportItineraryToIcsInputSchema,
  name: "exportItineraryToIcs",
  outputSchema: exportItineraryToIcsOutputSchema,
  validateOutput: true,
});
