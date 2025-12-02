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

    it("should clean trailing punctuation and return valid booking URL", () => {
      const activity = {
        date: "2025-01-01",
        description: "Book at https://www.viator.com/awesome-tour).",
        duration: 120,
        id: "ai_fallback:punctuation",
        location: "Test Location",
        name: "AI Suggested Activity",
        price: 2,
        rating: 0,
        type: "activity",
      };

      const url = getActivityBookingUrl(activity);

      expect(url).toBe("https://www.viator.com/awesome-tour");
    });

    it("should prioritize known booking domains when multiple URLs exist", () => {
      const activity = {
        date: "2025-01-01",
        description:
          "Option A https://example.com/tour and https://booking.com/preferred-tour",
        duration: 120,
        id: "ai_fallback:priority",
        location: "Test Location",
        name: "AI Suggested Activity",
        price: 2,
        rating: 0,
        type: "activity",
      };

      const url = getActivityBookingUrl(activity);

      expect(url).toBe("https://booking.com/preferred-tour");
    });

    it("should ignore IPv4 URLs and fall back to map search", () => {
      const activity = {
        date: "2025-01-01",
        description: "Avoid http://127.0.0.1/secret",
        duration: 120,
        id: "ai_fallback:ipv4",
        location: "Test Location",
        name: "AI Suggested Activity",
        price: 2,
        rating: 0,
        type: "activity",
      };

      const url = getActivityBookingUrl(activity);

      expect(url).toBe(
        "https://www.google.com/maps/search/?api=1&query=AI%20Suggested%20Activity%20Test%20Location"
      );
    });

    it("should ignore IPv6 URLs and fall back to map search", () => {
      const activity = {
        date: "2025-01-01",
        description: "Avoid https://[2001:db8::1]/secret",
        duration: 120,
        id: "ai_fallback:ipv6",
        location: "Test Location",
        name: "AI Suggested Activity",
        price: 2,
        rating: 0,
        type: "activity",
      };

      const url = getActivityBookingUrl(activity);

      expect(url).toBe(
        "https://www.google.com/maps/search/?api=1&query=AI%20Suggested%20Activity%20Test%20Location"
      );
    });

    it("should ignore localhost and .local hosts and fall back to map search", () => {
      const activity = {
        date: "2025-01-01",
        description:
          "Try http://localhost:3000/booking or https://internal.local/booking",
        duration: 120,
        id: "ai_fallback:localhosts",
        location: "Test Location",
        name: "AI Suggested Activity",
        price: 2,
        rating: 0,
        type: "activity",
      };

      const url = getActivityBookingUrl(activity);

      expect(url).toBe(
        "https://www.google.com/maps/search/?api=1&query=AI%20Suggested%20Activity%20Test%20Location"
      );
    });

    it("should select the first valid URL when no booking domains are present", () => {
      const activity = {
        date: "2025-01-01",
        description:
          "See https://example.com/first for details or https://another.test/path",
        duration: 120,
        id: "ai_fallback:first-valid",
        location: "Test Location",
        name: "AI Suggested Activity",
        price: 2,
        rating: 0,
        type: "activity",
      };

      const url = getActivityBookingUrl(activity);

      expect(url).toBe("https://example.com/first");
    });

    it("should return null when AI activity has no booking URL and no location data", () => {
      const activity = {
        date: "2025-01-01",
        description: "No links",
        duration: 120,
        id: "ai_fallback:nodata",
        location: "",
        name: "",
        price: 0,
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

    it("should refuse javascript URLs extracted from description", () => {
      const activity = {
        date: "2025-01-01",
        description: "javascript:alert(1)",
        duration: 120,
        id: "ai_fallback:inject",
        location: "",
        name: "",
        price: 0,
        rating: 0,
        type: "activity",
      };

      const result = openActivityBooking(activity);

      expect(result).toBe(false);
      expect(window.open).not.toHaveBeenCalled();
    });
  });
});
