/**
 * @fileoverview Zod schemas and TypeScript types for agent workflows.
 *
 * Defines request/response schemas for destination research, itinerary
 * planning, flight search, accommodation search, budget planning, memory
 * updates, and router classification workflows.
 */

import { z } from "zod";

/**
 * Canonical list of workflows supported by the frontend Agent runtime.
 */
export const agentWorkflowSchema = z.enum([
  "destination_research",
  "itinerary_planning",
  "flight_search",
  "accommodation_search",
  "budget_planning",
  "memory_update",
  "router",
]);

export type AgentWorkflow = z.infer<typeof agentWorkflowSchema>;

/**
 * Source citation schema for agent research results.
 *
 * Represents a web source with optional title, snippet, publication date,
 * and required URL for attribution and verification.
 */
export const agentSourceSchema = z.object({
  publishedAt: z.string().optional(),
  snippet: z.string().optional(),
  title: z.string().optional(),
  url: z.string().url(),
});

export type AgentSource = z.infer<typeof agentSourceSchema>;

/**
 * Individual destination item schema (activity, attraction, highlight, etc.).
 *
 * Represents a single item with title, optional description, tags, and URL.
 */
const destinationItemSchema = z.object({
  description: z.string().optional(),
  tags: z.array(z.string()).optional(),
  title: z.string(),
  url: z.string().url().optional(),
});

/**
 * Destination research request schema.
 *
 * Defines input parameters for researching a destination including optional
 * locale, travel dates, style preferences, and specific interests.
 */
export const destinationResearchRequestSchema = z.object({
  destination: z.string().min(1),
  locale: z.string().optional(),
  specificInterests: z.array(z.string()).optional(),
  travelDates: z.string().optional(),
  travelStyle: z.string().optional(),
});

/**
 * Destination research result schema.
 *
 * Research output including overview, activities, attractions, highlights,
 * culture, practical information, safety scores, and sources.
 */
export const destinationResearchResultSchema = z.object({
  activities: z.array(destinationItemSchema).optional(),
  attractions: z.array(destinationItemSchema).optional(),
  culture: z.array(destinationItemSchema).optional(),
  destination: z.string(),
  highlights: z.array(destinationItemSchema).optional(),
  overview: z.string().optional(),
  practical: z.array(destinationItemSchema).optional(),
  safety: z
    .object({
      scores: z
        .array(
          z.object({
            category: z.string(),
            description: z.string().optional(),
            value: z.number().min(0).max(100),
          })
        )
        .optional(),
      summary: z.string().optional(),
    })
    .optional(),
  schemaVersion: z.literal("dest.v1").default("dest.v1"),
  sources: z.array(agentSourceSchema).default([]),
});

export type DestinationResearchRequest = z.infer<
  typeof destinationResearchRequestSchema
>;
export type DestinationResearchResult = z.infer<typeof destinationResearchResultSchema>;

/**
 * Single day schema within an itinerary plan.
 *
 * Represents one day with date, day number, title, summary, and list of
 * activities with optional times, locations, and URLs.
 */
const itineraryDaySchema = z.object({
  activities: z
    .array(
      z.object({
        description: z.string().optional(),
        location: z.string().optional(),
        name: z.string(),
        time: z.string().optional(),
        url: z.string().url().optional(),
      })
    )
    .default([]),
  date: z.string().optional(),
  day: z.number().int().positive(),
  summary: z.string().optional(),
  title: z.string().optional(),
});

/**
 * Itinerary planning request schema.
 *
 * Defines input parameters for generating a multi-day itinerary including
 * destination, duration, budget, party size, interests, and travel dates.
 */
export const itineraryPlanRequestSchema = z.object({
  budgetPerDay: z.number().positive().optional(),
  destination: z.string().min(1),
  durationDays: z.number().int().positive().optional(),
  interests: z.array(z.string()).optional(),
  partySize: z.number().int().positive().optional(),
  travelDates: z.string().optional(),
});

/**
 * Itinerary planning result schema.
 *
 * Itinerary output with destination, overview, day-by-day plan, optional
 * recommendations, and source citations.
 */
export const itineraryPlanResultSchema = z.object({
  days: z.array(itineraryDaySchema).default([]),
  destination: z.string(),
  overview: z.string().optional(),
  recommendations: z.array(destinationItemSchema).optional(),
  schemaVersion: z.literal("itin.v1").default("itin.v1"),
  sources: z.array(agentSourceSchema).default([]),
});

export type ItineraryPlanRequest = z.infer<typeof itineraryPlanRequestSchema>;
export type ItineraryPlanResult = z.infer<typeof itineraryPlanResultSchema>;

/**
 * Flight segment schema for individual flight legs.
 *
 * Represents a single flight segment with origin, destination, departure/arrival
 * times, carrier information, and optional operating carrier/flight number.
 */
const flightSegmentSchema = z.object({
  arrival: z.string(),
  carrier: z.string(),
  departure: z.string(),
  destination: z.string(),
  flightNumber: z.string().optional(),
  operatingCarrier: z.string().optional(),
  origin: z.string(),
});

/**
 * Flight search request schema.
 *
 * Defines input parameters for searching flights including origin, destination,
 * departure date, optional return date, passenger count, and cabin class.
 */
