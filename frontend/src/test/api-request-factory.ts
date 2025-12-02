/**
 * @fileoverview Minimal helper to fabricate a Next.js NextRequest with JSON body for API route tests.
 */

import { NextRequest } from "next/server";

/**
 * Minimal helper to fabricate a Next.js NextRequest with JSON body for API route tests.
 */
export function makeJsonRequest(
  url: string,
  body: unknown,
  init?: { headers?: HeadersInit; method?: string }
): NextRequest {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  const method = init?.method ?? "POST";
  return new NextRequest(
    new Request(url, {
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
      headers,
      method,
    })
  );
}
