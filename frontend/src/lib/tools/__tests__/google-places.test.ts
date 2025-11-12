import { beforeEach, describe, expect, it, vi } from "vitest";

import { cacheLatLng, getCachedLatLng } from "@/lib/google/caching";
import { getGoogleMapsServerKey } from "@/lib/google/keys";

import { lookupPoiContext } from "../google-places";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

vi.mock("@/lib/google/caching", () => ({
  cacheLatLng: vi.fn().mockResolvedValue(undefined),
  getCachedLatLng: vi.fn().mockResolvedValue(null),
}));

vi.mock("@/lib/google/keys", () => ({
  getGoogleMapsServerKey: vi.fn().mockReturnValue("test-server-key"),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name, _options, fn) => fn()),
}));

describe("lookupPoiContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getCachedLatLng).mockResolvedValue(null);
    vi.mocked(cacheLatLng).mockResolvedValue(undefined);
    vi.mocked(getGoogleMapsServerKey).mockReturnValue("test-server-key");
  });

  it("returns stub when API key not configured", async () => {
    vi.mocked(getGoogleMapsServerKey).mockImplementation(() => {
      throw new Error("API key required");
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
          // Missing destination, query, and lat/lon
          radiusMeters: 1000,
        },
        mockContext
      )
    ).rejects.toThrow();
  });

  it("handles coordinates input", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      json: async () => ({
        places: [
          {
            displayName: { text: "Test POI" },
            id: "ChIJtest123",
            location: { latitude: 35.6895, longitude: 139.6917 },
            types: ["tourist_attraction"],
          },
        ],
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
          placeId: "ChIJtest123",
        }),
      ]),
      provider: "googleplaces",
    });
  });

  it("geocodes destination and fetches POIs", async () => {
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

    // Mock Places API response
    const placesResponse = {
      places: [
        {
          displayName: { text: "Tokyo Tower" },
          id: "ChIJtokyo123",
          location: { latitude: 35.6895, longitude: 139.6917 },
          types: ["tourist_attraction"],
        },
      ],
    };

    let callCount = 0;
    global.fetch = vi.fn().mockImplementation((url: string | URL) => {
      callCount++;
      const urlStr = typeof url === "string" ? url : url.toString();
      if (urlStr.includes("maps.googleapis.com/maps/api/geocode")) {
        // Geocoding API call
        return Promise.resolve({
          json: async () => geocodeResponse,
          ok: true,
        });
      }
      // Places API call
      return Promise.resolve({
        json: async () => placesResponse,
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
      provider: "googleplaces",
    });

    // Verify geocoding was called
    expect(callCount).toBeGreaterThanOrEqual(2);
    expect(vi.mocked(getCachedLatLng)).toHaveBeenCalledWith(
      "googleplaces:geocode:tokyo"
    );
    // Verify geocoding result was cached with 30-day max TTL
    expect(vi.mocked(cacheLatLng)).toHaveBeenCalledWith(
      "googleplaces:geocode:tokyo",
      { lat: 35.6895, lon: 139.6917 },
      30 * 24 * 60 * 60
    );
  });

  it("uses cached geocoding result when available", async () => {
    // Mock cached geocoding result
    vi.mocked(getCachedLatLng).mockImplementation((key: string) => {
      if (key === "googleplaces:geocode:tokyo") {
        return Promise.resolve({ lat: 35.6895, lon: 139.6917 });
      }
      return Promise.resolve(null);
    });

    // Mock Places API response
    const placesResponse = {
      places: [
        {
          displayName: { text: "Tokyo Tower" },
          id: "ChIJtokyo123",
          location: { latitude: 35.6895, longitude: 139.6917 },
          types: ["tourist_attraction"],
        },
      ],
    };

    global.fetch = vi.fn().mockResolvedValue({
      json: async () => placesResponse,
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
      provider: "googleplaces",
    });

    // Verify geocoding cache was checked
    expect(vi.mocked(getCachedLatLng)).toHaveBeenCalledWith(
      "googleplaces:geocode:tokyo"
    );
    // Verify Google Maps Geocoding API was NOT called (cache hit)
    const fetchCalls = vi.mocked(global.fetch).mock.calls;
    const geocodeCalls = fetchCalls.filter((call) => {
      const url = call[0];
      const urlStr =
        typeof url === "string" ? url : url instanceof URL ? url.toString() : "";
      return urlStr.includes("maps.googleapis.com/maps/api/geocode");
    });
    expect(geocodeCalls).toHaveLength(0);
  });

  it("handles query-only search", async () => {
    const placesResponse = {
      places: [
        {
          displayName: { text: "Restaurant" },
          id: "ChIJquery123",
          location: { latitude: 35.6895, longitude: 139.6917 },
          types: ["restaurant"],
        },
      ],
    };

    global.fetch = vi.fn().mockResolvedValue({
      json: async () => placesResponse,
      ok: true,
    });

    if (!lookupPoiContext.execute) {
      throw new Error("lookupPoiContext.execute is undefined");
    }

    const result = await lookupPoiContext.execute(
      {
        query: "restaurants in Tokyo",
        radiusMeters: 1000,
      },
      mockContext
    );

    expect(result).toMatchObject({
      pois: expect.arrayContaining([
        expect.objectContaining({
          name: "Restaurant",
        }),
      ]),
      provider: "googleplaces",
    });
  });
});
