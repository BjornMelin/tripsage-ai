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

    it("should extract booking URL from description for AI fallback activities", () => {
      const activity = {
        date: "2025-01-01",
        description: "Book now at https://www.getyourguide.com/awesome-tour",
        duration: 120,
        id: "ai_fallback:abc123",
        location: "Test Location",
        name: "AI Suggested Activity",
        price: 2,
        rating: 0,
        type: "activity",
      };

      const url = getActivityBookingUrl(activity);

      expect(url).toBe("https://www.getyourguide.com/awesome-tour");
    });

    it("should use metadata bookingUrl when provided", () => {
      const activity = {
        date: "2025-01-01",
        description: "No links here",
        duration: 120,
        id: "ai_fallback:meta1",
        location: "Test Location",
        metadata: { bookingUrl: "https://www.viator.com/some-tour" },
        name: "AI Suggested Activity",
        price: 2,
        rating: 0,
        type: "activity",
      };

      const url = getActivityBookingUrl(activity);

      expect(url).toBe("https://www.viator.com/some-tour");
    });

    it("should fall back to maps search when no booking URL exists", () => {
      const activity = {
        coordinates: { lat: 40.0, lng: -70.0 },
        date: "2025-01-01",
        description: "No links here",
        duration: 120,
        id: "ai_fallback:nolink",
        location: "Test Location",
        name: "AI Suggested Activity",
        price: 2,
        rating: 0,
        type: "activity",
      };

      const url = getActivityBookingUrl(activity);

      expect(url).toBe("https://www.google.com/maps/search/?api=1&query=40,-70");
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

    it("should open maps search when no AI booking URL exists", () => {
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

      expect(result).toBe(true);
      expect(window.open).toHaveBeenCalledWith(
        expect.stringContaining("https://www.google.com/maps/search/?api=1&query="),
        "_blank",
        "noopener,noreferrer"
      );
    });

    it("should open extracted AI booking URL when available", () => {
      const activity = {
        date: "2025-01-01",
        description: "Check https://www.tripadvisor.com/booking-link",
        duration: 120,
        id: "ai_fallback:booking123",
        location: "Test Location",
        name: "AI Suggested Activity",
        price: 2,
        rating: 0,
        type: "activity",
      };

      const result = openActivityBooking(activity);

      expect(result).toBe(true);
      expect(window.open).toHaveBeenCalledWith(
        "https://www.tripadvisor.com/booking-link",
        "_blank",
        "noopener,noreferrer"
      );
    });
  });
});
