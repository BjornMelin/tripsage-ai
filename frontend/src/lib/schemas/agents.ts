/**
 * @fileoverview Canonical Zod v4 schemas for Agent workflows (single source of truth).
 *
 * Defines request/response schemas for destination research, itinerary planning,
 * flight search, accommodation search, budget planning, memory updates, and
 * router classification workflows.
 */

import { z } from "zod";

/** Zod schema for supported agent workflow types. */
export const agentWorkflowSchema = z
  .enum([
    "destinationResearch",
    "itineraryPlanning",
    "flightSearch",
    "accommodationSearch",
    "budgetPlanning",
    "memoryUpdate",
    "router",
  ])
  .describe("Supported agent workflows");
/** TypeScript type for agent workflows. */
export type AgentWorkflow = z.infer<typeof agentWorkflowSchema>;

/** Zod schema for source citations in agent research results. */
export const agentSourceSchema = z
  .object({
    publishedAt: z.string().optional(),
    snippet: z.string().optional(),
    title: z.string().optional(),
    url: z.string().url(),
  })
  .describe("Source citation with URL and optional metadata");
/** TypeScript type for agent source citations. */
export type AgentSource = z.infer<typeof agentSourceSchema>;

// Destination item schema
const destinationItemSchema = z.object({
  description: z.string().optional(),
  tags: z.array(z.string()).optional(),
  title: z.string(),
  url: z.string().url().optional(),
});

/** Zod schema for destination research requests. */
export const destinationResearchRequestSchema = z
  .object({
    destination: z.string().min(1),
    locale: z.string().optional(),
    specificInterests: z.array(z.string()).optional(),
    travelDates: z.string().optional(),
    travelStyle: z.string().optional(),
  })
  .describe("Input for researching a destination");

/** Zod schema for destination research results. */
export const destinationResearchResultSchema = z
  .object({
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
  })
  .describe("Destination research output");

/** TypeScript type for destination research requests. */
export type DestinationResearchRequest = z.infer<
  typeof destinationResearchRequestSchema
>;
/** TypeScript type for destination research results. */
export type DestinationResearchResult = z.infer<typeof destinationResearchResultSchema>;

// Itinerary planning
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

/** Zod schema for itinerary planning requests. */
export const itineraryPlanRequestSchema = z
  .object({
    budgetPerDay: z.number().positive().optional(),
    destination: z.string().min(1),
    durationDays: z.number().int().positive().optional(),
    interests: z.array(z.string()).optional(),
    partySize: z.number().int().positive().optional(),
    travelDates: z.string().optional(),
  })
  .describe("Input for itinerary planning");

/** Zod schema for itinerary planning results. */
export const itineraryPlanResultSchema = z
  .object({
    days: z.array(itineraryDaySchema).default([]),
    destination: z.string(),
    overview: z.string().optional(),
    recommendations: z.array(destinationItemSchema).optional(),
    schemaVersion: z.literal("itin.v1").default("itin.v1"),
    sources: z.array(agentSourceSchema).default([]),
  })
  .describe("Itinerary planning output");

/** TypeScript type for itinerary planning requests. */
export type ItineraryPlanRequest = z.infer<typeof itineraryPlanRequestSchema>;
/** TypeScript type for itinerary planning results. */
export type ItineraryPlanResult = z.infer<typeof itineraryPlanResultSchema>;

// Flight search
const flightSegmentSchema = z.object({
  arrival: z.string(),
  carrier: z.string(),
  departure: z.string(),
  destination: z.string(),
  flightNumber: z.string().optional(),
  operatingCarrier: z.string().optional(),
  origin: z.string(),
});

/** Zod schema for flight search requests. */
export const flightSearchRequestSchema = z
  .object({
    cabinClass: z.string().optional(),
    departureDate: z.string(),
    destination: z.string().min(3),
    origin: z.string().min(3),
    passengers: z.number().int().positive().default(1),
    returnDate: z.string().optional(),
  })
  .describe("Input for flight search");

