/**
 * @fileoverview Central tool registry for AI SDK v6.
 * Exports all server-side tools for use in chat routes and agents and
 * provides a typed registry object for higher-level agents.
 */

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
 * Typed tool registry used by higher-level agents.
 *
 * Only actual AI tools (not helper utilities) are included here.
 */
export const toolRegistry = {
	addConversationMemory,
	bookAccommodation,
	checkAvailability,
	combineSearchResults,
	createTravelPlan,
	getAccommodationDetails,
	getActivityDetails,
	getTravelAdvisory,
	lookupPoiContext,
	saveTravelPlan,
	searchAccommodations,
	searchActivities,
	webSearch,
	webSearchBatch,
};
