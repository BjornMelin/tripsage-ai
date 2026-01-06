/**
 * @fileoverview Validation helpers for the search filters store.
 */

import type { FilterValue, ValidatedFilterOption } from "@schemas/stores";

/** Validate a range filter value against min/max constraints. */
export function validateRangeValue(
  value: FilterValue,
  config: ValidatedFilterOption
): { valid: boolean; error?: string } {
  if (typeof value !== "object" || value === null) {
    return { error: "Range value must be an object with min/max", valid: false };
  }

  const rangeValue = value as { min?: unknown; max?: unknown };
  const validation = config.validation;

  const min = rangeValue.min;
  const max = rangeValue.max;

  if (min !== undefined && typeof min !== "number") {
    return { error: "Minimum value must be a number", valid: false };
  }

  if (max !== undefined && typeof max !== "number") {
    return { error: "Maximum value must be a number", valid: false };
  }

  if (min !== undefined && max !== undefined && min > max) {
    return { error: "Minimum value cannot exceed maximum", valid: false };
  }

  if (!validation) {
    return { valid: true };
  }

  if (min !== undefined && validation.min !== undefined && min < validation.min) {
    return { error: `Minimum value must be at least ${validation.min}`, valid: false };
  }

  if (max !== undefined && validation.max !== undefined && max > validation.max) {
    return { error: `Maximum value must be at most ${validation.max}`, valid: false };
  }

  return { valid: true };
}
