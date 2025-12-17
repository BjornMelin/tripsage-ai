/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getOriginFromRequest } from "@/lib/url/server-origin";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

vi.mock("server-only", () => ({}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: vi.fn((key: string, fallback: string) => {
    if (key === "APP_BASE_URL") return process.env.APP_BASE_URL || fallback;
    if (key === "NEXT_PUBLIC_SITE_URL")
      return process.env.NEXT_PUBLIC_SITE_URL || fallback;
    return fallback;
  }),
}));

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    error: vi.fn(),
    warn: vi.fn(),
  }),
}));

describe("getOriginFromRequest", () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    vi.resetModules();
    process.env = { ...originalEnv };
    process.env.APP_BASE_URL = undefined;
    process.env.NEXT_PUBLIC_SITE_URL = undefined;
    process.env.NEXT_PUBLIC_BASE_URL = undefined;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  function createMockRequest(
    url: string,
    headers: Record<string, string> = {}
  ): NextRequest {
    const headersObj = new Headers();
    for (const [key, value] of Object.entries(headers)) {
      headersObj.set(key, value);
    }
    return unsafeCast<NextRequest>({
      headers: headersObj,
      url,
    });
  }

  describe("with forwarded headers", () => {
    it("uses x-forwarded-host with x-forwarded-proto", () => {
      const request = createMockRequest("http://localhost:3000/callback", {
        "x-forwarded-host": "example.com",
        "x-forwarded-proto": "https",
      });
      expect(getOriginFromRequest(request)).toBe("https://example.com");
    });

    it("defaults to https when x-forwarded-proto is missing", () => {
      const request = createMockRequest("http://localhost:3000/callback", {
        "x-forwarded-host": "example.com",
      });
      expect(getOriginFromRequest(request)).toBe("https://example.com");
    });

    it("handles http protocol explicitly", () => {
      const request = createMockRequest("http://localhost:3000/callback", {
        "x-forwarded-host": "internal.example.com",
        "x-forwarded-proto": "http",
      });
      expect(getOriginFromRequest(request)).toBe("http://internal.example.com");
    });

    it("takes first value from comma-separated x-forwarded-host", () => {
      const request = createMockRequest("http://localhost:3000/callback", {
        "x-forwarded-host": "first.com, second.com, third.com",
        "x-forwarded-proto": "https",
      });
      expect(getOriginFromRequest(request)).toBe("https://first.com");
    });

    it("takes first value from comma-separated x-forwarded-proto", () => {
      const request = createMockRequest("http://localhost:3000/callback", {
        "x-forwarded-host": "example.com",
        "x-forwarded-proto": "https, http",
      });
      expect(getOriginFromRequest(request)).toBe("https://example.com");
    });

    it("handles whitespace in comma-separated values", () => {
      const request = createMockRequest("http://localhost:3000/callback", {
        "x-forwarded-host": "  example.com  ,  other.com  ",
        "x-forwarded-proto": "  https  ,  http  ",
      });
      expect(getOriginFromRequest(request)).toBe("https://example.com");
    });

    it("defaults to https for invalid protocols", () => {
      const request = createMockRequest("http://localhost:3000/callback", {
        "x-forwarded-host": "example.com",
        "x-forwarded-proto": "ftp",
      });
      expect(getOriginFromRequest(request)).toBe("https://example.com");
    });

    it("normalizes protocol to lowercase", () => {
      const request = createMockRequest("http://localhost:3000/callback", {
        "x-forwarded-host": "example.com",
        "x-forwarded-proto": "HTTPS",
      });
      expect(getOriginFromRequest(request)).toBe("https://example.com");
    });
  });

  describe("without forwarded headers", () => {
    it("falls back to request URL origin", () => {
      const request = createMockRequest("https://app.example.com/callback");
      expect(getOriginFromRequest(request)).toBe("https://app.example.com");
    });

    it("preserves port in request URL origin", () => {
      const request = createMockRequest("http://localhost:3000/callback");
      expect(getOriginFromRequest(request)).toBe("http://localhost:3000");
    });
  });

  describe("edge cases", () => {
    it("handles empty x-forwarded-host by falling back", () => {
      const request = createMockRequest("https://fallback.com/callback", {
        "x-forwarded-host": "",
      });
      expect(getOriginFromRequest(request)).toBe("https://fallback.com");
    });

    it("handles whitespace-only x-forwarded-host by falling back", () => {
      const request = createMockRequest("https://fallback.com/callback", {
        "x-forwarded-host": "   ",
      });
      expect(getOriginFromRequest(request)).toBe("https://fallback.com");
    });
  });

  describe("security - configured origin priority", () => {
    it("prefers APP_BASE_URL over x-forwarded-host", () => {
      process.env.APP_BASE_URL = "https://configured.com";
      const request = createMockRequest("http://localhost:3000/callback", {
        "x-forwarded-host": "attacker.com",
        "x-forwarded-proto": "https",
      });
      expect(getOriginFromRequest(request)).toBe("https://configured.com");
    });

    it("prefers NEXT_PUBLIC_SITE_URL over x-forwarded-host", () => {
      process.env.NEXT_PUBLIC_SITE_URL = "https://site.com";
      const request = createMockRequest("http://localhost:3000/callback", {
        "x-forwarded-host": "attacker.com",
        "x-forwarded-proto": "https",
      });
      expect(getOriginFromRequest(request)).toBe("https://site.com");
    });
  });

  describe("security - host validation", () => {
    it("rejects x-forwarded-host with @ character (userinfo injection)", () => {
      const request = createMockRequest("https://fallback.com/callback", {
        "x-forwarded-host": "evil.com@trusted.com",
        "x-forwarded-proto": "https",
      });
      expect(getOriginFromRequest(request)).toBe("https://fallback.com");
    });

    it("rejects x-forwarded-host with spaces", () => {
      const request = createMockRequest("https://fallback.com/callback", {
        "x-forwarded-host": "evil .com",
        "x-forwarded-proto": "https",
      });
      expect(getOriginFromRequest(request)).toBe("https://fallback.com");
    });

    it("rejects x-forwarded-host with control characters", () => {
      const request = createMockRequest("https://fallback.com/callback", {
        "x-forwarded-host": "evil\t.com",
        "x-forwarded-proto": "https",
      });
      expect(getOriginFromRequest(request)).toBe("https://fallback.com");
    });

    it("rejects malformed hostnames", () => {
      const request = createMockRequest("https://fallback.com/callback", {
        "x-forwarded-host": "-invalid.com",
        "x-forwarded-proto": "https",
      });
      expect(getOriginFromRequest(request)).toBe("https://fallback.com");
    });

    it("accepts valid hostname with port", () => {
      const request = createMockRequest("http://localhost:3000/callback", {
        "x-forwarded-host": "example.com:8080",
        "x-forwarded-proto": "https",
      });
      expect(getOriginFromRequest(request)).toBe("https://example.com:8080");
    });
  });
});
