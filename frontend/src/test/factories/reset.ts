/**
 * @fileoverview Centralized factory reset utilities.
 * Call resetAllFactories() in beforeEach() to ensure deterministic test data.
 */

import { resetFilterFactory } from "./filter-factory";
import { resetSearchFactory } from "./search-factory";
import { resetTripFactory } from "./trip-factory";
import { resetUserFactory } from "./user-factory";

/**
 * Resets all factory ID counters to their initial state.
 * Call this in beforeEach() to ensure consistent, deterministic IDs across test runs.
 *
 * @example
 * beforeEach(() => {
 *   resetAllFactories();
 * });
 */
export const resetAllFactories = (): void => {
  resetUserFactory();
  resetTripFactory();
  resetSearchFactory();
  resetFilterFactory();
};
