/**
 * @fileoverview Trip-related Zod schemas for runtime validation.
 *
 * Defines schemas for trip creation, updates, filtering, suggestions, and itinerary items.
 * Uses Zod v4 APIs and schema registry for consistency.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";
import { tripStatusSchema, tripTypeSchema } from "./supabase";

const visibilitySchema = z.enum(["private", "shared", "public"]);

/** Schema for filtering trips based on various criteria. */
export const tripFiltersSchema = z.strictObject({
  destination: primitiveSchemas.nonEmptyString.max(200).optional(),
  endDate: z.string().optional(),
  startDate: z.string().optional(),
  status: tripStatusSchema.optional(),
});

/** Schema for creating new trips with required and optional fields. */
export const tripCreateSchema = z.strictObject({
  budget: primitiveSchemas.nonNegativeNumber.optional(),
  currency: primitiveSchemas.isoCurrency.default("USD"),
  description: primitiveSchemas.nonEmptyString.max(1000).optional(),
  destination: primitiveSchemas.nonEmptyString.max(200),
  endDate: z.string(),
  preferences: z.record(primitiveSchemas.nonEmptyString, z.unknown()).optional(),
  startDate: z.string(),
  status: tripStatusSchema.default("planning"),
  tags: z.array(primitiveSchemas.nonEmptyString).max(50).optional(),
  title: primitiveSchemas.nonEmptyString.max(200),
  travelers: primitiveSchemas.positiveNumber.int().default(1),
  tripType: tripTypeSchema.default("leisure"),
  visibility: visibilitySchema.default("private"),
});

/** Schema for updating existing trips, all fields optional. */
export const tripUpdateSchema = tripCreateSchema.partial();

/** Schema for AI-generated trip suggestions with ratings and metadata. */
export const tripSuggestionSchema = z.strictObject({
  bestTimeToVisit: primitiveSchemas.nonEmptyString,
  category: z.enum(["adventure", "relaxation", "culture", "nature", "city", "beach"]),
  currency: primitiveSchemas.isoCurrency.default("USD"),
  description: primitiveSchemas.nonEmptyString,
  destination: primitiveSchemas.nonEmptyString,
  difficulty: z.enum(["easy", "moderate", "challenging"]).optional(),
  duration: primitiveSchemas.positiveNumber.int(),
  estimatedPrice: primitiveSchemas.nonNegativeNumber,
  highlights: z.array(primitiveSchemas.nonEmptyString).default([]),
  id: primitiveSchemas.nonEmptyString,
  imageUrl: primitiveSchemas.url.nullable().optional(),
  metadata: z.record(primitiveSchemas.nonEmptyString, z.unknown()).optional(),
  rating: z.number().min(0).max(5).default(4.5),
  relevanceScore: z.number().optional(),
  seasonal: z.boolean().optional(),
  title: primitiveSchemas.nonEmptyString,
  trending: z.boolean().optional(),
});

/** Schema for creating itinerary items like activities, meals, and transportation. */
export const itineraryItemCreateSchema = z.strictObject({
  bookingStatus: z
    .enum(["planned", "reserved", "booked", "completed", "cancelled"])
    .default("planned"),
  currency: primitiveSchemas.isoCurrency.default("USD"),
  description: primitiveSchemas.nonEmptyString.max(1000).optional(),
  endTime: z.string().optional(),
  externalId: z.string().optional(),
  itemType: z.enum([
    "activity",
    "meal",
    "transport",
    "accommodation",
    "event",
    "other",
  ]),
  location: z.string().optional(),
  metadata: z.record(primitiveSchemas.nonEmptyString, z.unknown()).optional(),
  price: primitiveSchemas.nonNegativeNumber.optional(),
  startTime: z.string().optional(),
  title: primitiveSchemas.nonEmptyString.max(200),
  tripId: primitiveSchemas.positiveNumber.int(),
});

/** Schema for updating itinerary items, all fields optional. */
export const itineraryItemUpdateSchema = itineraryItemCreateSchema.partial();

/** Input type for creating new trips. */
export type TripCreateInput = z.infer<typeof tripCreateSchema>;

/** Input type for updating existing trips. */
export type TripUpdateInput = z.infer<typeof tripUpdateSchema>;

/** Type for trip filter criteria. */
export type TripFilters = z.infer<typeof tripFiltersSchema>;

/** Type for AI-generated trip suggestions. */
export type TripSuggestion = z.infer<typeof tripSuggestionSchema>;

/** Input type for creating itinerary items. */
export type ItineraryItemCreateInput = z.infer<typeof itineraryItemCreateSchema>;

/** Input type for updating itinerary items. */
export type ItineraryItemUpdateInput = z.infer<typeof itineraryItemUpdateSchema>;

/** Type for trip visibility levels. */
export type TripVisibility = z.infer<typeof visibilitySchema>;
