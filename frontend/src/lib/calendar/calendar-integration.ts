/**
 * @fileoverview Calendar integration abstraction layer.
 *
 * Unified interface for calendar providers with ICS import/export.
 */

import type { CalendarEvent, EventDateTime } from "@schemas/calendar";
import { calendarEventSchema } from "@schemas/calendar";
import { toClientAbsoluteUrl } from "@/lib/url/client-origin";
import type { DateRange } from "../dates/unified-date-utils";
import { DateUtils } from "../dates/unified-date-utils";

/** Converts relative path to absolute URL (client-side only). */
const toAbsoluteUrl = (path: string): string => toClientAbsoluteUrl(path);

/** Resolves event date/time value to Date. */
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

/** Serializes event date/time to payload. */
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

/** Normalizes remote event data to calendar event schema. */
const normalizeRemoteEvent = (event: Record<string, unknown>): CalendarEvent =>
  calendarEventSchema.parse({
    ...event,
    end: event.end ?? event.endTime,
    start: event.start ?? event.startTime,
    summary: event.summary ?? event.title ?? "Untitled Event",
  });

/** Serializes event data to payload. */
const serializeEventPayload = (event: CalendarEvent) => ({
  ...event,
  end: serializeEventDateTime(event.end),
  start: serializeEventDateTime(event.start),
});

/** Serializes partial event data to payload. */
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

/** Interface for calendar provider implementations. */
export interface CalendarProvider {
  /**
   * Retrieves events within date range.
   *
   * @param dateRange - Date range to fetch events for.
   * @returns Promise resolving to array of calendar events.
   */
  getEvents(dateRange: DateRange): Promise<CalendarEvent[]>;

  /**
   * Creates new calendar event.
   *
   * @param event - Event data without ID.
   * @returns Promise resolving to created event with ID.
   */
  createEvent(event: Omit<CalendarEvent, "id">): Promise<CalendarEvent>;

  /**
   * Updates existing calendar event.
   *
   * @param id - Event ID to update.
   * @param event - Partial event data to update.
   * @returns Promise resolving to updated event.
   */
  updateEvent(id: string, event: Partial<CalendarEvent>): Promise<CalendarEvent>;

  /**
   * Deletes calendar event.
   *
   * @param id - Event ID to delete.
   * @returns Promise resolving when event is deleted.
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
   * @param icsContent - ICS content to parse.
   * @returns Promise resolving to array of imported events.
   */
  importFromIcs(icsContent: string): Promise<CalendarEvent[]>;
}

/** Supabase-based calendar provider implementation. */
export class SupabaseCalendarProvider implements CalendarProvider {
  /**
   * Retrieves events from Supabase backend within date range.
   *
   * @param dateRange - Date range to fetch events for.
   * @returns Promise resolving to array of calendar events.
   */
  async getEvents(dateRange: DateRange): Promise<CalendarEvent[]> {
    const response = await fetch(toAbsoluteUrl("/api/calendar/events"), {
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

  /**
   * Creates event via Supabase backend API.
   *
   * @param event - Event data without ID.
   * @returns Promise resolving to created event.
   */
  async createEvent(event: Omit<CalendarEvent, "id">): Promise<CalendarEvent> {
    const response = await fetch(toAbsoluteUrl("/api/calendar/events"), {
      body: JSON.stringify(serializeEventPayload(event)),
      headers: { "Content-Type": "application/json" },
      method: "PUT",
    });
    const created = await response.json();
    return normalizeRemoteEvent(created);
  }

  /**
   * Updates event via Supabase backend API.
   *
   * @param id - Event ID to update.
   * @param event - Partial event data.
   * @returns Promise resolving to updated event.
   */
  async updateEvent(id: string, event: Partial<CalendarEvent>): Promise<CalendarEvent> {
    const response = await fetch(toAbsoluteUrl(`/api/calendar/events/${id}`), {
      body: JSON.stringify(serializePartialEventPayload(event)),
      headers: { "Content-Type": "application/json" },
      method: "PATCH",
    });
    const updated = await response.json();
    return normalizeRemoteEvent(updated);
  }

  /**
   * Deletes event via Supabase backend API.
   *
   * @param id - Event ID to delete.
   */
  async deleteEvent(id: string): Promise<void> {
    await fetch(toAbsoluteUrl(`/api/calendar/events/${id}`), { method: "DELETE" });
  }

  /**
   * Exports events to ICS via Supabase backend API.
   *
   * @param events - Array of events to export.
   * @returns Promise resolving to ICS string content.
   */
  async exportToIcs(events: CalendarEvent[]): Promise<string> {
    const response = await fetch(toAbsoluteUrl("/api/calendar/ics/export"), {
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

  /**
   * Imports events from ICS via Supabase backend API.
   *
   * @param icsContent - ICS content to parse.
   * @returns Promise resolving to array of imported events.
   */
  async importFromIcs(icsContent: string): Promise<CalendarEvent[]> {
    const response = await fetch(toAbsoluteUrl("/api/calendar/ics/import"), {
      body: JSON.stringify({ icsContent }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
    const events = await response.json();
    return events.map((event: Record<string, unknown>) => normalizeRemoteEvent(event));
  }
}

/**
 * Converts EventDateTime to Google Calendar API format.
 *
 * @param value - Event date/time value.
 * @returns Google Calendar date/time payload.
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

/**
 * Google Calendar API provider implementation.
 *
 * Server-only: requires API key and must not be used in client components.
 */
export class GoogleCalendarProvider implements CalendarProvider {
  private apiKey: string;
  private calendarId: string;

  /**
   * Asserts provider is used server-side only.
   *
   * @throws Error if used in client context.
   */
  assertServer() {
    if (typeof window !== "undefined") {
      throw new Error("GoogleCalendarProvider can only be used on the server.");
    }
  }

  /**
   * Creates Google Calendar provider instance.
   *
   * @param apiKey - Google Calendar API key.
   * @param calendarId - Calendar ID. Defaults to "primary".
   */
  constructor(apiKey: string, calendarId: string = "primary") {
    this.assertServer();
    this.apiKey = apiKey;
    this.calendarId = calendarId;
  }

  /**
   * Retrieves events from Google Calendar within date range.
   *
   * @param dateRange - Date range to fetch events for.
   * @returns Promise resolving to array of calendar events.
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

  /**
   * Creates event via Google Calendar API.
   *
   * @param event - Event data without ID.
   * @returns Promise resolving to created event.
   */
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

  /**
   * Updates event via Google Calendar API.
   *
   * @param id - Event ID to update.
   * @param event - Partial event data.
   * @returns Promise resolving to updated event.
   */
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

  /**
   * Deletes event via Google Calendar API.
   *
   * @param id - Event ID to delete.
   */
  async deleteEvent(id: string): Promise<void> {
    await fetch(
      `https://www.googleapis.com/calendar/v3/calendars/${this.calendarId}/events/${id}?key=${this.apiKey}`,
      { method: "DELETE" }
    );
  }

  /**
   * Exports events to ICS via backend API.
   *
   * @param events - Array of events to export.
   * @returns Promise resolving to ICS string content.
   */
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

  /**
   * Imports events from ICS via backend API.
   *
   * @param icsContent - ICS content to parse.
   * @returns Promise resolving to array of imported events.
   */
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
 * Factory for creating calendar provider instances.
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