/** Zod schema for flight search results. */
export const flightSearchResultSchema = z
  .object({
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
  })
  .describe("Flight search output");

/** TypeScript type for flight search requests. */
export type FlightSearchRequest = z.infer<typeof flightSearchRequestSchema>;
/** TypeScript type for flight search results. */
export type FlightSearchResult = z.infer<typeof flightSearchResultSchema>;

// Accommodation search
const stayOptionSchema = z.object({
  address: z.string().optional(),
  amenities: z.array(z.string()).optional(),
  currency: z.string().optional(),
  name: z.string(),
  nightlyRate: z.number().positive().optional(),
  rating: z.number().min(0).max(5).optional(),
  url: z.string().url().optional(),
});

/** Zod schema for accommodation search requests. */
export const accommodationSearchRequestSchema = z
  .object({
    checkIn: z.string(),
    checkOut: z.string(),
    destination: z.string().min(1),
    guests: z.number().int().positive().default(2),
    roomCount: z.number().int().positive().optional(),
  })
  .describe("Input for accommodation search");

/** Zod schema for accommodation search results. */
export const accommodationSearchResultSchema = z
  .object({
    schemaVersion: z.literal("stay.v1").default("stay.v1"),
    sources: z.array(agentSourceSchema).default([]),
    stays: z.array(stayOptionSchema),
  })
  .describe("Accommodation search output");

/** TypeScript type for accommodation search requests. */
export type AccommodationSearchRequest = z.infer<
  typeof accommodationSearchRequestSchema
>;
/** TypeScript type for accommodation search results. */
export type AccommodationSearchResult = z.infer<typeof accommodationSearchResultSchema>;

/** Zod schema for budget planning requests. */
export const budgetPlanRequestSchema = z
  .object({
    budgetCap: z.number().positive().optional(),
    destination: z.string().min(1),
    durationDays: z.number().int().positive(),
    preferredCurrency: z.string().optional(),
    travelers: z.number().int().positive().optional(),
  })
  .describe("Input for budget planning");

/** Zod schema for budget planning results. */
export const budgetPlanResultSchema = z
  .object({
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
    sources: z.array(agentSourceSchema).default([]),
    tips: z.array(z.string()).optional(),
  })
  .describe("Budget plan output");

/** TypeScript type for budget planning requests. */
export type BudgetPlanRequest = z.infer<typeof budgetPlanRequestSchema>;
/** TypeScript type for budget planning results. */
export type BudgetPlanResult = z.infer<typeof budgetPlanResultSchema>;

/** Zod schema for memory record entries. */
export const memoryRecordSchema = z
  .object({
    category: z.string().optional(),
    content: z.string(),
    createdAt: z.string().optional(),
    id: z.string().optional(),
  })
  .describe("Memory record entry");
/** TypeScript type for memory records. */
export type MemoryRecord = z.infer<typeof memoryRecordSchema>;

/** Zod schema for memory update requests. */
export const memoryUpdateRequestSchema = z
  .object({
    records: z.array(memoryRecordSchema),
    userId: z.string().uuid().optional(),
  })
  .describe("Input for updating user memories");
/** TypeScript type for memory update requests. */
export type MemoryUpdateRequest = z.infer<typeof memoryUpdateRequestSchema>;

/** Zod schema for router workflow classification results. */
export const routerClassificationSchema = z
  .object({
    agent: agentWorkflowSchema,
    confidence: z.number().min(0).max(1),
    reasoning: z.string().optional(),
  })
  .describe("Workflow classification result");
/** TypeScript type for router classifications. */
export type RouterClassification = z.infer<typeof routerClassificationSchema>;

/** Collection of all agent workflow schemas. */
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
/** TypeScript type for the agent schemas collection. */
export type AgentSchemas = typeof agentSchemas;
