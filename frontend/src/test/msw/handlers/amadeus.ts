/**
 * @fileoverview MSW handlers for Amadeus Self-Service Hotels endpoints.
 */

import type { HttpHandler } from "msw";
import { HttpResponse, http } from "msw";

export const amadeusHandlers: HttpHandler[] = [
  http.get(
    "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-geocode",
    ({ request }) => {
      const url = new URL(request.url);
      const latitude = Number(url.searchParams.get("latitude") ?? 0);
      const longitude = Number(url.searchParams.get("longitude") ?? 0);

      return HttpResponse.json({
        data: [
          {
            address: { cityName: "Paris", countryCode: "FR" },
            geoCode: { latitude, longitude },
            hotelId: "H1",
            name: "Amadeus Test Hotel",
            rating: "4",
          },
        ],
      });
    }
  ),

  http.get("https://test.api.amadeus.com/v3/shopping/hotel-offers", ({ request }) => {
    const url = new URL(request.url);
    const hotelIds = url.searchParams.get("hotelIds") ?? "H1";
    const checkInDate = url.searchParams.get("checkInDate") ?? "2025-01-01";
    const checkOutDate = url.searchParams.get("checkOutDate") ?? "2025-01-02";

    return HttpResponse.json({
      data: [
        {
          available: true,
          hotel: { hotelId: hotelIds.split(",")[0], name: "Amadeus Test Hotel" },
          offers: [
            {
              checkInDate,
              checkOutDate,
              guests: { adults: 2 },
              id: "OFFER1",
              price: { base: "200.00", currency: "USD", total: "240.00" },
              room: { type: "DLX", typeEstimated: { category: "DELUXE_ROOM" } },
            },
          ],
          type: "hotel-offers",
        },
      ],
    });
  }),

  http.post(
    "https://test.api.amadeus.com/v1/booking/hotel-bookings",
    async ({ request }) => {
      let payload: unknown;
      try {
        payload = await request.json();
      } catch {
        payload = {};
      }

      return HttpResponse.json({
        data: [
          {
            hotelId: "H1",
            id: "BK1",
            metadata: { request: payload },
            providerConfirmationId: "CONF123",
            self: "https://test.api.amadeus.com/v1/booking/hotel-bookings/BK1",
          },
        ],
      });
    }
  ),
];
