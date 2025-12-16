/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  AUTH_SERVER_FALLBACK_PATH,
  resolveServerRedirectUrl,
  safeNextPath,
} from "@/lib/auth/redirect-server";

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

describe("safeNextPath", () => {
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

  it("blocks protocol-relative URLs (//evil.com)", () => {
    expect(safeNextPath("//evil.com")).toBe("/dashboard");
    expect(safeNextPath("//evil.com/path")).toBe("/dashboard");
    expect(safeNextPath("//localhost")).toBe("/dashboard");
  });

  it("blocks absolute URLs with protocols", () => {
    expect(safeNextPath("https://evil.com")).toBe("/dashboard");
    expect(safeNextPath("http://evil.com")).toBe("/dashboard");
    expect(safeNextPath("https://evil.com/callback")).toBe("/dashboard");
    expect(safeNextPath("javascript:alert(1)")).toBe("/dashboard");
    expect(safeNextPath("data:text/html,<script>")).toBe("/dashboard");
  });

  it("blocks paths not starting with /", () => {
    expect(safeNextPath("dashboard")).toBe("/dashboard");
    expect(safeNextPath("../etc/passwd")).toBe("/dashboard");
    expect(safeNextPath(".hidden")).toBe("/dashboard");
  });

  it("normalizes backslashes to forward slashes", () => {
    expect(safeNextPath("/path\\to\\page")).toBe("/path/to/page");
  });

  it("blocks backslash-based protocol-relative patterns after normalization", () => {
    expect(safeNextPath("/\\evil.com")).toBe("/dashboard");
  });

  it("blocks URL-encoded protocol patterns", () => {
    expect(safeNextPath("/%2Fevil.com")).toBe("/dashboard");
    expect(safeNextPath("/%2F%2Fevil.com")).toBe("/dashboard");
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

  it("blocks paths with control characters", () => {
    expect(safeNextPath("/\t/evil.com")).toBe("/dashboard");
    expect(safeNextPath("/\n/evil.com")).toBe("/dashboard");
    expect(safeNextPath("/\r/evil.com")).toBe("/dashboard");
    expect(safeNextPath("/path\twith\ttabs")).toBe("/dashboard");
  });

  it("blocks paths containing @ (userinfo segments)", () => {
    expect(safeNextPath("/@attacker.com")).toBe("/dashboard");
    expect(safeNextPath("/user@evil.com/path")).toBe("/dashboard");
    expect(safeNextPath("/@")).toBe("/dashboard");
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
    return {
      headers: headersObj,
      url,
    } as unknown as NextRequest;
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
