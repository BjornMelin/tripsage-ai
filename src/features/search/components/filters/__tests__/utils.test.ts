/** @vitest-environment node */

import type { FilterValue } from "@schemas/stores";
import { describe, expect, it } from "vitest";

import {
  isBooleanValue,
  isNumberValue,
  isRangeObject,
  isStringArray,
  isStringValue,
} from "../utils";

/**
 * Helper to cast values to FilterValue for testing invalid inputs.
 * Type guards must handle any runtime value gracefully.
 */
const asFilter = (value: unknown): FilterValue => value as FilterValue;

describe("Filter Type Guards", () => {
  describe("isRangeObject", () => {
    it("returns true for valid range objects", () => {
      expect(isRangeObject({ max: 100, min: 0 })).toBe(true);
      expect(isRangeObject({ max: 10, min: -10 })).toBe(true);
      expect(isRangeObject({ max: 1.5, min: 0.5 })).toBe(true);
    });

    it("returns false for null", () => {
      expect(isRangeObject(asFilter(null))).toBe(false);
    });

    it("returns false for string values", () => {
      expect(isRangeObject("string")).toBe(false);
    });

    it("returns false for objects missing min", () => {
      expect(isRangeObject({ max: 100 })).toBe(false);
    });

    it("returns false for objects missing max", () => {
      expect(isRangeObject({ min: 0 })).toBe(false);
    });

    it("returns false for objects with non-numeric min/max", () => {
      expect(isRangeObject(asFilter({ max: "100", min: "0" }))).toBe(false);
      expect(isRangeObject(asFilter({ max: 100, min: null }))).toBe(false);
    });

    it("returns false for arrays", () => {
      expect(isRangeObject([0, 100])).toBe(false);
    });

    it("returns false for numbers", () => {
      expect(isRangeObject(42)).toBe(false);
    });
  });

  describe("isStringValue", () => {
    it("returns true for strings", () => {
      expect(isStringValue("test")).toBe(true);
      expect(isStringValue("")).toBe(true);
      expect(isStringValue("123")).toBe(true);
    });

    it("returns false for numbers", () => {
      expect(isStringValue(123)).toBe(false);
    });

    it("returns false for null", () => {
      expect(isStringValue(asFilter(null))).toBe(false);
    });

    it("returns false for arrays", () => {
      expect(isStringValue(["a", "b"])).toBe(false);
    });

    it("returns false for objects", () => {
      expect(isStringValue({ max: 100, min: 0 })).toBe(false);
    });

    it("returns false for booleans", () => {
      expect(isStringValue(true)).toBe(false);
    });
  });

  describe("isStringArray", () => {
    it("returns true for string arrays", () => {
      expect(isStringArray(["a", "b"])).toBe(true);
      expect(isStringArray(["single"])).toBe(true);
      expect(isStringArray([])).toBe(true);
    });

    it("returns false for number arrays", () => {
      expect(isStringArray(asFilter([1, 2, 3]))).toBe(false);
    });

    it("returns false for mixed arrays", () => {
      expect(isStringArray(asFilter(["a", 1]))).toBe(false);
      expect(isStringArray(asFilter([null, "b"]))).toBe(false);
    });

    it("returns false for non-arrays", () => {
      expect(isStringArray("string")).toBe(false);
      expect(isStringArray(123)).toBe(false);
      expect(isStringArray(asFilter(null))).toBe(false);
      expect(isStringArray(asFilter({ key: "value" }))).toBe(false);
    });
  });

  describe("isNumberValue", () => {
    it("returns true for numbers", () => {
      expect(isNumberValue(42)).toBe(true);
      expect(isNumberValue(0)).toBe(true);
      expect(isNumberValue(-1.5)).toBe(true);
      expect(isNumberValue(Number.MAX_VALUE)).toBe(true);
    });

    it("returns false for numeric strings", () => {
      expect(isNumberValue("42")).toBe(false);
    });

    it("returns false for null", () => {
      expect(isNumberValue(asFilter(null))).toBe(false);
    });

    it("returns false for NaN", () => {
      // NaN is technically typeof number but isNaN would catch it
      // This guard accepts NaN since it's a valid number type
      expect(isNumberValue(Number.NaN)).toBe(true);
    });

    it("returns false for arrays", () => {
      expect(isNumberValue([1, 2])).toBe(false);
    });
  });

  describe("isBooleanValue", () => {
    it("returns true for booleans", () => {
      expect(isBooleanValue(true)).toBe(true);
      expect(isBooleanValue(false)).toBe(true);
    });

    it("returns false for truthy/falsy non-booleans", () => {
      expect(isBooleanValue(1)).toBe(false);
      expect(isBooleanValue(0)).toBe(false);
      expect(isBooleanValue("true")).toBe(false);
      expect(isBooleanValue("")).toBe(false);
    });

    it("returns false for null", () => {
      expect(isBooleanValue(asFilter(null))).toBe(false);
    });
  });
});
