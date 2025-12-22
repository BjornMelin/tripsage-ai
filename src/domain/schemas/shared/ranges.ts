/**
 * @fileoverview Reusable range validation schemas for min/max constraints. Used for price ranges, duration ranges, and other numeric min/max validations.
 */

import { z } from "zod";

// ===== RANGE SCHEMAS =====

/**
 * Price range with min ≤ max validation.
 * Both min and max are optional; validation applies only when both are present.
 */
export const PRICE_RANGE_SCHEMA = z
  .strictObject({
    max: z.number().positive().optional(),
    min: z.number().nonnegative().optional(),
  })
  .refine((data) => !data.min || !data.max || data.min <= data.max, {
    error: "Min price must be less than or equal to max price",
    path: ["min"],
  });

/**
 * Duration range (in minutes or arbitrary units) with min ≤ max validation.
 * Both min and max are optional; validation applies only when both are present.
 */
export const DURATION_RANGE_SCHEMA = z
  .strictObject({
    max: z.number().positive().optional(),
    min: z.number().positive().optional(),
  })
  .refine((data) => !data.min || !data.max || data.min <= data.max, {
    error: "Min duration must be less than or equal to max duration",
    path: ["min"],
  });

/**
 * Generic numeric range with min ≤ max validation.
 * Both min and max are optional; validation applies only when both are present.
 */
export const NUMERIC_RANGE_SCHEMA = z
  .strictObject({
    max: z.number().optional(),
    min: z.number().optional(),
  })
  .refine((data) => !data.min || !data.max || data.min <= data.max, {
    error: "Min must be less than or equal to max",
    path: ["min"],
  });

// ===== TYPES =====

export type PriceRange = z.infer<typeof PRICE_RANGE_SCHEMA>;
export type DurationRange = z.infer<typeof DURATION_RANGE_SCHEMA>;
export type NumericRange = z.infer<typeof NUMERIC_RANGE_SCHEMA>;
