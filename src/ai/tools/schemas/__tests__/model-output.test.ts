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
    if (result.success) {
      expect(result.data).toMatchObject({
        activities: [
          {
            id: "act-1",
            location: "NYC",
            name: "Museum",
            type: "sightseeing",
          },
        ],
        metadata: { primarySource: "googleplaces", total: 1 },
      });
    }
  });

  it("rejects activity model output with invalid metadata", () => {
    const result = activityModelOutputSchema.safeParse({
      activities: [],
      metadata: { primarySource: "unknown", total: 1 },
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(
        result.error.issues.some(
          (issue) => issue.path.join(".") === "metadata.primarySource"
        )
      ).toBe(true);
    }
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
    if (result.success) {
      expect(result.data.currency).toBe("USD");
      expect(result.data.itineraryCount).toBe(1);
      expect(result.data.offers).toHaveLength(1);
      expect(result.data.offers[0]).toMatchObject({
        id: "offer-1",
        provider: "test",
      });
      expect(result.data.offers[0].slices[0]?.segments[0]).toMatchObject({
        destination: "LAX",
        origin: "SFO",
      });
    }
  });
});
