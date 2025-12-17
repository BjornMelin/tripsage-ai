/**
 * @fileoverview Calendar tools for AI SDK v6.
 *
 * Provides tools for creating calendar events, checking availability, and
 * exporting itineraries to ICS format.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import {
  createCalendarEventInputSchema,
  exportItineraryToIcsInputSchema,
  freeBusyRequestSchema,
} from "@schemas/calendar";
import { createEvent, queryFreeBusy } from "@/lib/calendar/google";
import { generateIcsFromEvents } from "@/lib/calendar/ics";

/**
 * Creates calendar events in Google Calendar.
 */
export const createCalendarEvent = createAiTool({
  description: "Create a calendar event in the user's Google Calendar.",
  execute: async (params) => {
    try {
      const { calendarId, ...eventData } = params;
      const result = await createEvent(eventData, calendarId);
      return {
        end: result.end,
        eventId: result.id,
        htmlLink: result.htmlLink,
        start: result.start,
        success: true,
        summary: result.summary,
      };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : "Unknown error",
        success: false,
      };
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
});

/**
 * Checks calendar availability and free/busy status.
 */
export const getAvailability = createAiTool({
  description: "Check calendar availability (free/busy) for specified calendars.",
  execute: async (params) => {
    try {
      const result = await queryFreeBusy(params);
      return {
        calendars: Object.entries(result.calendars).map(([id, data]) => ({
          busy: (data as { busy?: Array<{ start: string; end: string }> }).busy || [],
          calendarId: id,
        })),
        success: true,
        timeMax: result.timeMax.toISOString(),
        timeMin: result.timeMin.toISOString(),
      };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : "Unknown error",
        success: false,
      };
    }
  },
  guardrails: {
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 20,
      window: "1 m",
    },
  },
  inputSchema: freeBusyRequestSchema,
  name: "getAvailability",
});

/**
 * Exports calendar events to ICS format.
 */
export const exportItineraryToIcs = createAiTool({
  description: "Export a list of calendar events to ICS (iCalendar) format.",
  // biome-ignore lint/suspicious/useAwait: createAiTool requires Promise return type
  execute: async (params) => {
    try {
      const { icsString, eventCount } = generateIcsFromEvents({
        calendarName: params.calendarName,
        events: params.events,
        timezone: params.timezone ?? undefined,
      });

      return {
        calendarName: params.calendarName,
        eventCount,
        icsContent: icsString,
        success: true,
      };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : "Unknown error",
        success: false,
      };
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
});
