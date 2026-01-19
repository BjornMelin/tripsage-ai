/** @vitest-environment node */

import {
  DATE_RANGE_SCHEMA,
  FUTURE_DATE_SCHEMA,
  ISO_DATE_STRING,
  ISO_DATETIME_STRING,
  type IsoDateString,
  TIME_24H_SCHEMA,
  type Time24H,
} from "@schemas/shared/time";
import { describe, expect, it } from "vitest";

describe("ISO_DATE_STRING", () => {
  describe("valid dates", () => {
    it.concurrent("should accept valid date YYYY-MM-DD", () => {
      const result = ISO_DATE_STRING.safeParse("2024-01-15");
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toBe("2024-01-15");
      }
    });

    it.concurrent("should accept date at start of year", () => {
      const result = ISO_DATE_STRING.safeParse("2024-01-01");
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept date at end of year", () => {
      const result = ISO_DATE_STRING.safeParse("2024-12-31");
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept leap year date", () => {
      const result = ISO_DATE_STRING.safeParse("2024-02-29");
      expect(result.success).toBe(true);
    });
  });

  describe("invalid dates", () => {
    it.concurrent("should reject date with slashes", () => {
      const result = ISO_DATE_STRING.safeParse("2024/01/15");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject date without leading zeros", () => {
      const result = ISO_DATE_STRING.safeParse("2024-1-15");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject date with time", () => {
      const result = ISO_DATE_STRING.safeParse("2024-01-15T10:00:00");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject ISO datetime format", () => {
      const result = ISO_DATE_STRING.safeParse("2024-01-15T10:00:00Z");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject empty string", () => {
      const result = ISO_DATE_STRING.safeParse("");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject random string", () => {
      const result = ISO_DATE_STRING.safeParse("not-a-date");
      expect(result.success).toBe(false);
    });
  });

  describe("type inference", () => {
    it.concurrent("should export IsoDateString type", () => {
      const date: IsoDateString = "2024-01-15";
      expect(typeof date).toBe("string");
    });
  });
});

describe("TIME_24H_SCHEMA", () => {
  describe("valid times", () => {
    it.concurrent("should accept midnight 00:00", () => {
      const result = TIME_24H_SCHEMA.safeParse("00:00");
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept 23:59 (end of day)", () => {
      const result = TIME_24H_SCHEMA.safeParse("23:59");
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept noon 12:00", () => {
      const result = TIME_24H_SCHEMA.safeParse("12:00");
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept morning time 09:30", () => {
      const result = TIME_24H_SCHEMA.safeParse("09:30");
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept evening time 18:45", () => {
      const result = TIME_24H_SCHEMA.safeParse("18:45");
      expect(result.success).toBe(true);
    });
  });

  describe("invalid times", () => {
    it.concurrent("should reject 24:00 (invalid hour)", () => {
      const result = TIME_24H_SCHEMA.safeParse("24:00");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject 25:00 (invalid hour)", () => {
      const result = TIME_24H_SCHEMA.safeParse("25:00");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject 12:60 (invalid minute)", () => {
      const result = TIME_24H_SCHEMA.safeParse("12:60");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject time without leading zero", () => {
      const result = TIME_24H_SCHEMA.safeParse("9:30");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject 12-hour format with AM/PM", () => {
      const result = TIME_24H_SCHEMA.safeParse("9:30 AM");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject time with seconds", () => {
      const result = TIME_24H_SCHEMA.safeParse("12:00:00");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject empty string", () => {
      const result = TIME_24H_SCHEMA.safeParse("");
      expect(result.success).toBe(false);
    });
  });

  describe("type inference", () => {
    it.concurrent("should export Time24H type", () => {
      const time: Time24H = "14:30";
      expect(typeof time).toBe("string");
    });
  });
});

describe("ISO_DATETIME_STRING", () => {
  describe("valid datetimes", () => {
    it.concurrent("should accept ISO datetime with Z (UTC)", () => {
      const result = ISO_DATETIME_STRING.safeParse("2024-01-15T10:30:00Z");
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept ISO datetime with milliseconds and Z", () => {
      const result = ISO_DATETIME_STRING.safeParse("2024-01-15T10:30:00.123Z");
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept timezone offsets", () => {
      const result = ISO_DATETIME_STRING.safeParse("2024-01-15T10:30:00+05:00");
      expect(result.success).toBe(true);
    });
  });

  describe("invalid datetimes", () => {
    it.concurrent("should reject date only", () => {
      const result = ISO_DATETIME_STRING.safeParse("2024-01-15");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject invalid format", () => {
      const result = ISO_DATETIME_STRING.safeParse("not-a-datetime");
      expect(result.success).toBe(false);
    });
  });
});

describe("FUTURE_DATE_SCHEMA", () => {
  describe("valid future dates", () => {
    it.concurrent("should accept date in the future", () => {
      // Create a date 1 year from now
      const futureDate = new Date();
      futureDate.setFullYear(futureDate.getFullYear() + 1);
      const dateStr = futureDate.toISOString().split("T")[0];

      const result = FUTURE_DATE_SCHEMA.safeParse(dateStr);
      expect(result.success).toBe(true);
    });
  });

  describe("invalid dates", () => {
    it.concurrent("should reject date in the past", () => {
      const result = FUTURE_DATE_SCHEMA.safeParse("2020-01-01");
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject yesterday", () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const dateStr = yesterday.toISOString().split("T")[0];

      const result = FUTURE_DATE_SCHEMA.safeParse(dateStr);
      expect(result.success).toBe(false);
    });
  });
});

describe("DATE_RANGE_SCHEMA", () => {
  describe("valid ranges", () => {
    it.concurrent("should accept valid date range", () => {
      const result = DATE_RANGE_SCHEMA.safeParse({
        end: "2024-01-15",
        start: "2024-01-01",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept range spanning months", () => {
      const result = DATE_RANGE_SCHEMA.safeParse({
        end: "2024-03-20",
        start: "2024-01-15",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should accept range spanning years", () => {
      const result = DATE_RANGE_SCHEMA.safeParse({
        end: "2025-01-31",
        start: "2024-12-01",
      });
      expect(result.success).toBe(true);
    });
  });

  describe("invalid ranges", () => {
    it.concurrent("should reject end before start", () => {
      const result = DATE_RANGE_SCHEMA.safeParse({
        end: "2024-01-01",
        start: "2024-01-15",
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject same start and end date", () => {
      const result = DATE_RANGE_SCHEMA.safeParse({
        end: "2024-01-15",
        start: "2024-01-15",
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject invalid date format in start", () => {
      const result = DATE_RANGE_SCHEMA.safeParse({
        end: "2024-01-20",
        start: "01/15/2024",
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject invalid date format in end", () => {
      const result = DATE_RANGE_SCHEMA.safeParse({
        end: "01-20-2024",
        start: "2024-01-15",
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject missing start", () => {
      const result = DATE_RANGE_SCHEMA.safeParse({
        end: "2024-01-15",
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject missing end", () => {
      const result = DATE_RANGE_SCHEMA.safeParse({
        start: "2024-01-15",
      });
      expect(result.success).toBe(false);
    });
  });
});
