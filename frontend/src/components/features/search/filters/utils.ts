/**
 * @fileoverview Filter utility functions and type guards.
 *
 * Provides type-safe guards for filter value inspection and
 * reusable helpers for filter components.
 */

import type { FilterValue } from "@schemas/stores";

/**
 * Type guard for range filter values.
 * Validates that value is an object with numeric min and max properties.
 */
export function isRangeObject(
  value: FilterValue
): value is { min: number; max: number } {
  return (
    typeof value === "object" &&
    value !== null &&
    "min" in value &&
    "max" in value &&
    typeof (value as { min: unknown }).min === "number" &&
    typeof (value as { max: unknown }).max === "number"
  );
}

/**
 * Type guard for single string filter values.
 */
export function isStringValue(value: FilterValue): value is string {
  return typeof value === "string";
}

/**
 * Type guard for string array filter values (multi-select).
 */
export function isStringArray(value: FilterValue): value is string[] {
  return Array.isArray(value) && value.every((entry) => typeof entry === "string");
}

/**
 * Type guard for numeric filter values.
 */
export function isNumberValue(value: FilterValue): value is number {
  return typeof value === "number";
}

/**
 * Type guard for boolean filter values.
 */
export function isBooleanValue(value: FilterValue): value is boolean {
  return typeof value === "boolean";
}
