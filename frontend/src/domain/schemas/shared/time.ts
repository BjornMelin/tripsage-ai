/**
 * @fileoverview Shared time/date primitives for reuse across domains.
 */

import { z } from "zod";
import { primitiveSchemas } from "../registry";

export const ISO_DATE_STRING = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, { error: "Date must be in YYYY-MM-DD format" });

export const ISO_DATETIME_STRING = primitiveSchemas.isoDateTime;

export const FUTURE_DATE_STRING = ISO_DATE_STRING.refine(
  (date) => new Date(date) > new Date(),
  { error: "Date must be in the future" }
);

export const DATE_RANGE_SCHEMA = z
  .strictObject({
    start: ISO_DATE_STRING,
    end: ISO_DATE_STRING,
  })
  .refine((d) => new Date(d.end) > new Date(d.start), {
    error: "End date must be after start date",
  });

export type IsoDateString = z.infer<typeof ISO_DATE_STRING>;
export type IsoDateTimeString = z.infer<typeof ISO_DATETIME_STRING>;
