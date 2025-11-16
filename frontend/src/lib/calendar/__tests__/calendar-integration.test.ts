/**
 * @vitest-environment node
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { CalendarEvent } from "@/lib/schemas/calendar";
import { calendarEventSchema } from "@/lib/schemas/calendar";
import type { DateRange } from "../../dates/unified-date-utils";
import { DateUtils } from "../../dates/unified-date-utils";
import type { CalendarProvider } from "../calendar-integration";
import { calendarFactory } from "../calendar-integration";

// Mock fetch for all tests
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("CalendarIntegration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("calendarFactory", () => {
    it("should create SupabaseCalendarProvider", () => {
      const provider = calendarFactory.create("supabase");
      expect(provider).toBeDefined();
      expect(provider.constructor.name).toBe("SupabaseCalendarProvider");
    });

    it("should create GoogleCalendarProvider with API key", () => {
      const provider = calendarFactory.create("google", {
        apiKey: "test-api-key",
        calendarId: "test-calendar",
      });
      expect(provider).toBeDefined();
      expect(provider.constructor.name).toBe("GoogleCalendarProvider");
    });

    it("should throw error for Google provider without API key", () => {
      expect(() => calendarFactory.create("google")).toThrow(
        "API key required for Google Calendar provider"
      );
    });

    it("should throw error for unsupported provider type", () => {
      expect(() =>
        calendarFactory.create("unsupported" as unknown as "supabase")
      ).toThrow("Unsupported calendar type: unsupported");
    });
  });

  describe("SupabaseCalendarProvider", () => {
    let provider: CalendarProvider;
    const mockDateRange: DateRange = {
      end: new Date("2024-01-07T23:59:59Z"),
      start: new Date("2024-01-01T00:00:00Z"),
    };

    beforeEach(() => {
      provider = calendarFactory.create("supabase");
    });

    it("should get events successfully", async () => {
      const mockEvents = [
        {
          end: { dateTime: "2024-01-01T11:00:00Z" },
          id: "1",
          start: { dateTime: "2024-01-01T10:00:00Z" },
          summary: "Test Event",
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: async () => mockEvents,
        ok: true,
      });

      const events = await provider.getEvents(mockDateRange);

      expect(mockFetch).toHaveBeenCalledWith("/api/calendar/events", {
        body: JSON.stringify({
          end: DateUtils.formatForApi(mockDateRange.end),
          start: DateUtils.formatForApi(mockDateRange.start),
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });

      expect(events).toHaveLength(1);
      expect(events[0].id).toBe("1");
      expect(events[0].summary).toBe("Test Event");
      expect(events[0].start.dateTime).toEqual(DateUtils.parse("2024-01-01T10:00:00Z"));
      expect(events[0].end.dateTime).toEqual(DateUtils.parse("2024-01-01T11:00:00Z"));
    });

    it("should create event successfully", async () => {
      const mockEvent = {
        end: { dateTime: "2024-01-01T11:00:00Z" },
        id: "1",
        start: { dateTime: "2024-01-01T10:00:00Z" },
        summary: "New Event",
      };

      const newEvent: Omit<CalendarEvent, "id"> = calendarEventSchema.parse({
        end: { dateTime: new Date("2024-01-01T11:00:00Z") },
        start: { dateTime: new Date("2024-01-01T10:00:00Z") },
        summary: "New Event",
      });

      mockFetch.mockResolvedValueOnce({
        json: async () => mockEvent,
        ok: true,
      });

      const result = await provider.createEvent(newEvent);

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/calendar/events",
        expect.any(Object)
      );
      const [, request] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(JSON.parse((request.body as string) ?? "{}")).toMatchObject({
        summary: "New Event",
      });

      expect(result.id).toBe("1");
      expect(result.summary).toBe("New Event");
    });

    it("should update event successfully", async () => {
      const mockUpdatedEvent = {
        end: { dateTime: "2024-01-01T11:00:00Z" },
        id: "1",
        start: { dateTime: "2024-01-01T10:00:00Z" },
        summary: "Updated Event",
      };

      const updates: Partial<CalendarEvent> = {
        summary: "Updated Event",
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockUpdatedEvent,
        ok: true,
      });

      const result = await provider.updateEvent("1", updates);

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/calendar/events/1",
        expect.objectContaining({ method: "PATCH" })
      );
      expect(result.summary).toBe("Updated Event");
    });

    it("should delete event successfully", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
      });

      await expect(provider.deleteEvent("1")).resolves.not.toThrow();

      expect(mockFetch).toHaveBeenCalledWith("/api/calendar/events/1", {
        method: "DELETE",
      });
    });

    it("should export to ICS successfully", async () => {
      const events: CalendarEvent[] = [
        calendarEventSchema.parse({
          end: { dateTime: new Date("2024-01-01T11:00:00Z") },
          id: "1",
          start: { dateTime: new Date("2024-01-01T10:00:00Z") },
          summary: "Test Event",
        }),
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => "BEGIN:VCALENDAR\nEND:VCALENDAR",
      });

      const icsContent = await provider.exportToIcs(events);

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/calendar/ics/export",
        expect.objectContaining({ method: "POST" })
      );

      expect(icsContent).toBe("BEGIN:VCALENDAR\nEND:VCALENDAR");
    });

    it("should import from ICS successfully", async () => {
      const mockImportedEvents = [
        {
          end: { dateTime: "2024-01-01T11:00:00Z" },
          id: "1",
          start: { dateTime: "2024-01-01T10:00:00Z" },
          summary: "Imported Event",
        },
      ];

      const icsContent = "BEGIN:VCALENDAR\nEND:VCALENDAR";

      mockFetch.mockResolvedValueOnce({
        json: async () => mockImportedEvents,
        ok: true,
      });

      const events = await provider.importFromIcs(icsContent);

      expect(mockFetch).toHaveBeenCalledWith("/api/calendar/ics/import", {
        body: JSON.stringify({ icsContent }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });

      expect(events).toHaveLength(1);
      expect(events[0].summary).toBe("Imported Event");
    });
  });

  describe("GoogleCalendarProvider", () => {
    let provider: CalendarProvider;
    const mockDateRange: DateRange = {
      end: new Date("2024-01-07T23:59:59Z"),
      start: new Date("2024-01-01T00:00:00Z"),
    };

    beforeEach(() => {
      provider = calendarFactory.create("google", {
        apiKey: "test-api-key",
        calendarId: "test-calendar",
      });
    });

    it("should get events from Google Calendar API", async () => {
      const mockGoogleResponse = {
        items: [
          {
            end: { dateTime: "2024-01-01T11:00:00Z" },
            id: "1",
            start: { dateTime: "2024-01-01T10:00:00Z" },
            summary: "Google Event",
          },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockGoogleResponse,
        ok: true,
      });

      const events = await provider.getEvents(mockDateRange);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [requestUrl] = mockFetch.mock.calls[0] as [string];
      const parsedUrl = new URL(requestUrl);
      expect(parsedUrl.pathname).toContain("/calendars/test-calendar/events");
      expect(parsedUrl.searchParams.get("key")).toBe("test-api-key");
      expect(parsedUrl.searchParams.get("timeMin")).toBe(
        DateUtils.formatForApi(mockDateRange.start)
      );

      expect(events).toHaveLength(1);
      expect(events[0].summary).toBe("Google Event");
    });

    it("should create event in Google Calendar", async () => {
      const mockCreatedEvent = {
        end: { dateTime: "2024-01-01T11:00:00Z" },
        id: "1",
        start: { dateTime: "2024-01-01T10:00:00Z" },
        summary: "New Google Event",
      };

      const newEvent: Omit<CalendarEvent, "id"> = calendarEventSchema.parse({
        end: { dateTime: new Date("2024-01-01T11:00:00Z") },
        start: { dateTime: new Date("2024-01-01T10:00:00Z") },
        summary: "New Google Event",
      });

      mockFetch.mockResolvedValueOnce({
        json: async () => mockCreatedEvent,
        ok: true,
      });

      const result = await provider.createEvent(newEvent);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("www.googleapis.com/calendar/v3/calendars"),
        expect.objectContaining({
          body: expect.stringContaining("New Google Event"),
          method: "POST",
        })
      );

      expect(result.summary).toBe("New Google Event");
    });
  });
});

describe("CalendarEvent Interface", () => {
  it("should accept valid calendar event", () => {
    const event: CalendarEvent = calendarEventSchema.parse({
      attendees: [
        {
          email: "test@example.com",
        },
      ],
      description: "Test description",
      end: { dateTime: new Date() },
      id: "1",
      location: "Test location",
      metadata: { custom: "value" },
      recurrence: ["RRULE:FREQ=DAILY;INTERVAL=1"],
      start: { dateTime: new Date() },
      summary: "Test Event",
      timezone: "UTC",
    });

    expect(event.id).toBe("1");
    expect(event.summary).toBe("Test Event");
    expect(event.recurrence?.[0]).toContain("FREQ=DAILY");
  });

  it("should accept minimal calendar event", () => {
    const event: CalendarEvent = calendarEventSchema.parse({
      end: { dateTime: new Date() },
      id: "1",
      start: { dateTime: new Date() },
      summary: "Minimal Event",
    });

    expect(event.id).toBe("1");
    expect(event.description).toBeUndefined();
    expect(event.attendees).toEqual([]);
  });
});

describe("DateRange Type", () => {
  it("should accept valid date range", () => {
    const dateRange: DateRange = {
      end: new Date("2024-01-07"),
      start: new Date("2024-01-01"),
    };

    expect(dateRange.start).toBeInstanceOf(Date);
    expect(dateRange.end).toBeInstanceOf(Date);
  });
});
