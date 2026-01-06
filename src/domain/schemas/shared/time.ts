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

const parseIsoDateToLocalMidnight = (value: string): Date | null => {
  const [yearStr, monthStr, dayStr] = value.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  const day = Number(dayStr);

  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) {
    return null;
  }

  const date = new Date(year, month - 1, day);
  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return null;
  }

  return date;
};

const getTodayLocalMidnight = (): Date => {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
};

export const FUTURE_DATE_SCHEMA = ISO_DATE_STRING.superRefine((value, ctx) => {
  const parsed = parseIsoDateToLocalMidnight(value);
  if (!parsed) {
    ctx.addIssue({ code: "custom", error: "Please enter a valid date" });
    return;
  }

  if (parsed <= getTodayLocalMidnight()) {
    ctx.addIssue({ code: "custom", error: "Date must be in the future" });
  }
});

/**
 * @deprecated Use `FUTURE_DATE_SCHEMA`. This alias will be removed in a future release.
 */
export const FUTURE_DATE_STRING = FUTURE_DATE_SCHEMA;

export const DATE_RANGE_SCHEMA = z
  .strictObject({
    end: ISO_DATE_STRING,
    start: ISO_DATE_STRING,
  })
  .superRefine((value, ctx) => {
    const start = parseIsoDateToLocalMidnight(value.start);
    const end = parseIsoDateToLocalMidnight(value.end);

    if (!start) {
      ctx.addIssue({
        code: "custom",
        error: "Please enter a valid date",
        path: ["start"],
      });
    }

    if (!end) {
      ctx.addIssue({
        code: "custom",
        error: "Please enter a valid date",
        path: ["end"],
      });
    }

    if (!start || !end) return;

    if (end <= start) {
      ctx.addIssue({
        code: "custom",
        error: "End date must be after start date",
        path: ["end"],
      });
    }
  });

export type IsoDateString = z.infer<typeof ISO_DATE_STRING>;
export type IsoDateTimeString = z.infer<typeof ISO_DATETIME_STRING>;
export type Time24H = z.infer<typeof TIME_24H_SCHEMA>;
