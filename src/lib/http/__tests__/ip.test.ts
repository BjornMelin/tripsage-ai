/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getClientIpFromHeaders } from "@/lib/http/ip";

describe("getClientIpFromHeaders (shared)", () => {
  describe("when proxy headers are trusted (Vercel/TRUST_PROXY)", () => {
    beforeEach(() => {
      vi.stubEnv("VERCEL", "1");
    });

    afterEach(() => {
      vi.unstubAllEnvs();
    });

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

  describe("when proxy headers are NOT trusted (security)", () => {
    beforeEach(() => {
      vi.stubEnv("VERCEL", undefined);
      vi.stubEnv("TRUST_PROXY", undefined);
      vi.stubEnv("NODE_ENV", "production");
    });

    afterEach(() => {
      vi.unstubAllEnvs();
    });

    it("returns unknown even when x-real-ip is present", () => {
      const headers = new Headers({
        "x-real-ip": "198.51.100.5",
      });
      expect(getClientIpFromHeaders(headers)).toBe("unknown");
    });

    it("returns unknown even when x-forwarded-for is present", () => {
      const headers = new Headers({
        "x-forwarded-for": "203.0.113.10, 198.51.100.2",
      });
      expect(getClientIpFromHeaders(headers)).toBe("unknown");
    });

    it("returns unknown even when cf-connecting-ip is present", () => {
      const headers = new Headers({ "cf-connecting-ip": "9.9.9.9" });
      expect(getClientIpFromHeaders(headers)).toBe("unknown");
    });
  });

  describe("when running in development without explicit proxy trust", () => {
    beforeEach(() => {
      vi.stubEnv("VERCEL", undefined);
      vi.stubEnv("TRUST_PROXY", undefined);
      vi.stubEnv("NODE_ENV", "development");
    });

    afterEach(() => {
      vi.unstubAllEnvs();
    });

    it("uses proxy headers for local/CI compatibility", () => {
      const headers = new Headers({
        "x-forwarded-for": "203.0.113.10, 198.51.100.2",
      });
      expect(getClientIpFromHeaders(headers)).toBe("203.0.113.10");
    });
  });

  describe("TRUST_PROXY environment variable", () => {
    afterEach(() => {
      vi.unstubAllEnvs();
    });

    it("trusts proxy headers when TRUST_PROXY=true", () => {
      vi.stubEnv("VERCEL", undefined);
      vi.stubEnv("NODE_ENV", "production");
      vi.stubEnv("TRUST_PROXY", "true");
      const headers = new Headers({
        "x-real-ip": "198.51.100.5",
      });
      expect(getClientIpFromHeaders(headers)).toBe("198.51.100.5");
    });

    it("does not trust proxy headers in production when TRUST_PROXY is not set", () => {
      vi.stubEnv("VERCEL", undefined);
      vi.stubEnv("NODE_ENV", "production");
      vi.stubEnv("TRUST_PROXY", undefined);
      const headers = new Headers({
        "x-real-ip": "198.51.100.5",
      });
      expect(getClientIpFromHeaders(headers)).toBe("unknown");
    });
  });
});
