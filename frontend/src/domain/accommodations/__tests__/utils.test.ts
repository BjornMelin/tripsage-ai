/**
 * @fileoverview Unit tests for accommodation utility functions.
 */

import {
  extractTokenFromHref,
  normalizePhoneForRapid,
  splitGuestName,
} from "@domain/accommodations/service";
import { describe, expect, it } from "vitest";

describe("extractTokenFromHref", () => {
  it("should return undefined for undefined/null/empty input", () => {
    expect(extractTokenFromHref(undefined)).toBeUndefined();
    expect(extractTokenFromHref(null)).toBeUndefined();
    expect(extractTokenFromHref("")).toBeUndefined();
  });

  it("should extract token from valid href", () => {
    const href = "/rooms/123/rates/456?token=abc-123-def&other=param";
    expect(extractTokenFromHref(href)).toBe("abc-123-def");
  });

  it("should return undefined if token param is missing", () => {
    const href = "/rooms/123/rates/456?other=param";
    expect(extractTokenFromHref(href)).toBeUndefined();
  });

  it("should handle full URLs", () => {
    const href = "https://test.ean.com/rooms/123?token=xyz-789";
    expect(extractTokenFromHref(href)).toBe("xyz-789");
  });

  it("should return undefined for invalid URLs", () => {
    // partial path without base is handled by "https://test.ean.com" base in implementation
    // but "http://" is invalid URL constructor input if it was just ":"
    // The implementation uses `new URL(href, "https://test.ean.com")` so relative paths are valid.
    expect(extractTokenFromHref("just-a-string")).toBeUndefined();
  });
});

describe("splitGuestName", () => {
  it("should split first and last name", () => {
    expect(splitGuestName("John Doe")).toEqual({
      familyName: "Doe",
      givenName: "John",
    });
  });

  it("should handle multiple given names", () => {
    expect(splitGuestName("John Robert Doe")).toEqual({
      familyName: "Doe",
      givenName: "John Robert",
    });
  });

  it("should handle single name", () => {
    expect(splitGuestName("Cher")).toEqual({
      familyName: "Cher",
      givenName: "Cher",
    });
  });

  it("should handle extra whitespace", () => {
    expect(splitGuestName("  Jane   Doe  ")).toEqual({
      familyName: "Doe",
      givenName: "Jane",
    });
  });
});

describe("normalizePhoneForRapid", () => {
  it("should return default for empty input", () => {
    const expected = { countryCode: "1", number: "0000000" };
    expect(normalizePhoneForRapid(undefined)).toEqual(expected);
    expect(normalizePhoneForRapid("")).toEqual(expected);
    expect(normalizePhoneForRapid("   ")).toEqual(expected);
  });

  it("should return default for input with no digits", () => {
    const expected = { countryCode: "1", number: "0000000" };
    expect(normalizePhoneForRapid("abc")).toEqual(expected);
  });

  it("should handle short numbers (<= 7 digits)", () => {
    expect(normalizePhoneForRapid("5551234")).toEqual({
      countryCode: "1",
      number: "5551234",
    });
    // Pads with 0
    expect(normalizePhoneForRapid("123")).toEqual({
      countryCode: "1",
      number: "0000123",
    });
  });

  it("should handle 10-digit numbers (US standard)", () => {
    expect(normalizePhoneForRapid("4155551234")).toEqual({
      areaCode: "415",
      countryCode: "1",
      number: "5551234",
    });
  });

  it("should handle numbers with country code (> 10 digits)", () => {
    // Last 7 is number, prev 3 is area code, rest is country code
    // 44 20 7123 4567 -> 12 digits
    // number: 234567 (last 7) -> 34567 ??
    // Implementation: digits.slice(-7) -> last 7
    // digits.slice(length - 10, length - 7) -> area code
    // digits.slice(0, length - 10) -> country code

    // 123456789012
    // number: 6789012
    // area: 345
    // country: 12
    expect(normalizePhoneForRapid("123456789012")).toEqual({
      areaCode: "345",
      countryCode: "12",
      number: "6789012",
    });
  });

  it("should ignore non-digit characters", () => {
    expect(normalizePhoneForRapid("+1 (415) 555-1234")).toEqual({
      areaCode: "415",
      countryCode: "1",
      number: "5551234",
    });
  });
});
