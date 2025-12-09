/**
 * @fileoverview Canonical Zod v4 schemas for calendar entities, Google Calendar API
 * integration, and calendar tool input validation.
 *
 * Core schemas: Calendar entities, events, API responses
 * Tool schemas: Input validation for calendar tools (create events, export ICS)
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core business logic schemas for calendar management

/** Zod schema for Google Calendar event visibility levels. */
export const eventVisibilitySchema = z.enum([
  "default",
  "public",
  "private",
  "confidential",
]);
/** TypeScript type for event visibility. */
export type EventVisibility = z.infer<typeof eventVisibilitySchema>;

/** Zod schema for Google Calendar event status values. */
export const eventStatusSchema = z.enum(["confirmed", "tentative", "cancelled"]);
/** TypeScript type for event status. */
export type EventStatus = z.infer<typeof eventStatusSchema>;

/** Zod schema for attendee response status values. */
export const attendeeResponseStatusSchema = z.enum([
  "needsAction",
  "declined",
  "tentative",
  "accepted",
]);
/** TypeScript type for attendee response status. */
export type AttendeeResponseStatus = z.infer<typeof attendeeResponseStatusSchema>;

/** Zod schema for reminder notification methods. */
export const reminderMethodSchema = z.enum(["email", "popup", "sms"]);
/** TypeScript type for reminder methods. */
export type ReminderMethod = z.infer<typeof reminderMethodSchema>;

/** Zod schema for Google Calendar event date/time with timezone support. */
export const eventDateTimeSchema = z.object({
  date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, { error: "Date must be in YYYY-MM-DD format" })
    .optional()
    .or(z.date().transform((d) => d.toISOString().split("T")[0])),
  dateTime: z
    .union([z.date(), z.iso.datetime()])
    .optional()
    .transform((val) => (typeof val === "string" ? new Date(val) : val)),
  timeZone: z.string().optional(),
});
/** TypeScript type for event date/time. */
export type EventDateTime = z.infer<typeof eventDateTimeSchema>;

/** Zod schema for Google Calendar event reminders. */
export const eventReminderSchema = z.object({
  method: reminderMethodSchema.default("popup"),
  minutes: z.number().int().min(0).max(40320),
});
/** TypeScript type for event reminders. */
export type EventReminder = z.infer<typeof eventReminderSchema>;

/** Zod schema for Google Calendar event attendees. */
export const eventAttendeeSchema = z.object({
  additionalGuests: z.number().int().min(0).default(0),
  comment: z.string().optional(),
  displayName: z.string().optional(),
  email: primitiveSchemas.email,
  optional: z.boolean().default(false),
  responseStatus: attendeeResponseStatusSchema.default("needsAction"),
});
/** TypeScript type for event attendees. */
export type EventAttendee = z.infer<typeof eventAttendeeSchema>;

/** Zod schema for Google Calendar conference data. */
export const conferenceDataSchema = z.object({
  conferenceId: z.string().optional(),
  conferenceSolution: z.record(z.string(), z.unknown()).optional(),
  entryPoints: z.array(z.record(z.string(), z.unknown())).optional(),
  notes: z.string().optional(),
});
/** TypeScript type for conference data. */
export type ConferenceData = z.infer<typeof conferenceDataSchema>;

/** Zod schema for Google Calendar extended properties. */
export const extendedPropertiesSchema = z.object({
  private: z.record(z.string(), z.string()).default({}),
  shared: z.record(z.string(), z.string()).default({}),
});
/** TypeScript type for extended properties. */
export type ExtendedProperties = z.infer<typeof extendedPropertiesSchema>;

/**
 * Zod schema for Google Calendar events.
 */
export const calendarEventSchema = z.object({
  attendees: z.array(eventAttendeeSchema).default([]),
  attendeesOmitted: z.boolean().default(false),
  colorId: z.string().optional(),
  conferenceData: conferenceDataSchema.optional(),
  created: z.date().optional(),
  creator: z.record(z.string(), z.unknown()).optional(),
  description: z.string().max(8192).optional(),
  end: eventDateTimeSchema,
  endTimeUnspecified: z.boolean().default(false),
  etag: z.string().optional(),
  extendedProperties: extendedPropertiesSchema.optional(),
  hangoutLink: primitiveSchemas.url.optional(),
  htmlLink: primitiveSchemas.url.optional(),
  iCalUID: z.string().optional(),
  id: z.string().optional(),
  location: z.string().max(1024).optional(),
  organizer: z.record(z.string(), z.unknown()).optional(),
  originalStartTime: eventDateTimeSchema.optional(),
  recurrence: z.array(z.string()).optional(),
  recurringEventId: z.string().optional(),
  reminders: z
    .object({
      overrides: z.array(eventReminderSchema).optional(),
      useDefault: z.boolean().optional(),
    })
    .default({ useDefault: true }),
  sequence: z.number().int().min(0).default(0),
  start: eventDateTimeSchema,
  status: eventStatusSchema.default("confirmed"),
  summary: z.string().min(1).max(1024),
  transparency: z.enum(["opaque", "transparent"]).default("opaque"),
  travelMetadata: z.record(z.string(), z.unknown()).optional(),
  updated: z.date().optional(),
  visibility: eventVisibilitySchema.default("default"),
});
/** TypeScript type for calendar events. */
export type CalendarEvent = z.infer<typeof calendarEventSchema>;

