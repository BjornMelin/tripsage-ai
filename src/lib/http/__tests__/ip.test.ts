/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { getClientIpFromHeaders } from "@/lib/http/ip";

describe("getClientIpFromHeaders (shared)", () => {
  it("prefers x-real-ip when present", () => {
    const headers = new Headers({
      "x-forwarded-for": "203.0.113.10, 198.51.100.2",
      "x-real-ip": "198.51.100.5",
    });
    expect(getClientIpFromHeaders(headers)).toBe("198.51.100.5");
  });

  it("falls back to first x-forwarded-for value when x-real-ip is absent", () => {
    const headers = new Headers({
      "x-forwarded-for": "203.0.113.10, 198.51.100.2",
    });
    expect(getClientIpFromHeaders(headers)).toBe("203.0.113.10");
  });

  it("falls back to cf-connecting-ip when other headers are absent", () => {
    const headers = new Headers({ "cf-connecting-ip": "9.9.9.9" });
    expect(getClientIpFromHeaders(headers)).toBe("9.9.9.9");
  });

  it("returns unknown when no IP headers exist", () => {
    expect(getClientIpFromHeaders(new Headers())).toBe("unknown");
  });

  it("rejects invalid x-forwarded-for and uses cf-connecting-ip as fallback", () => {
    const headers = new Headers({
      "cf-connecting-ip": "9.9.9.9",
      "x-forwarded-for": "not-an-ip-address, 198.51.100.25",
    });
    expect(getClientIpFromHeaders(headers)).toBe("9.9.9.9");
  });
});
