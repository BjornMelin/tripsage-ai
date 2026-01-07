import { describe, expect, it } from "vitest";
import { createTrip, updateTrip, upsertItineraryItem } from "./actions";

describe("trips actions validation", () => {
  it("createTrip rejects invalid payloads before DB calls", async () => {
    const result = await createTrip({});
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.error).toBe("invalid_request");
  });

  it("updateTrip rejects invalid trip ids before DB calls", async () => {
    const result = await updateTrip(0, { title: "Invalid" });
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.error).toBe("invalid_request");
  });

  it("upsertItineraryItem rejects trip id mismatches before DB calls", async () => {
    const result = await upsertItineraryItem(1, {
      itemType: "other",
      payload: {},
      title: "Test item",
      tripId: 2,
    });

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error.error).toBe("invalid_request");
    expect(result.error.reason).toBe("Trip id mismatch");
  });
});
