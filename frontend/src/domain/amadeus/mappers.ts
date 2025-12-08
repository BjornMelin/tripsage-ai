/**
 * @fileoverview Mapping functions from Amadeus SDK responses to TripSage accommodation domain structures.
 */

import type { AccommodationSearchResult } from "@schemas/accommodations";
import type { AmadeusHotel, AmadeusHotelOffer } from "./schemas";

/**
 * Extract cancellation policy info from Amadeus policies object.
 */
function extractCancellationPolicy(policies: Record<string, unknown> | undefined):
  | {
      deadline?: string;
      description?: string;
      partialRefundable?: boolean;
      refundable?: boolean;
    }
  | undefined {
  if (!policies || typeof policies !== "object") return undefined;

  const cancellationRaw = (policies as Record<string, unknown>).cancellation;
  const cancellation =
    cancellationRaw && typeof cancellationRaw === "object"
      ? (cancellationRaw as Record<string, unknown>)
      : undefined;

  const cancellationType =
    typeof cancellation?.type === "string" ? cancellation.type : undefined;
  const refundable = policies.refundable === true || cancellationType === "FULL_REFUND";
  const partialRefundable = cancellationType === "PARTIAL_REFUND";

  const deadline =
    typeof cancellation?.deadline === "string" ? cancellation.deadline : undefined;
  const description =
    typeof cancellation?.description === "string"
      ? cancellation.description
      : undefined;

  return {
    deadline,
    description,
    partialRefundable,
    refundable,
  };
}

/**
 * Sum taxes from Amadeus price taxes array.
 */
function projectTaxes(
  taxes:
    | Array<{ amount: string; code?: string; currency?: string; included?: boolean }>
    | undefined
): Array<{ amount: number; code?: string; currency?: string; included?: boolean }> {
  if (!taxes) return [];
  return taxes
    .map((tax) => {
      const amount = Number.parseFloat(tax.amount);
      if (!Number.isFinite(amount)) {
        throw new Error(
          `Invalid tax amount encountered: ${JSON.stringify({
            amount: tax.amount,
            code: tax.code,
            currency: tax.currency,
          })}`
        );
      }
      return {
        amount,
        code: tax.code,
        currency: tax.currency,
        included: tax.included,
      };
    })
    .filter((tax) => tax.amount >= 0);
}

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
    const offerTaxTotals = offers.map((offer) => {
      const projected = projectTaxes(offer.price.taxes);
      return projected.reduce((sum, tax) => sum + tax.amount, 0);
    });
    const taxes = offerTaxTotals.length ? Math.min(...offerTaxTotals) : 0;

    // Choose most restrictive cancellation policy among offers (refundability false wins)
    const cancellationPolicy = offers
      .map((offer) => extractCancellationPolicy(offer.policies))
      .reduce<
        { deadline?: string; description?: string; refundable?: boolean } | undefined
      >((acc, current) => {
        if (!current) return acc;
        if (!acc) return current;
        // prefer non-refundable
        if (acc.refundable === false) return acc;
        if (current.refundable === false) return current;
        // otherwise earliest deadline is more restrictive
        if (acc.deadline && current.deadline) {
          return acc.deadline <= current.deadline ? acc : current;
        }
        return acc.deadline ? acc : current;
      }, undefined);

    const rooms = offers.map((offer) => ({
      description: offer.room?.description?.text,
      id: offer.id,
      rates: [
        {
          id: offer.id,
          price: {
            base:
              typeof offer.price.base === "string"
                ? Number.parseFloat(offer.price.base)
                : offer.price.base,
            currency: offer.price.currency,
            numeric: Number.parseFloat(offer.price.total),
            taxes: projectTaxes(offer.price.taxes),
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
      cancellationPolicy,
      chainCode: hotel.chainCode,
      geoCode: hotel.geoCode,
      id: hotel.hotelId,
      name: hotel.name,
      rooms,
      searchMeta: meta,
      starRating: undefined,
      taxes,
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
