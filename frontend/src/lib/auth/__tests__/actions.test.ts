/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import { logoutAction } from "../actions";

// Mock dependencies
const mockSignOut = vi.fn();
const mockSupabase = {
  auth: {
    signOut: mockSignOut,
  },
};

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(() => Promise.resolve(mockSupabase)),
}));

vi.mock("next/navigation", () => ({
  redirect: vi.fn(),
}));

describe("logoutAction", () => {
  it("should sign out and redirect to login", async () => {
    const { redirect } = await import("next/navigation");
    
    await logoutAction();

    expect(mockSignOut).toHaveBeenCalled();
    expect(redirect).toHaveBeenCalledWith("/login");
  });
});
