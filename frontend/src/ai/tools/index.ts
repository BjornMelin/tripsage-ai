/**
 * @fileoverview Central tool registry.
 *
 * Exports all server-side tools for use in chat routes and agents and
 * provides a typed registry object for higher-level agents.
 */

import type { ToolSet, TypedToolCall, TypedToolResult } from "ai";
import {
  bookAccommodation,
  checkAvailability,
  getAccommodationDetails,
  searchAccommodations,
} from "./server/accommodations";
import { getActivityDetails, searchActivities } from "./server/activities";
import {
  denyApproval,
  getApprovalStatus,
  grantApproval,
  requireApproval,
} from "./server/approvals";
import {
  createCalendarEvent,
  exportItineraryToIcs,
  getAvailability,
} from "./server/calendar";
import { searchFlights } from "./server/flights";
import { lookupPoiContext } from "./server/google-places";
import { distanceMatrix, geocode } from "./server/maps";
import { addConversationMemory, searchUserMemories } from "./server/memory";
import {
  combineSearchResults,
  createTravelPlan,
  deleteTravelPlan,
  saveTravelPlan,
  updateTravelPlan,
} from "./server/planning";
import { getTravelAdvisory } from "./server/travel-advisory";
import { getCurrentWeather } from "./server/weather";
import { crawlSite, crawlUrl } from "./server/web-crawl";
import { webSearch } from "./server/web-search";
import { webSearchBatch } from "./server/web-search-batch";

export {
  addConversationMemory,
  bookAccommodation,
  checkAvailability,
  combineSearchResults,
  crawlSite,
  crawlUrl,
  createCalendarEvent,
  createTravelPlan,
  deleteTravelPlan,
  denyApproval,
  distanceMatrix,
  exportItineraryToIcs,
  geocode,
  getAccommodationDetails,
  getActivityDetails,
  getApprovalStatus,
  getAvailability,
  getCurrentWeather,
  getTravelAdvisory,
  grantApproval,
  lookupPoiContext,
  requireApproval,
  saveTravelPlan,
  searchAccommodations,
  searchActivities,
  searchFlights,
  searchUserMemories,
  updateTravelPlan,
  webSearch,
  webSearchBatch,
};

/**
 * Typed tool registry for AI SDK v6 generateText/streamText.
 * Satisfies ToolSet for compile-time validation; includes only executable tools.
 */
export const toolRegistry = {
  addConversationMemory,
  bookAccommodation,
  checkAvailability,
  combineSearchResults,
  crawlSite,
  crawlUrl,
  createCalendarEvent,
  createTravelPlan,
  deleteTravelPlan,
  distanceMatrix,
  exportItineraryToIcs,
  geocode,
  getAccommodationDetails,
  getActivityDetails,
  getAvailability,
  getCurrentWeather,
  getTravelAdvisory,
  lookupPoiContext,
  saveTravelPlan,
  searchAccommodations,
  searchActivities,
  searchFlights,
  searchUserMemories,
  updateTravelPlan,
  webSearch,
  webSearchBatch,
} satisfies ToolSet;

/** Type for the complete tool registry. */
export type TripSageToolRegistry = typeof toolRegistry;

/**
 * Typed tool call for TripSage tools.
 *
 * Use for type-safe access to tool call inputs in step handlers.
 *
 * @example
 * ```typescript
 * const toolCall: TripSageToolCall = step.toolCalls[0];
 * if (toolCall.toolName === 'searchFlights') {
 *   console.log(toolCall.args.origin); // Type-safe access
 * }
 * ```
 */
export type TripSageToolCall = TypedToolCall<TripSageToolRegistry>;

/**
 * Typed tool result for TripSage tools.
 *
 * Use for type-safe access to tool results in step handlers.
 *
 * @example
 * ```typescript
 * const toolResult: TripSageToolResult = step.toolResults[0];
 * if (toolResult.toolName === 'searchFlights') {
 *   console.log(toolResult.result.flights); // Type-safe access
 * }
 * ```
 */
export type TripSageToolResult = TypedToolResult<TripSageToolRegistry>;
