/**
 * @fileoverview Handler for destination search parameters.
 */

import type { DestinationSearchParams } from "@schemas/search";
import {
  destinationSearchParamsStoreSchema,
  type ValidatedDestinationParams,
} from "@schemas/stores";
import { registerHandler } from "../registry";
import type { SearchParamsHandler } from "../types";

/** Default destination search parameters. */
const DEFAULTS: Partial<ValidatedDestinationParams> = {
  limit: 10,
  query: "",
  types: ["locality", "country"],
};

/**
 * Destination search parameters handler.
 * Manages default values, validation, and required field checking for destinations.
 */
const destinationHandler: SearchParamsHandler<ValidatedDestinationParams> = {
  getDefaults() {
    return { ...DEFAULTS };
  },

  getSchema() {
    return destinationSearchParamsStoreSchema;
  },

  hasRequiredParams(params) {
    return typeof params.query === "string" && params.query.trim().length > 0;
  },

  mergeParams(current, updates) {
    return { ...current, ...updates };
  },
  searchType: "destination",

  toSearchParams(params) {
    return params as DestinationSearchParams;
  },

  validate(params) {
    const result = destinationSearchParamsStoreSchema.safeParse(params);
    if (result.success) {
      return { data: result.data, success: true };
    }
    const errorMessage = result.error.issues.map((issue) => issue.message).join(", ");
    return { error: errorMessage || "Validation failed", success: false };
  },
};

// Register on module load
registerHandler(destinationHandler);

export { destinationHandler };
