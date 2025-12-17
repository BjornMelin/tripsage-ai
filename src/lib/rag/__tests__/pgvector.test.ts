/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import { toPgvector } from "../pgvector";

vi.mock("server-only", () => ({}));

describe("toPgvector", () => {
  it("formats numeric arrays as pgvector literals", () => {
    expect(toPgvector([1, 2, 3])).toBe("[1,2,3]");
    expect(toPgvector([0.1, -0.2, 3.5])).toBe("[0.1,-0.2,3.5]");
  });

  it("throws on non-finite values", () => {
    expect(() => toPgvector([Number.NaN])).toThrow(/Invalid embedding value/);
    expect(() => toPgvector([Number.POSITIVE_INFINITY])).toThrow(
      /Invalid embedding value/
    );
  });

  it("preserves scientific notation when present", () => {
    expect(toPgvector([1e-7, -1e-7])).toBe("[1e-7,-1e-7]");
  });
});
