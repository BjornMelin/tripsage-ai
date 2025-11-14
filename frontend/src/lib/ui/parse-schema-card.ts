/**
 * @fileoverview Utility to parse schema cards from chat message text.
 *
 * Extracts JSON from text (handles codefenced and plain JSON) and identifies
 * schema versions for rendering appropriate UI components.
 */

import type { z } from "zod";
import {
  accommodationSearchResultSchema,
  budgetPlanResultSchema,
  destinationResearchResultSchema,
  flightSearchResultSchema,
  itineraryPlanResultSchema,
} from "@/lib/schemas/agents";

type FlightSearchResult = z.infer<typeof flightSearchResultSchema>;
type AccommodationSearchResult = z.infer<typeof accommodationSearchResultSchema>;
type BudgetPlanResult = z.infer<typeof budgetPlanResultSchema>;
type DestinationResearchResult = z.infer<typeof destinationResearchResultSchema>;
type ItineraryPlanResult = z.infer<typeof itineraryPlanResultSchema>;

/**
 * Parsed schema card result.
 */
export type ParsedSchemaCard =
  | { data: FlightSearchResult; kind: "flight" }
  | { data: AccommodationSearchResult; kind: "stay" }
  | { data: BudgetPlanResult; kind: "budget" }
  | { data: DestinationResearchResult; kind: "destination" }
  | { data: ItineraryPlanResult; kind: "itinerary" };

/**
 * Parse a schema card from chat message text.
 *
 * Attempts to extract JSON from text (handles markdown codefenced JSON and
 * plain JSON) and validates against known schema versions. Returns null if
 * no valid schema card is found.
 *
 * @param text - Text content from chat message.
 * @returns Parsed schema card with kind and data, or null if not found/invalid.
 */
export function parseSchemaCard(text: string): ParsedSchemaCard | null {
  if (!text || typeof text !== "string") {
    return null;
  }

  let parsedJson: unknown = null;

  try {
    // Attempt to extract JSON from text (may be wrapped in markdown code blocks)
    const jsonMatch = text.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*\})/);
    const jsonStr = jsonMatch?.[1] ?? jsonMatch?.[2] ?? text;
    parsedJson = JSON.parse(jsonStr);
  } catch {
    // Not valid JSON, return null
    return null;
  }

  if (!parsedJson || typeof parsedJson !== "object") {
    return null;
  }

  // Disambiguate by explicit schemaVersion to avoid false positives on schemas
  const obj = parsedJson as { schemaVersion?: string };
  switch (obj.schemaVersion) {
    case "flight.v1": {
      const r = flightSearchResultSchema.safeParse(parsedJson);
      return r.success ? { data: r.data, kind: "flight" } : null;
    }
    case "stay.v1": {
      const r = accommodationSearchResultSchema.safeParse(parsedJson);
      return r.success ? { data: r.data, kind: "stay" } : null;
    }
    case "budget.v1": {
      const r = budgetPlanResultSchema.safeParse(parsedJson);
      return r.success ? { data: r.data, kind: "budget" } : null;
    }
    case "dest.v1": {
      const r = destinationResearchResultSchema.safeParse(parsedJson);
      return r.success ? { data: r.data, kind: "destination" } : null;
    }
    case "itin.v1": {
      const r = itineraryPlanResultSchema.safeParse(parsedJson);
      return r.success ? { data: r.data, kind: "itinerary" } : null;
    }
    default:
      return null;
  }

  // Unreachable: switch covers all return branches including default
}
