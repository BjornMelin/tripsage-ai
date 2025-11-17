import type { User } from "@supabase/supabase-js";
import { describe, expect, it, vi } from "vitest";
import { getOptionalUser, requireUser } from "@/lib/auth/server";

vi.mock("@/lib/supabase/server", () => {
  return {
    createServerSupabase: vi.fn(async () => ({ auth: {} })),
    getCurrentUser: vi.fn(async () => ({ user: null })),
  };
});

vi.mock("next/navigation", () => {
  return {
    redirect: vi.fn(() => {
      throw new Error("REDIRECT");
    }),
  };
});

const mockedSupabaseServer = vi.mocked(await import("@/lib/supabase/server"));
const mockedNavigation = vi.mocked(await import("next/navigation"));

describe("server-side auth helpers", () => {
  it("getOptionalUser returns null user when unauthenticated", async () => {
    mockedSupabaseServer.getCurrentUser.mockResolvedValueOnce({
      error: null,
      user: null,
    });

    const result = await getOptionalUser();

    expect(result.user).toBeNull();
    expect(mockedSupabaseServer.createServerSupabase).toHaveBeenCalledTimes(1);
    expect(mockedSupabaseServer.getCurrentUser).toHaveBeenCalledTimes(1);
  });

  it("requireUser returns context when user is present", async () => {
    const user = { id: "user-1" } as unknown as User;
    mockedSupabaseServer.getCurrentUser.mockResolvedValueOnce({
      error: null,
      user,
    });

    const result = await requireUser();

    expect(result.user).toEqual(user);
    expect(mockedNavigation.redirect).not.toHaveBeenCalled();
  });

  it("requireUser triggers redirect to login when unauthenticated", async () => {
    mockedSupabaseServer.getCurrentUser.mockResolvedValueOnce({
      error: null,
      user: null,
    });

    await expect(requireUser()).rejects.toThrow("REDIRECT");
    expect(mockedNavigation.redirect).toHaveBeenCalledWith("/login?next=%2Fdashboard");
  });
});
