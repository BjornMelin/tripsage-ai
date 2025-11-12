import { beforeEach, describe, expect, it, vi } from "vitest";

import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";

import { lookupPoiContext } from "../opentripmap";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: vi.fn().mockResolvedValue(null),
  setCachedJson: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name, _options, fn) => fn()),
}));

describe("lookupPoiContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Explicitly unset the env vars to ensure stub behavior
    process.env.OPENTRIPMAP_API_KEY = undefined;
    process.env.GOOGLE_MAPS_API_KEY = undefined;
    vi.mocked(getCachedJson).mockResolvedValue(null);
    vi.mocked(setCachedJson).mockResolvedValue(undefined);
  });

  it("returns stub when API key not configured", async () => {
    if (!lookupPoiContext.execute) {
      throw new Error("lookupPoiContext.execute is undefined");
    }
    const result = await lookupPoiContext.execute(
      {
        destination: "Tokyo",
        radiusMeters: 1000,
      },
      mockContext
    );
    expect(result).toMatchObject({
      pois: [],
      provider: "stub",
    });
  });

  it("validates input schema", async () => {
    if (!lookupPoiContext.execute) {
      throw new Error("lookupPoiContext.execute is undefined");
    }
    await expect(
      lookupPoiContext.execute(
        {
          // Missing both destination and lat/lon
          radiusMeters: 1000,
        },
        mockContext
      )
    ).rejects.toThrow();
  });

  it("handles coordinates input", async () => {
    process.env.OPENTRIPMAP_API_KEY = "test-key";
    global.fetch = vi.fn().mockResolvedValue({
      json: async () => ({
        features: [
          {
            geometry: {
              coordinates: [139.6917, 35.6895],
              type: "Point",
            },
            properties: {
              kind: "tourism",
              name: "Test POI",
              xid: "test-xid",
            },
            type: "Feature",
          },
        ],
        type: "FeatureCollection",
      }),
      ok: true,
    });

    if (!lookupPoiContext.execute) {
      throw new Error("lookupPoiContext.execute is undefined");
    }
    const result = await lookupPoiContext.execute(
      {
        lat: 35.6895,
        lon: 139.6917,
        radiusMeters: 1000,
      },
      mockContext
    );

    expect(result).toMatchObject({
      pois: expect.arrayContaining([
        expect.objectContaining({
          lat: 35.6895,
          lon: 139.6917,
          name: "Test POI",
        }),
      ]),
      provider: "opentripmap",
    });

    // Ensure radius is passed in meters (no /1000 conversion)
    const calledUrl = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toMatch(/radius=1000(&|$)/);
  });

  it("geocodes destination and fetches POIs", async () => {
    process.env.OPENTRIPMAP_API_KEY = "test-opentripmap-key";
    process.env.GOOGLE_MAPS_API_KEY = "test-gmaps-key";

    // Mock geocoding response
    const geocodeResponse = {
      results: [
        {
          geometry: {
            location: { lat: 35.6895, lng: 139.6917 },
          },
        },
      ],
      status: "OK",
    };

    // Mock OpenTripMap POI response
    const poiResponse = {
      features: [
        {
          geometry: {
            coordinates: [139.6917, 35.6895],
            type: "Point",
          },
          properties: {
            kind: "tourism",
            name: "Tokyo Tower",
            xid: "test-xid",
          },
          type: "Feature",
        },
      ],
      type: "FeatureCollection",
    };

    let callCount = 0;
    global.fetch = vi.fn().mockImplementation((url: string | URL) => {
      callCount++;
      const urlStr = typeof url === "string" ? url : url.toString();
      if (urlStr.includes("maps.googleapis.com")) {
        // Geocoding API call
        return Promise.resolve({
          json: async () => geocodeResponse,
          ok: true,
        });
      }
      // OpenTripMap API call
      return Promise.resolve({
        json: async () => poiResponse,
        ok: true,
      });
    });

    if (!lookupPoiContext.execute) {
      throw new Error("lookupPoiContext.execute is undefined");
    }

    const result = await lookupPoiContext.execute(
      {
        destination: "Tokyo",
        radiusMeters: 1000,
      },
      mockContext
    );

    expect(result).toMatchObject({
      pois: expect.arrayContaining([
        expect.objectContaining({
          lat: 35.6895,
          lon: 139.6917,
          name: "Tokyo Tower",
        }),
      ]),
      provider: "opentripmap",
    });

    // Verify geocoding was called
    expect(callCount).toBeGreaterThanOrEqual(2);
    expect(vi.mocked(getCachedJson)).toHaveBeenCalledWith(
      "opentripmap:geocode:googlemaps:tokyo"
    );
    // Verify geocoding result was cached
    expect(vi.mocked(setCachedJson)).toHaveBeenCalledWith(
      "opentripmap:geocode:googlemaps:tokyo",
      { lat: 35.6895, lon: 139.6917 },
      86400
    );
  });

  it("uses cached geocoding result when available", async () => {
    process.env.OPENTRIPMAP_API_KEY = "test-opentripmap-key";
    process.env.GOOGLE_MAPS_API_KEY = "test-gmaps-key";

    // Mock cached geocoding result
    vi.mocked(getCachedJson).mockImplementation((key: string) => {
      if (key === "opentripmap:geocode:googlemaps:tokyo") {
        return Promise.resolve({ lat: 35.6895, lon: 139.6917 });
      }
      return Promise.resolve(null);
    });

    // Mock OpenTripMap POI response
    const poiResponse = {
      features: [
        {
          geometry: {
            coordinates: [139.6917, 35.6895],
            type: "Point",
          },
          properties: {
            kind: "tourism",
            name: "Tokyo Tower",
            xid: "test-xid",
          },
          type: "Feature",
        },
      ],
      type: "FeatureCollection",
    };

    global.fetch = vi.fn().mockResolvedValue({
      json: async () => poiResponse,
      ok: true,
    });

    if (!lookupPoiContext.execute) {
      throw new Error("lookupPoiContext.execute is undefined");
    }

    const result = await lookupPoiContext.execute(
      {
        destination: "Tokyo",
        radiusMeters: 1000,
      },
      mockContext
    );

    expect(result).toMatchObject({
      pois: expect.arrayContaining([
        expect.objectContaining({
          name: "Tokyo Tower",
        }),
      ]),
      provider: "opentripmap",
    });

    // Verify geocoding cache was checked
    expect(vi.mocked(getCachedJson)).toHaveBeenCalledWith(
      "opentripmap:geocode:googlemaps:tokyo"
    );
    // Verify Google Maps API was NOT called (cache hit)
    const fetchCalls = vi.mocked(global.fetch).mock.calls;
    const geocodeCalls = fetchCalls.filter((call) => {
      const url = call[0];
      const urlStr =
        typeof url === "string" ? url : url instanceof URL ? url.toString() : "";
      return urlStr.includes("maps.googleapis.com");
    });
    expect(geocodeCalls).toHaveLength(0);
  });

  it("returns error when geocoding fails", async () => {
    process.env.OPENTRIPMAP_API_KEY = "test-opentripmap-key";
    process.env.GOOGLE_MAPS_API_KEY = undefined; // No Google Maps key

    if (!lookupPoiContext.execute) {
      throw new Error("lookupPoiContext.execute is undefined");
    }

    const result = await lookupPoiContext.execute(
      {
        destination: "InvalidDestination",
        radiusMeters: 1000,
      },
      mockContext
    );

    expect(result).toMatchObject({
      error: "Geocoding not available",
      inputs: {
        destination: "InvalidDestination",
        radiusMeters: 1000,
      },
      pois: [],
      provider: "opentripmap",
    });
  });

  it("handles geocoding API error gracefully", async () => {
    process.env.OPENTRIPMAP_API_KEY = "test-opentripmap-key";
    process.env.GOOGLE_MAPS_API_KEY = "test-gmaps-key";

    // Mock geocoding API error
    global.fetch = vi.fn().mockImplementation((url: string | URL) => {
      const urlStr = typeof url === "string" ? url : url.toString();
      if (urlStr.includes("maps.googleapis.com")) {
        return Promise.resolve({
          json: async () => ({ status: "ZERO_RESULTS" }),
          ok: true,
        });
      }
      return Promise.resolve({
        json: async () => ({}),
        ok: false,
      });
    });

    if (!lookupPoiContext.execute) {
      throw new Error("lookupPoiContext.execute is undefined");
    }

    const result = await lookupPoiContext.execute(
      {
        destination: "NonexistentPlace12345",
        radiusMeters: 1000,
      },
      mockContext
    );

    expect(result).toMatchObject({
      error: "Geocoding not available",
      pois: [],
      provider: "opentripmap",
    });
  });

  it("normalizes destination for cache key", async () => {
    process.env.OPENTRIPMAP_API_KEY = "test-opentripmap-key";
    process.env.GOOGLE_MAPS_API_KEY = "test-gmaps-key";

    // Mock cached geocoding result
    vi.mocked(getCachedJson).mockImplementation((key: string) => {
      if (key === "opentripmap:geocode:googlemaps:tokyo") {
        return Promise.resolve({ lat: 35.6895, lon: 139.6917 });
      }
      return Promise.resolve(null);
    });

    // Mock OpenTripMap POI response
    const poiResponse = {
      features: [
        {
          geometry: {
            coordinates: [139.6917, 35.6895],
            type: "Point",
          },
          properties: {
            kind: "tourism",
            name: "Tokyo Tower",
            xid: "test-xid",
          },
          type: "Feature",
        },
      ],
      type: "FeatureCollection",
    };

    global.fetch = vi.fn().mockResolvedValue({
      json: async () => poiResponse,
      ok: true,
    });

    if (!lookupPoiContext.execute) {
      throw new Error("lookupPoiContext.execute is undefined");
    }

    // Test with different casing and whitespace
    await lookupPoiContext.execute(
      {
        destination: "  TOKYO  ",
        radiusMeters: 1000,
      },
      mockContext
    );

    // Verify cache key was normalized (lowercase, trimmed)
    expect(vi.mocked(getCachedJson)).toHaveBeenCalledWith(
      "opentripmap:geocode:googlemaps:tokyo"
    );
  });
});
