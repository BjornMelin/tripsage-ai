/**
 * @fileoverview Tests for the auth callback route handler.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock the server client used by the route handler
const exchangeMock: any = vi.fn(async (_code: string) => ({ error: null }));
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { exchangeCodeForSession: exchangeMock },
  })),
}));

// Import after mocks
import { GET } from "../route";

/**
 * Creates a mock request object for testing.
 * @param url The request URL.
 * @param headers Optional headers for the request.
 * @return A mock request object.
 */
function makeReq(url: string, headers: Record<string, string> = {}): any {
  return { url, headers: new Headers(headers) };
}

describe("auth/callback route", () => {
  beforeEach(() => {
    exchangeMock.mockClear();
  });

  it("exchanges code and redirects to next path (local)", async () => {
    const req = makeReq("http://localhost/auth/callback?code=abc&next=%2Fdashboard");
    const res = await GET(req);
    expect(exchangeMock).toHaveBeenCalledWith("abc");
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/dashboard");
  });

  it("falls back to origin when next is invalid", async () => {
    const req = makeReq(
      "https://app.example.com/auth/callback?code=abc&next=https://evil"
    );
    const res = await GET(req);
    expect(res.headers.get("location")).toBe("https://app.example.com/dashboard");
  });

  it("redirects to login on error", async () => {
    exchangeMock.mockResolvedValueOnce({ error: new Error("bad") });
    const req = makeReq("https://app.example.com/auth/callback?code=bad");
    const res = await GET(req);
    expect(res.headers.get("location")).toBe(
      "https://app.example.com/login?error=oauth_failed"
    );
  });
});
