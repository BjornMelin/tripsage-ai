/**
 * @fileoverview Server Actions for flight search.
 */

"use server";

import "server-only";

import { type FlightSearchParams, flightSearchParamsSchema } from "@schemas/search";
import { normalizePlacesTextQuery } from "@/lib/google/places-utils";
import {
  err,
  ok,
  type Result,
  type ResultError,
  zodErrorToFieldErrors,
} from "@/lib/result";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const MAX_TELEMETRY_LOCATION_LENGTH = 64;
const logger = createServerLogger("search.flights.actions");

/**
 * Server action to validate and trace flight search submissions.
 *
 * @param params - Flight search parameters from the client.
 * @returns Validated flight search parameters.
 */
export async function submitFlightSearch(
  params: FlightSearchParams
): Promise<Result<FlightSearchParams, ResultError>> {
  const validation = flightSearchParamsSchema.safeParse(params);
  if (!validation.success) {
    logger.warn("Invalid flight search params", {
      issues: validation.error.issues,
    });
    return err({
      error: "invalid_request",
      fieldErrors: zodErrorToFieldErrors(validation.error),
      issues: validation.error.issues,
      reason: "Invalid flight search parameters",
    });
  }
  const parsed = validation.data;
  const safeOrigin = parsed.origin
    ? normalizePlacesTextQuery(parsed.origin).slice(0, MAX_TELEMETRY_LOCATION_LENGTH)
    : "";
  const safeDestination = parsed.destination
    ? normalizePlacesTextQuery(parsed.destination).slice(
        0,
        MAX_TELEMETRY_LOCATION_LENGTH
      )
    : "";
  return await withTelemetrySpan(
    "search.flight.server.submit",
    {
      attributes: {
        destination: safeDestination,
        origin: safeOrigin,
        searchType: "flight",
      },
    },
    () => {
      let normalizedPassengers: FlightSearchParams["passengers"] | undefined;
      if (parsed.passengers) {
        normalizedPassengers = parsed.passengers;
      } else if (
        parsed.adults !== undefined ||
        parsed.children !== undefined ||
        parsed.infants !== undefined
      ) {
        normalizedPassengers = {
          adults: parsed.adults ?? 1,
          children: parsed.children ?? 0,
          infants: parsed.infants ?? 0,
        };
      } else {
        normalizedPassengers = undefined;
      }

      return ok({
        ...parsed,
        cabinClass: parsed.cabinClass ?? "economy",
        passengers: normalizedPassengers,
      });
    }
  );
}
