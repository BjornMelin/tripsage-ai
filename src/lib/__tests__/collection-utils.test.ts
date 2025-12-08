/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { compact, groupBy, unique, without } from "../collection-utils";

describe("groupBy", () => {
  it("should group objects by a property", () => {
    const items = [
      { id: 1, type: "a" },
      { id: 2, type: "b" },
      { id: 3, type: "a" },
    ];
    const result = groupBy(items, (item) => item.type);
    expect(result).toEqual({
      a: [
        { id: 1, type: "a" },
        { id: 3, type: "a" },
      ],
      b: [{ id: 2, type: "b" }],
    });
  });

  it("should handle empty array", () => {
    const result = groupBy([], (item) => item);
    expect(result).toEqual({});
  });

  it("should handle numeric keys", () => {
    const items = [
      { bucket: 1, value: 10 },
      { bucket: 2, value: 20 },
      { bucket: 1, value: 15 },
    ];
    const result = groupBy(items, (item) => item.bucket);
    expect(result).toEqual({
      1: [
        { bucket: 1, value: 10 },
        { bucket: 1, value: 15 },
      ],
      2: [{ bucket: 2, value: 20 }],
    });
  });

  it("should handle all items having the same key", () => {
    const items = [1, 2, 3];
    const result = groupBy(items, () => "same");
    expect(result).toEqual({ same: [1, 2, 3] });
  });

  it("should handle complex key functions", () => {
    const items = [
      { age: 25, name: "alice" },
      { age: 30, name: "bob" },
      { age: 25, name: "charlie" },
    ];
    const result = groupBy(items, (item) => `age_${item.age}`);
    expect(result).toEqual({
      age_25: [
        { age: 25, name: "alice" },
        { age: 25, name: "charlie" },
      ],
      age_30: [{ age: 30, name: "bob" }],
    });
  });
});

describe("compact", () => {
  it("should remove null and undefined values", () => {
    const arr = [1, null, 2, undefined, 3];
    expect(compact(arr)).toEqual([1, 2, 3]);
  });

  it("should handle empty array", () => {
    expect(compact([])).toEqual([]);
  });

  it("should handle array with only null/undefined", () => {
    expect(compact([null, undefined, null])).toEqual([]);
  });

  it("should preserve falsy values that are not null/undefined", () => {
    const arr = [0, false, "", null, undefined];
    expect(compact(arr)).toEqual([0, false, ""]);
  });

  it("should preserve NaN", () => {
    const arr = [1, NaN, null, undefined, 2];
    const result = compact(arr);
    expect(result).toHaveLength(3);
    expect(result[0]).toBe(1);
    expect(Number.isNaN(result[1])).toBe(true);
    expect(result[2]).toBe(2);
  });

  it("should handle arrays of objects", () => {
    const arr = [{ id: 1 }, null, { id: 2 }, undefined];
    expect(compact(arr)).toEqual([{ id: 1 }, { id: 2 }]);
  });

  it("should not modify original array", () => {
    const arr = [1, null, 2];
    compact(arr);
    expect(arr).toEqual([1, null, 2]);
  });
});

describe("without", () => {
  it("should remove specified items", () => {
    expect(without([1, 2, 3, 4], 2, 4)).toEqual([1, 3]);
  });

  it("should handle empty array", () => {
    expect(without([], 1, 2)).toEqual([]);
  });

  it("should handle no items to remove", () => {
    expect(without([1, 2, 3])).toEqual([1, 2, 3]);
  });

  it("should handle items not in array", () => {
    expect(without([1, 2, 3], 4, 5)).toEqual([1, 2, 3]);
  });

  it("should handle duplicate values in array", () => {
    expect(without([1, 2, 2, 3, 2], 2)).toEqual([1, 3]);
  });

  it("should handle removing all items", () => {
    expect(without([1, 2], 1, 2)).toEqual([]);
  });

  it("should handle strings", () => {
    expect(without(["a", "b", "c"], "b")).toEqual(["a", "c"]);
  });

  it("should handle objects (by reference)", () => {
    const obj1 = { id: 1 };
    const obj2 = { id: 2 };
    const obj3 = { id: 3 };
    expect(without([obj1, obj2, obj3], obj2)).toEqual([obj1, obj3]);
  });

  it("should not modify original array", () => {
    const arr = [1, 2, 3];
    without(arr, 2);
    expect(arr).toEqual([1, 2, 3]);
  });
});

describe("unique", () => {
  it("should remove duplicate values", () => {
    expect(unique([1, 2, 2, 3, 1])).toEqual([1, 2, 3]);
  });

  it("should handle empty array", () => {
    expect(unique([])).toEqual([]);
  });

  it("should handle array with no duplicates", () => {
    expect(unique([1, 2, 3])).toEqual([1, 2, 3]);
  });

  it("should handle array with all duplicates", () => {
    expect(unique([1, 1, 1])).toEqual([1]);
  });

  it("should handle strings", () => {
    expect(unique(["a", "b", "a", "c", "b"])).toEqual(["a", "b", "c"]);
  });

  it("should preserve order of first occurrence", () => {
    expect(unique([3, 1, 2, 1, 3])).toEqual([3, 1, 2]);
  });

  it("should handle mixed types", () => {
    const arr = [1, "1", 2, "2", 1];
    expect(unique(arr)).toEqual([1, "1", 2, "2"]);
  });

  it("should handle NaN correctly", () => {
    // Note: Set treats NaN as equal to NaN
    const result = unique([NaN, 1, NaN, 2]);
    expect(result).toHaveLength(3);
    expect(Number.isNaN(result[0])).toBe(true);
    expect(result[1]).toBe(1);
    expect(result[2]).toBe(2);
  });

  it("should handle objects (by reference)", () => {
    const obj1 = { id: 1 };
    const obj2 = { id: 2 };
    const result = unique([obj1, obj2, obj1]);
    expect(result).toEqual([obj1, obj2]);
    expect(result).toHaveLength(2);
  });

  it("should not modify original array", () => {
    const arr = [1, 2, 2, 3];
    unique(arr);
    expect(arr).toEqual([1, 2, 2, 3]);
  });
});