export const flightSearchRequestSchema = z.object({
  cabinClass: z.string().optional(),
  departureDate: z.string(),
  destination: z.string().min(3),
  origin: z.string().min(3),
  passengers: z.number().int().positive().default(1),
  returnDate: z.string().optional(),
});

/**
 * Flight search result schema.
 *
 * Flight search output with currency, list of itineraries (each with
 * segments, price, booking URL), and source citations.
 */
export const flightSearchResultSchema = z.object({
  currency: z.string().default("USD"),
  itineraries: z.array(
    z.object({
      bookingUrl: z.string().url().optional(),
      id: z.string(),
      price: z.number().positive(),
      segments: z.array(flightSegmentSchema),
    })
  ),
  schemaVersion: z.literal("flight.v1").default("flight.v1"),
  sources: z.array(agentSourceSchema).default([]),
});

export type FlightSearchRequest = z.infer<typeof flightSearchRequestSchema>;
export type FlightSearchResult = z.infer<typeof flightSearchResultSchema>;

/**
 * Accommodation stay option schema.
 *
 * Represents a single accommodation option with name, address, amenities,
 * nightly rate, rating, currency, and optional booking URL.
 */
const stayOptionSchema = z.object({
  address: z.string().optional(),
  amenities: z.array(z.string()).optional(),
  currency: z.string().optional(),
  name: z.string(),
  nightlyRate: z.number().positive().optional(),
  rating: z.number().min(0).max(5).optional(),
  url: z.string().url().optional(),
});

/**
 * Accommodation search request schema.
 *
 * Defines input parameters for searching accommodations including destination,
 * check-in/out dates, guest count, and optional room count.
 */
export const accommodationSearchRequestSchema = z.object({
  checkIn: z.string(),
  checkOut: z.string(),
  destination: z.string().min(1),
  guests: z.number().int().positive().default(2),
  roomCount: z.number().int().positive().optional(),
});

/**
 * Accommodation search result schema.
 *
 * Accommodation search output with list of stay options and source citations.
 */
export const accommodationSearchResultSchema = z.object({
  schemaVersion: z.literal("stay.v1").default("stay.v1"),
  sources: z.array(agentSourceSchema).default([]),
  stays: z.array(stayOptionSchema),
});

export type AccommodationSearchRequest = z.infer<
  typeof accommodationSearchRequestSchema
>;
export type AccommodationSearchResult = z.infer<typeof accommodationSearchResultSchema>;

/**
 * Budget planning request schema.
 *
 * Defines input parameters for generating a budget plan including destination,
 * duration, optional budget cap, traveler count, and preferred currency.
 */
export const budgetPlanRequestSchema = z.object({
  budgetCap: z.number().positive().optional(),
  destination: z.string().min(1),
  durationDays: z.number().int().positive(),
  preferredCurrency: z.string().optional(),
  travelers: z.number().int().positive().optional(),
});

/**
 * Budget planning result schema.
 *
 * Budget plan output with currency, category allocations (amount, category,
 * rationale), and optional tips.
 */
export const budgetPlanResultSchema = z.object({
  allocations: z
    .array(
      z.object({
        amount: z.number().nonnegative(),
        category: z.string(),
        rationale: z.string().optional(),
      })
    )
    .default([]),
  currency: z.string().default("USD"),
  schemaVersion: z.literal("budget.v1").default("budget.v1"),
  tips: z.array(z.string()).optional(),
});

export type BudgetPlanRequest = z.infer<typeof budgetPlanRequestSchema>;
export type BudgetPlanResult = z.infer<typeof budgetPlanResultSchema>;

/**
 * Memory record schema for user preference and context storage.
 *
 * Represents a single memory entry with content, optional category,
 * creation timestamp, and unique identifier.
 */
export const memoryRecordSchema = z.object({
  category: z.string().optional(),
  content: z.string(),
  createdAt: z.string().optional(),
  id: z.string().optional(),
});

export type MemoryRecord = z.infer<typeof memoryRecordSchema>;

/**
 * Memory update request schema.
 *
 * Defines input for updating user memories with array of records and
 * optional user ID for scoping.
 */
export const memoryUpdateRequestSchema = z.object({
  records: z.array(memoryRecordSchema),
  userId: z.string().uuid().optional(),
});

/**
 * Router classification schema for workflow routing decisions.
 *
 * Represents a classification result with selected agent workflow,
 * confidence score (0-1), and optional reasoning explanation.
 */
export const routerClassificationSchema = z.object({
  agent: agentWorkflowSchema,
  confidence: z.number().min(0).max(1),
  reasoning: z.string().optional(),
});

export type RouterClassification = z.infer<typeof routerClassificationSchema>;

/**
 * Collection of all agent workflow schemas for programmatic access.
 *
 * Exports all request/response schemas and router classification schema
 * for validation and type inference.
 */
export const agentSchemas = {
  accommodationSearchRequestSchema,
  accommodationSearchResultSchema,
  budgetPlanRequestSchema,
  budgetPlanResultSchema,
  destinationResearchRequestSchema,
  destinationResearchResultSchema,
  flightSearchRequestSchema,
  flightSearchResultSchema,
  itineraryPlanRequestSchema,
  itineraryPlanResultSchema,
  memoryUpdateRequestSchema,
  routerClassificationSchema,
};

export type AgentSchemas = typeof agentSchemas;
