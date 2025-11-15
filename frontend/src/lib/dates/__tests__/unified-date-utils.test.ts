/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DATE_FORMATS, DateUtils, TIMEZONE_CONFIG } from "../unified-date-utils";

describe("DateUtils", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2024-01-15T10:30:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("parse", () => {
    it("should parse ISO date string", () => {
      const result = DateUtils.parse("2024-01-15T10:30:00Z");
      expect(result).toBeInstanceOf(Date);
      expect(result.getFullYear()).toBe(2024);
      expect(result.getMonth()).toBe(0);
      expect(result.getDate()).toBe(15);
    });

    it("should parse date string with pattern", () => {
      const result = DateUtils.parse("15/01/2024", "dd/MM/yyyy");
      expect(result).toBeInstanceOf(Date);
      expect(result.getFullYear()).toBe(2024);
      expect(result.getMonth()).toBe(0);
      expect(result.getDate()).toBe(15);
    });

    it("should throw error for empty string", () => {
      expect(() => DateUtils.parse("")).toThrow("Empty date string");
    });

    it("should throw error for invalid date", () => {
      expect(() => DateUtils.parse("invalid-date")).toThrow();
    });
  });

  describe("isValid", () => {
    it("should return true for valid date", () => {
      const validDate = new Date("2024-01-15T10:30:00Z");
      expect(DateUtils.isValid(validDate)).toBe(true);
    });

    it("should return false for invalid date", () => {
      const invalidDate = new Date("invalid");
      expect(DateUtils.isValid(invalidDate)).toBe(false);
    });
  });

  describe("format", () => {
    it("should format date with default pattern", () => {
      const date = new Date("2024-01-15T10:30:00Z");
      const result = DateUtils.format(date);
      expect(result).toMatch(/Jan 15, 2024 at \d+:\d+ [AP]M/);
    });

    it("should format date with custom pattern", () => {
      const date = new Date("2024-01-15T10:30:00Z");
      const result = DateUtils.format(date, "yyyy-MM-dd");
      expect(result).toBe("2024-01-15");
    });

    it("should throw error for invalid date", () => {
      const invalidDate = new Date("invalid");
      expect(() => DateUtils.format(invalidDate)).toThrow("Invalid date instance");
    });
  });

  describe("formatDisplay", () => {
    it("should format date for display", () => {
      const date = new Date("2024-01-15T10:30:00Z");
      const result = DateUtils.formatDisplay(date);
      expect(result).toMatch(/Jan 15, 2024 at \d+:\d+ [AP]M/);
    });
  });

  describe("formatForInput", () => {
    it("should format date for input fields", () => {
      const date = new Date("2024-01-15T10:30:00Z");
      const result = DateUtils.formatForInput(date);
      expect(result).toMatch(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/);
    });
  });

  describe("formatForApi", () => {
    it("should format date for API consumption", () => {
      const date = new Date("2024-01-15T10:30:00Z");
      const result = DateUtils.formatForApi(date);
      expect(result).toBe(date.toISOString());
    });

    it("should throw error for invalid date", () => {
      const invalidDate = new Date("invalid");
      expect(() => DateUtils.formatForApi(invalidDate)).toThrow(
        "Invalid date instance"
      );
    });
  });

  describe("add", () => {
    const baseDate = new Date("2024-01-15T10:30:00Z");

    it("should add minutes", () => {
      const result = DateUtils.add(baseDate, 30, "minutes");
      expect(result.getMinutes()).toBe(0);
    });

    it("should add hours", () => {
      const result = DateUtils.add(baseDate, 2, "hours");
      expect(result.getUTCHours()).toBe(12);
    });

    it("should add days", () => {
      const result = DateUtils.add(baseDate, 5, "days");
      expect(result.getDate()).toBe(20);
    });

    it("should add weeks", () => {
      const result = DateUtils.add(baseDate, 1, "weeks");
      expect(result.getDate()).toBe(22);
    });

    it("should add months", () => {
      const result = DateUtils.add(baseDate, 1, "months");
      expect(result.getMonth()).toBe(1);
      expect(result.getDate()).toBe(15);
    });

    it("should add years", () => {
      const result = DateUtils.add(baseDate, 1, "years");
      expect(result.getFullYear()).toBe(2025);
    });

    it("should handle negative amounts", () => {
      const result = DateUtils.add(baseDate, -5, "days");
      expect(result.getDate()).toBe(10);
    });
  });

  describe("difference", () => {
    const startDate = new Date("2024-01-15T10:30:00Z");
    const endDate = new Date("2024-01-20T15:45:00Z");

    it("should calculate difference in days", () => {
      const result = DateUtils.difference(endDate, startDate, "days");
      expect(result).toBe(5);
    });

    it("should calculate difference in weeks", () => {
      const result = DateUtils.difference(endDate, startDate, "weeks");
      expect(result).toBe(0); // Less than 1 week
    });

    it("should calculate difference in months", () => {
      const laterDate = new Date("2024-02-15T10:30:00Z");
      const result = DateUtils.difference(laterDate, startDate, "months");
      expect(result).toBe(1);
    });

    it("should calculate difference in years", () => {
      const laterDate = new Date("2025-01-15T10:30:00Z");
      const result = DateUtils.difference(laterDate, startDate, "years");
      expect(result).toBe(1);
    });

    it("should handle negative differences", () => {
      const result = DateUtils.difference(startDate, endDate, "days");
      expect(result).toBe(-5);
    });
  });

  describe("isBefore", () => {
    const earlierDate = new Date("2024-01-15T10:30:00Z");
    const laterDate = new Date("2024-01-20T15:45:00Z");

    it("should return true when first date is before second", () => {
      expect(DateUtils.isBefore(earlierDate, laterDate)).toBe(true);
    });

    it("should return false when first date is after second", () => {
      expect(DateUtils.isBefore(laterDate, earlierDate)).toBe(false);
    });

    it("should return false for same dates", () => {
      expect(DateUtils.isBefore(earlierDate, earlierDate)).toBe(false);
    });
  });

  describe("isAfter", () => {
    const earlierDate = new Date("2024-01-15T10:30:00Z");
    const laterDate = new Date("2024-01-20T15:45:00Z");

    it("should return true when first date is after second", () => {
      expect(DateUtils.isAfter(laterDate, earlierDate)).toBe(true);
    });

    it("should return false when first date is before second", () => {
      expect(DateUtils.isAfter(earlierDate, laterDate)).toBe(false);
    });

    it("should return false for same dates", () => {
      expect(DateUtils.isAfter(earlierDate, earlierDate)).toBe(false);
    });
  });

  describe("isSame", () => {
    const date1 = new Date("2024-01-15T10:30:00Z");
    const date2 = new Date("2024-01-15T15:45:00Z");
    const date3 = new Date("2024-01-16T10:30:00Z");

    it("should return true for same day", () => {
      expect(DateUtils.isSame(date1, date2, "day")).toBe(true);
    });

    it("should return false for different days", () => {
      expect(DateUtils.isSame(date1, date3, "day")).toBe(false);
    });

    it("should return true for same month", () => {
      expect(DateUtils.isSame(date1, date3, "month")).toBe(true);
    });

    it("should return true for same year", () => {
      const date2024 = new Date("2024-06-15T10:30:00Z");
      expect(DateUtils.isSame(date1, date2024, "year")).toBe(true);
    });
  });

  describe("startOf", () => {
    const date = new Date("2024-01-15T15:30:45Z");

    it("should return start of day", () => {
      const result = DateUtils.startOf(date, "day");
      expect(result.getHours()).toBe(0);
      expect(result.getMinutes()).toBe(0);
      expect(result.getSeconds()).toBe(0);
      expect(result.getMilliseconds()).toBe(0);
    });

    it("should return start of week", () => {
      const result = DateUtils.startOf(date, "week");
      expect(result.getDay()).toBe(1); // Monday
    });

    it("should return start of month", () => {
      const result = DateUtils.startOf(date, "month");
      expect(result.getDate()).toBe(1);
      expect(result.getHours()).toBe(0);
    });

    it("should return start of year", () => {
      const result = DateUtils.startOf(date, "year");
      expect(result.getMonth()).toBe(0);
      expect(result.getDate()).toBe(1);
    });
  });

  describe("endOf", () => {
    const date = new Date("2024-01-15T15:30:45Z");

    it("should return end of day", () => {
      const result = DateUtils.endOf(date, "day");
      expect(result.getHours()).toBe(23);
      expect(result.getMinutes()).toBe(59);
      expect(result.getSeconds()).toBe(59);
    });

    it("should return end of week", () => {
      const result = DateUtils.endOf(date, "week");
      expect(result.getDay()).toBe(0); // Sunday
    });

    it("should return end of month", () => {
      const result = DateUtils.endOf(date, "month");
      expect(result.getMonth()).toBe(0);
      expect(result.getDate()).toBe(31); // January has 31 days
    });

    it("should return end of year", () => {
      const result = DateUtils.endOf(date, "year");
      expect(result.getMonth()).toBe(11);
      expect(result.getDate()).toBe(31);
    });
  });

  describe("toUnix", () => {
    it("should convert date to Unix timestamp", () => {
      const date = new Date("2024-01-15T10:30:00Z");
      const result = DateUtils.toUnix(date);
      expect(typeof result).toBe("number");
      expect(result).toBeGreaterThan(0);
    });

    it("should throw error for invalid date", () => {
      const invalidDate = new Date("invalid");
      expect(() => DateUtils.toUnix(invalidDate)).toThrow("Invalid date instance");
    });
  });

  describe("compare", () => {
    const earlierDate = new Date("2024-01-15T10:30:00Z");
    const laterDate = new Date("2024-01-20T15:45:00Z");

    it("should return negative number when first date is before second", () => {
      const result = DateUtils.compare(earlierDate, laterDate);
      expect(result).toBeLessThan(0);
    });

    it("should return positive number when first date is after second", () => {
      const result = DateUtils.compare(laterDate, earlierDate);
      expect(result).toBeGreaterThan(0);
    });

    it("should return 0 for same dates", () => {
      expect(DateUtils.compare(earlierDate, earlierDate)).toBe(0);
    });
  });

  describe("min", () => {
    const date1 = new Date("2024-01-15T10:30:00Z");
    const date2 = new Date("2024-01-10T15:45:00Z");
    const date3 = new Date("2024-01-20T08:00:00Z");

    it("should return earliest date", () => {
      const result = DateUtils.min(date1, date2, date3);
      expect(result).toEqual(date2);
    });

    it("should handle single date", () => {
      const result = DateUtils.min(date1);
      expect(result).toEqual(date1);
    });
  });

  describe("max", () => {
    const date1 = new Date("2024-01-15T10:30:00Z");
    const date2 = new Date("2024-01-10T15:45:00Z");
    const date3 = new Date("2024-01-20T08:00:00Z");

    it("should return latest date", () => {
      const result = DateUtils.max(date1, date2, date3);
      expect(result).toEqual(date3);
    });

    it("should handle single date", () => {
      const result = DateUtils.max(date1);
      expect(result).toEqual(date1);
    });
  });
});

