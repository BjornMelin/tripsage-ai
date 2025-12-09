/**
 * @fileoverview Server Actions for hotel/accommodation search.
 */

"use server";

import {
  type SearchAccommodationParams,
  searchAccommodationParamsSchema,
} from "@schemas/search";
import { withTelemetrySpan } from "@/lib/telemetry/span";

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
  return await withTelemetrySpan(
    "search.hotel.server.submit",
    {
      attributes: {
        destination: params.destination ?? "",
        searchType: "accommodation",
      },
    },
    () => {
      const validation = searchAccommodationParamsSchema.safeParse(params);
      if (!validation.success) {
        throw new Error(
          `Invalid accommodation search params: ${validation.error.message}`
        );
      }
      return validation.data;
    }
  );
}
