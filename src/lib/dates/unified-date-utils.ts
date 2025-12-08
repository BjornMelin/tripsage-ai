/**
 * @fileoverview Unified date utility helpers built on date-fns v4 with typed
 * inputs, validation, and formatting presets for Tripsage frontend modules.
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
 * Timezone configuration constants.
 *
 * @constant TIMEZONE_CONFIG
 */
export const TIMEZONE_CONFIG = {
  /** Default timezone for the application. */
  default: "UTC",
  /** User-specific timezone setting. */
  user: "UTC",
} as const;

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
 * Converts a Date or timestamp to a Date instance.
 *
 * @private
 * @param input - Date object or timestamp to convert.
 * @returns A Date instance.
 */
function toDate(input: Date | number): Date {
  if (input instanceof Date) {
    return input;
  }
  return new Date(input);
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

export function getTimezoneOffset(
  timeZone: string,
  date: Date | number = new Date()
): number {
  const targetDate = toDate(date);
  const dtf = new Intl.DateTimeFormat("en-US", {
    day: "2-digit",
    hour: "2-digit",
    hour12: false,
    minute: "2-digit",
    month: "2-digit",
    second: "2-digit",
    timeZone,
    year: "numeric",
  });
  const parts = dtf.formatToParts(targetDate);
  const partValues: Record<string, string> = {};
  for (const part of parts) {
    if (part.type !== "literal") {
      partValues[part.type] = part.value;
    }
  }
  const year = Number.parseInt(partValues.year ?? "0", 10);
  const month = Number.parseInt(partValues.month ?? "1", 10) - 1;
  const day = Number.parseInt(partValues.day ?? "1", 10);
  const hour = Number.parseInt(partValues.hour ?? "0", 10);
  const minute = Number.parseInt(partValues.minute ?? "0", 10);
  const second = Number.parseInt(partValues.second ?? "0", 10);
  const utcMillis = Date.UTC(year, month, day, hour, minute, second);
  const timestamp = DateUtils.toUnix(targetDate) * 1000;
  return (utcMillis - timestamp) / 60000;
}

export function utcToZonedTime(date: Date | number, timeZone: string): Date {
  const utcDate = toDate(date);
  const offset = getTimezoneOffset(timeZone, utcDate);
  return DateUtils.add(utcDate, offset, "minutes");
}

export function zonedTimeToUtc(date: Date | number, timeZone: string): Date {
  const zonedDate = toDate(date);
  const offset = getTimezoneOffset(timeZone, zonedDate);
  return DateUtils.add(zonedDate, -offset, "minutes");
}

// biome-ignore lint/complexity/noStaticOnlyClass: Shared utility API consumed as static class across app.
export class TimezoneUtils {
  static utcToUserTimezone(
    date: Date,
    userTimezone: string = TIMEZONE_CONFIG.user
  ): Date {
    return utcToZonedTime(date, userTimezone);
  }

  static userTimezoneToUtc(
    date: Date,
    userTimezone: string = TIMEZONE_CONFIG.user
  ): Date {
    return zonedTimeToUtc(date, userTimezone);
  }

  static getTimezoneOffset(timezone: string = TIMEZONE_CONFIG.user): number {
    return getTimezoneOffset(timezone);
  }

  static formatInUserTimezone(
    date: Date,
    pattern: string = DATE_FORMATS.display,
    userTimezone: string = TIMEZONE_CONFIG.user
  ): string {
    const userDate = TimezoneUtils.utcToUserTimezone(date, userTimezone);
    return format(userDate, pattern);
  }
}

// biome-ignore lint/complexity/noStaticOnlyClass: Shared utility API consumed as static class across app.
export class CalendarUtils {
  static generateCalendarMonth(date: Date): Date[][] {
    const start = DateUtils.startOf(date, "month");
    const end = DateUtils.endOf(date, "month");
    const startWeek = DateUtils.startOf(start, "week");
    const endWeek = DateUtils.endOf(end, "week");
    const weeks: Date[][] = [];
    let weekStart = startWeek;
    while (
      DateUtils.isBefore(weekStart, endWeek) ||
      DateUtils.isSame(weekStart, endWeek, "day")
    ) {
      const weekDays = DateUtils.eachDay(weekStart, DateUtils.endOf(weekStart, "week"));
      weeks.push(weekDays);
      weekStart = DateUtils.add(weekStart, 7, "days");
    }
    return weeks;
  }

  static isCurrentMonth(date: Date, referenceDate: Date): boolean {
    return DateUtils.isSame(date, referenceDate, "month");
  }

  static isToday(date: Date): boolean {
    return DateUtils.isSame(date, new Date(), "day");
  }

  static isPast(date: Date): boolean {
    return DateUtils.isBefore(date, new Date());
  }

  static isFuture(date: Date): boolean {
    return DateUtils.isAfter(date, new Date());
  }
}

export function createDateRange(start: Date, end: Date): DateRange {
  ensureValidDate(start);
  ensureValidDate(end);
  if (DateUtils.isAfter(start, end)) {
    throw new Error("Start date must be before end date");
  }
  return { end, start };
}
