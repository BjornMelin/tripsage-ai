/**
 * @fileoverview Shared test helper for creating minimal NextRequest mocks.
 *
 * Use this helper when testing route handlers that only need to access
 * request headers. For tests requiring full NextRequest functionality,
 * consider a more complete mock or integration tests.
 */

import type { NextRequest } from "next/server";
import { unsafeCast } from "./unsafe-cast";

/**
 * Creates a minimal NextRequest mock with only headers populated.
 *
 * @param headers - Optional headers to include in the mock request.
 * @returns A minimal NextRequest mock suitable for testing header-only access.
 *
 * @example
 * ```typescript
 * const req = makeRequest({ "x-real-ip": "192.168.1.1" });
 * expect(getClientIpFromHeaders(req)).toBe("192.168.1.1");
 * ```
 *
 * @internal Only use where headers are the sole accessed property.
 */
export function makeRequest(headers: HeadersInit = {}): NextRequest {
  return unsafeCast<NextRequest>({ headers: new Headers(headers) });
}
