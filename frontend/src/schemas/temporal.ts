/**
 * @fileoverview Temporal schemas for date, time, duration, and recurrence.
 */

import { z } from "zod";

/**
 * Date range schema with validation.
 */
export const dateRangeSchema = z
  .object({
    endDate: z.date(),
    startDate: z.date(),
  })
  .refine((data) => data.endDate >= data.startDate, {
    message: "End date must be on or after start date",
    path: ["endDate"],
  });

export type DateRange = z.infer<typeof dateRangeSchema>;

/**
 * Time range within a day schema.
 */
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

export type TimeRange = z.infer<typeof timeRangeSchema>;

/**
 * Duration schema with days, hours, minutes.
 */
export const durationSchema = z.object({
  days: z.number().int().min(0).default(0),
  hours: z.number().int().min(0).max(23).default(0),
  minutes: z.number().int().min(0).max(59).default(0),
});

export type Duration = z.infer<typeof durationSchema>;

/**
 * DateTime range with timezone awareness.
 */
export const dateTimeRangeSchema = z
  .object({
    endDatetime: z.date(),
    startDatetime: z.date(),
    timezone: z.string().optional(),
  })
  .refine((data) => data.endDatetime > data.startDatetime, {
    message: "End datetime must be after start datetime",
    path: ["endDatetime"],
  });

export type DateTimeRange = z.infer<typeof dateTimeRangeSchema>;

/**
 * Recurrence rule schema (RFC 5545 compatible).
 */
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
  .refine(
    (data) => {
      if (data.count && data.until) {
        return false;
      }
      return true;
    },
    {
      message: "Cannot specify both count and until",
      path: ["count"],
    }
  );

export type RecurrenceRule = z.infer<typeof recurrenceRuleSchema>;

/**
 * Business hours schema for a location or service.
 */
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

export type BusinessHours = z.infer<typeof businessHoursSchema>;

/**
 * Availability information schema.
 */
export const availabilitySchema = z
  .object({
    available: z.boolean(),
    capacity: z.number().int().min(0).optional(),
    fromDatetime: z.date().optional(),
    restrictions: z.array(z.string()).optional(),
    toDatetime: z.date().optional(),
  })
  .refine(
    (data) => {
      if (data.fromDatetime && data.toDatetime) {
        return data.toDatetime > data.fromDatetime;
      }
      return true;
    },
    {
      message: "toDatetime must be after fromDatetime",
      path: ["toDatetime"],
    }
  );

export type Availability = z.infer<typeof availabilitySchema>;
