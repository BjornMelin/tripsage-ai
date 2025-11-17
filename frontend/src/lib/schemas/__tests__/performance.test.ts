/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { primitiveSchemas, refinedSchemas, transformSchemas } from "../registry";

describe("Validation Performance", () => {
  const iterations = 1000;
  const maxTimeMs = 5; // Per execplan requirement: <5ms validation time

  describe("primitiveSchemas performance", () => {
    it.concurrent("should validate uuid quickly", () => {
      const validUuid = "123e4567-e89b-12d3-a456-426614174000";
      const start = performance.now();

      for (let i = 0; i < iterations; i++) {
        primitiveSchemas.uuid.safeParse(validUuid);
      }

      const elapsed = performance.now() - start;
      const avgTime = elapsed / iterations;
      expect(avgTime).toBeLessThan(maxTimeMs);
    });

    it.concurrent("should validate email quickly", () => {
      const validEmail = "test@example.com";
      const start = performance.now();

      for (let i = 0; i < iterations; i++) {
        primitiveSchemas.email.safeParse(validEmail);
      }

      const elapsed = performance.now() - start;
      const avgTime = elapsed / iterations;
      expect(avgTime).toBeLessThan(maxTimeMs);
    });

    it.concurrent("should validate url quickly", () => {
      const validUrl = "https://example.com";
      const start = performance.now();

      for (let i = 0; i < iterations; i++) {
        primitiveSchemas.url.safeParse(validUrl);
      }

      const elapsed = performance.now() - start;
      const avgTime = elapsed / iterations;
      expect(avgTime).toBeLessThan(maxTimeMs);
    });
  });

  describe("transformSchemas performance", () => {
    it.concurrent("should transform email quickly", () => {
      const input = "Test@Example.COM";
      const start = performance.now();

      for (let i = 0; i < iterations; i++) {
        transformSchemas.lowercaseEmail.safeParse(input);
      }

      const elapsed = performance.now() - start;
      const avgTime = elapsed / iterations;
      expect(avgTime).toBeLessThan(maxTimeMs);
    });

    it.concurrent("should trim string quickly", () => {
      const input = "  hello world  ";
      const start = performance.now();

      for (let i = 0; i < iterations; i++) {
        transformSchemas.trimmedString.safeParse(input);
      }

      const elapsed = performance.now() - start;
      const avgTime = elapsed / iterations;
      expect(avgTime).toBeLessThan(maxTimeMs);
    });
  });

  describe("refinedSchemas performance", () => {
    it.concurrent("should validate strong password quickly", () => {
      const validPassword = "Test123!Password";
      const start = performance.now();

      for (let i = 0; i < iterations; i++) {
        refinedSchemas.strongPassword.safeParse(validPassword);
      }

      const elapsed = performance.now() - start;
      const avgTime = elapsed / iterations;
      expect(avgTime).toBeLessThan(maxTimeMs);
    });

    it.concurrent("should validate future date quickly", () => {
      const futureDate = new Date(Date.now() + 86400000).toISOString();
      const start = performance.now();

      for (let i = 0; i < iterations; i++) {
        refinedSchemas.futureDate.safeParse(futureDate);
      }

      const elapsed = performance.now() - start;
      const avgTime = elapsed / iterations;
      expect(avgTime).toBeLessThan(maxTimeMs);
    });
  });

  describe("Complex schema performance", () => {
    it.concurrent("should validate complex object quickly", () => {
      const complexObject = {
        email: "test@example.com",
        id: "123e4567-e89b-12d3-a456-426614174000",
        name: "Test User",
        url: "https://example.com",
      };

      const start = performance.now();

      for (let i = 0; i < iterations; i++) {
        // Simulate complex validation
        primitiveSchemas.email.safeParse(complexObject.email);
        primitiveSchemas.uuid.safeParse(complexObject.id);
        primitiveSchemas.nonEmptyString.safeParse(complexObject.name);
        primitiveSchemas.url.safeParse(complexObject.url);
      }

      const elapsed = performance.now() - start;
      const avgTime = elapsed / iterations;
      // Allow slightly more time for complex validation
      expect(avgTime).toBeLessThan(maxTimeMs * 4);
    });
  });
});
