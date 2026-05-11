/** @vitest-environment node */

import type { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { unsafeCast } from "@/test/helpers/unsafe-cast";

type CookieAdapter = {
  getAll: () => { name: string; value: string }[];
  setAll?: (
    cookies: { name: string; value: string; options?: Record<string, unknown> }[]
  ) => void;
};

let lastCookieAdapter: CookieAdapter | null = null;

vi.mock("@/lib/supabase/factory", () => ({
  createMiddlewareSupabase: (options: { cookies: CookieAdapter }) => {
    lastCookieAdapter = options.cookies;
    return {};
  },
  getCurrentUser: () => {
    lastCookieAdapter?.setAll?.([
      {
        name: "sb-access-token",
        options: { path: "/" },
        value: "refreshed-access",
      },
      {
        name: "sb-refresh-token",
        options: { path: "/" },
        value: "refreshed-refresh",
      },
    ]);
    return null;
  },
}));

function extractNonceFromCsp(cspHeader: string): string {
  const match = /'nonce-([^']+)'/.exec(cspHeader);
  if (!match?.[1]) {
    throw new Error(`Expected nonce in CSP header, got: ${cspHeader}`);
  }
  return match[1];
}

function getCspDirective(cspHeader: string, directive: string): string {
  return (
    cspHeader
      .split(";")
      .map((part) => part.trim())
      .find((part) => part.startsWith(`${directive} `)) ?? ""
  );
}

function createMockRequestCookies(initial: Record<string, string>) {
  const store = new Map(Object.entries(initial));
  return {
    delete: (name: string | { name: string }) => {
      const key = typeof name === "string" ? name : name.name;
      store.delete(key);
    },
    getAll: () => Array.from(store.entries()).map(([name, value]) => ({ name, value })),
    set: (name: string | { name: string; value: string }, value?: string) => {
      if (typeof name === "string") {
        store.set(name, value ?? "");
        return;
      }
      store.set(name.name, name.value);
    },
    toString: () =>
      Array.from(store.entries())
        .map(([name, value]) => `${name}=${value}`)
        .join("; "),
  };
}

