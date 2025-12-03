/**
 * @fileoverview Handler for flight search parameters.
 */

import type { FlightSearchParams } from "@schemas/search";
import {
  flightSearchParamsStoreSchema,
  type ValidatedFlightParams,
} from "@schemas/stores";
import { registerHandler } from "../registry";
import type { SearchParamsHandler } from "../types";

/** Default flight search parameters. */
const DEFAULTS: Partial<ValidatedFlightParams> = {
  adults: 1,
  cabinClass: "economy",
  children: 0,
  directOnly: false,
  excludedAirlines: [],
  infants: 0,
  preferredAirlines: [],
};

/**
 * Flight search parameters handler.
 * Manages default values, validation, and required field checking for flights.
 */
const flightHandler: SearchParamsHandler<ValidatedFlightParams> = {
  getDefaults() {
    return { ...DEFAULTS };
  },

  getSchema() {
    return flightSearchParamsStoreSchema;
  },

  hasRequiredParams(params) {
    return (
      typeof params.origin === "string" &&
      params.origin.length > 0 &&
      typeof params.destination === "string" &&
      params.destination.length > 0 &&
      typeof params.departureDate === "string" &&
      params.departureDate.length > 0
    );
  },

  mergeParams(current, updates) {
    return { ...current, ...updates };
  },
  searchType: "flight",

  toSearchParams(params) {
    return params as FlightSearchParams;
  },

  validate(params) {
    const result = flightSearchParamsStoreSchema.safeParse(params);
    if (result.success) {
      return { data: result.data, success: true };
    }
    const errorMessage = result.error.issues.map((issue) => issue.message).join(", ");
    return { error: errorMessage || "Validation failed", success: false };
  },
};

// Register on module load
registerHandler(flightHandler);

export { flightHandler };
