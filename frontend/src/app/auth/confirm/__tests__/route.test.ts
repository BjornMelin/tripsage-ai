/**
 * @fileoverview Tests for the auth confirm route handler.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const verifyMock: any = vi.fn(async (_args: any) => ({ error: null }));
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({ auth: { verifyOtp: verifyMock } })),
}));

// Mock next/navigation redirect helper
const redirectMock = vi.fn();
vi.mock("next/navigation", async (importOriginal) => {
  const actual = await importOriginal<any>();
  return {
    ...actual,
    redirect: (...args: any[]) => redirectMock(...args),
  };
});

import { GET } from "../route";

/**
 * Creates a mock request object for testing.
 * @param url The request URL.
 * @return A mock request object.
 */
function makeReq(url: string): any {
  return { url, headers: new Headers() };
}

describe("auth/confirm route", () => {
  beforeEach(() => {
    verifyMock.mockClear();
    redirectMock.mockClear();
  });

  it("verifies token and redirects to next path", async () => {
    const req = makeReq(
      "https://app.example.com/auth/confirm?token_hash=thash&type=email&next=%2F"
    );
    await GET(req);
    expect(verifyMock).toHaveBeenCalledWith({ type: "email", token_hash: "thash" });
    expect(redirectMock).toHaveBeenCalledWith("/");
  });

  it("redirects to error on verify failure", async () => {
    verifyMock.mockResolvedValueOnce({ error: new Error("invalid") });
    const req = makeReq(
      "https://app.example.com/auth/confirm?token_hash=bad&type=email"
    );
    await GET(req);
    expect(redirectMock).toHaveBeenCalledWith("/login?error=confirm_failed");
  });
});
