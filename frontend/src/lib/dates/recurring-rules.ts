/**
 * @fileoverview Recurring date generation utilities using date-fns v4.
 * Provides RecurringRule type and RecurringDateGenerator for creating
 * date sequences and parsing RRULE strings without external dependencies.
 */

import { DateUtils } from "./unified-date-utils";

/**
 * Supported recurrence frequencies for recurring events.
 *
 * @type RecurrenceFrequency
 */
export type RecurrenceFrequency = "daily" | "weekly" | "monthly" | "yearly";

/**
 * Configuration for recurring date rules.
 *
 * Defines how events repeat based on frequency, interval, and constraints.
 *
 * @interface RecurringRule
 */
export interface RecurringRule {
  /** How often the event repeats (daily, weekly, monthly, yearly). */
  frequency: RecurrenceFrequency;
  /** The interval between occurrences (e.g., 2 for every 2 weeks). */
  interval: number;
  /** Optional end date for the recurrence. */
  endDate?: Date;
  /** Optional maximum number of occurrences. */
  count?: number;
  /** Days of week for weekly recurrence (0=Sunday, 6=Saturday). */
  daysOfWeek?: number[];
  /** Day of month for monthly recurrence (1-31). */
  dayOfMonth?: number;
  /** Week of month for monthly recurrence (1-5). */
  weekOfMonth?: number;
}

/**
 * Utility class for generating recurring date sequences and parsing RRULE strings.
 *
 * Provides methods to create date occurrences based on recurrence rules and
 * convert between RecurringRule objects and RFC 5545 RRULE format strings.
 *
 * @class RecurringDateGenerator
 */
export class RecurringDateGenerator {
  /**
   * Generates a list of dates that match a recurring rule starting from a given date.
   *
   * @param startDate - The start date for generating occurrences.
   * @param rule - The recurrence rule to apply.
   * @param limit - Maximum number of occurrences to generate. Defaults to 50.
   * @returns Array of dates representing the occurrences.
   */
  static generateOccurrences(
    startDate: Date,
    rule: RecurringRule,
    limit: number = 50,
  ): Date[] {
    const occurrences: Date[] = [];
    let currentDate = new Date(startDate);
    let count = 0;

    while (count < limit) {
      if (rule.endDate && DateUtils.isAfter(currentDate, rule.endDate)) {
        break;
      }
      if (rule.count && count >= rule.count) {
        break;
      }

      if (this.matchesRule(currentDate, startDate, rule)) {
        occurrences.push(new Date(currentDate));
      }

      currentDate = this.nextOccurrence(currentDate, rule);
      count++;
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
    startDate: Date,
    rule: RecurringRule,
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
          weekOfMonth === rule.weekOfMonth &&
          rule.daysOfWeek.includes(date.getDay())
        );
      }
    }
    if (rule.frequency === "yearly") {
      if (rule.dayOfMonth && rule.daysOfWeek) {
        return (
          date.getDate() === rule.dayOfMonth &&
          rule.daysOfWeek.includes(date.getDay())
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
   * Supports common RRULE properties: FREQ, INTERVAL, UNTIL, COUNT, BYDAY, BYMONTHDAY.
   *
   * @param rrule - The RRULE string to parse.
   * @returns A RecurringRule object representing the parsed recurrence.
   */
  static parseRRule(rrule: string): RecurringRule {
    const rule: RecurringRule = {
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
      const dayMap: Record<string, number> = {
        SU: 0,
        MO: 1,
        TU: 2,
        WE: 3,
        TH: 4,
        FR: 5,
        SA: 6,
      };
      rule.daysOfWeek = byDayMatch[1]
        .split(",")
        .map((day) => dayMap[day] ?? 0)
        .filter((day) => day >= 0 && day <= 6);
    }

    const byMonthDayMatch = upper.match(/BYMONTHDAY=(\d+)/);
    if (byMonthDayMatch) {
      rule.dayOfMonth = Number.parseInt(byMonthDayMatch[1], 10);
    }

    return rule;
  }

  /**
   * Converts a RecurringRule object into an RFC 5545 RRULE string.
   *
   * @param rule - The recurrence rule to convert.
   * @returns A valid RRULE string representation.
   */
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