// ===== API SCHEMAS =====
// Request/response schemas for calendar API endpoints

/**
 * Zod schema for creating new Google Calendar events.
 * Validates event parameters including dates, attendees, and reminders.
 */
export const createEventRequestSchema = z.object({
  attendees: z.array(eventAttendeeSchema).default([]),
  conferenceDataVersion: z.number().int().optional(),
  description: z.string().max(8192).optional(),
  end: eventDateTimeSchema,
  location: z.string().max(1024).optional(),
  recurrence: z.array(z.string()).optional(),
  reminders: z
    .object({
      overrides: z.array(eventReminderSchema).optional(),
      useDefault: z.boolean().optional(),
    })
    .optional(),
  start: eventDateTimeSchema,
  summary: z.string().min(1).max(1024),
  timeZone: z.string().optional(),
  transparency: z.enum(["opaque", "transparent"]).default("opaque"),
  travelMetadata: z.record(z.string(), z.unknown()).optional(),
  visibility: eventVisibilitySchema.default("default"),
});
/** TypeScript type for create event requests. */
export type CreateEventRequest = z.infer<typeof createEventRequestSchema>;

/** Zod schema for updating existing Google Calendar events. */
export const updateEventRequestSchema = z.object({
  attendees: z.array(eventAttendeeSchema).optional(),
  description: z.string().max(8192).optional(),
  end: eventDateTimeSchema.optional(),
  location: z.string().max(1024).optional(),
  recurrence: z.array(z.string()).optional(),
  reminders: z
    .object({
      overrides: z.array(eventReminderSchema).optional(),
      useDefault: z.boolean().optional(),
    })
    .optional(),
  start: eventDateTimeSchema.optional(),
  summary: z.string().min(1).max(1024).optional(),
  timeZone: z.string().optional(),
  transparency: z.enum(["opaque", "transparent"]).optional(),
  travelMetadata: z.record(z.string(), z.unknown()).optional(),
  visibility: eventVisibilitySchema.optional(),
});
/** TypeScript type for update event requests. */
export type UpdateEventRequest = z.infer<typeof updateEventRequestSchema>;

/** Zod schema for Google Calendar list entries. */
export const calendarListEntrySchema = z.object({
  accessRole: z.string().default("reader"),
  backgroundColor: z.string().optional(),
  colorId: z.string().optional(),
  conferenceProperties: z.record(z.string(), z.unknown()).optional(),
  defaultReminders: z.array(eventReminderSchema).default([]),
  deleted: z.boolean().default(false),
  description: z.string().optional(),
  etag: z.string().optional(),
  foregroundColor: z.string().optional(),
  hidden: z.boolean().default(false),
  id: z.string(),
  kind: z.literal("calendar#calendarListEntry").default("calendar#calendarListEntry"),
  location: z.string().optional(),
  notificationSettings: z.record(z.string(), z.unknown()).optional(),
  primary: z.boolean().default(false),
  selected: z.boolean().default(true),
  summary: z.string(),
  summaryOverride: z.string().optional(),
  timeZone: z.string().optional(),
});
/** TypeScript type for calendar list entries. */
export type CalendarListEntry = z.infer<typeof calendarListEntrySchema>;

/** Zod schema for Google Calendar list responses. */
export const calendarListSchema = z.object({
  etag: z.string().optional(),
  items: z.array(calendarListEntrySchema).default([]),
  kind: z.literal("calendar#calendarList").default("calendar#calendarList"),
  nextPageToken: z.string().optional(),
  nextSyncToken: z.string().optional(),
});
/** TypeScript type for calendar list responses. */
export type CalendarList = z.infer<typeof calendarListSchema>;

/** Zod schema for free/busy calendar items. */
export const freeBusyCalendarItemSchema = z.object({
  id: z.string(),
});
/** TypeScript type for free/busy calendar items. */
export type FreeBusyCalendarItem = z.infer<typeof freeBusyCalendarItemSchema>;

/**
 * Zod schema for Google Calendar free/busy requests.
 * Validates parameters for checking calendar availability.
 */
export const freeBusyRequestSchema = z
  .object({
    calendarExpansionMax: z.number().int().min(1).max(50).default(50),
    groupExpansionMax: z.number().int().min(1).max(100).default(50),
    items: z.array(freeBusyCalendarItemSchema).min(1),
    timeMax: z.union([z.date(), z.string().transform((val) => new Date(val))]),
    timeMin: z.union([z.date(), z.string().transform((val) => new Date(val))]),
    timeZone: z.string().optional(),
  })
  .refine((data) => data.timeMax > data.timeMin, {
    error: "timeMax must be after timeMin",
    path: ["timeMax"],
  });
