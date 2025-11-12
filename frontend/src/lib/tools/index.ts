/**
 * @fileoverview Unified tool registry for AI SDK v6.
 */

import {
  bookAccommodation,
  getAccommodationDetails,
  searchAccommodations,
} from "./accommodations";
import { searchFlights } from "./flights";
import { distanceMatrix, geocode } from "./maps";
import { addConversationMemory, searchUserMemories } from "./memory";
import {
  combineSearchResults,
  createTravelPlan,
  deleteTravelPlan,
  saveTravelPlan,
  updateTravelPlan,
} from "./planning";
import type { AiTool } from "./types";
import { getCurrentWeather } from "./weather";
import { crawlSite, crawlUrl } from "./web-crawl";
import { webSearch } from "./web-search";
import { webSearchBatch } from "./web-search-batch";

export const toolRegistry = {
  addConversationMemory,
  bookAccommodation,
  combineSearchResults,
  crawlSite,
  crawlUrl,
  createTravelPlan,
  deleteTravelPlan,
  distanceMatrix,
  geocode,
  getAccommodationDetails,
  getCurrentWeather,
  saveTravelPlan,
  searchAccommodations,
  searchFlights,
  searchUserMemories,
  updateTravelPlan,
  webSearch,
  webSearchBatch,
} satisfies Record<string, AiTool>;

export type ToolRegistry = typeof toolRegistry;
