/**
 * @fileoverview Mapping functions from Amadeus SDK responses to TripSage accommodation domain structures.
 */

import type { AccommodationSearchResult } from "@schemas/accommodations";
import type { AmadeusHotel, AmadeusHotelOffer } from "./schemas";

/**
 * Map Amadeus hotels and offers to TripSage accommodation listings.
 *
 * @param hotels - Amadeus hotels.
 * @param offersByHotel - Amadeus offers by hotel.
 * @param meta - Meta data.
 * @returns TripSage accommodation listings.
 */
export function mapHotelsToListings(
  hotels: AmadeusHotel[],
  offersByHotel: Record<string, AmadeusHotelOffer[]>,
  meta: Record<string, unknown>
): AccommodationSearchResult["listings"] {
  return hotels.map((hotel) => {
    const offers = offersByHotel[hotel.hotelId] ?? [];
    const rooms = offers.map((offer) => ({
      description: offer.room?.description?.text,
      id: offer.id,
      rates: [
        {
          id: offer.id,
          price: {
            currency: offer.price.currency,
            numeric: Number.parseFloat(offer.price.total),
            total: offer.price.total,
          },
          refundability: offer.policies,
        },
      ],
      roomName: offer.room?.type ?? offer.room?.typeEstimated?.category,
    }));

    return {
      address: hotel.address,
      amenities: [],
      id: hotel.hotelId,
      name: hotel.name,
      rooms,
      searchMeta: meta,
      starRating: undefined,
    };
  });
}

/**
 * Collect prices from Amadeus offers.
 *
 * @param offers - Amadeus offers.
 * @returns Prices.
 */
export function collectPricesFromOffers(offers: AmadeusHotelOffer[]): number[] {
  return offers
    .map((offer) => Number.parseFloat(offer.price.total))
    .filter((value) => Number.isFinite(value));
}
