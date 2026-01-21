/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { ensureTripAccess } from "@/lib/trips/trip-access";
import { createMockSupabaseClient, getSupabaseMockState } from "@/test/mocks/supabase";

describe("ensureTripAccess", () => {
  const userId = "user-1";
  const tripId = 42;

  it("returns null when user owns the trip", async () => {
    const supabase = createMockSupabaseClient();
    const state = getSupabaseMockState(supabase);
    state.selectByTable.set("trips", {
      data: [{ id: tripId, user_id: userId }],
      error: null,
    });
    state.selectByTable.set("trip_collaborators", { data: [], error: null });

    const result = await ensureTripAccess({ supabase, tripId, userId });
    expect(result).toBeNull();
  });

  it("returns null when user is a collaborator", async () => {
    const supabase = createMockSupabaseClient();
    const state = getSupabaseMockState(supabase);
    state.selectByTable.set("trips", { data: [], error: null });
    state.selectByTable.set("trip_collaborators", {
      data: [{ id: "collab-1", trip_id: tripId, user_id: userId }],
      error: null,
    });

    const result = await ensureTripAccess({ supabase, tripId, userId });
    expect(result).toBeNull();
  });

  it("returns forbidden when trip exists but user lacks access", async () => {
    const supabase = createMockSupabaseClient();
    const state = getSupabaseMockState(supabase);
    state.selectByTable.set("trips", {
      data: [{ id: tripId, user_id: "someone-else" }],
      error: null,
    });
    state.selectByTable.set("trip_collaborators", { data: [], error: null });

    const result = await ensureTripAccess({ supabase, tripId, userId });
    expect(result).not.toBeNull();
    if (result) {
      expect(result.status).toBe(403);
      const body = (await result.json()) as { error?: string };
      expect(body.error).toBe("forbidden");
    }
  });

  it("returns not found when trip does not exist", async () => {
    const supabase = createMockSupabaseClient();
    const state = getSupabaseMockState(supabase);
    state.selectByTable.set("trips", { data: [], error: null });
    state.selectByTable.set("trip_collaborators", { data: [], error: null });

    const result = await ensureTripAccess({ supabase, tripId, userId });
    expect(result).not.toBeNull();
    if (result) {
      expect(result.status).toBe(404);
      const body = (await result.json()) as { error?: string; reason?: string };
      expect(body.error).toBe("not_found");
      expect(body.reason).toBe("Trip not found");
    }
  });

  it("returns 500 when owner check errors", async () => {
    const supabase = createMockSupabaseClient();
    const state = getSupabaseMockState(supabase);
    state.selectByTable.set("trips", { data: null, error: { message: "db down" } });
    state.selectByTable.set("trip_collaborators", { data: [], error: null });

    const result = await ensureTripAccess({ supabase, tripId, userId });
    expect(result).not.toBeNull();
    if (result) {
      expect(result.status).toBe(500);
      const body = (await result.json()) as { error?: string; reason?: string };
      expect(body.error).toBe("internal");
      expect(body.reason).toBe("Failed to validate trip access");
    }
  });

  it("returns 500 when collaborator check errors", async () => {
    const supabase = createMockSupabaseClient();
    const state = getSupabaseMockState(supabase);
    state.selectByTable.set("trips", { data: [], error: null });
    state.selectByTable.set("trip_collaborators", {
      data: null,
      error: { message: "collab query failed" },
    });

    const result = await ensureTripAccess({ supabase, tripId, userId });
    expect(result).not.toBeNull();
    if (result) {
      expect(result.status).toBe(500);
      const body = (await result.json()) as { error?: string; reason?: string };
      expect(body.error).toBe("internal");
      expect(body.reason).toBe("Failed to validate trip access");
    }
  });
});
