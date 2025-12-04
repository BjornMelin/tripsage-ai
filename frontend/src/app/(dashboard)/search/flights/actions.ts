/**
 * @fileoverview Server Actions for flight search.
 */

"use server";

import { type FlightSearchParams, flightSearchParamsSchema } from "@schemas/search";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Server action to validate and trace flight search submissions.
 *
 * @param params - Flight search parameters from the client.
 * @returns Validated flight search parameters.
 * @throws Error if validation fails.
 */
export async function submitFlightSearch(
  params: FlightSearchParams
): Promise<FlightSearchParams> {
  return await withTelemetrySpan(
    "search.flight.server.submit",
    {
      attributes: {
        destination: params.destination ?? "",
        origin: params.origin ?? "",
        searchType: "flight",
      },
    },
    () => {
      const validation = flightSearchParamsSchema.safeParse(params);
      if (!validation.success) {
        throw new Error(`Invalid flight search params: ${validation.error.message}`);
      }
      const parsed = validation.data;

      const normalizedPassengers = parsed.passengers
        ? parsed.passengers
        : parsed.adults || parsed.children || parsed.infants
          ? {
              adults: parsed.adults ?? 1,
              children: parsed.children ?? 0,
              infants: parsed.infants ?? 0,
            }
          : undefined;

      return {
        ...parsed,
        cabinClass: parsed.cabinClass ?? "economy",
        passengers: normalizedPassengers,
      };
    }
  );
}
