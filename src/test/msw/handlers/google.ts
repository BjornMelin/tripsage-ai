/**
 * @fileoverview MSW handlers for Google APIs (Places, Geocoding, Routes) used in tests.
 */

import type { HttpHandler } from "msw";
import { HttpResponse, http } from "msw";

const defaultPhotoName = "places/placeholder/photos/primary";
const activitySearchTerms = ["activities", "things to do"] as const;

function isActivitySearchQuery(query: string) {
  const normalized = query.toLowerCase();
  return activitySearchTerms.some((term) => normalized.includes(term));
}

/** Shared 404 error response for invalid resources. */
const RESOURCE_NOT_FOUND_ERROR = {
  error: {
    code: 404,
    message: "Resource not found",
    status: "NOT_FOUND",
  },
} as const;

/** MSW handlers for Google Places (New) API endpoints used in tests. */
export const googlePlacesHandlers: HttpHandler[] = [
  http.post("/api/places/search", async ({ request }) => {
    const fallbackQuery = "Sample Place";
    const body = (await request.json().catch(() => ({}))) as {
      maxResultCount?: number;
      textQuery?: string;
    };
    const textQuery = body.textQuery ?? fallbackQuery;

    const places = [
      {
        coordinates: { lat: 48.8566, lng: 2.3522 },
        formattedAddress: `${textQuery}, Example Country`,
        name: textQuery,
        photoName: defaultPhotoName,
        placeId: "mock-1",
        rating: 4.5,
        types: ["locality", "country"],
        url: `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent("mock-1")}`,
        userRatingCount: 128,
      },
      {
        coordinates: { lat: 48.8606, lng: 2.3376 },
        formattedAddress: `${textQuery} Arts District`,
        name: `${textQuery} Museum`,
        photoName: defaultPhotoName,
        placeId: "mock-2",
        rating: 4.6,
        types: ["museum", "establishment"],
        url: `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent("mock-2")}`,
        userRatingCount: 256,
      },
    ];

    return HttpResponse.json({
      places: places.slice(0, body.maxResultCount ?? places.length),
    });
  }),

  http.post(
    "https://places.googleapis.com/v1/places:searchText",
    async ({ request }) => {
      let textQuery = "Sample Hotel";
      try {
        const body = (await request.json()) as { textQuery?: string };
        if (body?.textQuery) textQuery = body.textQuery;
      } catch {
        // ignore parse errors; use defaults
      }

      // Handle activity searches differently
      if (isActivitySearchQuery(textQuery)) {
        return HttpResponse.json({
          places: [
            {
              displayName: { text: "Museum of Modern Art" },
              formattedAddress: "11 W 53rd St, New York, NY 10019",
              id: "ChIJN1t_tDeuEmsRUsoyG83frY4",
              location: { latitude: 40.7614, longitude: -73.9776 },
              photos: [{ name: defaultPhotoName }],
              priceLevel: "PRICE_LEVEL_MODERATE",
              rating: 4.6,
              types: ["museum", "tourist_attraction"],
              userRatingCount: 4523,
            },
            {
              displayName: { text: "Central Park" },
              formattedAddress: "New York, NY",
              id: "ChIJN1t_tDeuEmsRUsoyG83frY5",
              location: { latitude: 40.7829, longitude: -73.9654 },
              photos: [{ name: defaultPhotoName }],
              priceLevel: "PRICE_LEVEL_FREE",
              rating: 4.8,
              types: ["park", "tourist_attraction"],
              userRatingCount: 125000,
            },
          ],
        });
      }

      return HttpResponse.json({
        places: [
          {
            adrFormatAddress: "123 Example St, Test City",
            displayName: { text: textQuery },
            id: "places/1",
            photos: [{ name: defaultPhotoName }],
            priceLevel: "PRICE_LEVEL_MODERATE",
            rating: 4.4,
            types: ["lodging"],
            userRatingCount: 128,
          },
        ],
      });
    }
  ),

  http.get("https://places.googleapis.com/v1/places/:placeId", ({ params }) => {
    // Handle invalid place ID
    if (params.placeId === "invalid") {
      return HttpResponse.json(
        {
          error: {
            code: 404,
            message: "Place not found",
            status: "NOT_FOUND",
          },
        },
        { status: 404 }
      );
    }

    return HttpResponse.json({
      adrFormatAddress: "123 Example St, Test City",
      displayName: { text: "Sample Place" },
      id: params.placeId ?? "places/1",
      internationalPhoneNumber: "+1-555-000-0000",
      photos: [{ name: defaultPhotoName }],
      priceLevel: "PRICE_LEVEL_MODERATE",
      rating: 4.5,
      types: ["lodging"],
      userRatingCount: 256,
      websiteUri: "https://example.com",
    });
  }),

  // Handle requests to an invalid activity path explicitly
  http.get("https://places.googleapis.com/v1/activities/invalid", () =>
    HttpResponse.json(RESOURCE_NOT_FOUND_ERROR, { status: 404 })
  ),

  // Explicit invalid path for error-handling tests
  http.get("https://places.googleapis.com/v1/invalid", () =>
    HttpResponse.json(RESOURCE_NOT_FOUND_ERROR, { status: 404 })
  ),

  http.get("https://places.googleapis.com/v1/:photoName/media", ({ params }) => {
    const name = params.photoName ?? defaultPhotoName;
    return HttpResponse.json({
      attributions: [],
      name,
      uri: `https://images.example.com/${name}`,
    });
  }),
];

