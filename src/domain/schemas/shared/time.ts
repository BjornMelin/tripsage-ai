/**
 * @fileoverview Shared time/date primitives for reuse across domains.
 */

import { z } from "zod";
import { primitiveSchemas } from "../registry";

export const ISO_DATE_STRING = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, { error: "Date must be in YYYY-MM-DD format" });

export const ISO_DATETIME_STRING = primitiveSchemas.isoDateTime;

/** Time format HH:MM (24-hour format, 00:00 - 23:59). */
export const TIME_24H_SCHEMA = z
  .string()
  .regex(/^([01]\d|2[0-3]):[0-5]\d$/, { error: "Invalid time format (HH:MM)" });

export const FUTURE_DATE_STRING = ISO_DATE_STRING.refine(
  (date) => new Date(date) > new Date(),
  { error: "Date must be in the future" }
);

export const DATE_RANGE_SCHEMA = z
  .strictObject({
    end: ISO_DATE_STRING,
    start: ISO_DATE_STRING,
  })
  .refine((d) => new Date(d.end) > new Date(d.start), {
    error: "End date must be after start date",
  });

export type IsoDateString = z.infer<typeof ISO_DATE_STRING>;
export type IsoDateTimeString = z.infer<typeof ISO_DATETIME_STRING>;
export type Time24H = z.infer<typeof TIME_24H_SCHEMA>;
