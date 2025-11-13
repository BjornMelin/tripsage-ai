/**
 * @fileoverview Unified tool registry for AI SDK v6.
 *
 * Centralizes all available AI tools in a single registry object. Tools are
 * imported from their respective modules and validated against the AiTool type.
 * Used for programmatic tool discovery and dynamic tool selection.
 */

import {
  bookAccommodation,
  checkAvailability,
  getAccommodationDetails,
  searchAccommodations,
} from "./accommodations";
import { createCalendarEvent, exportItineraryToICS, getAvailability } from "./calendar";
import { searchFlights } from "./flights";
import { lookupPoiContext } from "./google-places";
import { distanceMatrix, geocode } from "./maps";
import { addConversationMemory, searchUserMemories } from "./memory";
import {
  combineSearchResults,
  createTravelPlan,
  deleteTravelPlan,
  saveTravelPlan,
  updateTravelPlan,
} from "./planning";
import { getTravelAdvisory } from "./travel-advisory";
import type { AiTool } from "./types";
import { getCurrentWeather } from "./weather";
import { crawlSite, crawlUrl } from "./web-crawl";
import { webSearch } from "./web-search";
import { webSearchBatch } from "./web-search-batch";

/**
 * Registry of all available AI tools.
 *
 * Maps tool names to their AI SDK v6 tool implementations. Includes tools
 * for accommodations, flights, maps, memory, planning, POI lookup, weather,
 * and web search. Validated at compile time to ensure all entries conform
 * to the AiTool type.
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
  // biome-ignore lint/style/useNamingConvention: ICS is a standard file format acronym
  exportItineraryToICS,
  geocode,
  getAccommodationDetails,
  getAvailability,
  getCurrentWeather,
  getTravelAdvisory,
  lookupPoiContext,
  saveTravelPlan,
  searchAccommodations,
  searchFlights,
  searchUserMemories,
  updateTravelPlan,
  webSearch,
  webSearchBatch,
} satisfies Record<string, AiTool>;

/**
 * Type of the tool registry.
 *
 * Infers the exact shape of toolRegistry, preserving tool names and their
 * corresponding tool implementations for type-safe access.
 */
export type ToolRegistry = typeof toolRegistry;
