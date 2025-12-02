import { NextRequest } from "next/server";

/**
 * Minimal helper to fabricate a Next.js NextRequest with JSON body for API route tests.
 */
export function makeJsonRequest(url: string, body: unknown): NextRequest {
  return new NextRequest(
    new Request(url, {
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    })
  );
}
