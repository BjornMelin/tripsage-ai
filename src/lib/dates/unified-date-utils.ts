/**
 * @fileoverview Unified date utility helpers built on date-fns v4 with typed inputs, validation, and formatting presets for Tripsage frontend modules.
 */

import {
  addDays,
  addHours,
  addMinutes,
  addMonths,
  addWeeks,
  addYears,
  differenceInDays,
  differenceInMonths,
  differenceInWeeks,
  differenceInYears,
  eachDayOfInterval,
  eachMonthOfInterval,
  eachWeekOfInterval,
  endOfDay,
  endOfMonth,
  endOfWeek,
  endOfYear,
  format,
  getUnixTime,
  isAfter as isAfterFn,
  isBefore as isBeforeFn,
  isSameDay,
  isSameMonth,
  isSameWeek,
  isSameYear,
  isValid as isValidFn,
  max as maxFn,
  min as minFn,
  parse,
  parseISO,
  startOfDay,
  startOfMonth,
  startOfWeek,
  startOfYear,
  subDays,
  subMonths,
  subWeeks,
  subYears,
} from "date-fns";

/**
 * Predefined date format patterns used throughout the application.
 *
 * @constant DATE_FORMATS
 */
export const DATE_FORMATS = {
  /** Format for API responses with timezone. */
  api: "yyyy-MM-dd'T'HH:mm:ss.SSSxxx",
  /** Default display format for UI. */
  display: "MMM d, yyyy 'at' h:mm a",
  /** Format for date input fields. */
  input: "yyyy-MM-dd'T'HH:mm",
  /** ISO 8601 format with timezone. */
  iso: "yyyy-MM-dd'T'HH:mm:ss.SSSxxx",
  /** Long format with seconds. */
  long: "MMMM d, yyyy 'at' h:mm:ss a",
  /** Short date-only format. */
  short: "MMM d, yyyy",
} as const;

/**
 * Represents a date range with start and end dates.
 * Uses schema format (startDate/endDate) for consistency.
 */
export type DateRange = {
  /** Start date of the range (inclusive). */
  start: Date;
  /** End date of the range (inclusive). */
  end: Date;
};

/**
 * Validates that a date instance is valid.
 *
 * @private
 * @param date - The date to validate.
 * @throws Error if the date is invalid.
 */
function ensureValidDate(date: Date): void {
  if (!isValidFn(date)) {
    throw new Error("Invalid date instance");
  }
}

/**
 * Unified date utility class providing consistent date operations.
 *
 * Wraps date-fns v4 functionality with a stable API and error handling.
 * All methods validate inputs and provide consistent behavior across the application.
 *
 * @class DateUtils
 */
// biome-ignore lint/complexity/noStaticOnlyClass: Shared utility API consumed as static class across app.
export class DateUtils {
  /**
   * Parses a date string into a Date object.
   *
   * @param dateString - The date string to parse.
   * @param pattern - Optional pattern for parsing. Defaults to ISO parsing.
   * @returns A parsed Date object.
   * @throws Error if the date string is empty or invalid.
   */
  static parse(dateString: string, pattern?: string): Date {
    if (!dateString) {
      throw new Error("Empty date string");
    }
    const parsed = pattern
      ? parse(dateString, pattern, new Date())
      : parseISO(dateString);
    ensureValidDate(parsed);
    return parsed;
  }

  /**
   * Checks if a date is valid.
   *
   * @param date - The date to validate.
   * @returns True if the date is valid, false otherwise.
   */
  static isValid(date: Date): boolean {
    return isValidFn(date);
  }

  /**
   * Formats a date using the specified pattern.
   *
   * @param date - The date to format.
   * @param pattern - The format pattern to use. Defaults to display format.
   * @returns The formatted date string.
   */
  static format(date: Date, pattern: string = DATE_FORMATS.display): string {
    ensureValidDate(date);
    return format(date, pattern);
  }

  /**
   * Formats a date for display in the UI.
   *
   * @param date - The date to format.
   * @returns The formatted display string.
   */
  static formatDisplay(date: Date): string {
    return DateUtils.format(date, DATE_FORMATS.display);
  }

  /**
   * Formats a date for input fields.
   *
   * @param date - The date to format.
   * @returns The formatted input string.
   */
  static formatForInput(date: Date): string {
    return DateUtils.format(date, DATE_FORMATS.input);
  }

