import { describe, expect, it } from "vitest";

import { schemaNowIso } from "../shared/runtime-clock";

describe("schemaNowIso", () => {
  it("normalizes deterministic timestamp references", () => {
    const isoTimestamp = "2026-05-25T12:34:56.789Z";

    expect(schemaNowIso(Date.parse(isoTimestamp))).toBe(isoTimestamp);
    expect(schemaNowIso(isoTimestamp)).toBe(isoTimestamp);
    expect(schemaNowIso(new Date(isoTimestamp))).toBe(isoTimestamp);
  });

  it("returns a current ISO timestamp by default", () => {
    const beforeMs = Date.now();
    const timestamp = schemaNowIso();
    const afterMs = Date.now();

    const parsedMs = Date.parse(timestamp);

    expect(timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(parsedMs).toBeGreaterThanOrEqual(beforeMs);
    expect(parsedMs).toBeLessThanOrEqual(afterMs);
  });

  it("rejects invalid timestamp references", () => {
    expect(() => schemaNowIso("not-a-date")).toThrow(
      "Invalid schema timestamp reference"
    );
  });
});
