/**
 * @fileoverview Canonical Zod v4 schemas for flights.
 * Defines domain entities, tool inputs/outputs, and normalized offers.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====

export const CABIN_CLASS_ENUM = z.enum([
  "economy",
  "premium_economy",
  "business",
  "first",
]);
export type CabinClass = z.infer<typeof CABIN_CLASS_ENUM>;

export const FLIGHT_LOCATION_SCHEMA = z.strictObject({
  airport: z.string().min(3).max(64).optional(),
  city: z.string().optional(),
  country: z.string().optional(),
  iata: z.string().min(3).max(3),
  terminal: z.string().optional(),
});
export type FlightLocation = z.infer<typeof FLIGHT_LOCATION_SCHEMA>;

export const FLIGHT_SEGMENT_SCHEMA = z.strictObject({
  arrivalTime: z.string().optional(),
  carrier: z.string().optional(),
  departureTime: z.string().optional(),
  destination: FLIGHT_LOCATION_SCHEMA,
  durationMinutes: z.number().int().positive().optional(),
  flightNumber: z.string().optional(),
  marketingCarrier: z.string().optional(),
  operatingCarrier: z.string().optional(),
  origin: FLIGHT_LOCATION_SCHEMA,
});
export type FlightSegment = z.infer<typeof FLIGHT_SEGMENT_SCHEMA>;

export const FLIGHT_SLICE_SCHEMA = z.strictObject({
  cabinClass: CABIN_CLASS_ENUM,
  segments: z.array(FLIGHT_SEGMENT_SCHEMA).min(1),
});
export type FlightSlice = z.infer<typeof FLIGHT_SLICE_SCHEMA>;

export const PRICING_SCHEMA = z.strictObject({
  amount: z.number().positive(),
  currency: primitiveSchemas.isoCurrency.default("USD"),
});
export type Pricing = z.infer<typeof PRICING_SCHEMA>;

export const FLIGHT_OFFER_SCHEMA = z.strictObject({
  id: z.string(),
  price: PRICING_SCHEMA,
  provider: z.enum(["duffel", "expedia", "cache"]),
  slices: z.array(FLIGHT_SLICE_SCHEMA).min(1),
});
export type FlightOffer = z.infer<typeof FLIGHT_OFFER_SCHEMA>;

// ===== TOOL INPUT / OUTPUT SCHEMAS =====

export const flightSearchRequestSchema = z
  .strictObject({
    cabinClass: CABIN_CLASS_ENUM.default("economy").describe("Preferred cabin class"),
    currency: primitiveSchemas.isoCurrency
      .default("USD")
      .describe("ISO 4217 currency code"),
    departureDate: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/)
      .describe("Outbound date (YYYY-MM-DD)"),
    destination: z.string().min(3).describe("Destination airport IATA code"),
    nonstop: z.boolean().default(false).optional().describe("Require nonstop only"),
    origin: z.string().min(3).describe("Origin airport IATA code"),
    passengers: z.number().int().positive().default(1).describe("Passenger count"),
    returnDate: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/)
      .optional()
      .describe("Return date (YYYY-MM-DD)"),
  })
  .describe("Input parameters for flight search");

export type FlightSearchRequest = z.infer<typeof flightSearchRequestSchema>;

export const flightSearchResultSchema = z
  .strictObject({
    currency: primitiveSchemas.isoCurrency.default("USD"),
    fromCache: z.boolean().default(false),
    itineraries: z
      .array(
        z.strictObject({
          bookingUrl: z.url().optional(),
          id: z.string(),
          price: z.number().positive(),
          segments: z.array(
            z.strictObject({
              arrival: z.string().optional(),
              carrier: z.string().optional(),
              departure: z.string().optional(),
              destination: z.string().min(3),
              flightNumber: z.string().optional(),
              operatingCarrier: z.string().optional(),
              origin: z.string().min(3),
            })
          ),
        })
      )
      .default([]),
    offers: z.array(FLIGHT_OFFER_SCHEMA).default([]),
    provider: z.enum(["duffel", "expedia", "cache"]).default("duffel"),
    schemaVersion: z.literal("flight.v2").default("flight.v2"),
    sources: z
      .array(
        z.object({
          publishedAt: z.string().optional(),
          snippet: z.string().optional(),
          title: z.string().optional(),
          url: z.url().optional(),
        })
      )
      .default([]),
  })
  .describe("Normalized flight search results");

export type FlightSearchResult = z.infer<typeof flightSearchResultSchema>;

export const flightSearchSchemas = {
  flightSearchRequestSchema,
  flightSearchResultSchema,
} as const;