describe("src/proxy.ts CSP nonce", () => {
  beforeEach(() => {
    lastCookieAdapter = null;
  });

  it("injects CSP nonce and propagates request headers for Next.js nonce extraction (production)", async () => {
    const { proxy } = await import("@/proxy");
    vi.stubEnv("NODE_ENV", "production");

    try {
      const request = unsafeCast<NextRequest>({
        cookies: createMockRequestCookies({}),
        headers: new Headers(),
        url: "https://example.com/dashboard",
      });

      const response = await proxy(request);
      const cspHeader = response.headers.get("Content-Security-Policy");

      expect(cspHeader).toBeTypeOf("string");

      const nonce = extractNonceFromCsp(cspHeader as string);

      // Next.js extracts the nonce from the CSP header present on the request during SSR.
      // NextResponse.next({ request: { headers } }) encodes request header overrides via
      // x-middleware-request-* response headers.
      expect(response.headers.get("x-middleware-request-x-nonce")).toBe(nonce);
      expect(response.headers.get("x-middleware-request-content-security-policy")).toBe(
        cspHeader
      );
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("keeps public static routes compatible without request nonce propagation (production)", async () => {
    const { proxy } = await import("@/proxy");
    vi.stubEnv("NODE_ENV", "production");

    try {
      const request = unsafeCast<NextRequest>({
        cookies: createMockRequestCookies({}),
        headers: new Headers(),
        url: "https://example.com/",
      });

      const response = await proxy(request);
      const cspHeader = response.headers.get("Content-Security-Policy");
      const reportOnlyCspHeader = response.headers.get(
        "Content-Security-Policy-Report-Only"
      );

      expect(cspHeader).toBeTypeOf("string");
      expect(cspHeader).toContain("script-src 'self' 'unsafe-inline'");
      expect(cspHeader).not.toContain("'nonce-");
      expect(reportOnlyCspHeader).toBeTypeOf("string");
      expect(reportOnlyCspHeader).toContain("report-uri /api/security/csp-report");
      expect(getCspDirective(reportOnlyCspHeader as string, "script-src")).toContain(
        "'report-sample'"
      );
      expect(
        getCspDirective(reportOnlyCspHeader as string, "script-src")
      ).not.toContain("'unsafe-inline'");
      expect(response.headers.get("x-middleware-request-x-nonce")).toBeNull();
      expect(
        response.headers.get("x-middleware-request-content-security-policy")
      ).toBeNull();
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("uses an explicit CSP report endpoint when configured", async () => {
    const { proxy } = await import("@/proxy");
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("CSP_REPORT_URI", "https://reports.example.com/csp");

    try {
      const request = unsafeCast<NextRequest>({
        cookies: createMockRequestCookies({}),
        headers: new Headers(),
        url: "https://example.com/",
      });

      const response = await proxy(request);

      expect(response.headers.get("Content-Security-Policy-Report-Only")).toContain(
        "report-uri https://reports.example.com/csp"
      );
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("excludes static assets and metadata files from proxy matcher", async () => {
    const { config } = await import("@/proxy");
    const matcherSource = config.matcher[0]?.source;

    expect(matcherSource).toContain("_next/static");
    expect(matcherSource).toContain("_next/image");
    expect(matcherSource).toContain("favicon.ico");
    expect(matcherSource).toContain("robots.txt");
    expect(matcherSource).toContain("sitemap.xml");
    expect(matcherSource).toContain("manifest.webmanifest");
    expect(matcherSource).toContain("manifest.json");
  });

  it("keeps dev-only CSP allowances (development)", async () => {
    const { proxy } = await import("@/proxy");
    vi.stubEnv("NODE_ENV", "development");

    try {
      const request = unsafeCast<NextRequest>({
        cookies: createMockRequestCookies({}),
        headers: new Headers(),
        url: "https://example.com/",
      });

      const response = await proxy(request);
      const cspHeader = response.headers.get("Content-Security-Policy");

      expect(cspHeader).toBeTypeOf("string");

      expect(cspHeader).toContain("script-src");
      expect(cspHeader).toContain("'unsafe-eval'");
      expect(cspHeader).toContain("'unsafe-inline'");
      expect(cspHeader).toContain("style-src 'self' 'unsafe-inline'");
      expect(cspHeader).not.toContain("upgrade-insecure-requests");
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("propagates refreshed Supabase cookies to the current request", async () => {
    const { proxy } = await import("@/proxy");
    vi.stubEnv("NODE_ENV", "production");

    try {
      const request = unsafeCast<NextRequest>({
        cookies: createMockRequestCookies({
          "sb-access-token": "stale-access",
          "sb-refresh-token": "stale-refresh",
        }),
        headers: new Headers(),
        url: "https://example.com/dashboard",
      });

      const response = await proxy(request);
      const requestCookieHeader = response.headers.get("x-middleware-request-cookie");

      expect(requestCookieHeader).toContain("sb-access-token=refreshed-access");
      expect(requestCookieHeader).toContain("sb-refresh-token=refreshed-refresh");
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("keeps Supabase cookie refresh active for authenticated routes in development", async () => {
    const { proxy } = await import("@/proxy");
    vi.stubEnv("NODE_ENV", "development");

    try {
      const request = unsafeCast<NextRequest>({
        cookies: createMockRequestCookies({
          "sb-access-token": "stale-access",
          "sb-refresh-token": "stale-refresh",
        }),
        headers: new Headers(),
        url: "https://example.com/dashboard",
      });

      const response = await proxy(request);
      const requestCookieHeader = response.headers.get("x-middleware-request-cookie");

      expect(requestCookieHeader).toContain("sb-access-token=refreshed-access");
      expect(requestCookieHeader).toContain("sb-refresh-token=refreshed-refresh");
      expect(response.headers.get("x-middleware-request-x-nonce")).toBeNull();
    } finally {
      vi.unstubAllEnvs();
    }
  });
});
