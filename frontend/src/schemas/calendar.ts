/**
 * @fileoverview Calendar event schemas aligned with Google Calendar API and
 * tripsage_core/models/api/calendar_models.py.
 */

import { z } from "zod";

/**
 * Event visibility options.
 */
export const eventVisibilitySchema = z.enum([
  "default",
  "public",
  "private",
  "confidential",
]);

export type EventVisibility = z.infer<typeof eventVisibilitySchema>;

/**
 * Event status options.
 */
export const eventStatusSchema = z.enum(["confirmed", "tentative", "cancelled"]);

export type EventStatus = z.infer<typeof eventStatusSchema>;

/**
 * Attendee response status options.
 */
export const attendeeResponseStatusSchema = z.enum([
  "needsAction",
  "declined",
  "tentative",
  "accepted",
]);

export type AttendeeResponseStatus = z.infer<typeof attendeeResponseStatusSchema>;

/**
 * Reminder method options.
 */
export const reminderMethodSchema = z.enum(["email", "popup", "sms"]);

export type ReminderMethod = z.infer<typeof reminderMethodSchema>;

/**
 * Event date/time representation (supports all-day or timed events).
 */
export const eventDateTimeSchema = z.object({
  date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, "Date must be in YYYY-MM-DD format")
    .optional()
    .or(z.date().transform((d) => d.toISOString().split("T")[0])),
  dateTime: z
    .union([z.date(), z.string().datetime()])
    .optional()
    .transform((val) => (typeof val === "string" ? new Date(val) : val)),
  timeZone: z.string().optional(),
});

export type EventDateTime = z.infer<typeof eventDateTimeSchema>;

/**
 * Event reminder configuration.
 */
export const eventReminderSchema = z.object({
  method: reminderMethodSchema.default("popup"),
  minutes: z.number().int().min(0).max(40320), // Max 4 weeks
});

export type EventReminder = z.infer<typeof eventReminderSchema>;

/**
 * Event attendee information.
 */
export const eventAttendeeSchema = z.object({
  additionalGuests: z.number().int().min(0).default(0),
  comment: z.string().optional(),
  displayName: z.string().optional(),
  email: z.string().email(),
  optional: z.boolean().default(false),
  responseStatus: attendeeResponseStatusSchema.default("needsAction"),
});

export type EventAttendee = z.infer<typeof eventAttendeeSchema>;

/**
 * Conference/meeting information for events.
 */
export const conferenceDataSchema = z.object({
  conferenceId: z.string().optional(),
  conferenceSolution: z.record(z.string(), z.unknown()).optional(),
  entryPoints: z.array(z.record(z.string(), z.unknown())).optional(),
  notes: z.string().optional(),
});

export type ConferenceData = z.infer<typeof conferenceDataSchema>;

/**
 * Extended properties for storing custom metadata.
 */
export const extendedPropertiesSchema = z.object({
  private: z.record(z.string(), z.string()).default({}),
  shared: z.record(z.string(), z.string()).default({}),
});

export type ExtendedProperties = z.infer<typeof extendedPropertiesSchema>;

/**
 * Complete calendar event schema.
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
  hangoutLink: z.string().url().optional(),
  htmlLink: z.string().url().optional(),
  // biome-ignore lint/style/useNamingConvention: iCalUID is a standard iCalendar field name
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

export type CalendarEvent = z.infer<typeof calendarEventSchema>;

/**
 * Request schema for creating calendar events.
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

export type CreateEventRequest = z.infer<typeof createEventRequestSchema>;

/**
 * Request schema for updating calendar events.
 */
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

export type UpdateEventRequest = z.infer<typeof updateEventRequestSchema>;

/**
 * Calendar list entry schema.
 */
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

export type CalendarListEntry = z.infer<typeof calendarListEntrySchema>;

/**
 * Calendar list response schema.
 */
export const calendarListSchema = z.object({
  etag: z.string().optional(),
  items: z.array(calendarListEntrySchema).default([]),
  kind: z.literal("calendar#calendarList").default("calendar#calendarList"),
  nextPageToken: z.string().optional(),
  nextSyncToken: z.string().optional(),
});

export type CalendarList = z.infer<typeof calendarListSchema>;

/**
 * Free/busy calendar item schema.
 */
export const freeBusyCalendarItemSchema = z.object({
  id: z.string(),
});

export type FreeBusyCalendarItem = z.infer<typeof freeBusyCalendarItemSchema>;

/**
 * Free/busy request schema.
 */
export const freeBusyRequestSchema = z
  .object({
    calendarExpansionMax: z.number().int().min(1).max(50).default(50),
    groupExpansionMax: z.number().int().min(1).max(100).default(50),
    items: z.array(freeBusyCalendarItemSchema).min(1),
    timeMax: z.date(),
    timeMin: z.date(),
    timeZone: z.string().optional(),
  })
  .refine((data) => data.timeMax > data.timeMin, {
    message: "timeMax must be after timeMin",
    path: ["timeMax"],
  });

export type FreeBusyRequest = z.infer<typeof freeBusyRequestSchema>;

/**
 * Free/busy response schema.
 */
export const freeBusyResponseSchema = z.object({
  calendars: z.record(z.string(), z.record(z.string(), z.unknown())).default({}),
  groups: z.record(z.string(), z.unknown()).default({}),
  kind: z.literal("calendar#freeBusy").default("calendar#freeBusy"),
  timeMax: z.date(),
  timeMin: z.date(),
});

export type FreeBusyResponse = z.infer<typeof freeBusyResponseSchema>;

/**
 * Events list request parameters schema.
 */
export const eventsListRequestSchema = z.object({
  alwaysIncludeEmail: z.boolean().default(false),
  calendarId: z.string().default("primary"),
  // biome-ignore lint/style/useNamingConvention: iCalUID is a standard iCalendar field name
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

export type EventsListRequest = z.infer<typeof eventsListRequestSchema>;

/**
 * Events list response schema.
 */
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

export type EventsListResponse = z.infer<typeof eventsListResponseSchema>;
