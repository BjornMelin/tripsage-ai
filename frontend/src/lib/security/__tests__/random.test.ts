/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import { nowIso, secureId, secureRandomInt, secureUuid } from "../random";

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

  describe("secureRandomInt", () => {
    it("returns 0 for max = 0", () => {
      expect(secureRandomInt(0)).toBe(0);
    });

    it("throws for negative max", () => {
      expect(() => secureRandomInt(-5)).toThrow(RangeError);
    });

    it("returns values within range [0, max]", () => {
      const max = 10;
      for (let i = 0; i < 100; i++) {
        const value = secureRandomInt(max);
        expect(value).toBeGreaterThanOrEqual(0);
        expect(value).toBeLessThanOrEqual(max);
        expect(Number.isInteger(value)).toBe(true);
      }
    });

    it("handles max = 1 correctly", () => {
      const results = new Set<number>();
      for (let i = 0; i < 50; i++) {
        results.add(secureRandomInt(1));
      }
      // Should produce both 0 and 1
      expect(results.has(0)).toBe(true);
      expect(results.has(1)).toBe(true);
      // All values should be 0 or 1
      for (const v of results) {
        expect(v === 0 || v === 1).toBe(true);
      }
    });

    it("handles larger max values", () => {
      const max = 1000;
      for (let i = 0; i < 50; i++) {
        const value = secureRandomInt(max);
        expect(value).toBeGreaterThanOrEqual(0);
        expect(value).toBeLessThanOrEqual(max);
      }
    });

    it("produces varied distribution over many calls", () => {
      const max = 5;
      const counts = new Map<number, number>();
      const iterations = 1000;

      for (let i = 0; i < iterations; i++) {
        const value = secureRandomInt(max);
        counts.set(value, (counts.get(value) ?? 0) + 1);
      }

      // All values 0-5 should appear at least once over 1000 iterations
      for (let i = 0; i <= max; i++) {
        expect(counts.has(i)).toBe(true);
      }
    });

    it("falls back when crypto is unavailable", () => {
      vi.stubGlobal("crypto", undefined as unknown as Crypto);
      try {
        const value = secureRandomInt(100);
        expect(value).toBeGreaterThanOrEqual(0);
        expect(value).toBeLessThanOrEqual(100);
      } finally {
        vi.unstubAllGlobals();
      }
    });

    it("throws when insecure fallback is disabled and crypto is unavailable", () => {
      vi.stubGlobal("crypto", undefined as unknown as Crypto);
      try {
        expect(() => secureRandomInt(10, { allowInsecureFallback: false })).toThrow(
          "secure_random_unavailable"
        );
      } finally {
        vi.unstubAllGlobals();
      }
    });

    it("throws when crypto is required but unavailable", () => {
      vi.stubGlobal("crypto", undefined as unknown as Crypto);
      try {
        expect(() => secureRandomInt(10, { requireCrypto: true })).toThrow(
          "secure_random_unavailable"
        );
      } finally {
        vi.unstubAllGlobals();
      }
    });
  });
});
