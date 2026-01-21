/**
 * @fileoverview Test helpers for Next.js Route Handlers.
 * Provides utilities to create mock requests with proper cookies/headers context
 * for testing route handlers that use `cookies()` from `next/headers`.
 */

import {
  type ReadonlyRequestCookies,
  RequestCookiesAdapter,
} from "next/dist/server/web/spec-extension/adapters/request-cookies";
import { RequestCookies } from "next/dist/server/web/spec-extension/cookies";
import { NextRequest } from "next/server";

/**
 * Creates a mock NextRequest with cookies and headers for testing.
 *
 * @param options Request configuration options.
 * @returns A NextRequest-like object suitable for route handler tests.
 */
export function createMockNextRequest(options: {
  body?: unknown;
  cookies?: Record<string, string>;
  headers?: Record<string, string>;
  method?: string;
  searchParams?: Record<string, string>;
  url?: string;
}): NextRequest {
  const {
    body,
    cookies: cookieMap = {},
    headers: headerMap = {},
    method = "POST",
    searchParams,
    url = "http://localhost/api/test",
  } = options;

  // Build URL with search params if provided
  const urlObj = new URL(url);
  if (searchParams) {
    Object.entries(searchParams).forEach(([key, value]) => {
      urlObj.searchParams.set(key, value);
    });
  }

  // Build cookie header string
  const cookieHeader = Object.entries(cookieMap)
    .map(([key, value]) => `${key}=${value}`)
    .join("; ");

  // Create headers with cookies
  const headers = new Headers();
  if (cookieHeader) {
    headers.set("cookie", cookieHeader);
  }
  Object.entries(headerMap).forEach(([key, value]) => {
    headers.set(key.toLowerCase(), value);
  });

  const resolveConfiguredOrigin = (): string | null => {
    const candidates = [
      process.env.APP_BASE_URL,
      process.env.NEXT_PUBLIC_SITE_URL,
      process.env.NEXT_PUBLIC_BASE_URL,
      process.env.NEXT_PUBLIC_APP_URL,
    ];
    for (const candidate of candidates) {
      if (!candidate) continue;
      try {
        return new URL(candidate).origin;
      } catch {
        // Ignore invalid URLs in test env overrides.
      }
    }
    return null;
  };

  const upperMethod = method.toUpperCase();
  if (
    !headers.has("origin") &&
    upperMethod !== "GET" &&
    upperMethod !== "HEAD" &&
    upperMethod !== "OPTIONS"
  ) {
    headers.set("origin", resolveConfiguredOrigin() ?? urlObj.origin);
  }

  // Create request with body if provided
  type NextRequestInit = NonNullable<ConstructorParameters<typeof NextRequest>[1]>;
  const init: NextRequestInit = {
    headers,
    method,
  };

  if (body !== undefined) {
    init.body = typeof body === "string" ? body : JSON.stringify(body);
    if (typeof body === "object") {
      headers.set("content-type", "application/json");
    }
  }

  return new NextRequest(urlObj.toString(), init);
}

/**
 * Mock implementation of Next.js cookies() that returns a ReadonlyRequestCookies
 * from the provided cookie map.
 *
 * This should be used with vi.mock() to replace the real cookies() function
 * in route handler tests.
 *
 * @param cookieMap Map of cookie name to value.
 * @returns Mock ReadonlyRequestCookies instance.
 */
export function createMockCookies(
  cookieMap: Record<string, string> = {}
): ReadonlyRequestCookies {
  const cookieHeader = Object.entries(cookieMap)
    .map(([key, value]) => `${key}=${value}`)
    .join("; ");
  const headers = new Headers();
  if (cookieHeader) {
    headers.set("cookie", cookieHeader);
  }

  return RequestCookiesAdapter.seal(new RequestCookies(headers));
}

/**
 * Creates a setup function for mocking `next/headers` cookies() in route handler tests.
 *
 * Use this pattern in your test file:
 * ```ts
 * import { vi } from "vitest";
 * import { createMockCookies } from "@/test/helpers/route";
 *
 * vi.mock("next/headers", () => ({
 *   cookies: vi.fn(() => Promise.resolve(createMockCookies({ "sb-access-token": "test-token" }))),
 * }));
 * ```
 *
 * @param cookieMap Map of cookie name to value.
 * @returns Mock ReadonlyRequestCookies instance.
 */
export function getMockCookiesForTest(cookieMap: Record<string, string> = {}) {
  return createMockCookies(cookieMap);
}

/**
 * Create a Next.js route params context matching app router handler signature.
 *
 * @param params Route params key/value map.
 * @returns Context with params promise.
 */
export function createRouteParamsContext(params: Record<string, string> = {}): {
  params: Promise<Record<string, string>>;
} {
  return { params: Promise.resolve(params) };
}

/**
 * Helper to run a route handler function with proper request context.
 *
 * @param handler Route handler function (POST, GET, etc.).
 * @param request Mock NextRequest.
 * @param context Route params context (defaults to empty params).
 * @returns Response from the handler.
 */
export function runRouteHandler(
  handler: (
    req: NextRequest,
    context: { params: Promise<Record<string, string>> }
  ) => Promise<Response>,
  request: NextRequest,
  context: { params: Promise<Record<string, string>> } = createRouteParamsContext()
): Promise<Response> {
  return handler(request, context);
}
