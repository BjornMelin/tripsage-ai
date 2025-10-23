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
      id: 42,
      user_id: "u42",
      name: "Trip",
      start_date: "2025-03-01",
      end_date: "2025-03-10",
      destination: "LON",
      budget: 1200,
      travelers: 1,
      status: "planning",
      trip_type: "leisure",
      flexibility: {},
      notes: null,
      search_metadata: {},
      created_at: "2025-03-01T00:00:00Z",
      updated_at: "2025-03-01T00:00:00Z",
    };
    const ui = mapTripRowToUI(row);
    expect(ui.id).toBe("42");
    expect(ui.name).toBe("Trip");
    expect(ui.startDate).toBe("2025-03-01");
  });

  it("createTrip uses insertSingle and returns UI mapping", async () => {
    const row: Tables<"trips"> = {
      id: 1,
      user_id: "u1",
      name: "New",
      start_date: "2025-01-01",
      end_date: "2025-01-02",
      destination: "NYC",
      budget: 100,
      travelers: 1,
      status: "planning",
      trip_type: "leisure",
      flexibility: {},
      notes: null,
      search_metadata: {},
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    };
    vi.spyOn(helpers, "insertSingle").mockResolvedValue({ data: row, error: null });
    const ui = await createTrip({
      user_id: "u1",
      name: "New",
      start_date: "2025-01-01",
      end_date: "2025-01-02",
      destination: "NYC",
      budget: 100,
      travelers: 1,
    });
    expect(ui.id).toBe("1");
    expect(ui.name).toBe("New");
  });

  it("updateTrip uses updateSingle and returns UI mapping", async () => {
    const row: Tables<"trips"> = {
      id: 2,
      user_id: "u2",
      name: "Upd",
      start_date: "2025-02-01",
      end_date: "2025-02-02",
      destination: "SFO",
      budget: 300,
      travelers: 2,
      status: "planning",
      trip_type: "leisure",
      flexibility: {},
      notes: null,
      search_metadata: {},
      created_at: "2025-02-01T00:00:00Z",
      updated_at: "2025-02-01T00:00:00Z",
    };
    vi.spyOn(helpers, "updateSingle").mockResolvedValue({ data: row, error: null });
    const ui = await updateTrip(2, "u2", { name: "Upd" });
    expect(ui.id).toBe("2");
    expect(ui.name).toBe("Upd");
  });
});
