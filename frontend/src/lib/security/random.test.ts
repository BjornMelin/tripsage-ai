/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import { nowIso, secureId, secureUuid } from "./random";

const UUID_V4_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

describe("security/random", () => {
  it("secureUUID generates RFC4122 v4 UUIDs", () => {
    const id = secureUuid();
    expect(UUID_V4_REGEX.test(id)).toBe(true);
  });

  it("secureUUID generates unique values across bursts", () => {
    const n = 1000;
    const set = new Set<string>();
    for (let i = 0; i < n; i++) set.add(secureUuid());
    expect(set.size).toBe(n);
  });

  it("secureId returns compact id and honors length", () => {
    const id8 = secureId(8);
    const id12 = secureId(12);
    expect(id8).toHaveLength(8);
    expect(id12).toHaveLength(12);
    expect(id8).not.toEqual(id12);
  });

  it("nowIso returns an ISO 8601 string", () => {
    const ts = nowIso();
    // Basic ISO check
    expect(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:.+Z$/.test(ts)).toBe(true);
  });

  it("falls back when crypto is unavailable", () => {
    vi.stubGlobal("crypto", undefined as unknown as Crypto);
    try {
      const id = secureUuid();
      // Not necessarily UUID format, but must be non-empty and unique across calls
      expect(id.length).toBeGreaterThan(0);
      const id2 = secureUuid();
      expect(id).not.toEqual(id2);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
