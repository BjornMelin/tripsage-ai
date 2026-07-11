/** @vitest-environment node */

import type { MockInstance } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { GET_OPTIONAL_USER_MOCK, SIGN_OUT_MOCK } = vi.hoisted(() => {
  const signOut = vi.fn(
    async (_options: {
      scope: "local";
    }): Promise<{ error: { message: string } | null }> => ({ error: null })
  );
  return {
    GET_OPTIONAL_USER_MOCK: vi.fn(async () => ({
      supabase: { auth: { signOut } },
      user: { id: "user-1" } as { id: string } | null,
    })),
    SIGN_OUT_MOCK: signOut,
  };
});

const DELETE_USER_MOCK = vi.hoisted(
  () =>
    vi.fn(async () => ({ error: null })) as MockInstance<
      (_userId: string) => Promise<{ error: { message: string } | null }>
    >
);

vi.mock("@/lib/auth/server", () => ({
  getOptionalUser: GET_OPTIONAL_USER_MOCK,
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminSupabase: () => ({
    auth: { admin: { deleteUser: DELETE_USER_MOCK } },
  }),
}));

import { DELETE } from "../route";

describe("/auth/delete route", () => {
  beforeEach(() => {
    GET_OPTIONAL_USER_MOCK.mockClear();
    DELETE_USER_MOCK.mockClear();
    SIGN_OUT_MOCK.mockReset().mockResolvedValue({ error: null });
  });

  it("clears the local session and returns ok:true when deletion succeeds", async () => {
    DELETE_USER_MOCK.mockResolvedValueOnce({ error: null });

    const res = await DELETE();
    expect(res.status).toBe(200);
    await expect(res.json()).resolves.toEqual({ ok: true });
    expect(SIGN_OUT_MOCK).toHaveBeenCalledWith({ scope: "local" });
  });

  it("returns 400 when Supabase admin deletion fails", async () => {
    DELETE_USER_MOCK.mockResolvedValueOnce({
      error: { message: "Delete failed" },
    });

    const res = await DELETE();
    expect(res.status).toBe(400);
    await expect(res.json()).resolves.toEqual({
      code: "DELETE_FAILED",
      error: "delete_failed",
      message: "Delete failed",
      reason: "Delete failed",
    });
    expect(SIGN_OUT_MOCK).not.toHaveBeenCalled();
  });

  it("keeps deletion successful when local session cleanup reports an error", async () => {
    DELETE_USER_MOCK.mockResolvedValueOnce({ error: null });
    SIGN_OUT_MOCK.mockResolvedValueOnce({
      error: { message: "Session cookie cleanup failed" },
    });

    const res = await DELETE();
    expect(res.status).toBe(200);
    await expect(res.json()).resolves.toEqual({ ok: true });
  });

  it("returns 401 when the request is unauthenticated", async () => {
    GET_OPTIONAL_USER_MOCK.mockResolvedValueOnce({
      supabase: { auth: { signOut: SIGN_OUT_MOCK } },
      user: null,
    });

    const res = await DELETE();
    expect(res.status).toBe(401);
    await expect(res.json()).resolves.toEqual({
      code: "UNAUTHORIZED",
      error: "unauthorized",
      message: "Authentication required",
      reason: "Authentication required",
    });
    expect(DELETE_USER_MOCK).not.toHaveBeenCalled();
    expect(SIGN_OUT_MOCK).not.toHaveBeenCalled();
  });

  it("returns 500 when user lookup throws", async () => {
    GET_OPTIONAL_USER_MOCK.mockRejectedValueOnce(new Error("auth unavailable"));

    const res = await DELETE();
    expect(res.status).toBe(500);
    await expect(res.json()).resolves.toMatchObject({
      code: "DELETE_FAILED",
      error: "delete_failed",
      reason: "auth unavailable",
    });
  });
});
