/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { logoutAction } from "../actions";

// Mock dependencies (hoisted for vi.mock)
const { mockSignOut, mockSupabase, loggerErrorMock } = vi.hoisted(() => {
  const signOut = vi.fn();
  return {
    loggerErrorMock: vi.fn(),
    mockSignOut: signOut,
    mockSupabase: {
      auth: {
        signOut,
      },
    },
  };
});

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(() => Promise.resolve(mockSupabase)),
}));

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    error: loggerErrorMock,
  }),
}));

vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  redirect: vi.fn(),
}));

describe("logoutAction", () => {
  beforeEach(() => {
    mockSignOut.mockReset();
    loggerErrorMock.mockReset();
    vi.clearAllMocks();
  });

  it("should sign out and redirect to login", async () => {
    const { redirect } = await import("next/navigation");
    const { revalidatePath } = await import("next/cache");

    mockSignOut.mockResolvedValueOnce(undefined);
    await logoutAction();

    expect(mockSignOut).toHaveBeenCalled();
    expect(revalidatePath).toHaveBeenCalledWith("/");
    expect(redirect).toHaveBeenCalledWith("/login");
  });

  it("logs and continues when sign out fails", async () => {
    const { redirect } = await import("next/navigation");
    const { revalidatePath } = await import("next/cache");

    const signOutError = new Error("sign-out-failed");
    mockSignOut.mockRejectedValueOnce(signOutError);

    await logoutAction();

    expect(loggerErrorMock).toHaveBeenCalledWith("Logout error", {
      error: signOutError,
    });
    expect(revalidatePath).toHaveBeenCalledWith("/");
    expect(redirect).toHaveBeenCalledWith("/login");
  });
});
