/** @vitest-environment node */

import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";
import { requireSameOrigin } from "@/lib/security/csrf";

function makeRequest(url: string, headers?: Record<string, string>): NextRequest {
  return new NextRequest(url, {
    headers,
    method: "POST",
  });
}

describe("requireSameOrigin", () => {
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
});
