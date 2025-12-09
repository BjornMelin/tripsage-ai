/** @vitest-environment node */

import type { TripsRow } from "@schemas/supabase";
import { describe, expect, it, vi } from "vitest";
import { createTrip, updateTrip } from "@/lib/repositories/trips-repo";
import * as helpers from "@/lib/supabase/typed-helpers";
import { mapDbTripToUi } from "@/lib/trips/mappers";

vi.mock("@/lib/supabase", () => ({
  createClient: () => ({}),
}));

describe("trips-repo", () => {
  it("mapTripRowToUI shapes core fields", () => {
    const userId = "123e4567-e89b-12d3-a456-426614174010";
    const row: TripsRow = {
      budget: 1200,
      created_at: "2025-03-01T00:00:00Z",
      currency: "USD",
      destination: "LON",
      end_date: "2025-03-10T00:00:00Z",
      flexibility: {},
      id: 42,
      name: "Trip",
      search_metadata: {},
      start_date: "2025-03-01T00:00:00Z",
      status: "planning",
      tags: null,
      travelers: 1,
      trip_type: "leisure",
      updated_at: "2025-03-01T00:00:00Z",
      user_id: userId,
    };
    const ui = mapDbTripToUi(row);
    expect(ui.id).toBe("42");
    expect(ui.title).toBe("Trip");
    expect(ui.startDate).toBe("2025-03-01T00:00:00Z");
    expect(ui.currency).toBe("USD");
  });

  it("createTrip uses insertSingle and returns UI mapping", async () => {
    const userId = "123e4567-e89b-12d3-a456-426614174011";
    const row: TripsRow = {
      budget: 100,
      created_at: "2025-01-01T00:00:00Z",
      currency: "USD",
      destination: "NYC",
      end_date: "2025-01-02T00:00:00Z",
      flexibility: {},
      id: 1,
      name: "New",
      search_metadata: {},
      start_date: "2025-01-01T00:00:00Z",
      status: "planning",
      tags: null,
      travelers: 1,
      trip_type: "leisure",
      updated_at: "2025-01-01T00:00:00Z",
      user_id: userId,
    };
    vi.spyOn(helpers, "insertSingle").mockResolvedValue({ data: row, error: null });
    const ui = await createTrip({
      budget: 100,
      destination: "NYC",
      end_date: "2025-01-02T00:00:00Z",
      name: "New", // Database uses 'name'
      start_date: "2025-01-01T00:00:00Z",
      travelers: 1,
      user_id: userId,
    });
    expect(ui.id).toBe("1");
    expect(ui.title).toBe("New"); // Frontend uses 'title'
  });

  it("updateTrip uses updateSingle and returns UI mapping", async () => {
    const userId = "123e4567-e89b-12d3-a456-426614174012";
    const row: TripsRow = {
      budget: 300,
      created_at: "2025-02-01T00:00:00Z",
      currency: "EUR",
      destination: "SFO",
      end_date: "2025-02-02T00:00:00Z",
      flexibility: {},
      id: 2,
      name: "Upd",
      search_metadata: {},
      start_date: "2025-02-01T00:00:00Z",
      status: "planning",
      tags: null,
      travelers: 2,
      trip_type: "leisure",
      updated_at: "2025-02-01T00:00:00Z",
      user_id: userId,
    };
    vi.spyOn(helpers, "updateSingle").mockResolvedValue({ data: row, error: null });
    const ui = await updateTrip(2, userId, { name: "Upd" }); // Database uses 'name'
    expect(ui.id).toBe("2");
    expect(ui.title).toBe("Upd"); // Frontend uses 'title'
  });
});
