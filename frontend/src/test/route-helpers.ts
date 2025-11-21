/**
 * @fileoverview Test helpers for Next.js Route Handlers.
 * Provides utilities to create mock requests with proper cookies/headers context
 * for testing route handlers that use `cookies()` from `next/headers`.
 */

import type { ReadonlyRequestCookies } from "next/dist/server/web/spec-extension/adapters/request-cookies";
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
  url?: string;
}): NextRequest {
  const {
    body,
    cookies: cookieMap = {},
    headers: headerMap = {},
    method = "POST",
    url = "http://localhost/api/test",
  } = options;

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

  // Create request with body if provided
  const init: RequestInit = {
    headers,
    method,
  };

  if (body !== undefined) {
    init.body = typeof body === "string" ? body : JSON.stringify(body);
    if (typeof body === "object") {
      headers.set("content-type", "application/json");
    }
  }

  // NextRequest constructor accepts its own RequestInit type
  return new NextRequest(
    url,
    init as unknown as ConstructorParameters<typeof NextRequest>[1]
  );
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
  const cookies = new Map<string, string>();
  Object.entries(cookieMap).forEach(([key, value]) => {
    cookies.set(key, value);
  });

  return {
    clear: () => {
      throw new Error("Mock cookies are readonly");
    },
    delete: () => {
      throw new Error("Mock cookies are readonly");
    },
    get: (name: string) => {
      const value = cookies.get(name);
      return value
        ? {
            name,
            value,
          }
        : undefined;
    },
    getAll: () =>
      Array.from(cookies.entries()).map(([name, value]) => ({ name, value })),
    has: (name: string) => cookies.has(name),
    set: () => {
      throw new Error("Mock cookies are readonly");
    },
    toString: () => {
      return Array.from(cookies.entries())
        .map(([key, value]) => `${key}=${value}`)
        .join("; ");
    },
  } as unknown as ReadonlyRequestCookies;
}

/**
 * Creates a setup function for mocking `next/headers` cookies() in route handler tests.
 *
 * Use this pattern in your test file:
 * ```ts
 * import { vi } from "vitest";
 * import { createMockCookies } from "@/test/route-helpers";
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
