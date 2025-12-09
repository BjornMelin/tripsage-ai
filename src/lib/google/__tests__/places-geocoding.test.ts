/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { cacheLatLng, getCachedLatLng } from "../caching";
import { postPlacesSearch } from "../client";
import { resolveLocationToLatLng } from "../places-geocoding";
import { buildGeocodeCacheKey } from "../places-utils";

vi.mock("../caching");
vi.mock("../client");
vi.mock("../places-utils");
vi.mock("@/lib/env/server", () => ({
  getGoogleMapsServerKey: vi.fn(() => "test-api-key"),
}));
vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name, _opts, fn) => fn()),
}));

describe("places-geocoding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("resolveLocationToLatLng", () => {
    it("should return cached coordinates when available", async () => {
      const cachedCoords = { lat: 40.7128, lon: -74.006 };
      vi.mocked(getCachedLatLng).mockResolvedValue(cachedCoords);
      vi.mocked(buildGeocodeCacheKey).mockReturnValue("googleplaces:geocode:hash123");

      const result = await resolveLocationToLatLng("New York, NY");

      expect(result).toEqual(cachedCoords);
      expect(getCachedLatLng).toHaveBeenCalledWith("googleplaces:geocode:hash123");
      expect(postPlacesSearch).not.toHaveBeenCalled();
    });

    it("should call API and cache result when cache misses", async () => {
      vi.mocked(getCachedLatLng).mockResolvedValue(null);
      vi.mocked(buildGeocodeCacheKey).mockReturnValue("googleplaces:geocode:hash123");
      const mockResponse = {
        json: vi.fn().mockResolvedValue({
          places: [
            {
              id: "place123",
              location: { latitude: 40.7128, longitude: -74.006 },
            },
          ],
        }),
        ok: true,
      };
      vi.mocked(postPlacesSearch).mockResolvedValue(
        mockResponse as unknown as Response
      );

      const result = await resolveLocationToLatLng("New York, NY");

      expect(result).toEqual({ lat: 40.7128, lon: -74.006 });
      expect(postPlacesSearch).toHaveBeenCalledWith({
        apiKey: "test-api-key",
        body: { maxResultCount: 1, textQuery: "New York, NY" },
        fieldMask: "places.id,places.location",
      });
      expect(cacheLatLng).toHaveBeenCalledWith(
        "googleplaces:geocode:hash123",
        { lat: 40.7128, lon: -74.006 },
        30 * 24 * 60 * 60
      );
    });

    it("should return null when API key is unavailable", async () => {
      vi.mocked(getCachedLatLng).mockResolvedValue(null);
      vi.mocked(buildGeocodeCacheKey).mockReturnValue("googleplaces:geocode:hash123");
      const { getGoogleMapsServerKey } = await import("@/lib/env/server");
      vi.mocked(getGoogleMapsServerKey).mockImplementation(() => {
        throw new Error("API key missing");
      });

      const result = await resolveLocationToLatLng("New York, NY");

      expect(result).toBeNull();
      expect(postPlacesSearch).not.toHaveBeenCalled();
    });

    it("should return null when API response is not ok", async () => {
      vi.mocked(getCachedLatLng).mockResolvedValue(null);
      vi.mocked(buildGeocodeCacheKey).mockReturnValue("googleplaces:geocode:hash123");
      const mockResponse = {
        ok: false,
        status: 400,
      };
      vi.mocked(postPlacesSearch).mockResolvedValue(
        mockResponse as unknown as Response
      );

      const result = await resolveLocationToLatLng("Invalid Location");

      expect(result).toBeNull();
      expect(cacheLatLng).not.toHaveBeenCalled();
    });

    it("should return null when no places found in response", async () => {
      vi.mocked(getCachedLatLng).mockResolvedValue(null);
      vi.mocked(buildGeocodeCacheKey).mockReturnValue("googleplaces:geocode:hash123");
      const mockResponse = {
        json: vi.fn().mockResolvedValue({ places: [] }),
        ok: true,
      };
      vi.mocked(postPlacesSearch).mockResolvedValue(
        mockResponse as unknown as Response
      );

      const result = await resolveLocationToLatLng("Unknown Place");

      expect(result).toBeNull();
      expect(cacheLatLng).not.toHaveBeenCalled();
    });
  });
});
