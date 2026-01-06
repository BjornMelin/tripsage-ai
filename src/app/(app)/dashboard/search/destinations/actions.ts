/**
 * @fileoverview Server actions for destination search.
 */

"use server";

import "server-only";

import {
  type DestinationSearchParams,
  destinationSearchParamsSchema,
} from "@schemas/search";
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

const MAX_TELEMETRY_QUERY_LENGTH = 256;
const logger = createServerLogger("search.destinations.actions");

/**
 * Server action to validate and trace destination search submissions.
 *
 * @param params - Destination search parameters from the client.
 * @returns Validated destination search parameters.
 */
export async function submitDestinationSearch(
  params: DestinationSearchParams
): Promise<Result<DestinationSearchParams, ResultError>> {
  const validation = destinationSearchParamsSchema.safeParse(params);
  if (!validation.success) {
    logger.warn("Invalid destination search params", {
      issues: validation.error.issues,
      query: String(params.query ?? "").slice(0, MAX_TELEMETRY_QUERY_LENGTH),
    });
    return err({
      error: "invalid_request",
      fieldErrors: zodErrorToFieldErrors(validation.error),
      issues: validation.error.issues,
      reason: "Invalid destination search parameters",
    });
  }
  const validatedQuery = normalizePlacesTextQuery(validation.data.query).slice(
    0,
    MAX_TELEMETRY_QUERY_LENGTH
  );
  return await withTelemetrySpan(
    "search.destination.server.submit",
    {
      attributes: {
        query: validatedQuery,
        searchType: "destination",
      },
    },
    () => ok(validation.data)
  );
}
