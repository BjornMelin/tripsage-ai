/** @vitest-environment node */

import { placeDetails, searchPlaces } from "@ai/tools";
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name, _options, fn) =>
    fn({
      addEvent: vi.fn(),
      setAttribute: vi.fn(),
    })
  ),
}));

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => undefined),
}));

const mapsKeyState: { value: string | undefined } = { value: "test_maps_key" };

vi.mock("@/lib/env/server", () => ({
  getGoogleMapsServerKey: () => {
    if (!mapsKeyState.value) {
      throw new Error(
        "GOOGLE_MAPS_SERVER_API_KEY is required for Google Maps Platform services"
      );
    }
    return mapsKeyState.value;
  },
}));

describe("places tools", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mapsKeyState.value = "test_maps_key";
    server.resetHandlers();
  });

  it("search.places maps upstream Places responses into canonical summaries", async () => {
    const captured = { body: null as unknown };

    server.use(
      http.post(
        "https://places.googleapis.com/v1/places:searchText",
        async ({ request }) => {
          captured.body = await request.json();
          return HttpResponse.json({
            places: [
              {
                displayName: { text: "Louvre Museum" },
                formattedAddress: "Rue de Rivoli, 75001 Paris, France",
                id: "ChIJb8Jg9pRu5kcR-4nECr6dO5c",
                location: { latitude: 48.8606, longitude: 2.3376 },
                photos: [{ name: "places/mock-1/photos/abc" }],
                rating: 4.7,
                types: ["museum", "tourist_attraction"],
                userRatingCount: 123456,
              },
            ],
          });
        }
      )
    );

    const result = await searchPlaces.execute?.(
      { maxResults: 5, query: "museum in Paris" },
      mockContext
    );

    expect(captured.body).toMatchObject({
      maxResultCount: 5,
      textQuery: "museum in Paris",
    });
    expect(result).toMatchObject({
      places: [
        expect.objectContaining({
          coordinates: { lat: 48.8606, lng: 2.3376 },
          formattedAddress: "Rue de Rivoli, 75001 Paris, France",
          name: "Louvre Museum",
          photoName: "places/mock-1/photos/abc",
          placeId: "ChIJb8Jg9pRu5kcR-4nECr6dO5c",
        }),
      ],
    });
  });

  it("search.placeDetails maps upstream details into canonical details", async () => {
    server.use(
      http.get("https://places.googleapis.com/v1/places/:placeId", ({ params }) => {
        return HttpResponse.json({
          businessStatus: "OPERATIONAL",
          displayName: { text: "Cafe Test" },
          formattedAddress: "123 Test St, Paris, France",
          id: `places/${params.placeId ?? "mock"}`,
          internationalPhoneNumber: "+33 1 23 45 67 89",
          location: { latitude: 48.8566, longitude: 2.3522 },
          photos: [{ name: "places/mock-2/photos/def" }],
          rating: 4.4,
          regularOpeningHours: {
            openNow: true,
            weekdayDescriptions: ["Monday: 9:00 AM – 5:00 PM"],
          },
          types: ["cafe", "food"],
          userRatingCount: 42,
          websiteUri: "https://example.com",
        });
      })
    );

    const result = await placeDetails.execute?.({ placeId: "mock-2" }, mockContext);

    expect(result).toMatchObject({
      businessStatus: "OPERATIONAL",
      coordinates: { lat: 48.8566, lng: 2.3522 },
      formattedAddress: "123 Test St, Paris, France",
      internationalPhoneNumber: "+33 1 23 45 67 89",
      name: "Cafe Test",
      photoName: "places/mock-2/photos/def",
      placeId: "places/mock-2",
      regularOpeningHours: {
        openNow: true,
        weekdayDescriptions: ["Monday: 9:00 AM – 5:00 PM"],
      },
      types: ["cafe", "food"],
      websiteUri: "https://example.com",
    });
  });

  it("throws when Places API key is not configured", async () => {
    mapsKeyState.value = undefined;
    await expect(
      searchPlaces.execute?.({ maxResults: 5, query: "paris" }, mockContext)
    ).rejects.toThrow(/not configured/i);
  });
});
