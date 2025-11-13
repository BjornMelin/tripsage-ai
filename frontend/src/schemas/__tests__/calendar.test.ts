import { describe, expect, it } from "vitest";
import {
  calendarEventSchema,
  createEventRequestSchema,
  eventDateTimeSchema,
  freeBusyRequestSchema,
  updateEventRequestSchema,
} from "@/schemas/calendar";

describe("calendar schemas", () => {
  describe("eventDateTimeSchema", () => {
    it("accepts dateTime", () => {
      const result = eventDateTimeSchema.parse({
        dateTime: new Date("2025-01-15T10:00:00Z"),
      });
      expect(result.dateTime).toBeInstanceOf(Date);
    });

    it("accepts date string", () => {
      const result = eventDateTimeSchema.parse({
        date: "2025-01-15",
      });
      expect(result.date).toBe("2025-01-15");
    });

    it("accepts timeZone", () => {
      const result = eventDateTimeSchema.parse({
        dateTime: new Date(),
        timeZone: "America/New_York",
      });
      expect(result.timeZone).toBe("America/New_York");
    });
  });

  describe("createEventRequestSchema", () => {
    it("requires summary and start/end", () => {
      const result = createEventRequestSchema.parse({
        summary: "Test Event",
        start: { dateTime: new Date() },
        end: { dateTime: new Date(Date.now() + 3600000) },
      });
      expect(result.summary).toBe("Test Event");
    });

    it("accepts optional fields", () => {
      const result = createEventRequestSchema.parse({
        summary: "Test Event",
        description: "Description",
        location: "Location",
        start: { dateTime: new Date() },
        end: { dateTime: new Date(Date.now() + 3600000) },
        attendees: [{ email: "test@example.com" }],
      });
      expect(result.description).toBe("Description");
      expect(result.location).toBe("Location");
      expect(result.attendees).toHaveLength(1);
    });

    it("rejects missing summary", () => {
      expect(() =>
        createEventRequestSchema.parse({
          start: { dateTime: new Date() },
          end: { dateTime: new Date() },
        })
      ).toThrow();
    });
  });

  describe("updateEventRequestSchema", () => {
    it("allows partial updates", () => {
      const result = updateEventRequestSchema.parse({
        summary: "Updated Summary",
      });
      expect(result.summary).toBe("Updated Summary");
    });

    it("allows empty object", () => {
      expect(() => updateEventRequestSchema.parse({})).not.toThrow();
    });
  });

  describe("calendarEventSchema", () => {
    it("parses complete event", () => {
      const result = calendarEventSchema.parse({
        id: "event123",
        summary: "Test Event",
        start: { dateTime: new Date() },
        end: { dateTime: new Date(Date.now() + 3600000) },
        status: "confirmed",
      });
      expect(result.id).toBe("event123");
      expect(result.status).toBe("confirmed");
    });

    it("applies defaults", () => {
      const result = calendarEventSchema.parse({
        summary: "Test Event",
        start: { dateTime: new Date() },
        end: { dateTime: new Date() },
      });
      expect(result.status).toBe("confirmed");
      expect(result.transparency).toBe("opaque");
      expect(result.visibility).toBe("default");
    });
  });

  describe("freeBusyRequestSchema", () => {
    it("requires timeMin, timeMax, and items", () => {
      const result = freeBusyRequestSchema.parse({
        timeMin: new Date("2025-01-15T00:00:00Z"),
        timeMax: new Date("2025-01-16T00:00:00Z"),
        items: [{ id: "primary" }],
      });
      expect(result.items).toHaveLength(1);
    });

    it("applies defaults", () => {
      const result = freeBusyRequestSchema.parse({
        timeMin: new Date(),
        timeMax: new Date(),
        items: [{ id: "primary" }],
      });
      expect(result.calendarExpansionMax).toBe(50);
      expect(result.groupExpansionMax).toBe(50);
    });
  });
});

