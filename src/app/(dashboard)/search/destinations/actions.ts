/**
 * @fileoverview Server actions for destination search.
 */

"use server";

import {
  type DestinationSearchParams,
  destinationSearchParamsSchema,
} from "@schemas/search";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Server action to validate and trace destination search submissions.
 *
 * @param params - Destination search parameters from the client.
 * @returns Validated destination search parameters.
 * @throws Error if validation fails.
 */
export async function submitDestinationSearch(
  params: DestinationSearchParams
): Promise<DestinationSearchParams> {
  return await withTelemetrySpan(
    "search.destination.server.submit",
    {
      attributes: {
        query: params.query ?? "",
        searchType: "destination",
      },
    },
    () => {
      const validation = destinationSearchParamsSchema.safeParse(params);
      if (!validation.success) {
        throw new Error(
          `Invalid destination search params: ${validation.error.message}`
        );
      }
      return validation.data;
    }
  );
}
