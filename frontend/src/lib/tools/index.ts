/**
 * @fileoverview Unified tool registry for AI SDK v6.
 */

import { bookAccommodation, searchAccommodations } from "./accommodations";
import { searchFlights } from "./flights";
import { distanceMatrix, geocode } from "./maps";
import { addConversationMemory, searchUserMemories } from "./memory";
import {
  combineSearchResults,
  createTravelPlan,
  saveTravelPlan,
  updateTravelPlan,
} from "./planning";
import type { AiTool } from "./types";
import { getCurrentWeather } from "./weather";
import { crawlSite, crawlUrl } from "./web-crawl";
import { webSearch } from "./web-search";

export const toolRegistry = {
  addConversationMemory,
  bookAccommodation,
  combineSearchResults,
  crawlSite,
  crawlUrl,
  createTravelPlan,
  distanceMatrix,
  geocode,
  getCurrentWeather,
  saveTravelPlan,
  searchAccommodations,
  searchFlights,
  searchUserMemories,
  updateTravelPlan,
  webSearch,
} satisfies Record<string, AiTool>;

export type ToolRegistry = typeof toolRegistry;
