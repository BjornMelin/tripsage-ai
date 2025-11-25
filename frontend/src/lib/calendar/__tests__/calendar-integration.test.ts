/** @vitest-environment node */

import type { CalendarEvent } from "@schemas/calendar";
import { calendarEventSchema } from "@schemas/calendar";
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createCalendarEvent } from "@/test/factories/calendar-factory";
import { resetAllFactories } from "@/test/factories/reset";
import { server } from "@/test/msw/server";
import type { DateRange } from "../../dates/unified-date-utils";
import { DateUtils } from "../../dates/unified-date-utils";
import type { CalendarProvider } from "../calendar-integration";
import { calendarFactory } from "../calendar-integration";

describe("CalendarIntegration", () => {
  beforeEach(() => {
    resetAllFactories();
    vi.clearAllMocks();
    server.resetHandlers();
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

      server.use(
        http.post("http://localhost:3000/api/calendar/events", async ({ request }) => {
          const body = await request.json();
          expect(body).toMatchObject({
            end: DateUtils.formatForApi(mockDateRange.end),
            start: DateUtils.formatForApi(mockDateRange.start),
          });
          return HttpResponse.json(mockEvents);
        })
      );

      const events = await provider.getEvents(mockDateRange);

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

      const { id: _omit, ...rest } = createCalendarEvent({ summary: "New Event" });
      const newEvent: Omit<CalendarEvent, "id"> = rest;

      server.use(
        http.put("http://localhost:3000/api/calendar/events", async ({ request }) => {
          const body = (await request.json()) as Record<string, unknown>;
          expect(body).toMatchObject({ summary: "New Event" });
          return HttpResponse.json(mockEvent);
        })
      );

      const result = await provider.createEvent(newEvent);

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

      server.use(
        http.patch("http://localhost:3000/api/calendar/events/1", () =>
          HttpResponse.json(mockUpdatedEvent)
        )
      );

      const result = await provider.updateEvent("1", updates);

      expect(result.summary).toBe("Updated Event");
    });

    it("should delete event successfully", async () => {
      server.use(
        http.delete("http://localhost:3000/api/calendar/events/1", () =>
          HttpResponse.json({}, { status: 200 })
        )
      );

      await expect(provider.deleteEvent("1")).resolves.not.toThrow();
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

      server.use(
        http.post(
          "http://localhost:3000/api/calendar/ics/export",
          async ({ request }) => {
            const body = (await request.json()) as { events?: unknown };
            expect(Array.isArray(body.events)).toBe(true);
            return HttpResponse.text("BEGIN:VCALENDAR\nEND:VCALENDAR");
          }
        )
      );

      const icsContent = await provider.exportToIcs(events);

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

      server.use(
        http.post(
          "http://localhost:3000/api/calendar/ics/import",
          async ({ request }) => {
            const body = await request.json();
            expect(body).toEqual({ icsContent });
            return HttpResponse.json(mockImportedEvents);
          }
        )
      );

      const events = await provider.importFromIcs(icsContent);

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

      server.use(
        http.get(
          "https://www.googleapis.com/calendar/v3/calendars/:calendarId/events",
          ({ request, params }) => {
            expect(params.calendarId).toBe("test-calendar");
            const url = new URL(request.url);
            expect(url.searchParams.get("key")).toBe("test-api-key");
            expect(url.searchParams.get("timeMin")).toBe(
              DateUtils.formatForApi(mockDateRange.start)
            );
            return HttpResponse.json(mockGoogleResponse);
          }
        )
      );

      const events = await provider.getEvents(mockDateRange);

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

      const { id: _omit, ...rest } = createCalendarEvent({
        summary: "New Google Event",
      });
      const newEvent: Omit<CalendarEvent, "id"> = rest;

      server.use(
        http.post(
          "https://www.googleapis.com/calendar/v3/calendars/:calendarId/events",
          async ({ request, params }) => {
            expect(params.calendarId).toBe("test-calendar");
            const body = await request.json();
            expect(JSON.stringify(body)).toContain("New Google Event");
            return HttpResponse.json(mockCreatedEvent);
          }
        )
      );

      const result = await provider.createEvent(newEvent);

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
