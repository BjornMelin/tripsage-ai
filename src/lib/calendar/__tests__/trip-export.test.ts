/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import type { Trip } from "@/stores/trip-store";
import { tripToCalendarEvents } from "../trip-export";

describe("trip-export", () => {
  const mockTrip: Trip = {
    currency: "USD",
    description: "A test trip",
    destinations: [
      {
        activities: ["Visit Eiffel Tower", "Louvre Museum"],
        country: "France",
        endDate: "2025-01-17",
        id: "dest-1",
        name: "Paris",
        startDate: "2025-01-15",
        transportation: {
          details: "Flight AA123",
          type: "flight",
        },
      },
      {
        activities: ["Big Ben"],
        country: "UK",
        endDate: "2025-01-20",
        id: "dest-2",
        name: "London",
        startDate: "2025-01-17",
      },
    ],
    endDate: "2025-01-20",
    id: "trip-1",
    startDate: "2025-01-15",
    title: "Test Trip",
  };

  describe("tripToCalendarEvents", () => {
    it("creates trip start event", () => {
      const events = tripToCalendarEvents(mockTrip);
      const tripEvent = events.find((e) => e.summary === "Test Trip");
      expect(tripEvent).toBeDefined();
      expect(tripEvent?.start.dateTime).toBeInstanceOf(Date);
    });

    it("creates arrival events for destinations", () => {
      const events = tripToCalendarEvents(mockTrip);
      const arrivalEvent = events.find((e) => e.summary === "Arrive in Paris");
      expect(arrivalEvent).toBeDefined();
      expect(arrivalEvent?.location).toContain("Paris");
    });

    it("creates activity events", () => {
      const events = tripToCalendarEvents(mockTrip);
      const activityEvents = events.filter(
        (e) => e.travelMetadata?.type === "activity"
      );
      expect(activityEvents.length).toBeGreaterThan(0);
      expect(activityEvents.some((e) => e.summary === "Visit Eiffel Tower")).toBe(true);
    });

    it("creates departure events", () => {
      const events = tripToCalendarEvents(mockTrip);
      const departureEvent = events.find((e) => e.summary === "Depart from Paris");
      expect(departureEvent).toBeDefined();
    });

    it("includes travel metadata", () => {
      const events = tripToCalendarEvents(mockTrip);
      const event = events[0];
      expect(event.travelMetadata?.tripId).toBe("trip-1");
    });

    it("handles trip without dates", () => {
      const tripWithoutDates: Trip = {
        ...mockTrip,
        endDate: undefined,
        startDate: undefined,
      };
      const events = tripToCalendarEvents(tripWithoutDates);
      // Should still create destination events if they have dates
      expect(events.length).toBeGreaterThan(0);
    });

    it("handles destinations without dates", () => {
      const tripWithUndatedDestinations: Trip = {
        ...mockTrip,
        destinations: [
          {
            ...mockTrip.destinations[0],
            endDate: undefined,
            startDate: undefined,
          },
        ],
      };
      const events = tripToCalendarEvents(tripWithUndatedDestinations);
      // Should create trip event but not destination events
      expect(events.length).toBeGreaterThanOrEqual(1);
    });

    it("handles empty destinations array", () => {
      const tripWithNoDestinations: Trip = {
        ...mockTrip,
        destinations: [],
      };
      const events = tripToCalendarEvents(tripWithNoDestinations);
      // Should still create trip event
      expect(events.length).toBeGreaterThanOrEqual(1);
    });

    it("handles destinations without activities", () => {
      const tripWithoutActivities: Trip = {
        ...mockTrip,
        destinations: [
          {
            ...mockTrip.destinations[0],
            activities: undefined,
          },
        ],
      };
      const events = tripToCalendarEvents(tripWithoutActivities);
      // Should create arrival/departure but no activity events
      const activityEvents = events.filter(
        (e) => e.travelMetadata?.type === "activity"
      );
      expect(activityEvents.length).toBe(0);
    });

    it("handles trip with only start date", () => {
      const tripWithOnlyStart: Trip = {
        ...mockTrip,
        endDate: undefined,
      };
      const events = tripToCalendarEvents(tripWithOnlyStart);
      expect(events.length).toBeGreaterThan(0);
    });

    it("preserves travel metadata structure", () => {
      const events = tripToCalendarEvents(mockTrip);
      const event = events[0];
      expect(event.travelMetadata).toHaveProperty("tripId");
      expect(event.travelMetadata).toHaveProperty("type");
    });
  });
});
