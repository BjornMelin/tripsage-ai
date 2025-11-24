/** @vitest-environment jsdom */

import { describe, expect, it, vi } from "vitest";
import { getActivityBookingUrl, openActivityBooking } from "../booking";

describe("booking helpers", () => {
  describe("getActivityBookingUrl", () => {
    it("should return Google Maps URL for Places activities", () => {
      const activity = {
        date: "2025-01-01",
        description: "Test",
        duration: 120,
        id: "ChIJN1t_tDeuEmsRUsoyG83frY4",
        location: "Test Location",
        name: "Test Activity",
        price: 2,
        rating: 4.5,
        type: "museum",
      };

      const url = getActivityBookingUrl(activity);

      expect(url).toBe(
        "https://www.google.com/maps/place/?q=place_id:ChIJN1t_tDeuEmsRUsoyG83frY4"
      );
    });

    it("should return null for AI fallback activities", () => {
      const activity = {
        date: "2025-01-01",
        description: "Test",
        duration: 120,
        id: "ai_fallback:abc123",
        location: "Test Location",
        name: "AI Suggested Activity",
        price: 2,
        rating: 0,
        type: "activity",
      };

      const url = getActivityBookingUrl(activity);

      expect(url).toBeNull();
    });
  });

  describe("openActivityBooking", () => {
    beforeEach(() => {
      // Mock window.open
      global.window.open = vi.fn();
    });

    it("should open Google Maps URL for Places activities", () => {
      const activity = {
        date: "2025-01-01",
        description: "Test",
        duration: 120,
        id: "ChIJN1t_tDeuEmsRUsoyG83frY4",
        location: "Test Location",
        name: "Test Activity",
        price: 2,
        rating: 4.5,
        type: "museum",
      };

      const result = openActivityBooking(activity);

      expect(result).toBe(true);
      expect(window.open).toHaveBeenCalledWith(
        "https://www.google.com/maps/place/?q=place_id:ChIJN1t_tDeuEmsRUsoyG83frY4",
        "_blank",
        "noopener,noreferrer"
      );
    });

    it("should return false for AI fallback activities", () => {
      const activity = {
        date: "2025-01-01",
        description: "Test",
        duration: 120,
        id: "ai_fallback:abc123",
        location: "Test Location",
        name: "AI Suggested Activity",
        price: 2,
        rating: 0,
        type: "activity",
      };

      const result = openActivityBooking(activity);

      expect(result).toBe(false);
      expect(window.open).not.toHaveBeenCalled();
    });
  });
});
