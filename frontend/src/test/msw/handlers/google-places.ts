/**
 * @fileoverview MSW handlers for Google Places (New) API endpoints used in tests.
 */

import type { HttpHandler } from "msw";
import { HttpResponse, http } from "msw";

const defaultPhotoName = "places/placeholder/photos/primary";

export const googlePlacesHandlers: HttpHandler[] = [
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

  http.get("https://places.googleapis.com/v1/places/:placeId", ({ params }) =>
    HttpResponse.json({
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
    })
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