/** MSW handlers for Google Geocoding API endpoints used in tests. */
export const googleGeocodingHandlers: HttpHandler[] = [
  http.get("https://maps.googleapis.com/maps/api/geocode/json", ({ request }) => {
    const url = new URL(request.url);
    const address = url.searchParams.get("address");
    const latlng = url.searchParams.get("latlng");

    const location = latlng
      ? (() => {
          const [lat, lng] = latlng.split(",").map((part) => Number(part.trim()));
          if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
          return { lat, lng };
        })()
      : null;

    const normalizedAddress = address?.trim() ?? "";

    if (normalizedAddress.toLowerCase().includes("zero results")) {
      return HttpResponse.json({ results: [], status: "ZERO_RESULTS" });
    }

    return HttpResponse.json({
      results: [
        {
          // biome-ignore lint/style/useNamingConvention: match upstream Geocoding API payload
          formatted_address:
            normalizedAddress || (location ? `(${location.lat}, ${location.lng})` : ""),
          geometry: {
            location: location ?? {
              lat: 40.7128,
              lng: -74.006,
            },
          },
          // biome-ignore lint/style/useNamingConvention: match upstream Geocoding API payload
          place_id: "place_123",
        },
      ],
      status: "OK",
    });
  }),

  http.get("https://maps.googleapis.com/maps/api/timezone/json", () => {
    return HttpResponse.json({
      dstOffset: 0,
      rawOffset: 0,
      status: "OK",
      timeZoneId: "Etc/UTC",
      timeZoneName: "UTC",
    });
  }),
];

/** MSW handlers for Google Routes API endpoints used in tests. */
export const googleRoutesHandlers: HttpHandler[] = [
  http.post("https://routes.googleapis.com/directions/v2:computeRoutes", () => {
    return HttpResponse.json({
      routes: [
        {
          distanceMeters: 1000,
          duration: "600s",
          legs: [{ stepCount: 0 }],
          polyline: { encodedPolyline: "" },
          routeLabels: [],
        },
      ],
    });
  }),

  http.post(
    "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
    async ({ request }) => {
      const body = (await request.json().catch(() => null)) as null | {
        destinations?: unknown[];
        origins?: unknown[];
      };

      const originCount =
        body && Array.isArray(body.origins) ? Math.max(0, body.origins.length) : 1;
      const destinationCount =
        body && Array.isArray(body.destinations)
          ? Math.max(0, body.destinations.length)
          : 1;

      const entries: Array<{
        condition: "ROUTE_EXISTS";
        destinationIndex: number;
        distanceMeters: number;
        duration: string;
        originIndex: number;
      }> = [];

      for (let originIndex = 0; originIndex < originCount; originIndex++) {
        for (
          let destinationIndex = 0;
          destinationIndex < destinationCount;
          destinationIndex++
        ) {
          const ordinal = originIndex * destinationCount + destinationIndex + 1;
          entries.push({
            condition: "ROUTE_EXISTS",
            destinationIndex,
            distanceMeters: 1000 * ordinal,
            duration: `${60 * ordinal}s`,
            originIndex,
          });
        }
      }

      const ndjson = `${entries.map((entry) => JSON.stringify(entry)).join("\n")}\n`;
      return HttpResponse.text(ndjson, {
        headers: { "Content-Type": "application/x-ndjson" },
      });
    }
  ),
];

/** Consolidated MSW handlers for all Google API mocks used in tests. */
export const googleHandlers: HttpHandler[] = [
  ...googlePlacesHandlers,
  ...googleGeocodingHandlers,
  ...googleRoutesHandlers,
];
