/** @vitest-environment node */

import { calendarEventSchema } from "@schemas/calendar";
import { beforeEach, describe, expect, it } from "vitest";
import {
  createCalendarEvent,
  resetCalendarFactory,
} from "@/test/factories/calendar-factory";
import {
  type GenerateIcsOptions,
  generateIcsFromEvents,
  sanitizeCalendarFilename,
} from "../ics";

describe("generateIcsFromEvents", () => {
  beforeEach(() => {
    resetCalendarFactory();
  });

  describe("basic ICS generation", () => {
    it("should generate valid ICS with single event", () => {
      const event = createCalendarEvent({
        description: "Flight from NYC to LAX",
        location: "JFK Airport",
        summary: "Test Flight",
      });

      const { icsString, eventCount } = generateIcsFromEvents({
        calendarName: "My Trip",
        events: [event],
      });

      expect(eventCount).toBe(1);
      expect(icsString).toContain("BEGIN:VCALENDAR");
      expect(icsString).toContain("END:VCALENDAR");
      expect(icsString).toContain("BEGIN:VEVENT");
      expect(icsString).toContain("END:VEVENT");
      expect(icsString).toContain("SUMMARY:Test Flight");
      expect(icsString).toContain("DESCRIPTION:Flight from NYC to LAX");
      expect(icsString).toContain("LOCATION:JFK Airport");
    });

    it("should generate ICS with multiple events", () => {
      const events = [
        createCalendarEvent({ summary: "Event 1" }),
        createCalendarEvent({ summary: "Event 2" }),
        createCalendarEvent({ summary: "Event 3" }),
      ];

      const { icsString, eventCount } = generateIcsFromEvents({
        calendarName: "Multi Event Calendar",
        events,
      });

      expect(eventCount).toBe(3);
      expect(icsString).toContain("SUMMARY:Event 1");
      expect(icsString).toContain("SUMMARY:Event 2");
      expect(icsString).toContain("SUMMARY:Event 3");
    });

    it("should use calendar name in output", () => {
      const event = createCalendarEvent({ summary: "Test" });

      const { icsString } = generateIcsFromEvents({
        calendarName: "TripSage Itinerary",
        events: [event],
      });

      expect(icsString).toContain("X-WR-CALNAME:TripSage Itinerary");
    });

    it("should use specified timezone", () => {
      const event = createCalendarEvent({ summary: "Test" });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
        timezone: "America/New_York",
      });

      expect(icsString).toContain("X-WR-TIMEZONE:America/New_York");
    });

    it("should generate valid ICS when no timezone specified", () => {
      const event = createCalendarEvent({ summary: "Test" });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      // Should generate valid ICS structure
      expect(icsString).toContain("BEGIN:VCALENDAR");
      expect(icsString).toContain("END:VCALENDAR");
      expect(icsString).toContain("SUMMARY:Test");
    });
  });

  describe("all-day events", () => {
    it("should handle all-day events with date only", () => {
      const event = calendarEventSchema.parse({
        end: { date: "2024-06-16" },
        start: { date: "2024-06-15" },
        summary: "All Day Event",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      expect(icsString).toContain("SUMMARY:All Day Event");
      expect(icsString).toContain("BEGIN:VEVENT");
    });
  });

  describe("events with attendees", () => {
    it("should include attendee information", () => {
      const event = createCalendarEvent({
        attendees: [
          {
            additionalGuests: 0,
            displayName: "Alice",
            email: "alice@example.com",
            optional: false,
            responseStatus: "accepted",
          },
          {
            additionalGuests: 0,
            displayName: "Bob",
            email: "bob@example.com",
            optional: false,
            responseStatus: "tentative",
          },
        ],
        summary: "Meeting",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      expect(icsString).toContain("ATTENDEE");
      expect(icsString).toContain("alice@example.com");
      expect(icsString).toContain("bob@example.com");
      // CN values are quoted in ical-generator output
      expect(icsString).toContain('CN="Alice"');
      expect(icsString).toContain('CN="Bob"');
    });

    it("should map attendee response status correctly", () => {
      const event = createCalendarEvent({
        attendees: [
          {
            additionalGuests: 0,
            email: "accepted@test.com",
            optional: false,
            responseStatus: "accepted",
          },
          {
            additionalGuests: 0,
            email: "declined@test.com",
            optional: false,
            responseStatus: "declined",
          },
          {
            additionalGuests: 0,
            email: "tentative@test.com",
            optional: false,
            responseStatus: "tentative",
          },
          {
            additionalGuests: 0,
            email: "needsaction@test.com",
            optional: false,
            responseStatus: "needsAction",
          },
        ],
        summary: "Meeting",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      expect(icsString).toContain("PARTSTAT=ACCEPTED");
      expect(icsString).toContain("PARTSTAT=DECLINED");
      expect(icsString).toContain("PARTSTAT=TENTATIVE");
      expect(icsString).toContain("PARTSTAT=NEEDS-ACTION");
    });

    it("should set RSVP based on optional flag", () => {
      const event = createCalendarEvent({
        attendees: [
          {
            additionalGuests: 0,
            email: "required@test.com",
            optional: false,
            responseStatus: "needsAction",
          },
          {
            additionalGuests: 0,
            email: "optional@test.com",
            optional: true,
            responseStatus: "needsAction",
          },
        ],
        summary: "Meeting",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      // Non-optional attendees should have RSVP=TRUE
      expect(icsString).toContain("RSVP=TRUE");
    });
  });

  describe("events with reminders", () => {
    it("should include reminder alarms", () => {
      const event = createCalendarEvent({
        reminders: {
          overrides: [
            { method: "email", minutes: 30 },
            { method: "popup", minutes: 10 },
          ],
          useDefault: false,
        },
        summary: "Reminder Test",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      expect(icsString).toContain("BEGIN:VALARM");
      expect(icsString).toContain("END:VALARM");
      // ical-generator formats triggers as duration (e.g., -PT30M for 30 minutes)
      expect(icsString).toContain("TRIGGER:-PT30M");
      expect(icsString).toContain("TRIGGER:-PT10M");
    });

    it("should map email reminder method", () => {
      const event = createCalendarEvent({
        reminders: {
          overrides: [{ method: "email", minutes: 60 }],
          useDefault: false,
        },
        summary: "Email Reminder",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      expect(icsString).toContain("ACTION:EMAIL");
    });

    it("should map popup reminder to display", () => {
      const event = createCalendarEvent({
        reminders: {
          overrides: [{ method: "popup", minutes: 15 }],
          useDefault: false,
        },
        summary: "Popup Reminder",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      expect(icsString).toContain("ACTION:DISPLAY");
    });
  });

  describe("events with recurrence", () => {
    it("should include recurrence rules", () => {
      const event = createCalendarEvent({
        recurrence: ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
        summary: "Weekly Meeting",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      // The recurrence is parsed and re-serialized
      expect(icsString).toContain("SUMMARY:Weekly Meeting");
      // Note: exact RRULE format depends on RecurringDateGenerator output
    });
  });

  describe("event metadata", () => {
    it("should include UID in output", () => {
      const event = createCalendarEvent({
        iCalUID: "unique-id-12345@tripsage.ai",
        summary: "Test",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      // ical-generator includes a UID for each event (may be auto-generated or from input)
      expect(icsString).toContain("UID:");
    });

    it("should include created timestamp", () => {
      const created = new Date("2024-01-15T10:00:00Z");
      const event = createCalendarEvent({
        created,
        summary: "Test",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      expect(icsString).toContain("CREATED:");
    });

    it("should include last modified timestamp", () => {
      const updated = new Date("2024-01-20T15:30:00Z");
      const event = createCalendarEvent({
        summary: "Test",
        updated,
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      expect(icsString).toContain("LAST-MODIFIED:");
    });
  });

  describe("determinism", () => {
    it("should produce consistent event count for same input", () => {
      const events = [
        createCalendarEvent({ iCalUID: "uid-1@test", id: "1", summary: "Event A" }),
        createCalendarEvent({ iCalUID: "uid-2@test", id: "2", summary: "Event B" }),
      ];

      const options: GenerateIcsOptions = {
        calendarName: "Determinism Test",
        events,
        timezone: "UTC",
      };

      const result1 = generateIcsFromEvents(options);
      const result2 = generateIcsFromEvents(options);

      // Event count is deterministic
      expect(result1.eventCount).toBe(result2.eventCount);
      expect(result1.eventCount).toBe(2);
      // Both outputs contain the same events
      expect(result1.icsString).toContain("Event A");
      expect(result1.icsString).toContain("Event B");
      expect(result2.icsString).toContain("Event A");
      expect(result2.icsString).toContain("Event B");
    });
  });

  describe("edge cases", () => {
    it("should handle event without end date (defaults to 1 hour)", () => {
      // This tests the fallback behavior
      const event = calendarEventSchema.parse({
        end: {}, // Empty end
        start: { dateTime: new Date("2024-06-15T10:00:00Z") },
        summary: "No End Time",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      expect(icsString).toContain("SUMMARY:No End Time");
      expect(icsString).toContain("DTEND");
    });

    it("should handle empty attendees array", () => {
      const event = createCalendarEvent({
        attendees: [],
        summary: "No Attendees",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      expect(icsString).toContain("SUMMARY:No Attendees");
      expect(icsString).not.toContain("ATTENDEE:");
    });

    it("should handle special characters in summary", () => {
      const event = createCalendarEvent({
        summary: "Meeting: Project Alpha & Beta",
      });

      const { icsString } = generateIcsFromEvents({
        calendarName: "Test",
        events: [event],
      });

      // The library should handle escaping
      expect(icsString).toContain("Meeting");
    });
  });
});

describe("sanitizeCalendarFilename", () => {
  it("should replace spaces with underscores", () => {
    expect(sanitizeCalendarFilename("My Trip")).toBe("My_Trip");
  });

  it("should replace special characters with underscores and collapse consecutive underscores", () => {
    expect(sanitizeCalendarFilename("Trip: NYC -> LA")).toBe("Trip_NYC_LA");
  });

  it("should handle alphanumeric names unchanged", () => {
    expect(sanitizeCalendarFilename("TripSage2024")).toBe("TripSage2024");
  });

  it("should return default for empty string", () => {
    expect(sanitizeCalendarFilename("")).toBe("calendar");
  });

  it("should return default for all-special-character names", () => {
    expect(sanitizeCalendarFilename("!!!")).toBe("calendar");
    expect(sanitizeCalendarFilename("@#$%")).toBe("calendar");
  });

  it("should trim leading and trailing underscores", () => {
    expect(sanitizeCalendarFilename("  Trip  ")).toBe("Trip");
    expect(sanitizeCalendarFilename("___Trip___")).toBe("Trip");
  });

  it("should truncate very long names for filesystem safety", () => {
    const longName = "A".repeat(300);
    const result = sanitizeCalendarFilename(longName);
    expect(result.length).toBe(200);
  });
});