  /**
   * Formats a date for API consumption (ISO format).
   *
   * @param date - The date to format.
   * @returns The ISO formatted date string.
   */
  static formatForApi(date: Date): string {
    ensureValidDate(date);
    return date.toISOString();
  }

  /**
   * Adds a specified amount of time to a date.
   *
   * @param date - The base date.
   * @param amount - The amount to add.
   * @param unit - The time unit to add.
   * @returns The new date with the added time.
   */
  static add(
    date: Date,
    amount: number,
    unit: "minutes" | "hours" | "days" | "weeks" | "months" | "years"
  ): Date {
    switch (unit) {
      case "minutes":
        return addMinutes(date, amount);
      case "hours":
        return addHours(date, amount);
      case "days":
        return addDays(date, amount);
      case "weeks":
        return addWeeks(date, amount);
      case "months":
        return addMonths(date, amount);
      case "years":
        return addYears(date, amount);
      default:
        throw new Error(`Unsupported unit: ${unit}`);
    }
  }

  static subtract(
    date: Date,
    amount: number,
    unit: "days" | "weeks" | "months" | "years"
  ): Date {
    switch (unit) {
      case "days":
        return subDays(date, amount);
      case "weeks":
        return subWeeks(date, amount);
      case "months":
        return subMonths(date, amount);
      case "years":
        return subYears(date, amount);
      default:
        throw new Error(`Unsupported unit: ${unit}`);
    }
  }

  static startOf(date: Date, unit: "day" | "week" | "month" | "year"): Date {
    switch (unit) {
      case "day":
        return startOfDay(date);
      case "week":
        return startOfWeek(date, { weekStartsOn: 1 });
      case "month":
        return startOfMonth(date);
      case "year":
        return startOfYear(date);
      default:
        throw new Error(`Unsupported unit: ${unit}`);
    }
  }

  static endOf(date: Date, unit: "day" | "week" | "month" | "year"): Date {
    switch (unit) {
      case "day":
        return endOfDay(date);
      case "week":
        return endOfWeek(date, { weekStartsOn: 1 });
      case "month":
        return endOfMonth(date);
      case "year":
        return endOfYear(date);
      default:
        throw new Error(`Unsupported unit: ${unit}`);
    }
  }

  static isAfter(date: Date, compareDate: Date): boolean {
    return isAfterFn(date, compareDate);
  }

  static isBefore(date: Date, compareDate: Date): boolean {
    return isBeforeFn(date, compareDate);
  }

  static isSame(
    date: Date,
    compareDate: Date,
    unit: "day" | "week" | "month" | "year"
  ): boolean {
    switch (unit) {
      case "day":
        return isSameDay(date, compareDate);
      case "week":
        return isSameWeek(date, compareDate);
      case "month":
        return isSameMonth(date, compareDate);
      case "year":
        return isSameYear(date, compareDate);
      default:
        throw new Error(`Unsupported unit: ${unit}`);
    }
  }

  static difference(
    date1: Date,
    date2: Date,
    unit: "days" | "weeks" | "months" | "years"
  ): number {
    switch (unit) {
      case "days":
        return differenceInDays(date1, date2);
      case "weeks":
        return differenceInWeeks(date1, date2);
      case "months":
        return differenceInMonths(date1, date2);
      case "years":
        return differenceInYears(date1, date2);
      default:
        throw new Error(`Unsupported unit: ${unit}`);
    }
  }

  static min(...dates: Date[]): Date {
    return minFn(dates);
  }

  static max(...dates: Date[]): Date {
    return maxFn(dates);
  }

  static eachDay(startDate: Date, endDate: Date): Date[] {
    return eachDayOfInterval({ end: endDate, start: startDate });
  }

  static eachWeek(startDate: Date, endDate: Date): Date[] {
    return eachWeekOfInterval({ end: endDate, start: startDate });
  }

  static eachMonth(startDate: Date, endDate: Date): Date[] {
    return eachMonthOfInterval({ end: endDate, start: startDate });
  }

  static toUnix(date: Date): number {
    ensureValidDate(date);
    return getUnixTime(date);
  }

  static compare(date1: Date, date2: Date): number {
    ensureValidDate(date1);
    ensureValidDate(date2);
    return date1.valueOf() - date2.valueOf();
  }
}
