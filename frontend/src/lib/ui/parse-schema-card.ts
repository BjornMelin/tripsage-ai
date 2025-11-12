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
} from "@/schemas/agents";

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

  // Check if parsed JSON matches flight.v1 schema
  const flightResult = flightSearchResultSchema.safeParse(parsedJson);
  if (flightResult.success) {
    return { data: flightResult.data, kind: "flight" };
  }

  // Check if parsed JSON matches stay.v1 schema
  const stayResult = accommodationSearchResultSchema.safeParse(parsedJson);
  if (stayResult.success) {
    return { data: stayResult.data, kind: "stay" };
  }

  // Check if parsed JSON matches budget.v1 schema
  const budgetResult = budgetPlanResultSchema.safeParse(parsedJson);
  if (budgetResult.success) {
    return { data: budgetResult.data, kind: "budget" };
  }

  // Check if parsed JSON matches dest.v1 schema
  const destResult = destinationResearchResultSchema.safeParse(parsedJson);
  if (destResult.success) {
    return { data: destResult.data, kind: "destination" };
  }

  // Check if parsed JSON matches itin.v1 schema
  const itinResult = itineraryPlanResultSchema.safeParse(parsedJson);
  if (itinResult.success) {
    return { data: itinResult.data, kind: "itinerary" };
  }

  // No matching schema found
  return null;
}
