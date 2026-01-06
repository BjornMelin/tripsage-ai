/**
 * @fileoverview Handler for accommodation search parameters.
 */

import {
  accommodationSearchParamsStoreSchema,
  type ValidatedAccommodationParams,
} from "@schemas/stores";
import { registerHandler } from "../registry";
import type { SearchParamsHandler } from "../types";

/** Default accommodation search parameters. */
const DEFAULTS: Partial<ValidatedAccommodationParams> = {
  adults: 1,
  amenities: [],
  children: 0,
  infants: 0,
  rooms: 1,
};

/**
 * Accommodation search parameters handler.
 * Manages default values, validation, and required field checking for accommodations.
 */
const accommodationHandler: SearchParamsHandler<ValidatedAccommodationParams> = {
  getDefaults() {
    return { ...DEFAULTS };
  },

  getSchema() {
    return accommodationSearchParamsStoreSchema;
  },

  hasRequiredParams(params) {
    return (
      typeof params.destination === "string" &&
      params.destination.trim().length > 0 &&
      typeof params.checkIn === "string" &&
      params.checkIn.trim().length > 0 &&
      typeof params.checkOut === "string" &&
      params.checkOut.trim().length > 0
    );
  },

  mergeParams(current, updates) {
    return { ...current, ...updates };
  },
  searchType: "accommodation",

  validate(params) {
    const result = accommodationSearchParamsStoreSchema.safeParse(params);
    if (result.success) {
      return { data: result.data, success: true };
    }
    return { error: result.error, success: false };
  },
};

// Register on module load
registerHandler(accommodationHandler);

export { accommodationHandler };