describe("Constants", () => {
  describe("DATE_FORMATS", () => {
    it("should have all required format patterns", () => {
      expect(DATE_FORMATS.api).toBeDefined();
      expect(DATE_FORMATS.display).toBeDefined();
      expect(DATE_FORMATS.input).toBeDefined();
      expect(DATE_FORMATS.iso).toBeDefined();
      expect(DATE_FORMATS.long).toBeDefined();
      expect(DATE_FORMATS.short).toBeDefined();
    });

    it("should have valid format strings", () => {
      Object.values(DATE_FORMATS).forEach((format) => {
        expect(typeof format).toBe("string");
        expect(format.length).toBeGreaterThan(0);
      });
    });
  });

  describe("TIMEZONE_CONFIG", () => {
    it("should have timezone configuration", () => {
      expect(TIMEZONE_CONFIG.default).toBeDefined();
      expect(TIMEZONE_CONFIG.user).toBeDefined();
      expect(typeof TIMEZONE_CONFIG.default).toBe("string");
      expect(typeof TIMEZONE_CONFIG.user).toBe("string");
    });
  });
});

describe("DateRange Type", () => {
  it("should accept valid date range", () => {
    const dateRange = {
      end: new Date("2024-01-07"),
      start: new Date("2024-01-01"),
    };

    expect(dateRange.start).toBeInstanceOf(Date);
    expect(dateRange.end).toBeInstanceOf(Date);
  });
});
