/**
 * @fileoverview Smoke tests for trips repository using typed helpers.
 */
import { describe, expect, it, vi } from "vitest";
import { createTrip, mapTripRowToUI, updateTrip } from "@/lib/repositories/trips-repo";
import type { Tables } from "@/lib/supabase/database.types";
import * as helpers from "@/lib/supabase/typed-helpers";

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({}),
}));

describe("trips-repo", () => {
  it("mapTripRowToUI shapes core fields", () => {
    const row: Tables<"trips"> = {
      budget: 1200,
      created_at: "2025-03-01T00:00:00Z",
      destination: "LON",
      end_date: "2025-03-10",
      flexibility: {},
      id: 42,
      name: "Trip",
      notes: null,
      search_metadata: {},
      start_date: "2025-03-01",
      status: "planning",
      travelers: 1,
      trip_type: "leisure",
      updated_at: "2025-03-01T00:00:00Z",
      user_id: "u42",
    };
    const ui = mapTripRowToUI(row);
    expect(ui.id).toBe("42");
    expect(ui.name).toBe("Trip");
    expect(ui.startDate).toBe("2025-03-01");
  });

  it("createTrip uses insertSingle and returns UI mapping", async () => {
    const row: Tables<"trips"> = {
      budget: 100,
      created_at: "2025-01-01T00:00:00Z",
      destination: "NYC",
      end_date: "2025-01-02",
      flexibility: {},
      id: 1,
      name: "New",
      notes: null,
      search_metadata: {},
      start_date: "2025-01-01",
      status: "planning",
      travelers: 1,
      trip_type: "leisure",
      updated_at: "2025-01-01T00:00:00Z",
      user_id: "u1",
    };
    vi.spyOn(helpers, "insertSingle").mockResolvedValue({ data: row, error: null });
    const ui = await createTrip({
      budget: 100,
      destination: "NYC",
      end_date: "2025-01-02",
      name: "New",
      start_date: "2025-01-01",
      travelers: 1,
      user_id: "u1",
    });
    expect(ui.id).toBe("1");
    expect(ui.name).toBe("New");
  });

  it("updateTrip uses updateSingle and returns UI mapping", async () => {
    const row: Tables<"trips"> = {
      budget: 300,
      created_at: "2025-02-01T00:00:00Z",
      destination: "SFO",
      end_date: "2025-02-02",
      flexibility: {},
      id: 2,
      name: "Upd",
      notes: null,
      search_metadata: {},
      start_date: "2025-02-01",
      status: "planning",
      travelers: 2,
      trip_type: "leisure",
      updated_at: "2025-02-01T00:00:00Z",
      user_id: "u2",
    };
    vi.spyOn(helpers, "updateSingle").mockResolvedValue({ data: row, error: null });
    const ui = await updateTrip(2, "u2", { name: "Upd" });
    expect(ui.id).toBe("2");
    expect(ui.name).toBe("Upd");
  });
});
