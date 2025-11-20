/**
 * @fileoverview Flights service orchestrating provider calls and normalization.
 */

import {
  type FlightSearchRequest,
  type FlightSearchResult,
  flightSearchRequestSchema,
  flightSearchResultSchema,
} from "@schemas/flights";
import { mapDuffelOffersList } from "./mappers";
import { fetchDuffelOffers } from "./providers/duffel";

/**
 * Search flights via Duffel and return normalized offers.
 *
 * @param params - The flight search request parameters.
 * @returns The flight search result.
 * @throws an Error with a structured message on HTTP failure.
 */
export async function searchFlightsService(
  params: FlightSearchRequest
): Promise<FlightSearchResult> {
  const parsed = flightSearchRequestSchema.parse(params);
  const payload = await fetchDuffelOffers(parsed);
  const { offers, currency, itineraries } = mapDuffelOffersList(
    payload,
    parsed.currency
  );

  return flightSearchResultSchema.parse({
    currency,
    fromCache: false,
    itineraries,
    offers,
    provider: "duffel",
    schemaVersion: "flight.v2",
  });
}
