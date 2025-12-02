/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { getPlaceDetails, postPlacesSearch } from "../client";
import {
  buildActivitySearchQuery,
  getActivityDetailsFromPlaces,
  mapPlacesPlaceToActivity,
  searchActivitiesWithPlaces,
} from "../places-activities";

vi.mock("@/lib/env/server", () => ({
  getGoogleMapsServerKey: vi.fn(() => "test-api-key"),
}));

vi.mock("../client", () => ({
  getPlaceDetails: vi.fn(),
  postPlacesSearch: vi.fn(),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name, _opts, fn) =>
    fn({
      addEvent: vi.fn(),
      setAttribute: vi.fn(),
    })
  ),
}));

describe("places-activities", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe("buildActivitySearchQuery", () => {
    it("should build query with category and destination", () => {
      const query = buildActivitySearchQuery("Paris", "museums");
      expect(query).toBe("museums activities in paris");
    });

    it("should build query without category", () => {
      const query = buildActivitySearchQuery("Tokyo");
      expect(query).toBe("activities in tokyo");
    });

    it("should normalize destination", () => {
      const query = buildActivitySearchQuery("  New York  ", "tours");
      expect(query).toBe("tours activities in new york");
    });
  });

  describe("mapPlacesPlaceToActivity", () => {
    it("should map Places place to Activity schema", () => {
      const place = {
        displayName: { text: "Museum of Modern Art" },
        formattedAddress: "11 W 53rd St, New York, NY 10019",
        id: "ChIJN1t_tDeuEmsRUsoyG83frY4",
        location: { latitude: 40.7614, longitude: -73.9776 },
        photos: [{ name: "places/photo1" }],
        priceLevel: "PRICE_LEVEL_MODERATE" as const,
        rating: 4.6,
        types: ["museum", "tourist_attraction"],
        userRatingCount: 4523,
      };

      const activity = mapPlacesPlaceToActivity(place, "2025-01-01");

      expect(activity.id).toBe("ChIJN1t_tDeuEmsRUsoyG83frY4");
      expect(activity.name).toBe("Museum of Modern Art");
      expect(activity.location).toBe("11 W 53rd St, New York, NY 10019");
      expect(activity.date).toBe("2025-01-01");
      expect(activity.rating).toBe(4.6);
      expect(activity.price).toBe(2); // PRICE_LEVEL_MODERATE maps to 2
      expect(activity.type).toBe("museum");
      expect(activity.coordinates).toEqual({ lat: 40.7614, lng: -73.9776 });
      // URL parameter order may vary, so check that all required params are present
      expect(activity.images?.[0]).toMatch(/^\/api\/places\/photo\?/);
      expect(activity.images?.[0]).toContain("name=places%2Fphoto1");
      expect(activity.images?.[0]).toContain("maxHeightPx=800");
      expect(activity.images?.[0]).toContain("maxWidthPx=1200");
    });

    it("should handle missing optional fields", () => {
      const place = {
        displayName: { text: "Test Activity" },
        formattedAddress: "Test Address",
        id: "places/1",
      };

      const activity = mapPlacesPlaceToActivity(place);

      expect(activity.id).toBe("places/1");
      expect(activity.name).toBe("Test Activity");
      expect(activity.rating).toBe(0);
      expect(activity.price).toBe(2); // Default moderate
      expect(activity.type).toBe("activity");
    });

    it("should map price levels correctly", () => {
      const testCases = [
        { expected: 0, priceLevel: "PRICE_LEVEL_FREE" },
        { expected: 1, priceLevel: "PRICE_LEVEL_INEXPENSIVE" },
        { expected: 2, priceLevel: "PRICE_LEVEL_MODERATE" },
        { expected: 3, priceLevel: "PRICE_LEVEL_EXPENSIVE" },
        { expected: 4, priceLevel: "PRICE_LEVEL_VERY_EXPENSIVE" },
        { expected: 2, priceLevel: undefined },
      ];

      for (const testCase of testCases) {
        const place = {
          displayName: { text: "Test" },
          formattedAddress: "Test",
          id: "places/1",
          priceLevel: testCase.priceLevel as
            | "PRICE_LEVEL_FREE"
            | "PRICE_LEVEL_INEXPENSIVE"
            | "PRICE_LEVEL_MODERATE"
            | "PRICE_LEVEL_EXPENSIVE"
            | "PRICE_LEVEL_VERY_EXPENSIVE"
            | undefined,
        };

        const activity = mapPlacesPlaceToActivity(place);
        expect(activity.price).toBe(testCase.expected);
      }
    });

    it("should extract activity type from types array", () => {
      const place = {
        displayName: { text: "Park" },
        formattedAddress: "Test",
        id: "places/1",
        types: ["park", "tourist_attraction"],
      };

      const activity = mapPlacesPlaceToActivity(place);
      expect(activity.type).toBe("park");
    });
  });

  describe("searchActivitiesWithPlaces", () => {
    it("should return empty array when API key is missing", async () => {
      const { getGoogleMapsServerKey } = await import("@/lib/env/server");
      vi.mocked(getGoogleMapsServerKey).mockImplementation(() => {
        throw new Error("API key missing");
      });

      const result = await searchActivitiesWithPlaces("activities in Paris");
      expect(result).toEqual([]);
    });

    it("should search and return activities", async () => {
      vi.mocked(postPlacesSearch).mockResolvedValue(
        new Response(
          JSON.stringify({
            places: [
              {
                displayName: { text: "Museum of Modern Art" },
                formattedAddress: "11 W 53rd St, New York, NY 10019",
                id: "ChIJN1t_tDeuEmsRUsoyG83frY4",
                location: { latitude: 40.7614, longitude: -73.9776 },
                photos: [{ name: "places/photo1" }],
                priceLevel: "PRICE_LEVEL_MODERATE",
                rating: 4.6,
                types: ["museum"],
                userRatingCount: 4523,
              },
            ],
          }),
          { status: 200 }
        )
      );

      const result = await searchActivitiesWithPlaces("activities in New York");

      expect(result).toHaveLength(1);
      expect(result[0].name).toBe("Museum of Modern Art");
      expect(result[0].id).toBe("ChIJN1t_tDeuEmsRUsoyG83frY4");
    });

    it("should return empty array on API error", async () => {
      vi.mocked(postPlacesSearch).mockResolvedValue(
        new Response(JSON.stringify({}), { status: 500 })
      );

      const result = await searchActivitiesWithPlaces("activities in Paris");
      expect(result).toEqual([]);
    });

    it("should respect maxResults parameter", async () => {
      const maxResults = 10;
      const places = Array.from({ length: 30 }, (_, i) => ({
        displayName: { text: `Activity ${i}` },
        formattedAddress: `Address ${i}`,
        id: `places/${i}`,
        location: { latitude: 40.7614, longitude: -73.9776 },
        rating: 4.0,
        types: ["tourist_attraction"],
      }));

      vi.mocked(postPlacesSearch).mockResolvedValue(
        new Response(JSON.stringify({ places: places.slice(0, maxResults) }), {
          status: 200,
        })
      );

      const result = await searchActivitiesWithPlaces("activities", maxResults);
      expect(result.length).toBeLessThanOrEqual(maxResults);
    });
  });

  describe("getActivityDetailsFromPlaces", () => {
    it("should return null when API key is missing", async () => {
      const { getGoogleMapsServerKey } = await import("@/lib/env/server");
      vi.mocked(getGoogleMapsServerKey).mockImplementation(() => {
        throw new Error("API key missing");
      });

      const result = await getActivityDetailsFromPlaces("places/123");
      expect(result).toBeNull();
    });

    it("should fetch and return activity details", async () => {
      vi.mocked(getPlaceDetails).mockResolvedValue(
        new Response(
          JSON.stringify({
            displayName: { text: "Museum of Modern Art" },
            editorialSummary: { text: "A world-renowned art museum" },
            formattedAddress: "11 W 53rd St, New York, NY 10019",
            id: "ChIJN1t_tDeuEmsRUsoyG83frY4",
            location: { latitude: 40.7614, longitude: -73.9776 },
            photos: [{ name: "places/photo1" }],
            priceLevel: "PRICE_LEVEL_MODERATE",
            rating: 4.6,
            types: ["museum"],
            userRatingCount: 4523,
          }),
          { status: 200 }
        )
      );

      const result = await getActivityDetailsFromPlaces("ChIJN1t_tDeuEmsRUsoyG83frY4");

      expect(result).not.toBeNull();
      expect(result?.id).toBe("ChIJN1t_tDeuEmsRUsoyG83frY4");
      expect(result?.name).toBe("Museum of Modern Art");
      expect(result?.description).toContain("world-renowned");
    });

    it("should return null on API error", async () => {
      vi.mocked(getPlaceDetails).mockResolvedValue(
        new Response(JSON.stringify({}), { status: 404 })
      );

      const result = await getActivityDetailsFromPlaces("invalid");
      expect(result).toBeNull();
    });
  });
});
