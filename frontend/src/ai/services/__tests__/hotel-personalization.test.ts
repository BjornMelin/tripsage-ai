/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type {
  HotelForPersonalization,
  HotelPersonalization,
  UserPreferences,
} from "../hotel-personalization";

// Mock dependencies before importing the module
vi.mock("@ai/models/registry", () => ({
  resolveProvider: vi.fn().mockResolvedValue({
    model: {
      doGenerate: vi.fn(),
      modelId: "test-model",
      provider: "test-provider",
    },
  }),
}));

vi.mock("ai", () => ({
  generateText: vi.fn(),
  Output: { object: vi.fn((value) => value) },
}));

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: vi.fn().mockResolvedValue(null),
  setCachedJson: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: vi.fn(),
  withTelemetrySpan: vi.fn(async (_name, _opts, fn) => fn()),
}));

vi.mock("@/lib/cache/hash", () => ({
  hashInputForCache: vi.fn().mockReturnValue("test-hash"),
}));

describe("hotel-personalization", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetModules();
  });

  describe("getDefaultPersonalization", () => {
    it("returns luxury vibe for resorts", async () => {
      const { getDefaultPersonalization } = await import("../hotel-personalization");
      const hotel: HotelForPersonalization = {
        amenities: ["pool", "spa", "beach access"],
        category: "resort",
        location: "Miami Beach",
        name: "Beach Resort",
        pricePerNight: 300,
      };

      const result = getDefaultPersonalization(hotel);

      expect(result.vibe).toBe("luxury");
      expect(result.reason).toContain("Beach Resort");
      expect(result.reason).toContain("luxury");
    });

    it("returns family vibe for kid-friendly hotels", async () => {
      const { getDefaultPersonalization } = await import("../hotel-personalization");
      const hotel: HotelForPersonalization = {
        amenities: ["kids club", "playground", "family pool"],
        location: "Orlando",
        name: "Family Inn",
        pricePerNight: 150,
      };

      const result = getDefaultPersonalization(hotel);

      expect(result.vibe).toBe("family");
    });

    it("returns romantic vibe for boutique hotels", async () => {
      const { getDefaultPersonalization } = await import("../hotel-personalization");
      const hotel: HotelForPersonalization = {
        amenities: ["romantic dinner", "wine bar"],
        category: "boutique",
        location: "Paris",
        name: "Boutique Hotel",
        pricePerNight: 250,
      };

      const result = getDefaultPersonalization(hotel);

      expect(result.vibe).toBe("romantic");
    });

    it("returns adventure vibe for outdoor hotels", async () => {
      const { getDefaultPersonalization } = await import("../hotel-personalization");
      const hotel: HotelForPersonalization = {
        amenities: ["hiking trails", "outdoor activities", "mountain views"],
        location: "Colorado",
        name: "Mountain Lodge",
        pricePerNight: 200,
      };

      const result = getDefaultPersonalization(hotel);

      expect(result.vibe).toBe("adventure");
    });

    it("returns business vibe as default", async () => {
      const { getDefaultPersonalization } = await import("../hotel-personalization");
      const hotel: HotelForPersonalization = {
        amenities: ["wifi", "business center"],
        location: "New York",
        name: "City Hotel",
        pricePerNight: 200,
      };

      const result = getDefaultPersonalization(hotel);

      expect(result.vibe).toBe("business");
    });

    it("adds 'Highly rated' tag for high-rated hotels", async () => {
      const { getDefaultPersonalization } = await import("../hotel-personalization");
      const hotel: HotelForPersonalization = {
        amenities: [],
        location: "London",
        name: "Excellent Hotel",
        pricePerNight: 200,
        rating: 4.8,
      };

      const result = getDefaultPersonalization(hotel);

      expect(result.personalizedTags).toContain("Highly rated");
    });

    it("adds star rating tag for 4+ star hotels", async () => {
      const { getDefaultPersonalization } = await import("../hotel-personalization");
      const hotel: HotelForPersonalization = {
        amenities: [],
        location: "Dubai",
        name: "Luxury Hotel",
        pricePerNight: 500,
        starRating: 5,
      };

      const result = getDefaultPersonalization(hotel);

      expect(result.personalizedTags).toContain("5-star property");
    });

    it("adds 'Great value' tag for budget hotels", async () => {
      const { getDefaultPersonalization } = await import("../hotel-personalization");
      const hotel: HotelForPersonalization = {
        amenities: [],
        location: "Austin",
        name: "Budget Inn",
        pricePerNight: 89,
      };

      const result = getDefaultPersonalization(hotel);

      expect(result.personalizedTags).toContain("Great value");
    });

    it("limits tags to 3", async () => {
      const { getDefaultPersonalization } = await import("../hotel-personalization");
      const hotel: HotelForPersonalization = {
        amenities: [],
        location: "Vegas",
        name: "Great Hotel",
        pricePerNight: 100,
        rating: 4.9,
        starRating: 5,
      };

      const result = getDefaultPersonalization(hotel);

      expect(result.personalizedTags.length).toBeLessThanOrEqual(3);
    });

    it("calculates score from rating", async () => {
      const { getDefaultPersonalization } = await import("../hotel-personalization");
      const hotel: HotelForPersonalization = {
        amenities: [],
        location: "Seattle",
        name: "Good Hotel",
        pricePerNight: 150,
        rating: 4.0,
      };

      const result = getDefaultPersonalization(hotel);

      expect(result.score).toBe(8); // 4.0 * 2 = 8
    });

    it("clamps score between 1 and 10", async () => {
      const { getDefaultPersonalization } = await import("../hotel-personalization");

      const lowRated: HotelForPersonalization = {
        amenities: [],
        location: "Nowhere",
        name: "Low Hotel",
        pricePerNight: 50,
        rating: 0.2,
      };

      const highRated: HotelForPersonalization = {
        amenities: [],
        location: "Paradise",
        name: "High Hotel",
        pricePerNight: 1000,
        rating: 5.0,
      };

      const lowResult = getDefaultPersonalization(lowRated);
      const highResult = getDefaultPersonalization(highRated);

      expect(lowResult.score).toBeGreaterThanOrEqual(1);
      expect(highResult.score).toBeLessThanOrEqual(10);
    });
  });

  describe("personalizeHotels", () => {
    it("returns empty map for empty hotels array", async () => {
      const { personalizeHotels } = await import("../hotel-personalization");

      const result = await personalizeHotels("user-123", [], {});

      expect(result.size).toBe(0);
    });

    it("returns cached results when available", async () => {
      const { getCachedJson } = await import("@/lib/cache/upstash");
      const cachedData: Array<HotelPersonalization & { hotelId: string }> = [
        {
          hotelId: "Test Hotel|test-hash",
          personalizedTags: ["Cached tag"],
          reason: "Cached reason",
          score: 8,
          vibe: "luxury",
        },
      ];
      vi.mocked(getCachedJson).mockResolvedValueOnce(cachedData);

      const { personalizeHotels } = await import("../hotel-personalization");

      const hotels: HotelForPersonalization[] = [
        {
          amenities: [],
          location: "Test City",
          name: "Test Hotel",
          pricePerNight: 200,
        },
      ];

      const result = await personalizeHotels("user-123", hotels, {});

      expect(result.get(0)?.reason).toBe("Cached reason");
      expect(result.get(0)?.vibe).toBe("luxury");
    });

    it("calls AI when cache misses", async () => {
      const { generateText } = await import("ai");
      vi.mocked(generateText).mockResolvedValueOnce({
        output: {
          hotels: [
            {
              index: 0,
              personalizedTags: ["AI tag"],
              reason: "AI reason",
              score: 9,
              vibe: "business" as const,
            },
          ],
        },
      } as Awaited<ReturnType<typeof generateText>>);

      const { personalizeHotels } = await import("../hotel-personalization");

      const hotels: HotelForPersonalization[] = [
        {
          amenities: ["wifi", "pool"],
          location: "Test City",
          name: "Test Hotel",
          pricePerNight: 200,
        },
      ];

      const result = await personalizeHotels("user-123", hotels, {
        travelStyle: "luxury",
      });

      expect(generateText).toHaveBeenCalled();
      expect(result.get(0)?.reason).toBe("AI reason");
    });

    it("caches AI results after generation", async () => {
      const { generateText } = await import("ai");
      const { setCachedJson } = await import("@/lib/cache/upstash");
      const { hashInputForCache } = await import("@/lib/cache/hash");

      vi.mocked(generateText).mockResolvedValueOnce({
        output: {
          hotels: [
            {
              index: 0,
              personalizedTags: ["Tag"],
              reason: "Reason",
              score: 7,
              vibe: "family" as const,
            },
          ],
        },
      } as Awaited<ReturnType<typeof generateText>>);

      const { personalizeHotels } = await import("../hotel-personalization");

      const hotels: HotelForPersonalization[] = [
        {
          amenities: [],
          location: "Cache City",
          name: "Cache Test Hotel",
          pricePerNight: 150,
        },
      ];

      const { PERSONALIZATION_CACHE_TTL } = await import("../hotel-personalization");

      await personalizeHotels("user-123", hotels, {});

      expect(setCachedJson).toHaveBeenCalledWith(
        expect.stringContaining("hotel:personalize:"),
        expect.arrayContaining([
          expect.objectContaining({
            hotelId: `Cache Test Hotel|${hashInputForCache({
              location: "Cache City",
              pricePerNight: 150,
            })}`,
            reason: "Reason",
          }),
        ]),
        PERSONALIZATION_CACHE_TTL
      );
    });

    it("uses expected cache TTL", async () => {
      const { PERSONALIZATION_CACHE_TTL } = await import("../hotel-personalization");
      expect(PERSONALIZATION_CACHE_TTL).toBe(1800);
    });

    it("preserves hotel indices from AI response", async () => {
      const { generateText } = await import("ai");

      // AI returns hotels out of order
      vi.mocked(generateText).mockResolvedValueOnce({
        output: {
          hotels: [
            {
              index: 2,
              personalizedTags: [],
              reason: "Hotel 2",
              score: 5,
              vibe: "business" as const,
            },
            {
              index: 0,
              personalizedTags: [],
              reason: "Hotel 0",
              score: 8,
              vibe: "luxury" as const,
            },
            {
              index: 1,
              personalizedTags: [],
              reason: "Hotel 1",
              score: 6,
              vibe: "family" as const,
            },
          ],
        },
      } as Awaited<ReturnType<typeof generateText>>);

      const { personalizeHotels } = await import("../hotel-personalization");

      const hotels: HotelForPersonalization[] = [
        { amenities: [], location: "City A", name: "Hotel A", pricePerNight: 100 },
        { amenities: [], location: "City B", name: "Hotel B", pricePerNight: 200 },
        { amenities: [], location: "City C", name: "Hotel C", pricePerNight: 300 },
      ];

      const result = await personalizeHotels("user-123", hotels, {});

      expect(result.get(0)?.reason).toBe("Hotel 0");
      expect(result.get(1)?.reason).toBe("Hotel 1");
      expect(result.get(2)?.reason).toBe("Hotel 2");
    });

    it("includes user preferences in prompt", async () => {
      const { generateText } = await import("ai");
      vi.mocked(generateText).mockResolvedValueOnce({
        output: { hotels: [] },
      } as Awaited<ReturnType<typeof generateText>>);

      const { personalizeHotels } = await import("../hotel-personalization");

      const hotels: HotelForPersonalization[] = [
        { amenities: [], location: "City", name: "Test", pricePerNight: 100 },
      ];

      const preferences: UserPreferences = {
        forBusiness: false,
        preferredAmenities: ["spa", "pool"],
        travelStyle: "luxury",
        tripPurpose: "honeymoon",
        withFamily: false,
      };

      await personalizeHotels("user-123", hotels, preferences);

      const call = vi.mocked(generateText).mock.calls[0][0];
      expect(call.prompt).toContain("luxury");
      expect(call.prompt).toContain("honeymoon");
      expect(call.prompt).toContain("spa");
      expect(call.prompt).toContain("pool");
    });

    it("sanitizes hotel data in prompt", async () => {
      const { generateText } = await import("ai");
      vi.mocked(generateText).mockResolvedValueOnce({
        output: { hotels: [] },
      } as Awaited<ReturnType<typeof generateText>>);

      const { personalizeHotels } = await import("../hotel-personalization");

      const hotels: HotelForPersonalization[] = [
        {
          amenities: ["wifi\ninjection", "pool"],
          location: "City\twith\ttabs",
          name: 'Malicious "Hotel\nName',
          pricePerNight: 100,
        },
      ];

      await personalizeHotels("user-123", hotels, {});

      const call = vi.mocked(generateText).mock.calls[0][0];
      // User input in hotel descriptions should be sanitized
      // The prompt structure has newlines, but user-provided data should not
      // Check that the malicious patterns were cleaned
      expect(call.prompt).toContain("Malicious Hotel Name"); // Quotes and newline stripped
      expect(call.prompt).toContain("City with tabs"); // Tabs replaced with spaces
      expect(call.prompt).toContain("wifi injection"); // Newline replaced with space
      // Should not contain the raw malicious characters in user data
      expect(call.prompt).not.toContain('Malicious "Hotel');
      expect(call.prompt).not.toContain("City\twith");
      expect(call.prompt).not.toContain("wifi\ninjection");
    });
  });
});
