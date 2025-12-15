/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { groupBy, mapToUnique } from "../collection-utils";

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

describe("mapToUnique", () => {
  it("returns an empty array for empty input", () => {
    expect(mapToUnique<number, number>([], (item) => item)).toEqual([]);
  });

  it("returns the full mapped list when all mapped values are unique", () => {
    const items = [{ id: 1 }, { id: 2 }, { id: 3 }];
    expect(mapToUnique(items, (item) => item.id)).toEqual([1, 2, 3]);
  });

  it("returns a single-element array when all items map to the same value", () => {
    const items = [{ id: 1 }, { id: 2 }, { id: 3 }];
    expect(mapToUnique(items, () => 1)).toEqual([1]);
  });

  it("deduplicates mapped primitive values while preserving first-seen order", () => {
    const items = [{ id: 1 }, { id: 2 }, { id: 1 }];
    expect(mapToUnique(items, (item) => item.id)).toEqual([1, 2]);
  });

  it("deduplicates by reference for non-primitive mapped values", () => {
    const a = { id: 1 };
    const b = { id: 1 };
    expect(mapToUnique([a, b, a], (item) => item)).toEqual([a, b]);
  });
});
