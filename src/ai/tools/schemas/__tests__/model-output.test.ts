/** @vitest-environment node */

import { activityModelOutputSchema } from "@ai/tools/schemas/activities";
import { flightModelOutputSchema } from "@ai/tools/schemas/flights";
import { describe, expect, it } from "vitest";

describe("tool model output schemas", () => {
  it("parses activity model output", () => {
    const result = activityModelOutputSchema.safeParse({
      activities: [
        {
          duration: 60,
          id: "act-1",
          location: "NYC",
          name: "Museum",
          price: 25,
          rating: 4.5,
          type: "sightseeing",
        },
      ],
      metadata: { primarySource: "googleplaces", total: 1 },
    });

    expect(result.success).toBe(true);
  });

  it("rejects activity model output with invalid metadata", () => {
    const result = activityModelOutputSchema.safeParse({
      activities: [],
      metadata: { primarySource: "unknown", total: 1 },
    });

    expect(result.success).toBe(false);
  });

  it("parses flight model output", () => {
    const result = flightModelOutputSchema.safeParse({
      currency: "USD",
      fromCache: false,
      itineraries: [
        {
          id: "it-1",
          price: 199,
          segments: [{ destination: "LAX", origin: "SFO" }],
        },
      ],
      itineraryCount: 1,
      offerCount: 1,
      offers: [
        {
          id: "offer-1",
          price: 199,
          provider: "test",
          slices: [
            {
              cabinClass: "economy",
              segmentCount: 1,
              segments: [{ destination: "LAX", origin: "SFO" }],
            },
          ],
        },
      ],
      provider: "test",
    });

    expect(result.success).toBe(true);
  });
});
