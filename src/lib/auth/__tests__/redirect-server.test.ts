/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

// Create hoisted mock functions so they can be accessed in tests
const mockLoggerWarn = vi.hoisted(() => vi.fn());
const mockLoggerError = vi.hoisted(() => vi.fn());

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
    error: mockLoggerError,
    warn: mockLoggerWarn,
  }),
}));

// Import after mocks are set up
import {
  AUTH_SERVER_FALLBACK_PATH,
  resolveServerRedirectUrl,
  safeNextPath,
} from "@/lib/auth/redirect-server";

describe("safeNextPath", () => {
  beforeEach(() => {
    mockLoggerWarn.mockClear();
    mockLoggerError.mockClear();
  });

  it("returns fallback for null", () => {
    expect(safeNextPath(null)).toBe("/dashboard");
  });

  it("returns fallback for undefined", () => {
    expect(safeNextPath(undefined)).toBe("/dashboard");
  });

  it("returns fallback for empty string", () => {
    expect(safeNextPath("")).toBe("/dashboard");
  });

  it("returns fallback for whitespace only", () => {
    expect(safeNextPath("   ")).toBe("/dashboard");
    expect(safeNextPath("\t\n")).toBe("/dashboard");
  });

  it("allows valid relative paths", () => {
    expect(safeNextPath("/dashboard")).toBe("/dashboard");
    expect(safeNextPath("/settings")).toBe("/settings");
    expect(safeNextPath("/trips/123")).toBe("/trips/123");
    expect(safeNextPath("/search?q=test")).toBe("/search?q=test");
  });

  it("blocks protocol-relative URLs (//evil.com) and logs security event", () => {
    expect(safeNextPath("//evil.com")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "protocol-relative" })
    );

    mockLoggerWarn.mockClear();
    expect(safeNextPath("//evil.com/path")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "protocol-relative" })
    );

    mockLoggerWarn.mockClear();
    expect(safeNextPath("//localhost")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "protocol-relative" })
    );
  });

  it("blocks absolute URLs with protocols and logs security event", () => {
    expect(safeNextPath("https://evil.com")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "absolute-url" })
    );

    mockLoggerWarn.mockClear();
    expect(safeNextPath("http://evil.com")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "absolute-url" })
    );

    // javascript: and data: are blocked as "missing-leading-slash" since they don't start with /
    mockLoggerWarn.mockClear();
    expect(safeNextPath("javascript:alert(1)")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "missing-leading-slash" })
    );
  });

  it("blocks paths not starting with / and logs security event", () => {
    expect(safeNextPath("dashboard")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "missing-leading-slash" })
    );

    mockLoggerWarn.mockClear();
    expect(safeNextPath("../etc/passwd")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "missing-leading-slash" })
    );
  });

  it("normalizes backslashes to forward slashes", () => {
    expect(safeNextPath("/path\\to\\page")).toBe("/path/to/page");
  });

  it("blocks backslash-based protocol-relative patterns after normalization and logs", () => {
    expect(safeNextPath("/\\evil.com")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "normalized-protocol-relative" })
    );
  });

  it("blocks URL-encoded protocol patterns and logs security event", () => {
    expect(safeNextPath("/%2Fevil.com")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "encoded-protocol-pattern" })
    );

    mockLoggerWarn.mockClear();
    expect(safeNextPath("/%2F%2Fevil.com")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "encoded-protocol-pattern" })
    );
  });

  it("handles double-encoded patterns safely", () => {
    const doubleEncoded = "/%252Fevil.com";
    const result = safeNextPath(doubleEncoded);
    expect(result.startsWith("/")).toBe(true);
    expect(result).not.toBe("//evil.com");
  });

  it("handles malformed URL encoding gracefully", () => {
    // Invalid percent-encoding - decodeURIComponent throws, but we handle it
    expect(safeNextPath("/%")).toMatch(/^\//);
    expect(safeNextPath("/%E")).toMatch(/^\//);
    expect(safeNextPath("/%GG")).toMatch(/^\//);
  });

  it("blocks paths with control characters and logs security event", () => {
    expect(safeNextPath("/\t/evil.com")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "contains-control-chars" })
    );

    mockLoggerWarn.mockClear();
    expect(safeNextPath("/\n/evil.com")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "contains-control-chars" })
    );
  });

  it("blocks paths containing @ (userinfo segments) and logs security event", () => {
    expect(safeNextPath("/@attacker.com")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "contains-userinfo-@" })
    );

    mockLoggerWarn.mockClear();
    expect(safeNextPath("/user@evil.com/path")).toBe("/dashboard");
    expect(mockLoggerWarn).toHaveBeenCalledWith(
      "blocked unsafe redirect path",
      expect.objectContaining({ reason: "contains-userinfo-@" })
    );
  });

  it("exports fallback constant", () => {
    expect(AUTH_SERVER_FALLBACK_PATH).toBe("/dashboard");
  });

  it("allows paths with URL fragments", () => {
    expect(safeNextPath("/dashboard#section1")).toBe("/dashboard#section1");
    expect(safeNextPath("/search?q=test#results")).toBe("/search?q=test#results");
    expect(safeNextPath("/trips/123#details")).toBe("/trips/123#details");
  });
});

describe("resolveServerRedirectUrl", () => {
  beforeEach(() => {
    vi.resetModules();
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

  it("uses request origin for valid relative path", () => {
    const request = createMockRequest("https://app.example.com/auth/callback");
    const result = resolveServerRedirectUrl(request, "/dashboard");
    expect(result).toBe("https://app.example.com/dashboard");
  });

  it("uses x-forwarded-host and x-forwarded-proto when present", () => {
    const request = createMockRequest("http://localhost:3000/auth/callback", {
      "x-forwarded-host": "example.com",
      "x-forwarded-proto": "https",
    });
    const result = resolveServerRedirectUrl(request, "/settings");
    expect(result).toBe("https://example.com/settings");
  });

  it("defaults to https when x-forwarded-proto is missing", () => {
    const request = createMockRequest("http://localhost:3000/auth/callback", {
      "x-forwarded-host": "example.com",
    });
    const result = resolveServerRedirectUrl(request, "/home");
    expect(result).toBe("https://example.com/home");
  });

  it("blocks open redirect attempts via next param", () => {
    const request = createMockRequest("https://app.example.com/auth/callback");
    expect(resolveServerRedirectUrl(request, "https://evil.com")).toBe(
      "https://app.example.com/dashboard"
    );
    expect(resolveServerRedirectUrl(request, "//evil.com")).toBe(
      "https://app.example.com/dashboard"
    );
  });

  it("handles comma-separated forwarded headers (first value)", () => {
    const request = createMockRequest("http://localhost:3000/auth/callback", {
      "x-forwarded-host": "first.com, second.com",
      "x-forwarded-proto": "https, http",
    });
    const result = resolveServerRedirectUrl(request, "/path");
    expect(result).toBe("https://first.com/path");
  });

  it("falls back to dashboard when next is missing", () => {
    const request = createMockRequest("https://app.example.com/auth/callback");
    expect(resolveServerRedirectUrl(request, null)).toBe(
      "https://app.example.com/dashboard"
    );
    expect(resolveServerRedirectUrl(request, undefined)).toBe(
      "https://app.example.com/dashboard"
    );
  });

  it("preserves URL fragments in redirect", () => {
    const request = createMockRequest("https://app.example.com/auth/callback");
    const result = resolveServerRedirectUrl(request, "/dashboard#section1");
    expect(result).toBe("https://app.example.com/dashboard#section1");
  });
});
