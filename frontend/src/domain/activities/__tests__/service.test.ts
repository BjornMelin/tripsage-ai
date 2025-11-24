/** @vitest-environment node */

import type { Activity, ActivitySearchParams } from "@schemas/search";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import type { ActivitiesServiceDeps } from "../service";
import { ActivitiesService } from "../service";

vi.mock("@/lib/env/server", () => ({
  getGoogleMapsServerKey: vi.fn(() => "test-key"),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name, _opts, fn) =>
    fn({
      addEvent: vi.fn(),
      recordException: vi.fn(),
      setAttribute: vi.fn(),
    })
  ),
}));

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: vi.fn(() => ({
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  })),
}));

vi.mock("@ai/tools/server/web-search", () => ({
  webSearch: {
    execute: vi.fn(),
  },
}));

describe("ActivitiesService", () => {
  let mockSupabase: {
    from: ReturnType<typeof vi.fn>;
  };
  let deps: ActivitiesServiceDeps;
  let service: ActivitiesService;

  beforeEach(async () => {
    const fromMock = vi.fn(() => ({
      insert: vi.fn(() => Promise.resolve({ data: null, error: null })),
      select: vi.fn(() => ({
        eq: vi.fn(() => ({
          eq: vi.fn(() => ({
            eq: vi.fn(() => ({
              gt: vi.fn(() => ({
                order: vi.fn(() => ({
                  limit: vi.fn(() => ({
                    maybeSingle: vi.fn(() =>
                      Promise.resolve({ data: null, error: null })
                    ),
                  })),
                })),
              })),
            })),
          })),
        })),
      })),
    }));

    mockSupabase = {
      from: fromMock,
    };

    deps = {
      supabase: vi.fn(() => Promise.resolve(mockSupabase as never)),
    };

    service = new ActivitiesService(deps);

    // Reset webSearch mock to ensure no shared state
    const { webSearch } = await import("@ai/tools/server/web-search");
    if (webSearch.execute) {
      vi.mocked(webSearch.execute).mockReset();
    }

    server.use(
      http.post("https://places.googleapis.com/v1/places:searchText", () =>
        HttpResponse.json({
          places: [
            {
              displayName: { text: "Museum of Modern Art" },
              formattedAddress: "11 W 53rd St, New York, NY 10019",
              id: "ChIJN1t_tDeuEmsRUsoyG83frY4",
              location: { latitude: 40.7614, longitude: -73.9776 },
              photos: [{ name: "places/photo1" }],
              priceLevel: "PRICE_LEVEL_MODERATE",
              rating: 4.6,
              types: ["museum", "tourist_attraction"],
              userRatingCount: 4523,
            },
          ],
        })
      )
    );
  });

  afterEach(() => {
    vi.clearAllMocks();
    server.resetHandlers();
  });

  describe("search", () => {
    it("should validate destination is required", async () => {
      await expect(
        service.search({} as unknown as ActivitySearchParams, {})
      ).rejects.toThrow("Destination is required");
    });

    it("should compute query hash consistently", () => {
      const params1: ActivitySearchParams = {
        category: "museums",
        destination: "Paris",
      };
      const params2: ActivitySearchParams = {
        category: "museums",
        destination: "Paris",
      };

      // Access private method via type assertion for testing
      // Using Record to bypass private access restrictions
      const serviceRecord = service as unknown as Record<string, unknown>;
      const computeQueryHash = serviceRecord.computeQueryHash as (
        params: ActivitySearchParams
      ) => string;
      const hash1 = computeQueryHash.call(service, params1);
      const hash2 = computeQueryHash.call(service, params2);

      expect(hash1).toBe(hash2);
    });

    it("should return cached results when available", async () => {
      const mockCacheData = {
        data: {
          expires_at: new Date(Date.now() + 3600000).toISOString(),
          results: [
            {
              date: "2025-01-01",
              description: "Test",
              duration: 120,
              id: "places/1",
              location: "Test Location",
              name: "Cached Activity",
              price: 2,
              rating: 4.5,
              type: "museum",
            },
          ],
          source: "googleplaces",
        },
        error: null,
      };

      const selectChain = {
        eq: vi.fn().mockReturnThis(),
        gt: vi.fn().mockReturnThis(),
        limit: vi.fn().mockReturnThis(),
        maybeSingle: vi.fn(() => Promise.resolve(mockCacheData)),
        order: vi.fn().mockReturnThis(),
      };

      mockSupabase.from.mockReturnValue({
        select: vi.fn(() => selectChain),
      } as never);

      const result = await service.search(
        { destination: "Paris" },
        { userId: "user-1" }
      );

      expect(result.metadata.cached).toBe(true);
      expect(result.activities).toHaveLength(1);
      expect(result.activities[0].name).toBe("Cached Activity");
    });

    it("should perform Places search on cache miss", async () => {
      const selectChain = {
        eq: vi.fn().mockReturnThis(),
        gt: vi.fn().mockReturnThis(),
        limit: vi.fn().mockReturnThis(),
        maybeSingle: vi.fn(() => Promise.resolve({ data: null, error: null })),
        order: vi.fn().mockReturnThis(),
      };

      mockSupabase.from.mockReturnValue({
        insert: vi.fn(() => Promise.resolve({ data: null, error: null })),
        select: vi.fn(() => selectChain),
      } as never);

      const result = await service.search(
        { category: "museums", destination: "New York" },
        { userId: "user-1" }
      );

      expect(result.metadata.cached).toBe(false);
      expect(result.activities.length).toBeGreaterThan(0);
      expect(result.metadata.primarySource).toBe("googleplaces");
    });

    it("should trigger AI fallback when Places returns zero results", async () => {
      server.use(
        http.post("https://places.googleapis.com/v1/places:searchText", () =>
          HttpResponse.json({ places: [] })
        )
      );

      const { webSearch } = await import("@ai/tools/server/web-search");
      if (!webSearch.execute) {
        throw new Error("webSearch.execute is not available");
      }
      vi.mocked(webSearch.execute).mockResolvedValue({
        fromCache: false,
        results: [
          {
            snippet: "A unique local experience",
            title: "Hidden Gem Activity",
            url: "https://example.com/activity",
          },
        ],
        tookMs: 100,
      });

      const selectChain = {
        eq: vi.fn().mockReturnThis(),
        gt: vi.fn().mockReturnThis(),
        limit: vi.fn().mockReturnThis(),
        maybeSingle: vi.fn(() => Promise.resolve({ data: null, error: null })),
        order: vi.fn().mockReturnThis(),
      };

      mockSupabase.from.mockReturnValue({
        insert: vi.fn(() => Promise.resolve({ data: null, error: null })),
        select: vi.fn(() => selectChain),
      } as never);

      const result = await service.search(
        { destination: "Unknown City" },
        { userId: "user-1" }
      );

      expect(webSearch.execute).toHaveBeenCalled();
      expect(result.metadata.primarySource).toBe("ai_fallback");
      expect(result.activities.some((a) => a.id.startsWith("ai_fallback:"))).toBe(true);
    });

    it("should not trigger fallback when Places returns sufficient results", async () => {
      const { webSearch } = await import("@ai/tools/server/web-search");
      if (webSearch.execute) {
        // Reset mock completely to ensure no shared state from parallel tests
        vi.mocked(webSearch.execute).mockReset();
        vi.mocked(webSearch.execute).mockClear();
      }

      // Mock Places API to return 5 results (well above the 3 threshold)
      // Use a non-popular destination to avoid isPopularDestination logic affecting fallback
      server.resetHandlers();
      server.use(
        http.post("https://places.googleapis.com/v1/places:searchText", () =>
          HttpResponse.json({
            places: [
              {
                displayName: { text: "Activity 1" },
                formattedAddress: "Address 1",
                id: "places/1",
                location: { latitude: 1.0, longitude: 1.0 },
                rating: 4.0,
                types: ["tourist_attraction"],
              },
              {
                displayName: { text: "Activity 2" },
                formattedAddress: "Address 2",
                id: "places/2",
                location: { latitude: 2.0, longitude: 2.0 },
                rating: 4.5,
                types: ["tourist_attraction"],
              },
              {
                displayName: { text: "Activity 3" },
                formattedAddress: "Address 3",
                id: "places/3",
                location: { latitude: 3.0, longitude: 3.0 },
                rating: 4.2,
                types: ["tourist_attraction"],
              },
              {
                displayName: { text: "Activity 4" },
                formattedAddress: "Address 4",
                id: "places/4",
                location: { latitude: 4.0, longitude: 4.0 },
                rating: 4.3,
                types: ["tourist_attraction"],
              },
              {
                displayName: { text: "Activity 5" },
                formattedAddress: "Address 5",
                id: "places/5",
                location: { latitude: 5.0, longitude: 5.0 },
                rating: 4.1,
                types: ["tourist_attraction"],
              },
            ],
          })
        )
      );

      const selectChain = {
        eq: vi.fn().mockReturnThis(),
        gt: vi.fn().mockReturnThis(),
        limit: vi.fn().mockReturnThis(),
        maybeSingle: vi.fn(() => Promise.resolve({ data: null, error: null })),
        order: vi.fn().mockReturnThis(),
      };

      mockSupabase.from.mockReturnValue({
        insert: vi.fn(() => Promise.resolve({ data: null, error: null })),
        select: vi.fn(() => selectChain),
      } as never);

      // Use a non-popular destination to ensure fallback logic is clear
      await service.search({ destination: "SmallTown" }, { userId: "user-1" });

      if (webSearch.execute) {
        expect(webSearch.execute).not.toHaveBeenCalled();
      }
    });
  });

  describe("details", () => {
    it("should require placeId", async () => {
      await expect(service.details("", {})).rejects.toThrow("Place ID is required");
    });

    it("should return cached activity details when available", async () => {
      const mockCacheData = {
        data: {
          expires_at: new Date(Date.now() + 3600000).toISOString(),
          results: [
            {
              date: "2025-01-01",
              description: "Test",
              duration: 120,
              id: "places/123",
              location: "Test Location",
              name: "Cached Activity",
              price: 2,
              rating: 4.5,
              type: "museum",
            },
          ],
        },
        error: null,
      };

      mockSupabase.from.mockReturnValue({
        select: vi.fn(() => ({
          eq: vi.fn().mockReturnThis(),
          gt: vi.fn().mockReturnThis(),
          limit: vi.fn().mockReturnThis(),
          maybeSingle: vi.fn(() => Promise.resolve(mockCacheData)),
          order: vi.fn().mockReturnThis(),
        })),
      } as never);

      server.use(
        http.get("https://places.googleapis.com/v1/places/123", () =>
          HttpResponse.json({
            displayName: { text: "Place Details" },
            formattedAddress: "123 Test St",
            id: "places/123",
            location: { latitude: 40.7614, longitude: -73.9776 },
            rating: 4.5,
            types: ["museum"],
          })
        )
      );

      const result = await service.details("places/123", { userId: "user-1" });

      expect(result.id).toBe("places/123");
      expect(result.name).toBe("Cached Activity");
    });

    it("should fetch from Places API when cache miss", async () => {
      mockSupabase.from.mockReturnValue({
        select: vi.fn(() => ({
          eq: vi.fn().mockReturnThis(),
          gt: vi.fn().mockReturnThis(),
          limit: vi.fn().mockReturnThis(),
          maybeSingle: vi.fn(() => Promise.resolve({ data: null, error: null })),
          order: vi.fn().mockReturnThis(),
        })),
      } as never);

      // The URL format is https://places.googleapis.com/v1/{placeId} (no /places/ prefix)
      server.use(
        http.get("https://places.googleapis.com/v1/:placeId", ({ params }) => {
          if (params.placeId === "ChIJN1t_tDeuEmsRUsoyG83frY4") {
            return HttpResponse.json({
              displayName: { text: "Museum of Modern Art" },
              formattedAddress: "11 W 53rd St, New York, NY 10019",
              id: "ChIJN1t_tDeuEmsRUsoyG83frY4",
              location: { latitude: 40.7614, longitude: -73.9776 },
              photos: [{ name: "places/photo1" }],
              priceLevel: "PRICE_LEVEL_MODERATE",
              rating: 4.6,
              types: ["museum", "tourist_attraction"],
              userRatingCount: 4523,
            });
          }
          return HttpResponse.json({}, { status: 404 });
        })
      );

      const result = await service.details("ChIJN1t_tDeuEmsRUsoyG83frY4", {
        userId: "user-1",
      });

      expect(result.id).toBe("ChIJN1t_tDeuEmsRUsoyG83frY4");
      expect(result.name).toBe("Museum of Modern Art");
    });

    it("should throw error when activity not found", async () => {
      mockSupabase.from.mockReturnValue({
        select: vi.fn(() => ({
          eq: vi.fn().mockReturnThis(),
          gt: vi.fn().mockReturnThis(),
          limit: vi.fn().mockReturnThis(),
          maybeSingle: vi.fn(() => Promise.resolve({ data: null, error: null })),
          order: vi.fn().mockReturnThis(),
        })),
      } as never);

      server.use(
        http.get("https://places.googleapis.com/v1/places/invalid", () =>
          HttpResponse.json({}, { status: 404 })
        )
      );

      await expect(service.details("invalid", {})).rejects.toThrow(
        "Activity not found"
      );
    });
  });

  describe("isPopularDestination", () => {
    it("should identify popular destinations", () => {
      // Access private method via type assertion for testing
      // Using Record to bypass private access restrictions
      const serviceRecord = service as unknown as Record<string, unknown>;
      const isPopular = (
        serviceRecord.isPopularDestination as (destination: string) => boolean
      ).bind(service);
      expect(isPopular("Paris")).toBe(true);
      expect(isPopular("Tokyo")).toBe(true);
      expect(isPopular("New York")).toBe(true);
      expect(isPopular("Random Small Town")).toBe(false);
    });
  });

  describe("normalizeWebResultsToActivities", () => {
    it("should map web search results to activities", () => {
      // Access private method via type assertion for testing
      // Using Record to bypass private access restrictions
      const serviceRecord = service as unknown as Record<string, unknown>;
      type NormalizeFn = (
        webResults: Array<{
          url: string;
          title?: string;
          snippet?: string;
        }>,
        destination: string,
        date?: string
      ) => Activity[];
      const normalize = (
        serviceRecord.normalizeWebResultsToActivities as NormalizeFn
      ).bind(service);

      const webResults = [
        {
          snippet: "A great museum experience",
          title: "Local Museum",
          url: "https://example.com/museum",
        },
        {
          snippet: "Guided walking tour",
          title: "Central Park Tour",
          url: "https://example.com/park",
        },
      ];

      const activities = normalize(webResults, "New York", "2025-01-01");

      expect(activities).toHaveLength(2);
      expect(activities[0].id).toMatch(/^ai_fallback:/);
      expect(activities[0].name).toBe("Local Museum");
      expect(activities[0].type).toBe("museum");
      expect(activities[1].type).toBe("tour");
    });

    it("should skip results without title or snippet", () => {
      // Access private method via type assertion for testing
      // Using Record to bypass private access restrictions
      const serviceRecord = service as unknown as Record<string, unknown>;
      type NormalizeFn = (
        webResults: Array<{
          url: string;
          title?: string;
          snippet?: string;
        }>,
        destination: string,
        date?: string
      ) => Activity[];
      const normalize = (
        serviceRecord.normalizeWebResultsToActivities as NormalizeFn
      ).bind(service);

      const webResults = [
        { snippet: "", title: "", url: "https://example.com" },
        {
          snippet: "Valid snippet",
          title: "Valid Title",
          url: "https://example.com/2",
        },
      ];

      const activities = normalize(webResults, "Paris", "2025-01-01");

      expect(activities).toHaveLength(1);
      expect(activities[0].name).toBe("Valid Title");
    });
  });
});
