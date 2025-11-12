import { describe, expect, it } from "vitest";

import {
  accommodationSearchRequestSchema,
  destinationResearchRequestSchema,
  destinationResearchResultSchema,
  flightSearchResultSchema,
  itineraryPlanResultSchema,
} from "@/schemas/agents";

describe("agent schemas", () => {
  it("parses destination requests with defaults", () => {
    const parsed = destinationResearchRequestSchema.parse({
      destination: "Tokyo",
    });
    expect(parsed.destination).toBe("Tokyo");
  });

  it("applies schema versions on results", () => {
    const parsed = destinationResearchResultSchema.parse({
      destination: "Lisbon",
      highlights: [],
      sources: [],
    });
    expect(parsed.schemaVersion).toBe("dest.v1");
  });

  it("validates itinerary result shape", () => {
    const parsed = itineraryPlanResultSchema.parse({
      days: [{ activities: [], day: 1 }],
      destination: "Madrid",
      sources: [],
    });
    expect(parsed.days).toHaveLength(1);
  });

  it("ensures flight results provide itineraries", () => {
    expect(() =>
      flightSearchResultSchema.parse({
        currency: "USD",
        itineraries: [],
        sources: [],
      })
    ).not.toThrow();
  });

  it("requires accommodation request minimum fields", () => {
    expect(() =>
      accommodationSearchRequestSchema.parse({
        checkIn: "2025-01-01",
        checkOut: "2025-01-05",
        destination: "Paris",
      })
    ).not.toThrow();
  });
});
