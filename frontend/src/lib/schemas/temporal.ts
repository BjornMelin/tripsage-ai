/**
 * @fileoverview Canonical temporal schemas for date/time, duration, ranges, recurrence.
 */

import { z } from "zod";

/** Zod schema for date ranges with validation. */
export const dateRangeSchema = z
  .object({ endDate: z.date(), startDate: z.date() })
  .refine((data) => data.endDate >= data.startDate, {
    message: "End date must be on or after start date",
    path: ["endDate"],
  });
/** TypeScript type for date ranges. */
export type DateRange = z.infer<typeof dateRangeSchema>;

/** Zod schema for time ranges with validation. */
export const timeRangeSchema = z
  .object({
    endTime: z
      .string()
      .regex(/^([01]\d|2[0-3]):[0-5]\d$/, "Invalid time format (HH:MM)"),
    startTime: z
      .string()
      .regex(/^([01]\d|2[0-3]):[0-5]\d$/, "Invalid time format (HH:MM)"),
  })
  .refine((data) => data.endTime > data.startTime, {
    message: "End time must be after start time",
    path: ["endTime"],
  });
/** TypeScript type for time ranges. */
export type TimeRange = z.infer<typeof timeRangeSchema>;

/** Zod schema for time durations. */
export const durationSchema = z.object({
  days: z.number().int().min(0).default(0),
  hours: z.number().int().min(0).max(23).default(0),
  minutes: z.number().int().min(0).max(59).default(0),
});
/** TypeScript type for durations. */
export type Duration = z.infer<typeof durationSchema>;

/** Zod schema for datetime ranges with timezone support. */
export const dateTimeRangeSchema = z
  .object({
    endDatetime: z.date(),
    startDatetime: z.date(),
    timezone: z.string().optional(),
  })
  .refine((d) => d.endDatetime > d.startDatetime, {
    message: "End datetime must be after start datetime",
    path: ["endDatetime"],
  });
/** TypeScript type for datetime ranges. */
export type DateTimeRange = z.infer<typeof dateTimeRangeSchema>;

/** Zod schema for recurrence rules (RFC 5545 compliant). */
export const recurrenceRuleSchema = z
  .object({
    byDay: z.array(z.enum(["MO", "TU", "WE", "TH", "FR", "SA", "SU"])).optional(),
    byMonth: z.array(z.number().int().min(1).max(12)).optional(),
    byMonthDay: z.array(z.number().int().min(1).max(31)).optional(),
    count: z.number().int().min(1).optional(),
    frequency: z.enum(["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]),
    interval: z.number().int().min(1).default(1),
    until: z.date().optional(),
  })
  .refine((d) => !(d.count && d.until), {
    message: "Cannot specify both count and until",
    path: ["count"],
  });
/** TypeScript type for recurrence rules. */
export type RecurrenceRule = z.infer<typeof recurrenceRuleSchema>;

/** Zod schema for weekly business hours. */
export const businessHoursSchema = z.object({
  friday: timeRangeSchema.optional(),
  monday: timeRangeSchema.optional(),
  saturday: timeRangeSchema.optional(),
  sunday: timeRangeSchema.optional(),
  thursday: timeRangeSchema.optional(),
  timezone: z.string().optional(),
  tuesday: timeRangeSchema.optional(),
  wednesday: timeRangeSchema.optional(),
});
/** TypeScript type for business hours. */
export type BusinessHours = z.infer<typeof businessHoursSchema>;

/** Zod schema for availability information with capacity and restrictions. */
export const availabilitySchema = z
  .object({
    available: z.boolean(),
    capacity: z.number().int().min(0).optional(),
    fromDatetime: z.date().optional(),
    restrictions: z.array(z.string()).optional(),
    toDatetime: z.date().optional(),
  })
  .refine(
    (d) => (d.fromDatetime && d.toDatetime ? d.toDatetime > d.fromDatetime : true),
    {
      message: "toDatetime must be after fromDatetime",
      path: ["toDatetime"],
    }
  );
/** TypeScript type for availability. */
export type Availability = z.infer<typeof availabilitySchema>;
