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
import {
  err,
  ok,
  type Result,
  type ResultError,
  zodErrorToFieldErrors,
} from "@/lib/result";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const MAX_TELEMETRY_DESTINATION_LENGTH = 256;

/**
 * Server action to validate and trace hotel search submissions.
 *
 * @param params - Accommodation search parameters from the client.
 * @returns Validated accommodation search parameters.
 */
export async function submitHotelSearch(
  params: SearchAccommodationParams
): Promise<Result<SearchAccommodationParams, ResultError>> {
  const validation = searchAccommodationParamsSchema.safeParse(params);
  if (!validation.success) {
    return err({
      error: "invalid_request",
      fieldErrors: zodErrorToFieldErrors(validation.error),
      issues: validation.error.issues,
      reason: "Invalid accommodation search parameters",
    });
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
    () => ok(validation.data)
  );
}
