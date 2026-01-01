import { ISO_DATETIME_STRING } from "@schemas/shared/time";
import type { TripSuggestion } from "@schemas/trips";
import { describe, expect, it } from "vitest";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import {
  computeDefaultTripDates,
  computeDefaultTripTitle,
  makeCreateTripPayload,
  PLAN_TRIP_FORM_SCHEMA,
} from "./create-trip-flow";

describe("create-trip-flow", () => {
  describe("computeDefaultTripTitle", () => {
    it("returns a default title when destination is empty", () => {
      expect(computeDefaultTripTitle("")).toBe("New Trip");
      expect(computeDefaultTripTitle("   ")).toBe("New Trip");
    });

    it("builds a title from the destination", () => {
      expect(computeDefaultTripTitle(" Tokyo ")).toBe("Trip to Tokyo");
    });
  });

  describe("computeDefaultTripDates", () => {
    it("returns a start date tomorrow and end date 7 days after start", () => {
      const now = new Date(2026, 0, 1, 12, 0, 0);
      const { startDate, endDate } = computeDefaultTripDates(now);
      expect(startDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(endDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);

      const expectedStart = DateUtils.format(
        DateUtils.add(now, 1, "days"),
        "yyyy-MM-dd"
      );
      const expectedEnd = DateUtils.format(
        DateUtils.add(DateUtils.parse(expectedStart), 7, "days"),
        "yyyy-MM-dd"
      );

      expect(startDate).toBe(expectedStart);
      expect(endDate).toBe(expectedEnd);
    });
  });

  describe("PLAN_TRIP_FORM_SCHEMA", () => {
    it("requires a destination", () => {
      const result = PLAN_TRIP_FORM_SCHEMA.safeParse({
        description: "",
        destination: "",
        endDate: "2026-01-01",
        startDate: "2026-01-01",
        title: "",
      });
      expect(result.success).toBe(false);
    });

    it("allows end date on or after start date", () => {
      const sameDay = PLAN_TRIP_FORM_SCHEMA.safeParse({
        description: "",
        destination: "Paris",
        endDate: "2026-01-01",
        startDate: "2026-01-01",
        title: "",
      });
      expect(sameDay.success).toBe(true);

      const earlierEnd = PLAN_TRIP_FORM_SCHEMA.safeParse({
        description: "",
        destination: "Paris",
        endDate: "2025-12-31",
        startDate: "2026-01-01",
        title: "",
      });
      expect(earlierEnd.success).toBe(false);
    });
  });

  describe("makeCreateTripPayload", () => {
    const defaults = { endDate: "2099-01-08", startDate: "2099-01-01" };

    it("builds a payload with safe defaults and ISO datetimes", () => {
      const payload = makeCreateTripPayload(
        {
          description: "",
          destination: " Tokyo, Japan ",
          endDate: "2099-01-10",
          startDate: "2099-01-03",
          title: "",
        },
        defaults,
        null
      );

      expect(payload.destination).toBe("Tokyo, Japan");
      expect(payload.title).toBe("Trip to Tokyo, Japan");
      expect(payload.currency).toBe("USD");
      expect(payload.description).toBeUndefined();
      expect(payload.status).toBe("planning");
      expect(payload.travelers).toBe(1);
      expect(payload.tripType).toBe("leisure");
      expect(payload.visibility).toBe("private");

      expect(ISO_DATETIME_STRING.safeParse(payload.startDate).success).toBe(true);
      expect(ISO_DATETIME_STRING.safeParse(payload.endDate).success).toBe(true);
    });

    it("prefers suggestion title when no custom title is provided", () => {
      const suggestion: TripSuggestion = {
        bestTimeToVisit: "Spring",
        category: "culture",
        currency: "USD",
        description: "A great trip",
        destination: "Paris",
        duration: 5,
        estimatedPrice: 2000,
        highlights: ["A", "B", "C"],
        id: "sug-1",
        rating: 4.5,
        title: "Paris Getaway",
      };

      const payload = makeCreateTripPayload(
        {
          description: "",
          destination: "Paris",
          endDate: "",
          startDate: defaults.startDate,
          title: "",
        },
        defaults,
        suggestion
      );

      expect(payload.title).toBe("Paris Getaway");
    });

    it("computes an end date from suggestion duration when end date is missing", () => {
      const suggestion: TripSuggestion = {
        bestTimeToVisit: "Spring",
        category: "culture",
        currency: "USD",
        description: "A great trip",
        destination: "Paris",
        duration: 5,
        estimatedPrice: 2000,
        highlights: ["A", "B", "C"],
        id: "sug-1",
        rating: 4.5,
        title: "Paris Getaway",
      };

      const payload = makeCreateTripPayload(
        {
          description: "",
          destination: "Paris",
          endDate: "",
          startDate: "2099-01-01",
          title: "",
        },
        defaults,
        suggestion
      );

      const expectedEndIsoDate = DateUtils.format(
        DateUtils.add(DateUtils.parse("2099-01-01"), 5, "days"),
        "yyyy-MM-dd"
      );
      const expectedEnd = DateUtils.formatForApi(DateUtils.parse(expectedEndIsoDate));
      expect(payload.endDate).toBe(expectedEnd);
    });

    it("computes a start date from suggestion duration when start date is missing", () => {
      const suggestion: TripSuggestion = {
        bestTimeToVisit: "Spring",
        category: "culture",
        currency: "USD",
        description: "A great trip",
        destination: "Paris",
        duration: 5,
        estimatedPrice: 2000,
        highlights: ["A", "B", "C"],
        id: "sug-1",
        rating: 4.5,
        title: "Paris Getaway",
      };

      const payload = makeCreateTripPayload(
        {
          description: "",
          destination: "Paris",
          endDate: "2099-01-10",
          startDate: "",
          title: "",
        },
        defaults,
        suggestion
      );

      const expectedStartIsoDate = DateUtils.format(
        DateUtils.subtract(DateUtils.parse("2099-01-10"), 5, "days"),
        "yyyy-MM-dd"
      );
      const expectedStart = DateUtils.formatForApi(
        DateUtils.parse(expectedStartIsoDate)
      );
      expect(payload.startDate).toBe(expectedStart);
    });
  });
});
