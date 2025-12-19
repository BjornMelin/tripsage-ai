/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { isValidInternalKey } from "@/lib/security/internal-key";

describe("isValidInternalKey", () => {
  it("returns false when provided key is missing", () => {
    expect(isValidInternalKey(null, "expected")).toBe(false);
  });

  it("throws when expected key is empty", () => {
    expect(() => isValidInternalKey("provided", "")).toThrow(
      "Missing expected internal key: check server configuration"
    );
  });

  it("returns false when keys have different lengths", () => {
    expect(isValidInternalKey("short", "much-longer")).toBe(false);
  });

  it("returns true when keys match exactly", () => {
    expect(isValidInternalKey("same-key", "same-key")).toBe(true);
  });

  it("returns false when keys differ but have the same length", () => {
    expect(isValidInternalKey("abc123", "abd123")).toBe(false);
  });
});
