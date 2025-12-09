/** @vitest-environment node */

import type { MockInstance } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/helpers/route";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

// Mock the server client used by the route handler
const EXCHANGE_MOCK = vi.hoisted(
  () =>
    vi.fn(async (_code: string) => ({ error: null })) as MockInstance<
      (_code: string) => Promise<{ error: Error | null }>
    >
);
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { exchangeCodeForSession: EXCHANGE_MOCK },
  })),
}));

// Import after mocks
import { GET } from "../route";

describe("auth/callback route", () => {
  beforeEach(() => {
    EXCHANGE_MOCK.mockClear();
  });

  it("exchanges code and redirects to next path (local)", async () => {
    const req = createMockNextRequest({
      headers: {},
      method: "GET",
      url: "http://localhost/auth/callback?code=abc&next=%2Fdashboard",
    });
    const res = await GET(req);
    expect(EXCHANGE_MOCK).toHaveBeenCalledWith("abc");
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/dashboard");
  });

  it("falls back to origin when next is invalid", async () => {
    const req = createMockNextRequest({
      headers: {},
      method: "GET",
      url: "https://app.example.com/auth/callback?code=abc&next=https://evil",
    });
    const res = await GET(req);
    expect(res.headers.get("location")).toBe("https://app.example.com/dashboard");
  });

  it("redirects to login on error", async () => {
    EXCHANGE_MOCK.mockResolvedValueOnce({ error: new Error("bad") });
    const req = createMockNextRequest({
      headers: {},
      method: "GET",
      url: "https://app.example.com/auth/callback?code=bad",
    });
    const res = await GET(req);
    expect(res.headers.get("location")).toBe(
      "https://app.example.com/login?error=oauth_failed"
    );
  });
});
