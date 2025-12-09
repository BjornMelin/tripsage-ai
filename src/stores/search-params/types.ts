/**
 * @fileoverview Search params handler interface for strategy pattern.
 *
 * This module defines the handler interface that each search type implements
 * to provide type-specific parameter handling. The strategy pattern eliminates
 * switch statements and enables extensibility - adding a new search type only
 * requires creating a new handler file.
 */

import type { SearchParams } from "@schemas/search";
import type { SearchType } from "@schemas/stores";
import type { ZodError, z } from "zod";

/**
 * Handler interface for search type-specific parameter logic.
 *
 * Each search type implements this interface to handle its own:
 * - Default values
 * - Validation rules (via Zod schema)
 * - Required fields check
 * - Parameter merging
 *
 * @template T - The specific params type for this search type
 */
export interface SearchParamsHandler<T = unknown> {
  /** The search type this handler manages */
  readonly searchType: SearchType;

  /** Returns the Zod schema for validating parameters. */
  getSchema(): z.ZodType<T>;

  /** Returns default parameters for this search type. */
  getDefaults(): Partial<T>;

  /**
   * Validates parameters using the Zod schema.
   * Returns fully validated parameters on success, or a ZodError on failure.
   *
   * @param params - Partial parameters to validate
   * @returns Validation result with fully validated T on success, or ZodError
   */
  validate(
    params: Partial<T>
  ): { success: true; data: T } | { success: false; error: ZodError };

  /**
   * Checks if minimum required params are present for search.
   * This determines if a search can be executed.
   *
   * @param params - Partial parameters to check
   */
  hasRequiredParams(params: Partial<T>): boolean;

  /**
   * Merges updates into existing params with type-specific logic.
   *
   * @param current - Current parameters
   * @param updates - Updates to apply
   */
  mergeParams(current: Partial<T>, updates: Partial<T>): Partial<T>;

  /**
   * Converts fully validated params to the generic SearchParams union type.
   * Called with params that have successfully passed validate().
   * Optional method; implement only if SearchParams conversion is needed.
   */
  toSearchParams?(params: T): SearchParams;
}

/** Type helper for extracting the params type from a handler. */
export type HandlerParams<H> = H extends SearchParamsHandler<infer T> ? T : never;
