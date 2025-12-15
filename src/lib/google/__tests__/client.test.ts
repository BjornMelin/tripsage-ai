/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Capture fetch arguments via retryWithBackoff mock
let capturedFetchFn: (() => Promise<Response>) | null = null;

vi.mock("@/lib/http/retry", () => ({
  retryWithBackoff: vi.fn((fn) => {
    capturedFetchFn = fn;
    // Create a mock response
    return Promise.resolve(
      new Response(JSON.stringify({}), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      })
    );
  }),
}));

// Import after mocking
const {
  getGeocode,
  getPlaceDetails,
  getPlacePhoto,
  getReverseGeocode,
  getTimezone,
  postComputeRouteMatrix,
  postComputeRoutes,
  postNearbySearch,
  postPlacesSearch,
} = await import("../client");

describe("Google API Client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedFetchFn = null;
  });

  describe("postPlacesSearch", () => {
    it("should call retryWithBackoff with correct fetch configuration", async () => {
      await postPlacesSearch({
        apiKey: "test-key",
        body: { textQuery: "restaurants" },
        fieldMask: "places.id,places.displayName",
      });

      expect(capturedFetchFn).toBeDefined();

      // Execute the captured fetch function to get the Request
      const mockFetch = vi.fn().mockResolvedValue(new Response());
      vi.stubGlobal("fetch", mockFetch);

      await capturedFetchFn?.();

      expect(mockFetch).toHaveBeenCalledWith(
        "https://places.googleapis.com/v1/places:searchText",
        expect.objectContaining({
          body: JSON.stringify({ textQuery: "restaurants" }),
          headers: {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": "test-key",
            "X-Goog-FieldMask": "places.id,places.displayName",
          },
          method: "POST",
        })
      );

      vi.unstubAllGlobals();
    });
  });

  describe("getPlaceDetails", () => {
    it("should include session token when provided", async () => {
      await getPlaceDetails({
        apiKey: "test-key",
        fieldMask: "displayName",
        placeId: "ChIJ123abc",
        sessionToken: "session-123",
      });

      expect(capturedFetchFn).toBeDefined();

      const mockFetch = vi.fn().mockResolvedValue(new Response());
      vi.stubGlobal("fetch", mockFetch);

      await capturedFetchFn?.();

      expect(mockFetch).toHaveBeenCalledWith(
        "https://places.googleapis.com/v1/ChIJ123abc",
        expect.objectContaining({
          headers: expect.objectContaining({
            "X-Goog-Session-Token": "session-123",
          }),
        })
      );

      vi.unstubAllGlobals();
    });

    it("should throw error for invalid placeId", async () => {
      await expect(
        getPlaceDetails({
          apiKey: "test-key",
          fieldMask: "displayName",
          placeId: "invalid place id with spaces",
        })
      ).rejects.toThrow("Invalid placeId");
    });

    it("should throw error for empty fieldMask", async () => {
      await expect(
        getPlaceDetails({
          apiKey: "test-key",
          fieldMask: "",
          placeId: "ChIJ123abc",
        })
      ).rejects.toThrow("fieldMask is required");
    });
  });

  describe("postComputeRoutes", () => {
    it("should call correct Routes API endpoint", async () => {
      await postComputeRoutes({
        apiKey: "test-key",
        body: { destination: {}, origin: {} },
        fieldMask: "routes.duration",
      });

      expect(capturedFetchFn).toBeDefined();

      const mockFetch = vi.fn().mockResolvedValue(new Response());
      vi.stubGlobal("fetch", mockFetch);

      await capturedFetchFn?.();

      expect(mockFetch).toHaveBeenCalledWith(
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        expect.objectContaining({
          headers: expect.objectContaining({
            "X-Goog-Api-Key": "test-key",
            "X-Goog-FieldMask": "routes.duration",
          }),
          method: "POST",
        })
      );

      vi.unstubAllGlobals();
    });
  });

  describe("postComputeRouteMatrix", () => {
    it("should call correct Routes API matrix endpoint", async () => {
      await postComputeRouteMatrix({
        apiKey: "test-key",
        body: { destinations: [], origins: [] },
        fieldMask: "originIndex,destinationIndex",
      });

      expect(capturedFetchFn).toBeDefined();

      const mockFetch = vi.fn().mockResolvedValue(new Response());
      vi.stubGlobal("fetch", mockFetch);

      await capturedFetchFn?.();

      expect(mockFetch).toHaveBeenCalledWith(
        "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
        expect.objectContaining({
          method: "POST",
        })
      );

      vi.unstubAllGlobals();
    });
  });

  describe("getGeocode", () => {
    it("should construct correct URL with address parameter", async () => {
      await getGeocode({
        address: "123 Main St, New York, NY",
        apiKey: "test-key",
      });

      expect(capturedFetchFn).toBeDefined();

      const mockFetch = vi.fn().mockResolvedValue(new Response());
      vi.stubGlobal("fetch", mockFetch);

      await capturedFetchFn?.();

      const calledUrl = mockFetch.mock.calls[0][0];
      expect(calledUrl).toContain("maps.googleapis.com/maps/api/geocode/json");
      expect(calledUrl).toContain("address=123+Main+St%2C+New+York%2C+NY");
      expect(calledUrl).toContain("key=test-key");

      vi.unstubAllGlobals();
    });
  });

  describe("getReverseGeocode", () => {
    it("should construct correct URL with latlng parameter", async () => {
      await getReverseGeocode({
        apiKey: "test-key",
        lat: 40.7128,
        lng: -74.006,
      });

      expect(capturedFetchFn).toBeDefined();

      const mockFetch = vi.fn().mockResolvedValue(new Response());
      vi.stubGlobal("fetch", mockFetch);

      await capturedFetchFn?.();

      const calledUrl = mockFetch.mock.calls[0][0];
      expect(calledUrl).toContain("latlng=40.7128%2C-74.006");

      vi.unstubAllGlobals();
    });

    it("should throw error for invalid latitude", async () => {
      await expect(
        getReverseGeocode({ apiKey: "test-key", lat: 100, lng: 0 })
      ).rejects.toThrow("Invalid latitude");

      await expect(
        getReverseGeocode({ apiKey: "test-key", lat: -100, lng: 0 })
      ).rejects.toThrow("Invalid latitude");
    });

    it("should throw error for invalid longitude", async () => {
      await expect(
        getReverseGeocode({ apiKey: "test-key", lat: 0, lng: 200 })
      ).rejects.toThrow("Invalid longitude");

      await expect(
        getReverseGeocode({ apiKey: "test-key", lat: 0, lng: -200 })
      ).rejects.toThrow("Invalid longitude");
    });
  });

  describe("getTimezone", () => {
    it("should construct correct URL with location and timestamp", async () => {
      const mockTimestamp = 1700000000;
      await getTimezone({
        apiKey: "test-key",
        lat: 35.6762,
        lng: 139.6503,
        timestamp: mockTimestamp,
      });

      expect(capturedFetchFn).toBeDefined();

      const mockFetch = vi.fn().mockResolvedValue(new Response());
      vi.stubGlobal("fetch", mockFetch);

      await capturedFetchFn?.();

      const calledUrl = mockFetch.mock.calls[0][0];
      expect(calledUrl).toContain("maps.googleapis.com/maps/api/timezone/json");
      expect(calledUrl).toContain("location=35.6762%2C139.6503");
      expect(calledUrl).toContain("timestamp=1700000000");

      vi.unstubAllGlobals();
    });

    it("should throw error for invalid coordinates", async () => {
      await expect(
        getTimezone({ apiKey: "test-key", lat: 100, lng: 0 })
      ).rejects.toThrow("Invalid latitude");

      await expect(
        getTimezone({ apiKey: "test-key", lat: 0, lng: 200 })
      ).rejects.toThrow("Invalid longitude");
    });
  });

  describe("getPlacePhoto", () => {
    it("should construct correct URL with photo name", async () => {
      await getPlacePhoto({
        apiKey: "test-key",
        photoName: "places/ABC123/photos/XYZ789",
      });

      expect(capturedFetchFn).toBeDefined();

      const mockFetch = vi.fn().mockResolvedValue(new Response());
      vi.stubGlobal("fetch", mockFetch);

      await capturedFetchFn?.();

      const calledUrl = mockFetch.mock.calls[0][0];
      expect(calledUrl).toContain(
        "places.googleapis.com/v1/places/ABC123/photos/XYZ789/media"
      );

      vi.unstubAllGlobals();
    });

    it("should include dimension parameters when provided", async () => {
      await getPlacePhoto({
        apiKey: "test-key",
        maxHeightPx: 400,
        maxWidthPx: 600,
        photoName: "places/ABC123/photos/XYZ789",
      });

      expect(capturedFetchFn).toBeDefined();

      const mockFetch = vi.fn().mockResolvedValue(new Response());
      vi.stubGlobal("fetch", mockFetch);

      await capturedFetchFn?.();

      const calledUrl = mockFetch.mock.calls[0][0];
      expect(calledUrl).toContain("maxWidthPx=600");
      expect(calledUrl).toContain("maxHeightPx=400");

      vi.unstubAllGlobals();
    });

    it("should throw error for invalid photoName format", async () => {
      await expect(
        getPlacePhoto({
          apiKey: "test-key",
          photoName: "invalid-photo-name",
        })
      ).rejects.toThrow("Invalid photoName");
    });
  });

  describe("postNearbySearch", () => {
    it("should construct correct request body", async () => {
      await postNearbySearch({
        apiKey: "test-key",
        fieldMask: "places.id",
        includedTypes: ["restaurant", "cafe"],
        lat: 40.7128,
        lng: -74.006,
        maxResultCount: 15,
        radiusMeters: 2000,
      });

      expect(capturedFetchFn).toBeDefined();

      const mockFetch = vi.fn().mockResolvedValue(new Response());
      vi.stubGlobal("fetch", mockFetch);

      await capturedFetchFn?.();

      expect(mockFetch).toHaveBeenCalledWith(
        "https://places.googleapis.com/v1/places:searchNearby",
        expect.objectContaining({
          body: JSON.stringify({
            locationRestriction: {
              circle: {
                center: { latitude: 40.7128, longitude: -74.006 },
                radius: 2000,
              },
            },
            maxResultCount: 15,
            includedTypes: ["restaurant", "cafe"],
          }),
          method: "POST",
        })
      );

      vi.unstubAllGlobals();
    });

    it("should throw error for invalid coordinates", async () => {
      await expect(
        postNearbySearch({
          apiKey: "test-key",
          fieldMask: "places.id",
          lat: 100,
          lng: 0,
        })
      ).rejects.toThrow("Invalid latitude");
    });

    it("should throw error for invalid maxResultCount", async () => {
      await expect(
        postNearbySearch({
          apiKey: "test-key",
          fieldMask: "places.id",
          lat: 0,
          lng: 0,
          maxResultCount: 25,
        })
      ).rejects.toThrow("Invalid maxResultCount");
    });

    it("should throw error for invalid radiusMeters", async () => {
      await expect(
        postNearbySearch({
          apiKey: "test-key",
          fieldMask: "places.id",
          lat: 0,
          lng: 0,
          radiusMeters: 100000,
        })
      ).rejects.toThrow("Invalid radiusMeters");
    });
  });
});
