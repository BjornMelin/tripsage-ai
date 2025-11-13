/**
 * @fileoverview Calendar tools for AI SDK v6.
 *
 * Provides tools for creating calendar events, checking availability, and
 * exporting itineraries to ICS format.
 */

import "server-only";

import { tool } from "ai";
import { z } from "zod";
import { createEvent, queryFreeBusy } from "@/lib/calendar/google";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import {
  calendarEventSchema,
  createEventRequestSchema,
  freeBusyRequestSchema,
} from "@/lib/schemas/calendar";

/**
 * Type assertion to allow any tool options.
 */
const toolAny = tool as unknown as (opts: Record<string, unknown>) => unknown;

/**
 * Zod input schema for create calendar event tool.
 */
export const createCalendarEventInputSchema = createEventRequestSchema.extend({
  calendarId: z.string().default("primary"),
});

/**
 * Create calendar event tool.
 *
 * Creates a new event in the user's Google Calendar.
 */
export const createCalendarEvent = toolAny({
  description:
    "Create a calendar event in the user's Google Calendar. Use this to add " +
    "travel-related events, meetings, or activities to their calendar.",
  execute: async (params: z.infer<typeof createCalendarEventInputSchema>) => {
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
      const message = error instanceof Error ? error.message : "Unknown error";
      return {
        error: message,
        success: false,
      };
    }
  },
  parameters: createCalendarEventInputSchema,
});

/**
 * Zod input schema for get availability tool.
 */
export const getAvailabilityInputSchema = freeBusyRequestSchema;

/**
 * Get availability tool.
 *
 * Queries free/busy information for specified calendars to check availability.
 */
export const getAvailability = toolAny({
  description:
    "Check calendar availability (free/busy) for specified calendars within " +
    "a time range. Use this to find available time slots for scheduling.",
  execute: async (params: z.infer<typeof getAvailabilityInputSchema>) => {
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
      const message = error instanceof Error ? error.message : "Unknown error";
      return {
        error: message,
        success: false,
      };
    }
  },
  parameters: getAvailabilityInputSchema,
});

/**
 * Zod input schema for export itinerary to ICS tool.
 */
// biome-ignore lint/style/useNamingConvention: ICS is a standard file format acronym
export const exportItineraryToICSInputSchema = z.object({
  calendarName: z.string().default("TripSage Itinerary"),
  events: z.array(calendarEventSchema).min(1, "At least one event is required"),
  timezone: z.string().optional(),
});

/**
 * Export itinerary to ICS tool.
 *
 * Generates an ICS file from a list of events for download or import into
 * other calendar applications.
 */
// biome-ignore lint/style/useNamingConvention: ICS is a standard file format acronym
export const exportItineraryToICS = toolAny({
  description:
    "Export a list of calendar events to ICS (iCalendar) format. Use this " +
    "to generate a downloadable calendar file from an itinerary or event list.",
  execute: async (params: z.infer<typeof exportItineraryToICSInputSchema>) => {
    try {
      // Call the ICS export route internally
      const siteUrl = getServerEnvVarWithFallback(
        "NEXT_PUBLIC_SITE_URL",
        "http://localhost:3000"
      );
      const response = await fetch(`${siteUrl}/api/calendar/ics/export`, {
        body: JSON.stringify(params),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });

      if (!response.ok) {
        const errorText = await response.text();
        return {
          error: `ICS export failed: ${response.status} ${errorText}`,
          success: false,
        };
      }

      const icsContent = await response.text();
      return {
        calendarName: params.calendarName,
        eventCount: params.events.length,
        icsContent,
        success: true,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      return {
        error: message,
        success: false,
      };
    }
  },
  parameters: exportItineraryToICSInputSchema,
});
