/**
 * @fileoverview Server Actions for hotel/accommodation search.
 */

"use server";

import "server-only";

import {
  type SearchAccommodationParams,
  searchAccommodationParamsSchema,
} from "@schemas/search";
import { normalizePlacesTextQuery } from "@/lib/google/places-utils";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const MAX_TELEMETRY_DESTINATION_LENGTH = 256;

/**
 * Server action to validate and trace hotel search submissions.
 *
 * @param params - Accommodation search parameters from the client.
 * @returns Validated accommodation search parameters.
 * @throws Error if validation fails.
 */
export async function submitHotelSearch(
  params: SearchAccommodationParams
): Promise<SearchAccommodationParams> {
  const validation = searchAccommodationParamsSchema.safeParse(params);
  if (!validation.success) {
    throw new Error(`Invalid accommodation search params: ${validation.error.message}`);
  }
  const validatedDestination = validation.data.destination
    ? normalizePlacesTextQuery(validation.data.destination).slice(
        0,
        MAX_TELEMETRY_DESTINATION_LENGTH
      )
    : "";
  return await withTelemetrySpan(
    "search.hotel.server.submit",
    {
      attributes: {
        destination: validatedDestination,
        searchType: "accommodation",
      },
    },
    () => {
      return validation.data;
    }
  );
}
