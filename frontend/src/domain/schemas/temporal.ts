/**
 * @fileoverview Temporal schemas for date/time, duration, ranges, and recurrence.
 * Includes date ranges, time ranges, durations, recurrence rules, and business hours.
 */

import { z } from "zod";

// ===== CORE SCHEMAS =====
// Core business logic schemas for temporal data

/**
 * Zod schema for date ranges with validation.
 * Ensures end date is on or after start date.
 */
export const dateRangeSchema = z
  .object({ endDate: z.date(), startDate: z.date() })
  .refine((data) => data.endDate >= data.startDate, {
    error: "End date must be on or after start date",
    path: ["endDate"],
  });

/** TypeScript type for date ranges. */
export type DateRange = z.infer<typeof dateRangeSchema>;

/**
 * Zod schema for time ranges with validation.
 * Validates time format and ensures end time is after start time.
 */
export const timeRangeSchema = z
  .object({
    endTime: z
      .string()
      .regex(/^([01]\d|2[0-3]):[0-5]\d$/, { error: "Invalid time format (HH:MM)" }),
    startTime: z
      .string()
      .regex(/^([01]\d|2[0-3]):[0-5]\d$/, { error: "Invalid time format (HH:MM)" }),
  })
  .refine((data) => data.endTime > data.startTime, {
    error: "End time must be after start time",
    path: ["endTime"],
  });

/** TypeScript type for time ranges. */
export type TimeRange = z.infer<typeof timeRangeSchema>;

/**
 * Zod schema for time durations.
 * Validates duration components including days, hours, and minutes.
 */
export const durationSchema = z.object({
  days: z.number().int().min(0).default(0),
  hours: z.number().int().min(0).max(23).default(0),
  minutes: z.number().int().min(0).max(59).default(0),
});

/** TypeScript type for durations. */
export type Duration = z.infer<typeof durationSchema>;

/**
 * Zod schema for datetime ranges with timezone support.
 * Validates datetime range and ensures end datetime is after start datetime.
 */
export const dateTimeRangeSchema = z
  .object({
    endDatetime: z.date(),
    startDatetime: z.date(),
    timezone: z.string().optional(),
  })
  .refine((d) => d.endDatetime > d.startDatetime, {
    error: "End datetime must be after start datetime",
    path: ["endDatetime"],
  });

/** TypeScript type for datetime ranges. */
export type DateTimeRange = z.infer<typeof dateTimeRangeSchema>;

/**
 * Zod schema for recurrence rules (RFC 5545 compliant).
 * Validates recurrence configuration with business rules.
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
  .refine((d) => !(d.count && d.until), {
    error: "Cannot specify both count and until",
    path: ["count"],
  });

/** TypeScript type for recurrence rules. */
export type RecurrenceRule = z.infer<typeof recurrenceRuleSchema>;

/**
 * Zod schema for weekly business hours.
 * Defines business hours for each day of the week with optional timezone.
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

/** TypeScript type for business hours. */
export type BusinessHours = z.infer<typeof businessHoursSchema>;

/**
 * Zod schema for availability information with capacity and restrictions.
 * Validates availability data including datetime ranges and capacity limits.
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
    (d) => (d.fromDatetime && d.toDatetime ? d.toDatetime > d.fromDatetime : true),
    {
      error: "toDatetime must be after fromDatetime",
      path: ["toDatetime"],
    }
  );

/** TypeScript type for availability. */
export type Availability = z.infer<typeof availabilitySchema>;

/**
 * Zod schema for recurrence frequency (lowercase format for internal use).
 * Defines available recurrence frequencies.
 */
export const recurrenceFrequencySchema = z.enum([
  "daily",
  "weekly",
  "monthly",
  "yearly",
]);

/** TypeScript type for recurrence frequency. */
export type RecurrenceFrequency = z.infer<typeof recurrenceFrequencySchema>;

/**
 * Zod schema for recurring rule configuration (internal format with numeric day-of-week).
 * This format is used by RecurringDateGenerator and can be converted to/from RFC 5545.
 */
export const recurringRuleSchema = z
  .object({
    /** Optional maximum number of occurrences. */
    count: z.number().int().min(1).optional(),
    /** Day of month for monthly recurrence (1-31). */
    dayOfMonth: z.number().int().min(1).max(31).optional(),
    /** Days of week for weekly recurrence (0=Sunday, 6=Saturday). */
    daysOfWeek: z.array(z.number().int().min(0).max(6)).optional(),
    /** Optional end date for the recurrence. */
    endDate: z.date().optional(),
    /** How often the event repeats (daily, weekly, monthly, yearly). */
    frequency: recurrenceFrequencySchema,
    /** The interval between occurrences (e.g., 2 for every 2 weeks). */
    interval: z.number().int().min(1).default(1),
    /** Week of month for monthly recurrence (1-5). */
    weekOfMonth: z.number().int().min(1).max(5).optional(),
  })
  .refine((d) => !(d.count && d.endDate), {
    error: "Cannot specify both count and endDate",
    path: ["count"],
  });

/** TypeScript type for recurring rule. */
export type RecurringRule = z.infer<typeof recurringRuleSchema>;
