/**
 * @fileoverview Recurring date generation utilities using date-fns v4.
 * Provides RecurringRule type and RecurringDateGenerator for creating
 * date sequences and parsing RRULE strings without external dependencies.
 */

import type { RecurrenceFrequency, RecurringRule } from "@/lib/schemas/temporal";
import { recurringRuleSchema } from "@/lib/schemas/temporal";
import { DateUtils } from "./unified-date-utils";

// Re-export types from schemas
export type { RecurrenceFrequency, RecurringRule };

/**
 * Utility class for generating recurring date sequences and parsing RRULE strings.
 *
 * Provides methods to create date occurrences based on recurrence rules and
 * convert between RecurringRule objects and RFC 5545 RRULE format strings.
 *
 * @class RecurringDateGenerator
 */
// biome-ignore lint/complexity/noStaticOnlyClass: Shared via static methods.
export class RecurringDateGenerator {
  /**
   * Generates a list of dates that match a recurring rule starting from a given date.
   *
   * @param startDate - Anchor date for generating occurrences.
   * @param rule - Recurrence definition to apply.
   * @param limit - Maximum number of occurrences to emit (default 50).
   * @returns Array of generated occurrence dates.
   */
  static generateOccurrences(
    startDate: Date,
    rule: RecurringRule,
    limit: number = 50
  ): Date[] {
    if (rule.frequency === "weekly" && rule.daysOfWeek?.length) {
      return RecurringDateGenerator.generateWeeklyWithDays(startDate, rule, limit);
    }

    const occurrences: Date[] = [];
    let currentDate = new Date(startDate);
    let occurrenceCount = 0;

    while (occurrenceCount < limit) {
      if (rule.endDate && DateUtils.isAfter(currentDate, rule.endDate)) {
        break;
      }
      if (rule.count && occurrenceCount >= rule.count) {
        break;
      }

      if (RecurringDateGenerator.matchesRule(currentDate, startDate, rule)) {
        occurrences.push(new Date(currentDate));
        occurrenceCount++;
      }

      currentDate = RecurringDateGenerator.nextOccurrence(currentDate, rule);
    }

    return occurrences;
  }

  private static generateWeeklyWithDays(
    startDate: Date,
    rule: RecurringRule,
    limit: number
  ): Date[] {
    const occurrences: Date[] = [];
    const sortedDays = [...(rule.daysOfWeek ?? [])].sort();
    const startWeek = DateUtils.startOf(startDate, "week");
    let candidate = new Date(startDate);

    while (occurrences.length < limit) {
      if (rule.endDate && DateUtils.isAfter(candidate, rule.endDate)) {
        break;
      }

      const weekDiff = Math.abs(
        DateUtils.difference(DateUtils.startOf(candidate, "week"), startWeek, "weeks")
      );
      const withinInterval = weekDiff % rule.interval === 0;
      if (
        withinInterval &&
        sortedDays.includes(candidate.getDay()) &&
        (!rule.count || occurrences.length < rule.count)
      ) {
        occurrences.push(new Date(candidate));
        if (rule.count && occurrences.length >= rule.count) {
          break;
        }
      }

      candidate = DateUtils.add(candidate, 1, "days");
    }

    return occurrences;
  }

  /**
   * Checks if a given date matches the recurrence rule constraints.
   *
   * @private
   * @param date - The date to check.
   * @param startDate - The original start date for context.
   * @param rule - The recurrence rule to match against.
   * @returns True if the date matches the rule, false otherwise.
   */
  private static matchesRule(
    date: Date,
    _startDate: Date,
    rule: RecurringRule
  ): boolean {
    if (rule.frequency === "weekly" && rule.daysOfWeek) {
      return rule.daysOfWeek.includes(date.getDay());
    }
    if (rule.frequency === "monthly") {
      if (rule.dayOfMonth) {
        return date.getDate() === rule.dayOfMonth;
      }
      if (rule.weekOfMonth && rule.daysOfWeek) {
        const weekOfMonth = Math.ceil(date.getDate() / 7);
        return (
          weekOfMonth === rule.weekOfMonth && rule.daysOfWeek.includes(date.getDay())
        );
      }
    }
    if (rule.frequency === "yearly") {
      if (rule.dayOfMonth && rule.daysOfWeek) {
        return (
          date.getDate() === rule.dayOfMonth && rule.daysOfWeek.includes(date.getDay())
        );
      }
    }
    return true;
  }

