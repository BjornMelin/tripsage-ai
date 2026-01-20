/** @vitest-environment node */

import {
  itineraryItemUpsertSchema,
  tripCreateSchema,
  tripSettingsFormSchema,
  tripUpdateSchema,
} from "@schemas/trips";
import { describe, expect, it } from "vitest";

describe("trips schemas", () => {
  describe("tripCreateSchema", () => {
    it("accepts ISO datetime inputs by normalizing to dates", () => {
      const result = tripCreateSchema.safeParse({
        currency: "USD",
        destination: "Paris, France",
        endDate: "2026-02-10T00:00:00.000Z",
        startDate: "2026-02-01T00:00:00.000Z",
        status: "planning",
        title: "Trip to Paris",
        travelers: 1,
        tripType: "leisure",
        visibility: "private",
      });

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.startDate).toBe("2026-02-01");
        expect(result.data.endDate).toBe("2026-02-10");
      }
    });

    it("normalizes ISO datetimes with timezone offsets", () => {
      const result = tripCreateSchema.safeParse({
        currency: "USD",
        destination: "Mumbai, India",
        endDate: "2026-02-10T12:00:00+05:30",
        startDate: "2026-02-01T12:00:00+05:30",
        status: "planning",
        title: "Trip with offset",
        travelers: 1,
        tripType: "leisure",
        visibility: "private",
      });

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.startDate).toBe("2026-02-01");
        expect(result.data.endDate).toBe("2026-02-10");
      }
    });

    it("accepts ISO date inputs", () => {
      const result = tripCreateSchema.safeParse({
        currency: "USD",
        destination: "Tokyo, Japan",
        endDate: "2026-02-10",
        startDate: "2026-02-01",
        status: "planning",
        title: "Tokyo weekender",
        travelers: 1,
        tripType: "leisure",
        visibility: "private",
      });

      expect(result.success).toBe(true);
    });

    it("rejects non-ISO date strings", () => {
      const result = tripCreateSchema.safeParse({
        currency: "USD",
        destination: "Tokyo, Japan",
        endDate: "02/10/2026",
        startDate: "02/01/2026",
        status: "planning",
        title: "Bad date trip",
        travelers: 1,
        tripType: "leisure",
        visibility: "private",
      });

      expect(result.success).toBe(false);
    });
  });

  describe("tripUpdateSchema", () => {
    it("accepts null description to clear", () => {
      const result = tripUpdateSchema.safeParse({ description: null });
      expect(result.success).toBe(true);
    });

    it("rejects empty description strings", () => {
      const result = tripUpdateSchema.safeParse({ description: "" });
      expect(result.success).toBe(false);
    });
  });

  describe("tripSettingsFormSchema", () => {
    it("accepts a minimal payload", () => {
      const result = tripSettingsFormSchema.safeParse({ title: "Tokyo weekender" });
      expect(result.success).toBe(true);
    });

    it("rejects endDate before startDate", () => {
      const result = tripSettingsFormSchema.safeParse({
        endDate: "2026-02-01",
        startDate: "2026-02-05",
        title: "Backwards trip",
      });
      expect(result.success).toBe(false);
    });

    it("rejects invalid ISO date strings", () => {
      const result = tripSettingsFormSchema.safeParse({
        startDate: "2026-2-5",
        title: "Bad date",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("itineraryItemUpsertSchema", () => {
    it("validates a minimal itinerary item", () => {
      const result = itineraryItemUpsertSchema.safeParse({
        itemType: "other",
        payload: {},
        title: "Free time",
        tripId: 1,
      });

      expect(result.success).toBe(true);
    });

    it("rejects invalid typed payload fields", () => {
      const result = itineraryItemUpsertSchema.safeParse({
        itemType: "activity",
        payload: { url: "not-a-url" },
        title: "Museum",
        tripId: 1,
      });

      expect(result.success).toBe(false);
    });
  });
});
