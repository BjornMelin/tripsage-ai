/** @vitest-environment node */

import type { MockInstance } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const REQUIRE_USER_MOCK = vi.hoisted(
  () =>
    vi.fn(async () => ({ user: { id: "user-1" } })) as MockInstance<
      (_args: { redirectTo: string }) => Promise<{ user: { id: string } }>
    >
);

const DELETE_USER_MOCK = vi.hoisted(
  () =>
    vi.fn(async () => ({ error: null })) as MockInstance<
      (_userId: string) => Promise<{ error: { message: string } | null }>
    >
);

vi.mock("@/lib/auth/server", () => ({
  requireUser: REQUIRE_USER_MOCK,
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminSupabase: () => ({
    auth: { admin: { deleteUser: DELETE_USER_MOCK } },
  }),
}));

import { DELETE } from "../route";

describe("/auth/delete route", () => {
  beforeEach(() => {
    REQUIRE_USER_MOCK.mockClear();
    DELETE_USER_MOCK.mockClear();
  });

  it("returns ok:true when deletion succeeds", async () => {
    REQUIRE_USER_MOCK.mockResolvedValueOnce({ user: { id: "user-1" } });
    DELETE_USER_MOCK.mockResolvedValueOnce({ error: null });

    const res = await DELETE();
    expect(res.status).toBe(200);
    await expect(res.json()).resolves.toEqual({ ok: true });
  });

  it("returns 400 when Supabase admin deletion fails", async () => {
    REQUIRE_USER_MOCK.mockResolvedValueOnce({ user: { id: "user-1" } });
    DELETE_USER_MOCK.mockResolvedValueOnce({
      error: { message: "Delete failed" },
    });

    const res = await DELETE();
    expect(res.status).toBe(400);
    await expect(res.json()).resolves.toEqual({
      code: "DELETE_FAILED",
      message: "Delete failed",
    });
  });

  it("returns 500 when requireUser throws", async () => {
    REQUIRE_USER_MOCK.mockRejectedValueOnce(new Error("not authenticated"));

    const res = await DELETE();
    expect(res.status).toBe(500);
    await expect(res.json()).resolves.toMatchObject({ code: "DELETE_FAILED" });
  });
});