  /**
   * Calculates the next occurrence date based on the recurrence rule.
   *
   * @private
   * @param date - The current date.
   * @param rule - The recurrence rule to apply.
   * @returns The next date that should be checked.
   */
  private static nextOccurrence(date: Date, rule: RecurringRule): Date {
    switch (rule.frequency) {
      case "daily":
        return DateUtils.add(date, rule.interval, "days");
      case "weekly":
        return DateUtils.add(date, rule.interval * 7, "days");
      case "monthly":
        return DateUtils.add(date, rule.interval, "months");
      case "yearly":
        return DateUtils.add(date, rule.interval, "years");
      default:
        throw new Error(`Unsupported frequency: ${rule.frequency}`);
    }
  }

  /**
   * Parses an RFC 5545 RRULE string into a RecurringRule object.
   *
   * @param rrule - RRULE string containing frequency definitions.
   * @returns Parsed recurrence configuration.
   */
  // biome-ignore lint/style/useNamingConvention: Preserve RR abbreviation for RFC terminology.
  static parseRRule(rrule: string): RecurringRule {
    const rule: Partial<RecurringRule> = {
      frequency: "daily",
      interval: 1,
    };

    const upper = rrule.toUpperCase();
    const freqMatch = upper.match(/FREQ=(DAILY|WEEKLY|MONTHLY|YEARLY)/);
    if (freqMatch) {
      rule.frequency = freqMatch[1].toLowerCase() as RecurrenceFrequency;
    }

    const intervalMatch = upper.match(/INTERVAL=(\d+)/);
    if (intervalMatch) {
      rule.interval = Number.parseInt(intervalMatch[1], 10);
    }

    const untilMatch = upper.match(/UNTIL=(\d{8}T?\d{6}Z?)/);
    if (untilMatch) {
      rule.endDate = DateUtils.parse(untilMatch[1]);
    }

    const countMatch = upper.match(/COUNT=(\d+)/);
    if (countMatch) {
      rule.count = Number.parseInt(countMatch[1], 10);
    }

    const byDayMatch = upper.match(/BYDAY=([A-Z,]+)/);
    if (byDayMatch) {
      const dayMap = new Map<string, number>([
        ["FR", 5],
        ["MO", 1],
        ["SA", 6],
        ["SU", 0],
        ["TH", 4],
        ["TU", 2],
        ["WE", 3],
      ]);
      rule.daysOfWeek = byDayMatch[1]
        .split(",")
        .map((day) => dayMap.get(day) ?? 0)
        .filter((day) => day >= 0 && day <= 6);
    }

    const byMonthDayMatch = upper.match(/BYMONTHDAY=(\d+)/);
    if (byMonthDayMatch) {
      rule.dayOfMonth = Number.parseInt(byMonthDayMatch[1], 10);
    }

    // Validate and parse the rule using Zod schema
    const parsed = recurringRuleSchema.safeParse(rule);
    if (!parsed.success) {
      throw new Error(`Invalid recurrence rule: ${parsed.error.message}`);
    }
    return parsed.data;
  }

  /**
   * Converts a RecurringRule object into an RFC 5545 RRULE string.
   *
   * @param rule - Recurrence configuration to encode.
   * @returns Valid RRULE string representation.
   */
  // biome-ignore lint/style/useNamingConvention: Preserve RR abbreviation for RFC terminology.
  static toRRule(rule: RecurringRule): string {
    const parts = [`FREQ=${rule.frequency.toUpperCase()}`];

    if (rule.interval !== 1) {
      parts.push(`INTERVAL=${rule.interval}`);
    }

    if (rule.endDate) {
      parts.push(`UNTIL=${DateUtils.formatForApi(rule.endDate).replace(/[-:]/g, "")}`);
    }

    if (rule.count) {
      parts.push(`COUNT=${rule.count}`);
    }

    if (rule.daysOfWeek && rule.daysOfWeek.length > 0) {
      const dayMap = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"];
      const days = rule.daysOfWeek.map((day) => dayMap[day]).join(",");
      parts.push(`BYDAY=${days}`);
    }

    if (rule.dayOfMonth) {
      parts.push(`BYMONTHDAY=${rule.dayOfMonth}`);
    }

    return parts.join(";");
  }
}
