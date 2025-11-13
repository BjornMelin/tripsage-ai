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
    it("accepts dateTime as Date object", () => {
      const result = eventDateTimeSchema.parse({
        dateTime: new Date("2025-01-15T10:00:00Z"),
      });
      expect(result.dateTime).toBeInstanceOf(Date);
    });

    it("accepts dateTime as ISO string and transforms to Date", () => {
      const result = eventDateTimeSchema.parse({
        dateTime: "2025-01-15T10:00:00.000Z",
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

    it("rejects invalid date string format", () => {
      expect(() =>
        eventDateTimeSchema.parse({
          date: "2025/01/15", // Invalid format
        })
      ).toThrow();
    });

    it("rejects invalid datetime string", () => {
      expect(() =>
        eventDateTimeSchema.parse({
          dateTime: "invalid-date",
        })
      ).toThrow();
    });

    it("allows both date and dateTime to be optional", () => {
      const result = eventDateTimeSchema.parse({
        timeZone: "UTC",
      });
      expect(result.timeZone).toBe("UTC");
      expect(result.date).toBeUndefined();
      expect(result.dateTime).toBeUndefined();
    });
  });

  describe("createEventRequestSchema", () => {
    it("requires summary and start/end", () => {
      const result = createEventRequestSchema.parse({
        end: { dateTime: new Date(Date.now() + 3600000) },
        start: { dateTime: new Date() },
        summary: "Test Event",
      });
      expect(result.summary).toBe("Test Event");
    });

    it("accepts optional fields", () => {
      const result = createEventRequestSchema.parse({
        attendees: [{ email: "test@example.com" }],
        description: "Description",
        end: { dateTime: new Date(Date.now() + 3600000) },
        location: "Location",
        start: { dateTime: new Date() },
        summary: "Test Event",
      });
      expect(result.description).toBe("Description");
      expect(result.location).toBe("Location");
      expect(result.attendees).toHaveLength(1);
    });

    it("rejects missing summary", () => {
      expect(() =>
        createEventRequestSchema.parse({
          end: { dateTime: new Date() },
          start: { dateTime: new Date() },
        })
      ).toThrow();
    });

    it("rejects missing start", () => {
      expect(() =>
        createEventRequestSchema.parse({
          end: { dateTime: new Date() },
          summary: "Test Event",
        })
      ).toThrow();
    });

    it("rejects missing end", () => {
      expect(() =>
        createEventRequestSchema.parse({
          start: { dateTime: new Date() },
          summary: "Test Event",
        })
      ).toThrow();
    });

    it("validates summary length", () => {
      expect(() =>
        createEventRequestSchema.parse({
          end: { dateTime: new Date() },
          start: { dateTime: new Date() },
          summary: "a".repeat(1025), // Exceeds max length
        })
      ).toThrow();
    });

    it("validates description length", () => {
      expect(() =>
        createEventRequestSchema.parse({
          description: "a".repeat(8193), // Exceeds max length
          end: { dateTime: new Date() },
          start: { dateTime: new Date() },
          summary: "Test Event",
        })
      ).toThrow();
    });

    it("validates attendee email format", () => {
      expect(() =>
        createEventRequestSchema.parse({
          attendees: [{ email: "invalid-email" }],
          end: { dateTime: new Date() },
          start: { dateTime: new Date() },
          summary: "Test Event",
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
        end: { dateTime: new Date(Date.now() + 3600000) },
        id: "event123",
        start: { dateTime: new Date() },
        status: "confirmed",
        summary: "Test Event",
      });
      expect(result.id).toBe("event123");
      expect(result.status).toBe("confirmed");
    });

    it("applies defaults", () => {
      const result = calendarEventSchema.parse({
        end: { dateTime: new Date() },
        start: { dateTime: new Date() },
        summary: "Test Event",
      });
      expect(result.status).toBe("confirmed");
      expect(result.transparency).toBe("opaque");
      expect(result.visibility).toBe("default");
    });
  });

  describe("freeBusyRequestSchema", () => {
    it("requires timeMin, timeMax, and items", () => {
      const result = freeBusyRequestSchema.parse({
        items: [{ id: "primary" }],
        timeMax: new Date("2025-01-16T00:00:00Z"),
        timeMin: new Date("2025-01-15T00:00:00Z"),
      });
      expect(result.items).toHaveLength(1);
    });

    it("applies defaults", () => {
      const timeMin = new Date();
      const timeMax = new Date(timeMin.getTime() + 3600000); // 1 hour later
      const result = freeBusyRequestSchema.parse({
        items: [{ id: "primary" }],
        timeMax,
        timeMin,
      });
      expect(result.calendarExpansionMax).toBe(50);
      expect(result.groupExpansionMax).toBe(50);
    });

    it("rejects empty items array", () => {
      expect(() =>
        freeBusyRequestSchema.parse({
          items: [],
          timeMax: new Date(),
          timeMin: new Date(),
        })
      ).toThrow();
    });

    it("validates calendarExpansionMax range", () => {
      expect(() =>
        freeBusyRequestSchema.parse({
          calendarExpansionMax: 51, // Exceeds max
          items: [{ id: "primary" }],
          timeMax: new Date(),
          timeMin: new Date(),
        })
      ).toThrow();
    });

    it("validates groupExpansionMax range", () => {
      expect(() =>
        freeBusyRequestSchema.parse({
          groupExpansionMax: 101, // Exceeds max
          items: [{ id: "primary" }],
          timeMax: new Date(),
          timeMin: new Date(),
        })
      ).toThrow();
    });

    it("validates timeMax is after timeMin", () => {
      expect(() =>
        freeBusyRequestSchema.parse({
          items: [{ id: "primary" }],
          timeMax: new Date("2025-01-15T00:00:00Z"), // Before timeMin
          timeMin: new Date("2025-01-16T00:00:00Z"),
        })
      ).toThrow();
    });
  });
});
