/**
 * @fileoverview Zod schemas for travel planning API responses and travel planning tool inputs.
 *
 * Core schemas: Travel planning API parameters and data structures
 * Tool schemas: Input validation for travel planning tools (create plan, combine results, save plan)
 */

import { z } from "zod";

const UUID_V4 = z.uuid().describe("Unique identifier for travel plans");
const ISO_DATE = z
  .string()
  .date({ error: "must be YYYY-MM-DD" })
  .describe("Date in YYYY-MM-DD format");
const PREFERENCES = z
  .record(z.string(), z.unknown())
  .default({})
  .describe("User preferences for travel planning");

/** Schema for combineSearchResults tool input. */
export const combineSearchResultsInputSchema = z.strictObject({
  accommodationResults: z
    .record(z.string(), z.unknown())
    .nullable()
    .describe("Search results for accommodations"),
  activityResults: z
    .record(z.string(), z.unknown())
    .nullable()
    .describe("Search results for activities"),
  destinationInfo: z
    .record(z.string(), z.unknown())
    .nullable()
    .describe("Information about the destination"),
  endDate: ISO_DATE.nullable().describe("End date for the travel period"),
  flightResults: z
    .record(z.string(), z.unknown())
    .nullable()
    .describe("Search results for flights"),
  startDate: ISO_DATE.nullable().describe("Start date for the travel period"),
  userPreferences: PREFERENCES.nullable().describe(
    "User preferences to consider in planning"
  ),
});

/** Schema for createTravelPlan tool input. */
export const createTravelPlanInputSchema = z.strictObject({
  budget: z
    .number()
    .min(0)
    .nullable()
    .describe("Total budget for the trip in the user's currency"),
  destinations: z
    .array(z.string().min(1))
    .min(1)
    .describe("List of destination cities or places to visit"),
  endDate: ISO_DATE.describe("End date for the travel plan"),
  preferences: PREFERENCES.nullable().describe(
    "User preferences for accommodation, activities, etc."
  ),
  startDate: ISO_DATE.describe("Start date for the travel plan"),
  title: z
    .string()
    .min(1, { error: "title required" })
    .describe("Descriptive title for the travel plan"),
  travelers: z.number().int().min(1).max(50).default(1).describe("Number of travelers"),
  userId: z.string().min(1).nullable().describe("User identifier for the plan owner"),
});

/** Schema for saveTravelPlan tool input. */
export const saveTravelPlanInputSchema = z.strictObject({
  finalize: z
    .boolean()
    .default(false)
    .nullable()
    .describe("Whether to finalize and lock the plan"),
  planId: UUID_V4.describe("Unique identifier of the plan to save"),
  userId: z.string().min(1).nullable().describe("User identifier for authorization"),
});

/** Schema for updateTravelPlan tool input. */
export const updateTravelPlanInputSchema = z.strictObject({
  planId: UUID_V4.describe("Unique identifier of the plan to update"),
  updates: z.record(z.string(), z.unknown()).describe("Fields to update in the plan"),
  userId: z.string().min(1).nullable().describe("User identifier for authorization"),
});