/** TypeScript type for free/busy requests. */
export type FreeBusyRequest = z.infer<typeof freeBusyRequestSchema>;

/** Zod schema for Google Calendar free/busy responses. */
export const freeBusyResponseSchema = z.object({
  calendars: z.record(z.string(), z.record(z.string(), z.unknown())).default({}),
  groups: z.record(z.string(), z.unknown()).default({}),
  kind: z.literal("calendar#freeBusy").default("calendar#freeBusy"),
  timeMax: z.date(),
  timeMin: z.date(),
});
/** TypeScript type for free/busy responses. */
export type FreeBusyResponse = z.infer<typeof freeBusyResponseSchema>;

/** Zod schema for Google Calendar events list requests. */
export const eventsListRequestSchema = z.object({
  alwaysIncludeEmail: z.boolean().default(false),
  calendarId: z.string().default("primary"),
  iCalUID: z.string().optional(),
  maxAttendees: z.number().int().min(1).optional(),
  maxResults: z.number().int().min(1).max(2500).default(250),
  orderBy: z.enum(["startTime", "updated"]).optional(),
  pageToken: z.string().optional(),
  privateExtendedProperty: z.array(z.string()).optional(),
  q: z.string().optional(),
  sharedExtendedProperty: z.array(z.string()).optional(),
  showDeleted: z.boolean().default(false),
  showHiddenInvitations: z.boolean().default(false),
  singleEvents: z.boolean().default(false),
  syncToken: z.string().optional(),
  timeMax: z.date().optional(),
  timeMin: z.date().optional(),
  timeZone: z.string().optional(),
  updatedMin: z.date().optional(),
});
/** TypeScript type for events list requests. */
export type EventsListRequest = z.infer<typeof eventsListRequestSchema>;

/** Zod schema for Google Calendar events list responses. */
export const eventsListResponseSchema = z.object({
  accessRole: z.string().optional(),
  defaultReminders: z.array(eventReminderSchema).default([]),
  description: z.string().optional(),
  etag: z.string().optional(),
  items: z.array(calendarEventSchema).default([]),
  kind: z.literal("calendar#events").default("calendar#events"),
  nextPageToken: z.string().optional(),
  nextSyncToken: z.string().optional(),
  summary: z.string().optional(),
  timeZone: z.string().optional(),
  updated: z.date().optional(),
});
/** TypeScript type for events list responses. */
export type EventsListResponse = z.infer<typeof eventsListResponseSchema>;

/**
 * Zod schema for POST /api/calendar/ics/import request body.
 * Validates ICS import request parameters for route handlers.
 */
export const icsImportRequestSchema = z.object({
  icsData: z.string().min(1, { error: "ICS data is required" }),
  validateOnly: z.boolean().default(true),
});

/** TypeScript type for ICS import requests. */
export type IcsImportRequest = z.infer<typeof icsImportRequestSchema>;

/**
 * Zod schema for POST /api/calendar/ics/export request body.
 * Validates ICS export request parameters for route handlers.
 */
export const icsExportRequestSchema = z.object({
  calendarName: z.string().default("TripSage Calendar"),
  events: z
    .array(calendarEventSchema)
    .min(1, { error: "At least one event is required" }),
  timezone: z.string().optional(),
});

/** TypeScript type for ICS export requests. */
export type IcsExportRequest = z.infer<typeof icsExportRequestSchema>;

/**
 * Calendar connection status response type.
 * Used by calendar status API and components.
 */
export interface CalendarStatusResponse {
  connected: boolean;
  calendars?: Array<{
    id: string;
    summary: string;
    description?: string;
    timeZone?: string;
    primary?: boolean;
    accessRole?: string;
  }>;
  message?: string;
}

// ===== TOOL INPUT SCHEMAS =====
// Schemas for calendar tool input validation and processing

/**
 * Schema for creating calendar events with Google Calendar.
 * Validates calendar event creation parameters for AI tools.
 */
export const createCalendarEventInputSchema = createEventRequestSchema.extend({
  calendarId: z
    .string()
    .default("primary")
    .describe("Google Calendar ID to create event in"),
});

/**
 * Schema for exporting calendar events to ICS format.
 * Validates itinerary export parameters for AI tools.
 */
export const exportItineraryToIcsInputSchema = z.strictObject({
  calendarName: z
    .string()
    .default("TripSage Itinerary")
    .describe("Name for the calendar in ICS export"),
  events: z
    .array(calendarEventSchema)
    .min(1, { error: "At least one event is required" })
    .describe("List of calendar events to export"),
  timezone: z.string().nullable().describe("Timezone for the exported calendar"),
});
