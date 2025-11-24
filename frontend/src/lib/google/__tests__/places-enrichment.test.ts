/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { cacheLatLng, cachePlaceId, getCachedPlaceId } from "../caching";
import { getPlaceDetails, postPlacesSearch } from "../client";
import { enrichHotelListingWithPlaces } from "../places-enrichment";
import { buildGeocodeCacheKey, buildQueryToPlaceIdKey } from "../places-utils";

vi.mock("../caching");
vi.mock("../client");
vi.mock("../places-utils");
vi.mock("@/lib/env/server", () => ({
  getGoogleMapsServerKey: vi.fn(() => "test-api-key"),
}));
vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name, _opts, fn) => fn()),
}));

describe("places-enrichment", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("enrichHotelListingWithPlaces", () => {
    it("should return original listing when hotel name is missing", async () => {
      const listing = { hotel: { address: { cityName: "NYC" } } };

      const result = await enrichHotelListingWithPlaces(listing);

      expect(result).toEqual(listing);
      expect(postPlacesSearch).not.toHaveBeenCalled();
    });

    it("should use cached place_id when available", async () => {
      const listing = {
        hotel: {
          address: { cityName: "NYC", lines: ["123 Main St"] },
          name: "Test Hotel",
        },
      };
      vi.mocked(getCachedPlaceId).mockResolvedValue("cached-place-id");
      vi.mocked(buildQueryToPlaceIdKey).mockReturnValue("places:q2id:hash123");
      const mockDetailsResponse = {
        json: vi.fn().mockResolvedValue({
          displayName: "Test Hotel",
          id: "cached-place-id",
          rating: 4.5,
        }),
        ok: true,
      };
      vi.mocked(getPlaceDetails).mockResolvedValue(
        mockDetailsResponse as unknown as Response
      );

      const result = await enrichHotelListingWithPlaces(listing);

      expect(result.place).toEqual({ id: "cached-place-id" });
      expect(result.placeDetails).toBeDefined();
      expect(postPlacesSearch).not.toHaveBeenCalled();
      expect(getPlaceDetails).toHaveBeenCalledWith({
        apiKey: "test-api-key",
        fieldMask:
          "id,displayName,formattedAddress,location,rating,userRatingCount,internationalPhoneNumber,photos.name,googleMapsUri",
        placeId: "cached-place-id",
      });
    });

    it("should search for place_id and cache it when not cached", async () => {
      const listing = {
        hotel: {
          address: { cityName: "NYC", lines: ["123 Main St"] },
          name: "Test Hotel",
        },
      };
      vi.mocked(getCachedPlaceId).mockResolvedValue(null);
      vi.mocked(buildQueryToPlaceIdKey).mockReturnValue("places:q2id:hash123");
      vi.mocked(buildGeocodeCacheKey).mockReturnValue("googleplaces:geocode:hash123");
      const mockSearchResponse = {
        json: vi.fn().mockResolvedValue({
          places: [
            {
              id: "new-place-id",
              location: { latitude: 40.7128, longitude: -74.006 },
            },
          ],
        }),
        ok: true,
      };
      vi.mocked(postPlacesSearch).mockResolvedValue(
        mockSearchResponse as unknown as Response
      );
      const mockDetailsResponse = {
        json: vi.fn().mockResolvedValue({
          displayName: "Test Hotel",
          id: "new-place-id",
        }),
        ok: true,
      };
      vi.mocked(getPlaceDetails).mockResolvedValue(
        mockDetailsResponse as unknown as Response
      );

      const result = await enrichHotelListingWithPlaces(listing);

      expect(result.place).toEqual({ id: "new-place-id" });
      expect(result.placeDetails).toBeDefined();
      expect(postPlacesSearch).toHaveBeenCalled();
      expect(cachePlaceId).toHaveBeenCalledWith("places:q2id:hash123", "new-place-id");
      expect(cacheLatLng).toHaveBeenCalledWith(
        "googleplaces:geocode:hash123",
        { lat: 40.7128, lon: -74.006 },
        30 * 24 * 60 * 60
      );
      expect(getPlaceDetails).toHaveBeenCalled();
    });

    it("should return original listing when search fails", async () => {
      const listing = {
        hotel: {
          address: { cityName: "NYC" },
          name: "Test Hotel",
        },
      };
      vi.mocked(getCachedPlaceId).mockResolvedValue(null);
      vi.mocked(buildQueryToPlaceIdKey).mockReturnValue("places:q2id:hash123");
      const mockSearchResponse = {
        ok: false,
      };
      vi.mocked(postPlacesSearch).mockResolvedValue(
        mockSearchResponse as unknown as Response
      );

      const result = await enrichHotelListingWithPlaces(listing);

      expect(result).toEqual(listing);
      expect(getPlaceDetails).not.toHaveBeenCalled();
    });

    it("should return listing with minimal place info when details fetch fails", async () => {
      const listing = {
        hotel: {
          address: { cityName: "NYC" },
          name: "Test Hotel",
        },
      };
      vi.mocked(getCachedPlaceId).mockResolvedValue("place-id");
      vi.mocked(buildQueryToPlaceIdKey).mockReturnValue("places:q2id:hash123");
      const mockDetailsResponse = {
        ok: false,
      };
      vi.mocked(getPlaceDetails).mockResolvedValue(
        mockDetailsResponse as unknown as Response
      );

      const result = await enrichHotelListingWithPlaces(listing);

      expect(result.place).toEqual({ id: "place-id" });
      expect(result.placeDetails).toBeUndefined();
    });

    it("should never cache full place or placeDetails payloads", async () => {
      const listing = {
        hotel: {
          address: { cityName: "NYC" },
          name: "Test Hotel",
        },
      };
      vi.mocked(getCachedPlaceId).mockResolvedValue(null);
      vi.mocked(buildQueryToPlaceIdKey).mockReturnValue("places:q2id:hash123");
      vi.mocked(buildGeocodeCacheKey).mockReturnValue("googleplaces:geocode:hash123");
      const mockSearchResponse = {
        json: vi.fn().mockResolvedValue({
          places: [
            {
              displayName: "Test Hotel",
              id: "place-id",
              location: { latitude: 40.7128, longitude: -74.006 },
              rating: 4.5,
            },
          ],
        }),
        ok: true,
      };
      vi.mocked(postPlacesSearch).mockResolvedValue(
        mockSearchResponse as unknown as Response
      );
      const mockDetailsResponse = {
        json: vi.fn().mockResolvedValue({
          displayName: "Test Hotel",
          id: "place-id",
          photos: [{ name: "photo1" }],
          rating: 4.5,
        }),
        ok: true,
      };
      vi.mocked(getPlaceDetails).mockResolvedValue(
        mockDetailsResponse as unknown as Response
      );

      await enrichHotelListingWithPlaces(listing);

      // Verify only place_id and lat/lng are cached (policy-compliant)
      expect(cachePlaceId).toHaveBeenCalledWith("places:q2id:hash123", "place-id");
      // Verify getPlaceDetails is always called (details never cached)
      expect(getPlaceDetails).toHaveBeenCalled();
      // Verify cachePlaceId is only called with place_id string, not full objects
      expect(cachePlaceId).toHaveBeenCalledWith(expect.any(String), expect.any(String));
    });
  });
});
