/**
 * @fileoverview Tests for the auth confirm route handler.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const VERIFY_MOCK: any = vi.fn(async (_args: any) => ({ error: null }));
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({ auth: { verifyOtp: VERIFY_MOCK } })),
}));

// Mock next/navigation redirect helper
const REDIRECT_MOCK = vi.fn();
vi.mock("next/navigation", async (importOriginal) => {
  const actual = await importOriginal<any>();
  return {
    ...actual,
    redirect: (...args: any[]) => REDIRECT_MOCK(...args),
  };
});

import { GET } from "../route";

/**
 * Creates a mock request object for testing.
 * @param url The request URL.
 * @return A mock request object.
 */
function makeReq(url: string): any {
  return { headers: new Headers(), url };
}

describe("auth/confirm route", () => {
  beforeEach(() => {
    VERIFY_MOCK.mockClear();
    REDIRECT_MOCK.mockClear();
  });

  it("verifies token and redirects to next path", async () => {
    const req = makeReq(
      "https://app.example.com/auth/confirm?token_hash=thash&type=email&next=%2F"
    );
    await GET(req);
    expect(VERIFY_MOCK).toHaveBeenCalledWith({ token_hash: "thash", type: "email" });
    expect(REDIRECT_MOCK).toHaveBeenCalledWith("/");
  });

  it("redirects to error on verify failure", async () => {
    VERIFY_MOCK.mockResolvedValueOnce({ error: new Error("invalid") });
    const req = makeReq(
      "https://app.example.com/auth/confirm?token_hash=bad&type=email"
    );
    await GET(req);
    expect(REDIRECT_MOCK).toHaveBeenCalledWith("/error");
  });
});
