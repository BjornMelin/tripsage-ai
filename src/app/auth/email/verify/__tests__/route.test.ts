/** @vitest-environment node */

import { NextRequest } from "next/server";
import { describe, expect, it, vi } from "vitest";
import { getMockCookiesForTest } from "@/test/helpers/route";

const COOKIES_MOCK = vi.hoisted(() => vi.fn());

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: COOKIES_MOCK,
}));

COOKIES_MOCK.mockImplementation(() =>
  Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
);

import { POST } from "../route";

describe("POST /auth/email/verify", () => {
  it("returns 413 and cancels stream when body exceeds limit", async () => {
    let pulls = 0;
    let cancelled = false;

    const chunk = new Uint8Array(2048).fill(97);
    const stream = new ReadableStream<Uint8Array>({
      cancel() {
        cancelled = true;
      },
      pull(controller) {
        pulls += 1;
        controller.enqueue(chunk);
      },
    });

    const req = new NextRequest("https://example.com/auth/email/verify", {
      body: stream,
      // Required by Node's fetch when using a streaming request body.
      duplex: "half",
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const res = await POST(req);
    expect(res.status).toBe(413);
    expect(await res.json()).toEqual({
      code: "PAYLOAD_TOO_LARGE",
      message: "Request body exceeds limit",
    });
    expect(cancelled).toBe(true);
    expect(pulls).toBeLessThan(20);
  });
});
