/**
 * @fileoverview Calendar integration abstraction layer.
 * Provides unified interface for different calendar providers and
 * consolidates ICS import/export functionality using date-fns v4.
 */

import type { DateRange } from "../dates/unified-date-utils";
import { DateUtils } from "../dates/unified-date-utils";
import type { RecurringRule } from "../dates/recurring-rules";

/**
 * Represents a calendar event with all essential properties.
 *
 * @interface CalendarEvent
 */
export interface CalendarEvent {
  /** Unique identifier for the event. */
  id: string;
  /** Event title or summary. */
  title: string;
  /** Optional event description. */
  description?: string;
  /** Event start time. */
  start: Date;
  /** Event end time. */
  end: Date;
  /** Optional timezone identifier. */
  timezone?: string;
  /** Optional event location. */
  location?: string;
  /** Optional list of attendee email addresses. */
  attendees?: string[];
  /** Optional recurrence rule for repeating events. */
  recurring?: RecurringRule;
  /** Optional metadata for provider-specific information. */
  metadata?: Record<string, unknown>;
}

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
  exportToICS(events: CalendarEvent[]): Promise<string>;
  
  /**
   * Imports events from ICS format.
   *
   * @param icsContent - The ICS content to parse.
   * @returns Promise resolving to an array of imported events.
   */
  importFromICS(icsContent: string): Promise<CalendarEvent[]>;
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
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        start: DateUtils.formatForApi(dateRange.start),
        end: DateUtils.formatForApi(dateRange.end),
      }),
    });
    const events = await response.json();
    return events.map((event: any) => ({
      ...event,
      start: DateUtils.parse(event.start),
      end: DateUtils.parse(event.end),
    }));
  }

  async createEvent(event: Omit<CalendarEvent, "id">): Promise<CalendarEvent> {
    const response = await fetch("/api/calendar/events", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...event,
        start: DateUtils.formatForApi(event.start),
        end: DateUtils.formatForApi(event.end),
      }),
    });
    const created = await response.json();
    return {
      ...created,
      start: DateUtils.parse(created.start),
      end: DateUtils.parse(created.end),
    };
  }

  async updateEvent(id: string, event: Partial<CalendarEvent>): Promise<CalendarEvent> {
    const response = await fetch(`/api/calendar/events/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...event,
        start: event.start ? DateUtils.formatForApi(event.start) : undefined,
        end: event.end ? DateUtils.formatForApi(event.end) : undefined,
      }),
    });
    const updated = await response.json();
    return {
      ...updated,
      start: DateUtils.parse(updated.start),
      end: DateUtils.parse(updated.end),
    };
  }

  async deleteEvent(id: string): Promise<void> {
    await fetch(`/api/calendar/events/${id}`, { method: "DELETE" });
  }

  async exportToICS(events: CalendarEvent[]): Promise<string> {
    const response = await fetch("/api/calendar/ics/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        events: events.map((event) => ({
          ...event,
          start: DateUtils.formatForApi(event.start),
          end: DateUtils.formatForApi(event.end),
        })),
      }),
    });
    return response.text();
  }

  async importFromICS(icsContent: string): Promise<CalendarEvent[]> {
    const response = await fetch("/api/calendar/ics/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ icsContent }),
    });
    const events = await response.json();
    return events.map((event: any) => ({
      ...event,
      start: DateUtils.parse(event.start),
      end: DateUtils.parse(event.end),
    }));
  }
}

/**
 * Google Calendar API provider implementation.
 *
 * Integrates with Google Calendar API for calendar operations.
 *
 * @class GoogleCalendarProvider
 */
export class GoogleCalendarProvider implements CalendarProvider {
  private apiKey: string;
  private calendarId: string;

  /**
   * Creates a new Google Calendar provider instance.
   *
   * @param apiKey - Google Calendar API key.
   * @param calendarId - Calendar ID to use. Defaults to "primary".
   */
  constructor(apiKey: string, calendarId: string = "primary") {
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
      timeMin: DateUtils.formatForApi(dateRange.start),
      timeMax: DateUtils.formatForApi(dateRange.end),
      singleEvents: "true",
      orderBy: "startTime",
      key: this.apiKey,
    });

    const response = await fetch(
      `https://www.googleapis.com/calendar/v3/calendars/${this.calendarId}/events?${params}`,
    );
    const data = await response.json();

    return data.items.map((item: any) => ({
      id: item.id,
      title: item.summary,
      description: item.description,
      start: DateUtils.parse(item.start.date || item.start.dateTime),
      end: DateUtils.parse(item.end.date || item.end.dateTime),
      location: item.location,
      metadata: item,
    }));
  }

  async createEvent(event: Omit<CalendarEvent, "id">): Promise<CalendarEvent> {
    const response = await fetch(
      `https://www.googleapis.com/calendar/v3/calendars/${this.calendarId}/events?key=${this.apiKey}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          summary: event.title,
          description: event.description,
          location: event.location,
          start: {
            date: event.start.toISOString().split("T")[0],
            dateTime: DateUtils.formatForApi(event.start),
          },
          end: {
            date: event.end.toISOString().split("T")[0],
            dateTime: DateUtils.formatForApi(event.end),
          },
        }),
      },
    );
    const created = await response.json();
    return {
      id: created.id,
      title: created.summary,
      description: created.description,
      start: DateUtils.parse(created.start.date || created.start.dateTime),
      end: DateUtils.parse(created.end.date || created.end.dateTime),
      location: created.location,
      metadata: created,
    };
  }

  async updateEvent(id: string, event: Partial<CalendarEvent>): Promise<CalendarEvent> {
    const response = await fetch(
      `https://www.googleapis.com/calendar/v3/calendars/${this.calendarId}/events/${id}?key=${this.apiKey}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          summary: event.title,
          description: event.description,
          location: event.location,
          start: event.start
            ? {
                date: event.start.toISOString().split("T")[0],
                dateTime: DateUtils.formatForApi(event.start),
              }
            : undefined,
          end: event.end
            ? {
                date: event.end.toISOString().split("T")[0],
                dateTime: DateUtils.formatForApi(event.end),
              }
            : undefined,
        }),
      },
    );
    const updated = await response.json();
    return {
      id: updated.id,
      title: updated.summary,
      description: updated.description,
      start: DateUtils.parse(updated.start.date || updated.start.dateTime),
      end: DateUtils.parse(updated.end.date || updated.end.dateTime),
      location: updated.location,
      metadata: updated,
    };
  }

  async deleteEvent(id: string): Promise<void> {
    await fetch(
      `https://www.googleapis.com/calendar/v3/calendars/${this.calendarId}/events/${id}?key=${this.apiKey}`,
      { method: "DELETE" },
    );
  }

  async exportToICS(events: CalendarEvent[]): Promise<string> {
    const response = await fetch("/api/calendar/ics/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        events: events.map((event) => ({
          ...event,
          start: DateUtils.formatForApi(event.start),
          end: DateUtils.formatForApi(event.end),
        })),
      }),
    });
    return response.text();
  }

  async importFromICS(icsContent: string): Promise<CalendarEvent[]> {
    const response = await fetch("/api/calendar/ics/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ icsContent }),
    });
    const events = await response.json();
    return events.map((event: any) => ({
      ...event,
      start: DateUtils.parse(event.start),
      end: DateUtils.parse(event.end),
    }));
  }
}

/**
 * Factory class for creating calendar provider instances.
 *
 * Provides a centralized way to instantiate different calendar providers
 * based on type and configuration options.
 *
 * @class CalendarFactory
 */
export class CalendarFactory {
  /**
   * Creates a calendar provider instance based on the specified type.
   *
   * @param type - The type of calendar provider to create.
   * @param options - Optional configuration for the provider.
   * @param options.apiKey - API key required for Google Calendar provider.
   * @param options.calendarId - Calendar ID for Google Calendar provider.
   * @returns A configured calendar provider instance.
   * @throws Error if required options are missing or provider type is unsupported.
   */
  static create(type: "supabase" | "google", options?: { apiKey?: string; calendarId?: string }): CalendarProvider {
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
  }
}
