import type { NextRequest } from "next/server";
import type { MockInstance } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const VERIFY_MOCK: MockInstance<
  (_args: { token_hash: string; type: string }) => Promise<{ error: Error | null }>
> = vi.fn(async (_args: { token_hash: string; type: string }) => ({ error: null }));

vi.mock("@/lib/supabase", () => ({
  createServerSupabase: vi.fn(async () => ({ auth: { verifyOtp: VERIFY_MOCK } })),
}));

// Mock next/navigation redirect helper
const REDIRECT_MOCK = vi.hoisted(
  () => vi.fn() as MockInstance<(...args: string[]) => never>
);
vi.mock("next/navigation", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    redirect: REDIRECT_MOCK,
  };
});

import { GET } from "../route";

/**
 * Creates a mock request object for testing.
 * @param url The request URL.
 * @return A mock request object.
 */
function makeReq(url: string): NextRequest {
  return { headers: new Headers(), url } as NextRequest;
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
