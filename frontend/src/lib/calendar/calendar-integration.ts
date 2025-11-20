/**
 * @fileoverview Calendar integration abstraction layer.
 * Provides unified interface for different calendar providers and
 * consolidates ICS import/export functionality using date-fns v4.
 */

import type { CalendarEvent, EventDateTime } from "@domain/types";
import { calendarEventSchema } from "@schemas/calendar";
import type { DateRange } from "../dates/unified-date-utils";
import { DateUtils } from "../dates/unified-date-utils";

const resolveDateTimeValue = (value: EventDateTime): Date => {
  if (value.dateTime instanceof Date) {
    return value.dateTime;
  }
  if (typeof value.dateTime === "string") {
    return DateUtils.parse(value.dateTime);
  }
  if (value.date) {
    return DateUtils.parse(value.date);
  }
  throw new Error("Calendar event missing date/time value.");
};

const serializeEventDateTime = (value: EventDateTime) => {
  if (value.date) {
    return { date: value.date };
  }
  const resolved = resolveDateTimeValue(value);
  return {
    date: resolved.toISOString().split("T")[0],
    dateTime: DateUtils.formatForApi(resolved),
  };
};

const normalizeRemoteEvent = (event: Record<string, unknown>): CalendarEvent =>
  calendarEventSchema.parse({
    ...event,
    end: event.end ?? event.endTime,
    start: event.start ?? event.startTime,
    summary: event.summary ?? event.title ?? "Untitled Event",
  });

const serializeEventPayload = (event: CalendarEvent) => ({
  ...event,
  end: serializeEventDateTime(event.end),
  start: serializeEventDateTime(event.start),
});

const serializePartialEventPayload = (event: Partial<CalendarEvent>) => {
  const payload: Record<string, unknown> = { ...event };
  if (event.end) {
    payload.end = serializeEventDateTime(event.end);
  }
  if (event.start) {
    payload.start = serializeEventDateTime(event.start);
  }
  return payload;
};

/**
 * Interface for calendar provider implementations.
 *
 * Defines the contract for interacting with different calendar services.
 *
 * @interface CalendarProvider
 */
export interface CalendarProvider {
  /**
   * Retrieves events within a specified date range.
   *
   * @param dateRange - The date range to fetch events for.
   * @returns Promise resolving to an array of calendar events.
   */
  getEvents(dateRange: DateRange): Promise<CalendarEvent[]>;

  /**
   * Creates a new calendar event.
   *
   * @param event - The event data (without ID).
   * @returns Promise resolving to the created event with assigned ID.
   */
  createEvent(event: Omit<CalendarEvent, "id">): Promise<CalendarEvent>;

  /**
   * Updates an existing calendar event.
   *
   * @param id - The ID of the event to update.
   * @param event - Partial event data to update.
   * @returns Promise resolving to the updated event.
   */
  updateEvent(id: string, event: Partial<CalendarEvent>): Promise<CalendarEvent>;

  /**
   * Deletes a calendar event.
   *
   * @param id - The ID of the event to delete.
   * @returns Promise resolving when the event is deleted.
   */
  deleteEvent(id: string): Promise<void>;

  /**
   * Exports events to ICS format.
   *
   * @param events - Array of events to export.
   * @returns Promise resolving to ICS string content.
   */
  exportToIcs(events: CalendarEvent[]): Promise<string>;

  /**
   * Imports events from ICS format.
   *
   * @param icsContent - The ICS content to parse.
   * @returns Promise resolving to an array of imported events.
   */
  importFromIcs(icsContent: string): Promise<CalendarEvent[]>;
}

/**
 * Supabase-based calendar provider implementation.
 *
 * Integrates with the TripSage backend API for calendar operations.
 *
 * @class SupabaseCalendarProvider
 */
