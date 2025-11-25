/**
 * @fileoverview Trip-related Zod schemas for runtime validation.
 * Includes trip creation, updates, filtering, suggestions, and itinerary items.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";
import { EMAIL_SCHEMA, NAME_SCHEMA } from "./shared/person";
import { tripStatusSchema, tripTypeSchema } from "./supabase";

// ===== CORE SCHEMAS =====
// Core business logic schemas for trip management

/** Zod schema for trip visibility levels. */
export const visibilitySchema = z.enum(["private", "shared", "public"]);

/** TypeScript type for trip visibility levels. */
export type TripVisibility = z.infer<typeof visibilitySchema>;

/**
 * Zod schema for filtering trips based on various criteria.
 * Supports filtering by destination, date range, and status.
 */
export const tripFiltersSchema = z.strictObject({
  destination: primitiveSchemas.nonEmptyString.max(200).optional(),
  endDate: z.string().optional(),
  startDate: z.string().optional(),
  status: tripStatusSchema.optional(),
});

/** TypeScript type for trip filter criteria. */
export type TripFilters = z.infer<typeof tripFiltersSchema>;

/**
 * Zod schema for creating new trips with required and optional fields.
 * Validates trip parameters including dates, budget, travelers, and preferences.
 */
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

/** TypeScript type for trip creation input. */
export type TripCreateInput = z.infer<typeof tripCreateSchema>;

/**
 * Zod schema for updating existing trips.
 * Allows partial updates while maintaining validation constraints.
 */
export const tripUpdateSchema = tripCreateSchema.partial();

/** TypeScript type for trip update input. */
export type TripUpdateInput = z.infer<typeof tripUpdateSchema>;

/**
 * Zod schema for AI-generated trip suggestions with ratings and metadata.
 * Includes destination details, pricing, difficulty, and recommendation scores.
 */
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

/** TypeScript type for AI-generated trip suggestions. */
export type TripSuggestion = z.infer<typeof tripSuggestionSchema>;

/**
 * Zod schema for creating itinerary items like activities, meals, and transportation.
 * Validates item details including booking status, timing, and pricing.
 */
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

/** TypeScript type for itinerary item creation input. */
export type ItineraryItemCreateInput = z.infer<typeof itineraryItemCreateSchema>;

/**
 * Zod schema for updating existing itinerary items.
 * Allows partial updates of itinerary item properties.
 */
export const itineraryItemUpdateSchema = itineraryItemCreateSchema.partial();

/** TypeScript type for itinerary item update input. */
export type ItineraryItemUpdateInput = z.infer<typeof itineraryItemUpdateSchema>;

// ===== FORM SCHEMAS =====
// UI form validation schemas with user-friendly error messages

// Common form validation patterns
const CURRENCY_SCHEMA = primitiveSchemas.isoCurrency;
const FUTURE_DATE_SCHEMA = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, { error: "Please enter a valid date (YYYY-MM-DD)" })
  .refine((date) => !Number.isNaN(new Date(date).getTime()), {
    error: "Please enter a valid date",
  })
  .refine((date) => new Date(date) > new Date(), {
    error: "Date must be in the future",
  });

/**
 * Form schema for creating new trips.
 * Includes validation for dates, travelers, budget, and collaboration settings.
 */
export const createTripFormSchema = z
  .object({
    allowCollaboration: z.boolean(),
    budget: z
      .object({
        currency: CURRENCY_SCHEMA,
        total: z.number().positive({ error: "Budget must be positive" }),
      })
      .optional(),
    description: z.string().max(1000, { error: "Description too long" }).optional(),
    destination: z.string().min(1, { error: "Destination is required" }),
    endDate: FUTURE_DATE_SCHEMA,
    startDate: FUTURE_DATE_SCHEMA,
    tags: z.array(z.string().max(50)).max(10).optional(),
    title: z
      .string()
      .min(1, { error: "Trip title is required" })
      .max(200, { error: "Title too long" }),
    travelers: z
      .array(
        z.object({
          ageGroup: z.enum(["adult", "child", "infant"]).optional(),
          email: EMAIL_SCHEMA.optional(),
          name: NAME_SCHEMA,
          role: z.enum(["owner", "collaborator", "viewer"]).optional(),
        })
      )
      .min(1, { error: "At least one traveler is required" })
      .max(20, { error: "Too many travelers" }),
  })
  .refine((data) => new Date(data.endDate) > new Date(data.startDate), {
    error: "End date must be after start date",
    path: ["endDate"],
  });

/** TypeScript type for trip creation form data. */
export type CreateTripFormData = z.infer<typeof createTripFormSchema>;

/**
 * Form schema for updating existing trips.
 * Allows partial updates of trip properties with validation.
 */
export const updateTripFormSchema = z.object({
  budget: z.number().optional(),
  description: z.string().optional(),
  destination: z.string().optional(),
  endDate: z.iso.date().optional(),
  id: primitiveSchemas.uuid,
  maxParticipants: z.number().optional(),
  startDate: z.iso.date().optional(),
  tags: z.array(z.string()).optional(),
  title: z.string().optional(),
});

/** TypeScript type for trip update form data. */
export type UpdateTripFormData = z.infer<typeof updateTripFormSchema>;

/**
 * Form schema for adding travelers to trips.
 * Validates traveler details and invitation settings.
 */
export const addTravelerFormSchema = z.object({
  ageGroup: z.enum(["adult", "child", "infant"]),
  email: EMAIL_SCHEMA.optional(),
  name: NAME_SCHEMA,
  role: z.enum(["collaborator", "viewer"]),
  sendInvitation: z.boolean(),
});

/** TypeScript type for add traveler form data. */
export type AddTravelerFormData = z.infer<typeof addTravelerFormSchema>;
