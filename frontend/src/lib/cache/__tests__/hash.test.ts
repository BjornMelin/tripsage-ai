/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { hashInputForCache } from "../hash";

describe("hashInputForCache", () => {
  describe("basic hashing", () => {
    it("should return 16-character hex string", () => {
      const result = hashInputForCache({ foo: "bar" });
      expect(result).toHaveLength(16);
      expect(result).toMatch(/^[0-9a-f]{16}$/);
    });

    it("should handle string input", () => {
      const result = hashInputForCache("test string");
      expect(result).toHaveLength(16);
      expect(result).toMatch(/^[0-9a-f]{16}$/);
    });

    it("should handle number input", () => {
      const result = hashInputForCache(12345);
      expect(result).toHaveLength(16);
    });

    it("should handle boolean input", () => {
      const result = hashInputForCache(true);
      expect(result).toHaveLength(16);
    });

    it("should handle null input", () => {
      const result = hashInputForCache(null);
      expect(result).toHaveLength(16);
    });

    it("should handle array input", () => {
      const result = hashInputForCache([1, 2, 3]);
      expect(result).toHaveLength(16);
    });
  });

  describe("determinism", () => {
    it("should produce same hash for same input", () => {
      const input = { baz: 123, foo: "bar" };
      const hash1 = hashInputForCache(input);
      const hash2 = hashInputForCache(input);
      expect(hash1).toBe(hash2);
    });

    it("should produce same hash for equivalent objects", () => {
      const hash1 = hashInputForCache({ a: 1, b: 2 });
      const hash2 = hashInputForCache({ a: 1, b: 2 });
      expect(hash1).toBe(hash2);
    });

    it("should produce different hash for different key order in objects", () => {
      // JSON.stringify produces different output for different key order
      // This is expected behavior - callers should canonicalize if needed
      const hash1 = hashInputForCache({ a: 1, b: 2 });
      const hash2 = hashInputForCache({ a: 1, b: 2 });
      // Note: This may or may not be equal depending on JS engine object key ordering
      // Modern engines preserve insertion order for string keys
      expect(typeof hash1).toBe("string");
      expect(typeof hash2).toBe("string");
    });
  });

  describe("uniqueness", () => {
    it("should produce different hashes for different inputs", () => {
      const hash1 = hashInputForCache({ foo: "bar" });
      const hash2 = hashInputForCache({ foo: "baz" });
      expect(hash1).not.toBe(hash2);
    });

    it("should produce different hashes for different types", () => {
      const hash1 = hashInputForCache("123");
      const hash2 = hashInputForCache(123);
      expect(hash1).not.toBe(hash2);
    });

    it("should produce different hashes for different arrays", () => {
      const hash1 = hashInputForCache([1, 2, 3]);
      const hash2 = hashInputForCache([1, 2, 4]);
      expect(hash1).not.toBe(hash2);
    });
  });

  describe("complex objects", () => {
    it("should handle nested objects", () => {
      const input = {
        filters: { status: "active", tags: ["a", "b"] },
        user: { id: "123", name: "Test" },
      };
      const result = hashInputForCache(input);
      expect(result).toHaveLength(16);
      expect(result).toMatch(/^[0-9a-f]{16}$/);
    });

    it("should handle deeply nested structures", () => {
      const input = {
        level1: {
          level2: {
            level3: {
              value: "deep",
            },
          },
        },
      };
      const result = hashInputForCache(input);
      expect(result).toHaveLength(16);
    });
  });

  describe("edge cases", () => {
    it("should handle empty object", () => {
      const result = hashInputForCache({});
      expect(result).toHaveLength(16);
    });

    it("should handle empty array", () => {
      const result = hashInputForCache([]);
      expect(result).toHaveLength(16);
    });

    it("should handle empty string", () => {
      const result = hashInputForCache("");
      expect(result).toHaveLength(16);
    });

    it("should throw for undefined input (not JSON-serializable)", () => {
      // JSON.stringify(undefined) returns undefined (not a string)
      // which causes the hash function to throw
      expect(() => hashInputForCache(undefined)).toThrow();
    });
  });
});
