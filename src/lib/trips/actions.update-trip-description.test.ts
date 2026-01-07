/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";

const mockUpdate = vi.fn();

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(() => {
    const maybeSingle = vi.fn(() => ({
      data: null,
      error: { code: "99999", message: "Update failed" },
    }));

    const select = vi.fn(() => ({ maybeSingle }));
    const eq = vi.fn(() => ({ select }));

    mockUpdate.mockImplementation((updates: unknown) => {
      return { eq, updates };
    });

    const from = vi.fn(() => ({
      update: (updates: unknown) => {
        mockUpdate(updates);
        return { eq };
      },
    }));

    return {
      auth: {
        getUser: vi.fn(() => ({ data: { user: { id: "user-123" } } })),
      },
      from,
    };
  }),
}));

describe("updateTrip", () => {
  it("sets description to null when clearing", async () => {
    const { updateTrip } = await import("./actions");

    await updateTrip(1, { description: null });

    expect(mockUpdate).toHaveBeenCalledTimes(1);
    const updates = mockUpdate.mock.calls[0]?.[0] as Record<string, unknown>;
    expect(updates.description).toBe(null);
  });
});
