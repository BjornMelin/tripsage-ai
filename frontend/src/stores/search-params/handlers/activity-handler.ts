/**
 * @fileoverview Handler for activity search parameters.
 */

import type { ActivitySearchParams } from "@schemas/search";
import {
  activitySearchParamsStoreSchema,
  type ValidatedActivityParams,
} from "@schemas/stores";
import { registerHandler } from "../registry";
import type { SearchParamsHandler } from "../types";

/** Default activity search parameters. */
const DEFAULTS: Partial<ValidatedActivityParams> = {
  adults: 1,
  children: 0,
  infants: 0,
};

/**
 * Activity search parameters handler.
 * Manages default values, validation, and required field checking for activities.
 */
const activityHandler: SearchParamsHandler<ValidatedActivityParams> = {
  getDefaults() {
    return { ...DEFAULTS };
  },

  getSchema() {
    return activitySearchParamsStoreSchema;
  },

  hasRequiredParams(params) {
    return typeof params.destination === "string" && params.destination.length > 0;
  },

  mergeParams(current, updates) {
    return { ...current, ...updates };
  },
  searchType: "activity",

  toSearchParams(params) {
    return params as ActivitySearchParams;
  },

  validate(params) {
    const result = activitySearchParamsStoreSchema.safeParse(params);
    if (result.success) {
      return { data: result.data, success: true };
    }
    const errorMessage = result.error.issues.map((issue) => issue.message).join(", ");
    return { error: errorMessage || "Validation failed", success: false };
  },
};

// Register on module load
registerHandler(activityHandler);

export { activityHandler };
