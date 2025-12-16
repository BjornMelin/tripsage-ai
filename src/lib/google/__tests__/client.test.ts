/** @vitest-environment node */

import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import {
  getGeocode,
  getPlaceDetails,
  getPlacePhoto,
  getReverseGeocode,
  getTimezone,
  parseNdjsonResponse,
  postComputeRouteMatrix,
  postComputeRoutes,
  postNearbySearch,
  postPlacesSearch,
} from "../client";

describe("Google API Client", () => {
  beforeEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
  });

  describe("postPlacesSearch", () => {
    it("should call retryWithBackoff with correct fetch configuration", async () => {
      server.use(
        http.post(
          "https://places.googleapis.com/v1/places:searchText",
          async ({ request }) => {
            expect(request.headers.get("Content-Type")).toBe("application/json");
            expect(request.headers.get("X-Goog-Api-Key")).toBe("test-key");
            expect(request.headers.get("X-Goog-FieldMask")).toBe(
              "places.id,places.displayName"
            );

            const body = await request.json();
            expect(body).toEqual({ textQuery: "restaurants" });

            return HttpResponse.json({});
          }
        )
      );

      await postPlacesSearch({
        apiKey: "test-key",
        body: { textQuery: "restaurants" },
        fieldMask: "places.id,places.displayName",
      });
    });
  });

  describe("getPlaceDetails", () => {
    it("should include session token when provided", async () => {
      server.use(
        http.get("https://places.googleapis.com/v1/ChIJ123abc", ({ request }) => {
          expect(request.headers.get("X-Goog-Api-Key")).toBe("test-key");
          expect(request.headers.get("X-Goog-FieldMask")).toBe("displayName");
          expect(request.headers.get("X-Goog-Session-Token")).toBe("session-123");

          return HttpResponse.json({ id: "ChIJ123abc" });
        })
      );

      await getPlaceDetails({
        apiKey: "test-key",
        fieldMask: "displayName",
        placeId: "ChIJ123abc",
        sessionToken: "session-123",
      });
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
      server.use(
        http.post(
          "https://routes.googleapis.com/directions/v2:computeRoutes",
          async ({ request }) => {
            expect(request.headers.get("Content-Type")).toBe("application/json");
            expect(request.headers.get("X-Goog-Api-Key")).toBe("test-key");
            expect(request.headers.get("X-Goog-FieldMask")).toBe("routes.duration");

            const body = await request.json();
            expect(body).toEqual({ destination: {}, origin: {} });

            return HttpResponse.json({});
          }
        )
      );

      await postComputeRoutes({
        apiKey: "test-key",
        body: { destination: {}, origin: {} },
        fieldMask: "routes.duration",
      });
    });
  });

  describe("postComputeRouteMatrix", () => {
    it("should call correct Routes API matrix endpoint", async () => {
      server.use(
        http.post(
          "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
          ({ request }) => {
            expect(request.headers.get("X-Goog-Api-Key")).toBe("test-key");
            expect(request.headers.get("X-Goog-FieldMask")).toBe(
              "originIndex,destinationIndex"
            );
            return HttpResponse.json({});
          }
        )
      );

      await postComputeRouteMatrix({
        apiKey: "test-key",
        body: { destinations: [], origins: [] },
        fieldMask: "originIndex,destinationIndex",
      });
    });
  });

  describe("getGeocode", () => {
    it("should construct correct URL with address parameter", async () => {
      server.use(
        http.get("https://maps.googleapis.com/maps/api/geocode/json", ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get("address")).toBe("123 Main St, New York, NY");
          expect(url.searchParams.get("key")).toBe("test-key");

          return HttpResponse.json({ results: [], status: "OK" });
        })
      );

      await getGeocode({
        address: "123 Main St, New York, NY",
        apiKey: "test-key",
      });
    });
  });

  describe("getReverseGeocode", () => {
    it("should construct correct URL with latlng parameter", async () => {
      server.use(
        http.get("https://maps.googleapis.com/maps/api/geocode/json", ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get("latlng")).toBe("40.7128,-74.006");
          expect(url.searchParams.get("key")).toBe("test-key");

          return HttpResponse.json({ results: [], status: "OK" });
        })
      );

      await getReverseGeocode({
        apiKey: "test-key",
        lat: 40.7128,
        lng: -74.006,
      });
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
      server.use(
        http.get(
          "https://maps.googleapis.com/maps/api/timezone/json",
          ({ request }) => {
            const url = new URL(request.url);
            expect(url.searchParams.get("location")).toBe("35.6762,139.6503");
            expect(url.searchParams.get("timestamp")).toBe("1700000000");
            expect(url.searchParams.get("key")).toBe("test-key");

            return HttpResponse.json({ status: "OK" });
          }
        )
      );

      const mockTimestamp = 1700000000;
      await getTimezone({
        apiKey: "test-key",
        lat: 35.6762,
        lng: 139.6503,
        timestamp: mockTimestamp,
      });
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
      server.use(
        http.get(
          "https://places.googleapis.com/v1/places/:placeId/photos/:photoId/media",
          ({ params }) => {
            expect(params.placeId).toBe("ABC123");
            expect(params.photoId).toBe("XYZ789");
            return new HttpResponse("ok", { status: 200 });
          }
        )
      );

      await getPlacePhoto({
        apiKey: "test-key",
        maxWidthPx: 400,
        photoName: "places/ABC123/photos/XYZ789",
      });
    });

    it("should include dimension parameters when provided", async () => {
      server.use(
        http.get(
          "https://places.googleapis.com/v1/places/:placeId/photos/:photoId/media",
          ({ request }) => {
            const url = new URL(request.url);
            expect(url.searchParams.get("maxWidthPx")).toBe("600");
            expect(url.searchParams.get("maxHeightPx")).toBe("400");
            return new HttpResponse("ok", { status: 200 });
          }
        )
      );

      await getPlacePhoto({
        apiKey: "test-key",
        maxHeightPx: 400,
        maxWidthPx: 600,
        photoName: "places/ABC123/photos/XYZ789",
      });
    });

    it("should throw error for invalid photoName format", async () => {
      await expect(
        getPlacePhoto({
          apiKey: "test-key",
          maxWidthPx: 400,
          photoName: "invalid-photo-name",
        })
      ).rejects.toThrow("Invalid photoName");
    });

    it("should throw error when no dimension parameter provided", async () => {
      await expect(
        getPlacePhoto({
          apiKey: "test-key",
          photoName: "places/ABC123/photos/XYZ789",
        })
      ).rejects.toThrow("Either maxWidthPx or maxHeightPx must be provided");
    });
  });

  describe("postNearbySearch", () => {
    it("should construct correct request body", async () => {
      server.use(
        http.post(
          "https://places.googleapis.com/v1/places:searchNearby",
          async ({ request }) => {
            expect(request.headers.get("Content-Type")).toBe("application/json");
            expect(request.headers.get("X-Goog-Api-Key")).toBe("test-key");
            expect(request.headers.get("X-Goog-FieldMask")).toBe("places.id");

            const body = await request.json();
            expect(body).toEqual({
              includedTypes: ["restaurant", "cafe"],
              locationRestriction: {
                circle: {
                  center: { latitude: 40.7128, longitude: -74.006 },
                  radius: 2000,
                },
              },
              maxResultCount: 15,
            });

            return HttpResponse.json({});
          }
        )
      );

      await postNearbySearch({
        apiKey: "test-key",
        fieldMask: "places.id",
        includedTypes: ["restaurant", "cafe"],
        lat: 40.7128,
        lng: -74.006,
        maxResultCount: 15,
        radiusMeters: 2000,
      });
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

  describe("parseNdjsonResponse", () => {
    it("should parse single line NDJSON", async () => {
      const response = new Response('{"originIndex":0,"destinationIndex":0}\n');
      const result = await parseNdjsonResponse(response);
      expect(result).toEqual([{ destinationIndex: 0, originIndex: 0 }]);
    });

    it("should parse multiple line NDJSON", async () => {
      const ndjson =
        '{"originIndex":0,"destinationIndex":0}\n{"originIndex":0,"destinationIndex":1}\n{"originIndex":1,"destinationIndex":0}\n';
      const response = new Response(ndjson);
      const result = await parseNdjsonResponse(response);
      expect(result).toEqual([
        { destinationIndex: 0, originIndex: 0 },
        { destinationIndex: 1, originIndex: 0 },
        { destinationIndex: 0, originIndex: 1 },
      ]);
    });

    it("should skip empty lines", async () => {
      const ndjson = '{"a":1}\n\n{"b":2}\n   \n{"c":3}\n';
      const response = new Response(ndjson);
      const result = await parseNdjsonResponse(response);
      expect(result).toEqual([{ a: 1 }, { b: 2 }, { c: 3 }]);
    });

    it("should throw error for invalid JSON line", async () => {
      const response = new Response('{"valid":true}\ninvalid json\n');
      await expect(parseNdjsonResponse(response)).rejects.toThrow(
        "Failed to parse NDJSON line 2"
      );
    });

    it("should return empty array for empty response", async () => {
      const response = new Response("");
      const result = await parseNdjsonResponse(response);
      expect(result).toEqual([]);
    });
  });

  describe("getPlacePhoto with skipHttpRedirect", () => {
    it("should include skipHttpRedirect parameter when true", async () => {
      server.use(
        http.get(
          "https://places.googleapis.com/v1/places/:placeId/photos/:photoId/media",
          ({ request }) => {
            const url = new URL(request.url);
            expect(url.searchParams.get("skipHttpRedirect")).toBe("true");
            return new HttpResponse("ok", { status: 200 });
          }
        )
      );

      await getPlacePhoto({
        apiKey: "test-key",
        maxWidthPx: 400,
        photoName: "places/ABC123/photos/XYZ789",
        skipHttpRedirect: true,
      });
    });

    it("should not include skipHttpRedirect when not provided", async () => {
      server.use(
        http.get(
          "https://places.googleapis.com/v1/places/:placeId/photos/:photoId/media",
          ({ request }) => {
            const url = new URL(request.url);
            expect(url.searchParams.has("skipHttpRedirect")).toBe(false);
            return new HttpResponse("ok", { status: 200 });
          }
        )
      );

      await getPlacePhoto({
        apiKey: "test-key",
        maxWidthPx: 400,
        photoName: "places/ABC123/photos/XYZ789",
      });
    });
  });
});