export class SupabaseCalendarProvider implements CalendarProvider {
  /**
   * Retrieves events from the Supabase backend within the specified date range.
   *
   * @param dateRange - The date range to fetch events for.
   * @returns Promise resolving to an array of calendar events.
   */
  async getEvents(dateRange: DateRange): Promise<CalendarEvent[]> {
    const response = await fetch("/api/calendar/events", {
      body: JSON.stringify({
        end: DateUtils.formatForApi(dateRange.end),
        start: DateUtils.formatForApi(dateRange.start),
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
    const events = await response.json();
    const list = Array.isArray(events) ? events : (events?.items ?? []);
    return list.map((event: Record<string, unknown>) => normalizeRemoteEvent(event));
  }

  async createEvent(event: Omit<CalendarEvent, "id">): Promise<CalendarEvent> {
    const response = await fetch("/api/calendar/events", {
      body: JSON.stringify(serializeEventPayload(event)),
      headers: { "Content-Type": "application/json" },
      method: "PUT",
    });
    const created = await response.json();
    return normalizeRemoteEvent(created);
  }

  async updateEvent(id: string, event: Partial<CalendarEvent>): Promise<CalendarEvent> {
    const response = await fetch(`/api/calendar/events/${id}`, {
      body: JSON.stringify(serializePartialEventPayload(event)),
      headers: { "Content-Type": "application/json" },
      method: "PATCH",
    });
    const updated = await response.json();
    return normalizeRemoteEvent(updated);
  }

  async deleteEvent(id: string): Promise<void> {
    await fetch(`/api/calendar/events/${id}`, { method: "DELETE" });
  }

  async exportToIcs(events: CalendarEvent[]): Promise<string> {
    const response = await fetch("/api/calendar/ics/export", {
      body: JSON.stringify({
        events: events.map((event) => ({
          ...event,
          end: DateUtils.formatForApi(resolveDateTimeValue(event.end)),
          start: DateUtils.formatForApi(resolveDateTimeValue(event.start)),
        })),
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
    return response.text();
  }

  async importFromIcs(icsContent: string): Promise<CalendarEvent[]> {
    const response = await fetch("/api/calendar/ics/import", {
      body: JSON.stringify({ icsContent }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
    const events = await response.json();
    return events.map((event: Record<string, unknown>) => normalizeRemoteEvent(event));
  }
}

/**
 * Google Calendar API provider implementation.
 *
 * Integrates with Google Calendar API for calendar operations.
 *
 * @class GoogleCalendarProvider
 */
const toGoogleDateTimePayload = (value: EventDateTime) => {
  if (value.date) {
    return { date: value.date };
  }
  const resolved = resolveDateTimeValue(value);
  return {
    date: resolved.toISOString().split("T")[0],
    dateTime: DateUtils.formatForApi(resolved),
  };
};

export class GoogleCalendarProvider implements CalendarProvider {
  private apiKey: string;
  private calendarId: string;

  assertServer() {
    if (typeof window !== "undefined") {
      throw new Error("GoogleCalendarProvider can only be used on the server.");
    }
  }

  /**
   * Creates a new Google Calendar provider instance.
   *
   * @param apiKey - Google Calendar API key.
   * @param calendarId - Calendar ID to use. Defaults to "primary".
   */
  constructor(apiKey: string, calendarId: string = "primary") {
    this.assertServer();
    this.apiKey = apiKey;
    this.calendarId = calendarId;
  }

  /**
   * Retrieves events from Google Calendar within the specified date range.
   *
   * @param dateRange - The date range to fetch events for.
   * @returns Promise resolving to an array of calendar events.
   */
  async getEvents(dateRange: DateRange): Promise<CalendarEvent[]> {
    const params = new URLSearchParams({
      key: this.apiKey,
      orderBy: "startTime",
      singleEvents: "true",
      timeMax: DateUtils.formatForApi(dateRange.end),
      timeMin: DateUtils.formatForApi(dateRange.start),
    });

    const response = await fetch(
      `https://www.googleapis.com/calendar/v3/calendars/${this.calendarId}/events?${params}`
    );
    const data = await response.json();

    return (data.items || []).map((item: Record<string, unknown>) =>
      normalizeRemoteEvent({
        ...item,
        end: item.end,
        id: item.id,
        location: item.location,
        metadata: item,
        start: item.start,
        summary: item.summary,
      })
    );
  }

  async createEvent(event: Omit<CalendarEvent, "id">): Promise<CalendarEvent> {
    const response = await fetch(
      `https://www.googleapis.com/calendar/v3/calendars/${this.calendarId}/events?key=${this.apiKey}`,
      {
        body: JSON.stringify({
          description: event.description,
          end: toGoogleDateTimePayload(event.end),
          location: event.location,
          start: toGoogleDateTimePayload(event.start),
          summary: event.summary,
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      }
    );
    const created = await response.json();
    return normalizeRemoteEvent(created);
  }

  async updateEvent(id: string, event: Partial<CalendarEvent>): Promise<CalendarEvent> {
    const response = await fetch(
      `https://www.googleapis.com/calendar/v3/calendars/${this.calendarId}/events/${id}?key=${this.apiKey}`,
      {
        body: JSON.stringify({
          description: event.description,
          end: event.end ? toGoogleDateTimePayload(event.end) : undefined,
          location: event.location,
          start: event.start ? toGoogleDateTimePayload(event.start) : undefined,
          summary: event.summary,
        }),
        headers: { "Content-Type": "application/json" },
        method: "PATCH",
      }
    );
    const updated = await response.json();
    return normalizeRemoteEvent(updated);
  }

  async deleteEvent(id: string): Promise<void> {
    await fetch(
      `https://www.googleapis.com/calendar/v3/calendars/${this.calendarId}/events/${id}?key=${this.apiKey}`,
      { method: "DELETE" }
    );
  }

  async exportToIcs(events: CalendarEvent[]): Promise<string> {
    const response = await fetch("/api/calendar/ics/export", {
      body: JSON.stringify({
        events: events.map((event) => ({
          ...event,
          end: DateUtils.formatForApi(resolveDateTimeValue(event.end)),
          start: DateUtils.formatForApi(resolveDateTimeValue(event.start)),
        })),
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
    return response.text();
  }

  async importFromIcs(icsContent: string): Promise<CalendarEvent[]> {
    const response = await fetch("/api/calendar/ics/import", {
      body: JSON.stringify({ icsContent }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
    const events = await response.json();
    return events.map((event: Record<string, unknown>) => normalizeRemoteEvent(event));
  }
}

/**
 * Factory helpers for creating calendar providers.
 */
export const calendarFactory = {
  create(
    type: "supabase" | "google",
    options?: { apiKey?: string; calendarId?: string }
  ): CalendarProvider {
    switch (type) {
      case "supabase":
        return new SupabaseCalendarProvider();
      case "google":
        if (!options?.apiKey) {
          throw new Error("API key required for Google Calendar provider");
        }
        return new GoogleCalendarProvider(options.apiKey, options.calendarId);
      default:
        throw new Error(`Unsupported calendar type: ${type}`);
    }
  },
};
