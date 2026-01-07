/** @vitest-environment node */

import {
  itineraryItemUpsertSchema,
  tripSettingsFormSchema,
  tripUpdateSchema,
} from "@schemas/trips";
import { describe, expect, it } from "vitest";

describe("trips schemas", () => {
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
