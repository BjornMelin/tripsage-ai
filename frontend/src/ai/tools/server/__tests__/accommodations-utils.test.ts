import {
  extractTokenFromHref,
  normalizePhoneForRapid,
  splitGuestName,
} from "@ai/tools";
import { describe, expect, it } from "vitest";

describe("accommodations helper utilities", () => {
  it("splits guest names into first and last parts", () => {
    expect(splitGuestName("Jane Doe")).toEqual({
      familyName: "Doe",
      givenName: "Jane",
    });
    expect(splitGuestName("José María Rodríguez")).toEqual({
      familyName: "Rodríguez",
      givenName: "José María",
    });
    expect(splitGuestName("Cher")).toEqual({
      familyName: "Cher",
      givenName: "Cher",
    });
  });

  it("normalizes phone numbers for Rapid requirements", () => {
    expect(normalizePhoneForRapid("+1 (555) 123-4567")).toEqual({
      areaCode: "555",
      countryCode: "1",
      number: "1234567",
    });
    expect(normalizePhoneForRapid("442071234567")).toEqual({
      areaCode: "071",
      countryCode: "442",
      number: "234567",
    });
    expect(normalizePhoneForRapid(undefined)).toEqual({
      countryCode: "1",
      number: "0000000",
    });
  });

  it("extracts Rapid tokens from href values", () => {
    expect(
      extractTokenFromHref(
        "/v3/properties/123/rooms/abc/rates/def?token=abc123&expires_at=2025-01-01T00%3A00%3A00Z"
      )
    ).toBe("abc123");
    expect(extractTokenFromHref("https://test.ean.com/v3/foo?other=1")).toBeUndefined();
    expect(extractTokenFromHref(undefined)).toBeUndefined();
  });
});
