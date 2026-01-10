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
      });

      const response = await proxy(request);
      const cspHeader = response.headers.get("Content-Security-Policy");

      expect(cspHeader).toBeTypeOf("string");
      if (typeof cspHeader !== "string") {
        throw new Error("Expected CSP header to be present");
      }

      const nonce = extractNonceFromCsp(cspHeader);

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

  it("keeps dev-only CSP allowances (development)", async () => {
    const { proxy } = await import("@/proxy");
    vi.stubEnv("NODE_ENV", "development");

    try {
      const request = unsafeCast<NextRequest>({
        cookies: createMockRequestCookies({}),
        headers: new Headers(),
      });

      const response = await proxy(request);
      const cspHeader = response.headers.get("Content-Security-Policy");

      expect(cspHeader).toBeTypeOf("string");
      if (typeof cspHeader !== "string") {
        throw new Error("Expected CSP header to be present");
      }

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
      });

      const response = await proxy(request);
      const requestCookieHeader = response.headers.get("x-middleware-request-cookie");

      expect(requestCookieHeader).toContain("sb-access-token=refreshed-access");
      expect(requestCookieHeader).toContain("sb-refresh-token=refreshed-refresh");
    } finally {
      vi.unstubAllEnvs();
    }
  });
});
