/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RecurringRule } from "../recurring-rules";
import { RecurringDateGenerator } from "../recurring-rules";
import { DateUtils } from "../unified-date-utils";

describe("RecurringDateGenerator", () => {
  beforeEach(() => {
    // Use a fixed date for consistent testing
    vi.setSystemTime(new Date("2024-01-01T00:00:00Z"));
  });

  describe("generateOccurrences", () => {
    it("should generate daily occurrences", () => {
      const startDate = new Date("2024-01-01T10:00:00Z");
      const rule: RecurringRule = {
        frequency: "daily",
        interval: 1,
      };

      const occurrences = RecurringDateGenerator.generateOccurrences(
        startDate,
        rule,
        5
      );

      expect(occurrences).toHaveLength(5);
      expect(occurrences[0]).toEqual(startDate);
      expect(occurrences[1]).toEqual(DateUtils.add(startDate, 1, "days"));
      expect(occurrences[2]).toEqual(DateUtils.add(startDate, 2, "days"));
    });

    it("should generate weekly occurrences", () => {
      const startDate = new Date("2024-01-01T10:00:00Z"); // Monday
      const rule: RecurringRule = {
        frequency: "weekly",
        interval: 1,
      };

      const occurrences = RecurringDateGenerator.generateOccurrences(
        startDate,
        rule,
        3
      );

      expect(occurrences).toHaveLength(3);
      expect(occurrences[0]).toEqual(startDate);
      expect(occurrences[1]).toEqual(DateUtils.add(startDate, 7, "days"));
      expect(occurrences[2]).toEqual(DateUtils.add(startDate, 14, "days"));
    });

    it("should generate monthly occurrences", () => {
      const startDate = new Date("2024-01-01T10:00:00Z");
      const rule: RecurringRule = {
        frequency: "monthly",
        interval: 1,
      };

      const occurrences = RecurringDateGenerator.generateOccurrences(
        startDate,
        rule,
        3
      );

      expect(occurrences).toHaveLength(3);
      expect(occurrences[0]).toEqual(startDate);
      expect(occurrences[1]).toEqual(DateUtils.add(startDate, 1, "months"));
      expect(occurrences[2]).toEqual(DateUtils.add(startDate, 2, "months"));
    });

    it("should generate yearly occurrences", () => {
      const startDate = new Date("2024-01-01T10:00:00Z");
      const rule: RecurringRule = {
        frequency: "yearly",
        interval: 1,
      };

      const occurrences = RecurringDateGenerator.generateOccurrences(
        startDate,
        rule,
        3
      );

      expect(occurrences).toHaveLength(3);
      expect(occurrences[0]).toEqual(startDate);
      expect(occurrences[1]).toEqual(DateUtils.add(startDate, 1, "years"));
      expect(occurrences[2]).toEqual(DateUtils.add(startDate, 2, "years"));
    });

    it("should respect interval", () => {
      const startDate = new Date("2024-01-01T10:00:00Z");
      const rule: RecurringRule = {
        frequency: "daily",
        interval: 3,
      };

      const occurrences = RecurringDateGenerator.generateOccurrences(
        startDate,
        rule,
        3
      );

      expect(occurrences).toHaveLength(3);
      expect(occurrences[0]).toEqual(startDate);
      expect(occurrences[1]).toEqual(DateUtils.add(startDate, 3, "days"));
      expect(occurrences[2]).toEqual(DateUtils.add(startDate, 6, "days"));
    });

    it("should respect end date", () => {
      const startDate = new Date("2024-01-01T10:00:00Z");
      const endDate = new Date("2024-01-05T10:00:00Z");
      const rule: RecurringRule = {
        endDate,
        frequency: "daily",
        interval: 1,
      };

      const occurrences = RecurringDateGenerator.generateOccurrences(
        startDate,
        rule,
        10
      );

      expect(occurrences).toHaveLength(5);
      expect(occurrences[4]).toEqual(endDate);
    });

    it("should respect count limit", () => {
      const startDate = new Date("2024-01-01T10:00:00Z");
      const rule: RecurringRule = {
        count: 3,
        frequency: "daily",
        interval: 1,
      };

      const occurrences = RecurringDateGenerator.generateOccurrences(
        startDate,
        rule,
        10
      );

      expect(occurrences).toHaveLength(3);
    });

    it("should filter by days of week for weekly recurrence", () => {
      const startDate = new Date("2024-01-01T10:00:00Z"); // Monday
      const rule: RecurringRule = {
        daysOfWeek: [1, 3, 5], // Monday, Wednesday, Friday
        frequency: "weekly",
        interval: 1,
      };

      const occurrences = RecurringDateGenerator.generateOccurrences(
        startDate,
        rule,
        6
      );

      expect(occurrences).toHaveLength(6);
      expect(occurrences[0].getDay()).toBe(1); // Monday
      expect(occurrences[1].getDay()).toBe(3); // Wednesday
      expect(occurrences[2].getDay()).toBe(5); // Friday
      // second week mirrors same sequence
      expect(occurrences[3].getDay()).toBe(1);
      expect(occurrences[4].getDay()).toBe(3);
      expect(occurrences[5].getDay()).toBe(5);
    });

    it("should filter by day of month for monthly recurrence", () => {
      const startDate = new Date("2024-01-15T10:00:00Z"); // Start on the 15th
      const rule: RecurringRule = {
        dayOfMonth: 15,
        frequency: "monthly",
        interval: 1,
      };

      const occurrences = RecurringDateGenerator.generateOccurrences(
        startDate,
        rule,
        5
      );

      expect(occurrences.length).toBeGreaterThan(0);
      // All occurrences should be on the 15th day of the month
      occurrences.forEach((occurrence) => {
        expect(occurrence.getDate()).toBe(15);
      });
    });
  });

  describe("parseRRule", () => {
    it("should parse simple daily rule", () => {
      const rrule = "FREQ=DAILY";
      const rule = RecurringDateGenerator.parseRRule(rrule);

      expect(rule.frequency).toBe("daily");
      expect(rule.interval).toBe(1);
    });

    it("should parse rule with interval", () => {
      const rrule = "FREQ=WEEKLY;INTERVAL=2";
      const rule = RecurringDateGenerator.parseRRule(rrule);

      expect(rule.frequency).toBe("weekly");
      expect(rule.interval).toBe(2);
    });

    it("should parse rule with until date", () => {
      const rrule = "FREQ=DAILY;UNTIL=20240131T235959Z";
      const rule = RecurringDateGenerator.parseRRule(rrule);

      expect(rule.frequency).toBe("daily");
      expect(rule.endDate).toEqual(DateUtils.parse("20240131T235959Z"));
    });

    it("should parse rule with count", () => {
      const rrule = "FREQ=MONTHLY;COUNT=12";
      const rule = RecurringDateGenerator.parseRRule(rrule);

      expect(rule.frequency).toBe("monthly");
      expect(rule.count).toBe(12);
    });

    it("should parse rule with days of week", () => {
      const rrule = "FREQ=WEEKLY;BYDAY=MO,WE,FR";
      const rule = RecurringDateGenerator.parseRRule(rrule);

      expect(rule.frequency).toBe("weekly");
      expect(rule.daysOfWeek).toEqual([1, 3, 5]);
    });

    it("should parse rule with day of month", () => {
      const rrule = "FREQ=MONTHLY;BYMONTHDAY=15";
      const rule = RecurringDateGenerator.parseRRule(rrule);

      expect(rule.frequency).toBe("monthly");
      expect(rule.dayOfMonth).toBe(15);
    });

    it("should parse complex rule", () => {
      const rrule = "FREQ=WEEKLY;INTERVAL=2;BYDAY=TU,TH;COUNT=10";
      const rule = RecurringDateGenerator.parseRRule(rrule);

      expect(rule.frequency).toBe("weekly");
      expect(rule.interval).toBe(2);
      expect(rule.daysOfWeek).toEqual([2, 4]);
      expect(rule.count).toBe(10);
    });

    it("should handle lowercase input", () => {
      const rrule = "freq=daily;interval=3";
      const rule = RecurringDateGenerator.parseRRule(rrule);

      expect(rule.frequency).toBe("daily");
      expect(rule.interval).toBe(3);
    });

    it("should return default rule for empty string", () => {
      const rule = RecurringDateGenerator.parseRRule("");

      expect(rule.frequency).toBe("daily");
      expect(rule.interval).toBe(1);
    });
  });

  describe("toRRule", () => {
    it("should convert simple daily rule", () => {
      const rule: RecurringRule = {
        frequency: "daily",
        interval: 1,
      };

      const rrule = RecurringDateGenerator.toRRule(rule);
      expect(rrule).toBe("FREQ=DAILY");
    });

    it("should convert rule with interval", () => {
      const rule: RecurringRule = {
        frequency: "weekly",
        interval: 2,
      };

      const rrule = RecurringDateGenerator.toRRule(rule);
      expect(rrule).toBe("FREQ=WEEKLY;INTERVAL=2");
    });

    it("should convert rule with end date", () => {
      const rule: RecurringRule = {
        endDate: new Date("2024-01-31T23:59:59Z"),
        frequency: "daily",
        interval: 1,
      };

      const rrule = RecurringDateGenerator.toRRule(rule);
      expect(rrule).toContain("FREQ=DAILY");
      expect(rrule).toContain("UNTIL=");
    });

    it("should convert rule with count", () => {
      const rule: RecurringRule = {
        count: 12,
        frequency: "monthly",
        interval: 1,
      };

      const rrule = RecurringDateGenerator.toRRule(rule);
      expect(rrule).toBe("FREQ=MONTHLY;COUNT=12");
    });

    it("should convert rule with days of week", () => {
      const rule: RecurringRule = {
        daysOfWeek: [1, 3, 5],
        frequency: "weekly",
        interval: 1,
      };

      const rrule = RecurringDateGenerator.toRRule(rule);
      expect(rrule).toBe("FREQ=WEEKLY;BYDAY=MO,WE,FR");
    });

    it("should convert rule with day of month", () => {
      const rule: RecurringRule = {
        dayOfMonth: 15,
        frequency: "monthly",
        interval: 1,
      };

      const rrule = RecurringDateGenerator.toRRule(rule);
      expect(rrule).toBe("FREQ=MONTHLY;BYMONTHDAY=15");
    });

    it("should convert complex rule", () => {
      const rule: RecurringRule = {
        count: 10,
        daysOfWeek: [2, 4],
        frequency: "weekly",
        interval: 2,
      };

      const rrule = RecurringDateGenerator.toRRule(rule);
      expect(rrule).toBe("FREQ=WEEKLY;INTERVAL=2;COUNT=10;BYDAY=TU,TH");
    });
  });

  describe("Round-trip conversion", () => {
    it("should maintain consistency through parse and convert", () => {
      const originalRule: RecurringRule = {
        count: 15,
        daysOfWeek: [1, 3, 5],
        frequency: "weekly",
        interval: 2,
      };

      const rrule = RecurringDateGenerator.toRRule(originalRule);
      const parsedRule = RecurringDateGenerator.parseRRule(rrule);

      expect(parsedRule.frequency).toBe(originalRule.frequency);
      expect(parsedRule.interval).toBe(originalRule.interval);
      expect(parsedRule.daysOfWeek).toEqual(originalRule.daysOfWeek);
      expect(parsedRule.count).toBe(originalRule.count);
    });
  });
});

describe("RecurringRule Type", () => {
  it("should accept valid recurring rule", () => {
    const rule: RecurringRule = {
      count: 10,
      dayOfMonth: 15,
      daysOfWeek: [1, 2, 3, 4, 5],
      endDate: new Date("2024-12-31"),
      frequency: "daily",
      interval: 1,
      weekOfMonth: 2,
    };

    expect(rule.frequency).toBe("daily");
    expect(rule.interval).toBe(1);
    expect(rule.endDate).toBeInstanceOf(Date);
    expect(rule.count).toBe(10);
    expect(rule.daysOfWeek).toHaveLength(5);
    expect(rule.dayOfMonth).toBe(15);
    expect(rule.weekOfMonth).toBe(2);
  });

  it("should accept minimal recurring rule", () => {
    const rule: RecurringRule = {
      frequency: "yearly",
      interval: 1,
    };

    expect(rule.frequency).toBe("yearly");
    expect(rule.endDate).toBeUndefined();
    expect(rule.count).toBeUndefined();
    expect(rule.daysOfWeek).toBeUndefined();
  });
});
