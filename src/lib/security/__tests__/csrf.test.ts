/** @vitest-environment node */

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { __resetServerEnvCacheForTest } from "@/lib/env/server";
import { requireSameOrigin } from "@/lib/security/csrf";

/**
 * Creates a mock NextRequest for testing security guards.
 *
 * @param url - The request URL.
 * @param headers - Optional HTTP headers to include.
 * @returns A NextRequest configured for testing.
 */
function makeRequest(url: string, headers?: Record<string, string>): NextRequest {
  return new NextRequest(url, {
    headers,
    method: "POST",
  });
}

describe("requireSameOrigin", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    __resetServerEnvCacheForTest();
  });
  it("allows matching Origin header", () => {
    const req = makeRequest("https://app.example.com/api/test", {
      origin: "https://app.example.com",
    });
    const result = requireSameOrigin(req);
    expect(result.ok).toBe(true);
  });

  it("allows matching Referer header", () => {
    const req = makeRequest("https://app.example.com/api/test", {
      referer: "https://app.example.com/settings",
    });
    const result = requireSameOrigin(req);
    expect(result.ok).toBe(true);
  });

  it("rejects mismatched Origin header", () => {
    const req = makeRequest("https://app.example.com/api/test", {
      origin: "https://evil.example.net",
    });
    const result = requireSameOrigin(req);
    expect(result.ok).toBe(false);
  });

  it("rejects missing Origin and Referer by default", () => {
    const req = makeRequest("https://app.example.com/api/test");
    const result = requireSameOrigin(req);
    expect(result.ok).toBe(false);
  });

  it("allows missing headers when explicitly configured", () => {
    const req = makeRequest("https://app.example.com/api/test");
    const result = requireSameOrigin(req, { allowMissingHeaders: true });
    expect(result.ok).toBe(true);
  });

  it("allows additional configured origins", () => {
    const req = makeRequest("https://app.example.com/api/test", {
      origin: "https://partner.example.com",
    });
    const result = requireSameOrigin(req, {
      allowedOrigins: ["https://partner.example.com"],
    });
    expect(result.ok).toBe(true);
  });

  it("allows cross-site requests when origin is in allowedOrigins", () => {
    const req = makeRequest("https://app.example.com/api/test", {
      origin: "https://partner.example.com",
      "sec-fetch-site": "cross-site",
    });
    const result = requireSameOrigin(req, {
      allowedOrigins: ["https://partner.example.com"],
    });
    expect(result.ok).toBe(true);
  });

  it("blocks cross-site requests when origin is not allowlisted", () => {
    const req = makeRequest("https://app.example.com/api/test", {
      origin: "https://evil.example.net",
      "sec-fetch-site": "cross-site",
    });
    const result = requireSameOrigin(req);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe(
        "Request blocked by Sec-Fetch-Site (not same-origin or same-site)"
      );
    }
  });

  it("rejects malformed Origin header", () => {
    const req = makeRequest("https://app.example.com/api/test", {
      origin: "not-a-valid-url",
    });
    const result = requireSameOrigin(req);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("Invalid Origin or Referer header");
    }
  });

  it("treats literal 'null' Origin as missing and falls back to Referer", () => {
    const req = makeRequest("https://app.example.com/api/test", {
      origin: "null",
      referer: "https://app.example.com/dashboard",
    });
    const result = requireSameOrigin(req);
    expect(result.ok).toBe(true);
  });

  it("prioritizes Origin over Referer when both are present", () => {
    const req = makeRequest("https://app.example.com/api/test", {
      origin: "https://evil.example.net",
      referer: "https://app.example.com/dashboard",
    });
    const result = requireSameOrigin(req);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("Request origin does not match expected origin");
    }
  });

  it("normalizes origins case-insensitively", () => {
    // 1. Mixed-case request URL vs lower-case Origin header
    const req1 = makeRequest("https://APP.EXAMPLE.COM/api/test", {
      origin: "https://app.example.com",
    });
    // Expected origin from request URL will be normalized to lowercase
    const result1 = requireSameOrigin(req1);
    expect(result1.ok).toBe(true);

    // 2. Lower-case request URL vs mixed-case Origin header
    const req2 = makeRequest("https://app.example.com/api/test", {
      origin: "https://App.Example.Com",
    });
    const result2 = requireSameOrigin(req2);
    expect(result2.ok).toBe(true);

    // 3. Mixed-case allowedOrigins configuration
    const req3 = makeRequest("https://app.example.com/api/test", {
      origin: "https://other.example.net",
    });
    const result3 = requireSameOrigin(req3, {
      allowedOrigins: ["HTTPS://OTHER.EXAMPLE.NET"],
    });
    expect(result3.ok).toBe(true);
  });

  it("matches IPv6 origins with bracketed hosts", () => {
    vi.stubEnv("APP_BASE_URL", "https://[::1]:3000");
    __resetServerEnvCacheForTest();
    const req = makeRequest("https://[::1]:3000/api/test", {
      origin: "https://[::1]:3000",
    });
    const result = requireSameOrigin(req);
    expect(result.ok).toBe(true);
  });
});
