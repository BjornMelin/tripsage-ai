/**
 * @fileoverview Trip-related Zod schemas for runtime validation. Includes trip creation, updates, filtering, suggestions, and itinerary items.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";
import { EMAIL_SCHEMA, NAME_SCHEMA } from "./shared/person";
import { FUTURE_DATE_SCHEMA } from "./shared/time";
import { tripStatusSchema, tripTypeSchema } from "./supabase";

// ===== CORE SCHEMAS =====
// Core business logic schemas for trip management

/** Zod schema for trip visibility levels. */
export const visibilitySchema = z.enum(["private", "shared", "public"]);

/** TypeScript type for trip visibility levels. */
export type TripVisibility = z.infer<typeof visibilitySchema>;

/** Zod schema for trip collaborator permission tiers. */
export const tripCollaboratorRoleSchema = z.enum(["viewer", "editor", "owner"]);

/** TypeScript type for trip collaborator permission tiers. */
export type TripCollaboratorRole = z.infer<typeof tripCollaboratorRoleSchema>;

/**
 * Zod schema for collaborator rows returned by the collaboration API.
 *
 * Note: The trip owner is derived from the trip record and is not a row in
 * `public.trip_collaborators`.
 */
export const tripCollaboratorSchema = z.strictObject({
  createdAt: z.string().nullable(),
  id: z.number().int(),
  role: tripCollaboratorRoleSchema,
  tripId: z.number().int(),
  userEmail: EMAIL_SCHEMA.optional(),
  userId: primitiveSchemas.uuid,
});

/** TypeScript type for collaborator rows returned by the collaboration API. */
export type TripCollaborator = z.infer<typeof tripCollaboratorSchema>;

/** Zod schema for inviting/adding a collaborator to a trip. */
export const tripCollaboratorInviteSchema = z.strictObject({
  email: EMAIL_SCHEMA,
  role: tripCollaboratorRoleSchema.default("viewer"),
});

/** TypeScript type for collaborator invite inputs. */
export type TripCollaboratorInviteInput = z.infer<typeof tripCollaboratorInviteSchema>;

/** Zod schema for updating a collaborator's role. */
export const tripCollaboratorRoleUpdateSchema = z.strictObject({
  role: tripCollaboratorRoleSchema,
});

/** TypeScript type for collaborator role updates. */
export type TripCollaboratorRoleUpdateInput = z.infer<
  typeof tripCollaboratorRoleUpdateSchema
>;

/**
 * Zod schema for trip destinations (UI/store representation).
 * Represents a destination within a trip with activities, accommodation, and transportation.
 */
export const tripDestinationSchema = z.strictObject({
  accommodation: z
    .object({
      name: z.string(),
      price: z.number().optional(),
      type: z.string(),
    })
    .optional(),
  activities: z.array(z.string()).optional(),
  coordinates: z
    .object({
      latitude: z.number(),
      longitude: z.number(),
    })
    .optional(),
  country: z.string(),
  endDate: z.string().optional(),
  estimatedCost: z.number().optional(),
  id: z.string(),
  name: z.string(),
  notes: z.string().optional(),
  startDate: z.string().optional(),
  transportation: z
    .object({
      details: z.string(),
      price: z.number().optional(),
      type: z.string(),
    })
    .optional(),
});

/** TypeScript type for trip destinations. */
export type TripDestination = z.infer<typeof tripDestinationSchema>;

/**
 * Zod schema for trip preferences (UI/store representation).
 * Includes budget breakdown, accommodation preferences, transportation, activities, etc.
 */
export const tripPreferencesSchema = z
  .strictObject({
    accessibilityNeeds: z.array(z.string()).optional(),
    accommodation: z
      .object({
        amenities: z.array(z.string()).optional(),
        locationPreference: z.string().optional(),
        minRating: z.number().optional(),
        type: z.string().optional(),
      })
      .optional(),
    activities: z.array(z.string()).optional(),
    budget: z
      .object({
        accommodationBudget: z.number().optional(),
        activitiesBudget: z.number().optional(),
        currency: z.string().optional(),
        foodBudget: z.number().optional(),
        total: z.number().optional(),
        transportationBudget: z.number().optional(),
      })
      .optional(),
    dietaryRestrictions: z.array(z.string()).optional(),
    transportation: z
      .object({
        flightPreferences: z
          .object({
            maxStops: z.number().optional(),
            preferredAirlines: z.array(z.string()).optional(),
            seatClass: z.string().optional(),
            timeWindow: z.string().optional(),
          })
          .optional(),
        localTransportation: z.array(z.string()).optional(),
      })
      .optional(),
  })
  .catchall(z.unknown()); // Allow additional preferences

/** TypeScript type for trip preferences. */
export type TripPreferences = z.infer<typeof tripPreferencesSchema>;

/**
 * Zod schema for UI Trip representation.
 * Maps database trips to UI-friendly format with camelCase fields and flat budget.
 * This is the canonical schema for the trip store and UI components.
 */
export const storeTripSchema = z.strictObject({
  budget: primitiveSchemas.nonNegativeNumber.optional(),
  createdAt: z.string().optional(),
  currency: primitiveSchemas.isoCurrency.default("USD"),
  description: z.string().optional(),
  destination: z.string().optional(),
  destinations: z.array(tripDestinationSchema).default([]),
  endDate: z.string().optional(),
  id: z.string(),
  preferences: tripPreferencesSchema.optional(),
  startDate: z.string().optional(),
  status: tripStatusSchema.optional(),
  tags: z.array(z.string()).optional(),
  title: z.string(),
  travelers: z.number().int().optional(),
  tripType: tripTypeSchema.optional(),
  updatedAt: z.string().optional(),
  userId: z.string().optional(),
  visibility: visibilitySchema.optional(),
});

/** TypeScript type for UI Trip representation. */
export type UiTrip = z.infer<typeof storeTripSchema>;

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
export const itineraryItemTypeSchema = z.enum([
  "activity",
  "meal",
  "transport",
  "accommodation",
  "event",
  "other",
]);

/** TypeScript type for itinerary item types. */
export type ItineraryItemType = z.infer<typeof itineraryItemTypeSchema>;

export const itineraryItemBookingStatusSchema = z.enum([
  "planned",
  "reserved",
  "booked",
  "completed",
  "cancelled",
]);

export type ItineraryItemBookingStatus = z.infer<
  typeof itineraryItemBookingStatusSchema
>;

const itineraryItemBaseSchema = z.strictObject({
  bookingStatus: itineraryItemBookingStatusSchema.default("planned"),
  currency: primitiveSchemas.isoCurrency.default("USD"),
  description: primitiveSchemas.nonEmptyString.max(1000).optional(),
  endAt: primitiveSchemas.isoDateTime.optional(),
  externalId: z.string().optional(),
  location: z.string().optional(),
  price: primitiveSchemas.nonNegativeNumber.optional(),
  startAt: primitiveSchemas.isoDateTime.optional(),
  title: primitiveSchemas.nonEmptyString.max(200),
  tripId: primitiveSchemas.positiveNumber.int(),
});

const itineraryActivityPayloadSchema = z
  .strictObject({
    placeId: z.string().optional(),
    provider: z.string().optional(),
    url: primitiveSchemas.url.optional(),
  })
  .catchall(z.unknown());

const itineraryMealPayloadSchema = z
  .strictObject({
    cuisine: z.string().optional(),
    reservationName: z.string().optional(),
    reservationPhone: z.string().optional(),
    url: primitiveSchemas.url.optional(),
  })
  .catchall(z.unknown());

const itineraryTransportPayloadSchema = z
  .strictObject({
    bookingReference: z.string().optional(),
    from: z.string().optional(),
    mode: z
      .enum(["flight", "train", "car", "bus", "ferry", "walk", "rideshare", "other"])
      .optional(),
    to: z.string().optional(),
    url: primitiveSchemas.url.optional(),
  })
  .catchall(z.unknown());

const itineraryAccommodationPayloadSchema = z
  .strictObject({
    checkIn: primitiveSchemas.isoDateTime.optional(),
    checkOut: primitiveSchemas.isoDateTime.optional(),
    propertyName: z.string().optional(),
    provider: z.string().optional(),
    url: primitiveSchemas.url.optional(),
  })
  .catchall(z.unknown());

const itineraryEventPayloadSchema = z
  .strictObject({
    eventId: z.string().optional(),
    organizer: z.string().optional(),
    ticketsUrl: primitiveSchemas.url.optional(),
  })
  .catchall(z.unknown());

const itineraryOtherPayloadSchema = z.strictObject({}).catchall(z.unknown());

export const itineraryItemCreateSchema = z.discriminatedUnion("itemType", [
  itineraryItemBaseSchema.extend({
    itemType: z.literal("activity"),
    payload: itineraryActivityPayloadSchema,
  }),
  itineraryItemBaseSchema.extend({
    itemType: z.literal("meal"),
    payload: itineraryMealPayloadSchema,
  }),
  itineraryItemBaseSchema.extend({
    itemType: z.literal("transport"),
    payload: itineraryTransportPayloadSchema,
  }),
  itineraryItemBaseSchema.extend({
    itemType: z.literal("accommodation"),
    payload: itineraryAccommodationPayloadSchema,
  }),
  itineraryItemBaseSchema.extend({
    itemType: z.literal("event"),
    payload: itineraryEventPayloadSchema,
  }),
  itineraryItemBaseSchema.extend({
    itemType: z.literal("other"),
    payload: itineraryOtherPayloadSchema,
  }),
]);

/** TypeScript type for itinerary item creation input. */
export type ItineraryItemCreateInput = z.infer<typeof itineraryItemCreateSchema>;

/**
 * Zod schema for creating or updating itinerary items.
 *
 * - New item: omit `id`
 * - Update existing: include `id`
 */
export const itineraryItemUpsertSchema = z.discriminatedUnion("itemType", [
  itineraryItemBaseSchema.extend({
    id: primitiveSchemas.positiveNumber.int().optional(),
    itemType: z.literal("activity"),
    payload: itineraryActivityPayloadSchema,
  }),
  itineraryItemBaseSchema.extend({
    id: primitiveSchemas.positiveNumber.int().optional(),
    itemType: z.literal("meal"),
    payload: itineraryMealPayloadSchema,
  }),
  itineraryItemBaseSchema.extend({
    id: primitiveSchemas.positiveNumber.int().optional(),
    itemType: z.literal("transport"),
    payload: itineraryTransportPayloadSchema,
  }),
  itineraryItemBaseSchema.extend({
    id: primitiveSchemas.positiveNumber.int().optional(),
    itemType: z.literal("accommodation"),
    payload: itineraryAccommodationPayloadSchema,
  }),
  itineraryItemBaseSchema.extend({
    id: primitiveSchemas.positiveNumber.int().optional(),
    itemType: z.literal("event"),
    payload: itineraryEventPayloadSchema,
  }),
  itineraryItemBaseSchema.extend({
    id: primitiveSchemas.positiveNumber.int().optional(),
    itemType: z.literal("other"),
    payload: itineraryOtherPayloadSchema,
  }),
]);

/** TypeScript type for itinerary item upsert input. */
export type ItineraryItemUpsertInput = z.infer<typeof itineraryItemUpsertSchema>;

const itineraryItemUiBaseSchema = itineraryItemBaseSchema.extend({
  createdAt: primitiveSchemas.isoDateTime.optional(),
  createdBy: primitiveSchemas.uuid,
  id: primitiveSchemas.positiveNumber.int(),
  updatedAt: primitiveSchemas.isoDateTime.optional(),
});

/** Zod schema for itinerary items returned by queries and actions. */
export const itineraryItemSchema = z.discriminatedUnion("itemType", [
  itineraryItemUiBaseSchema.extend({
    itemType: z.literal("activity"),
    payload: itineraryActivityPayloadSchema,
  }),
  itineraryItemUiBaseSchema.extend({
    itemType: z.literal("meal"),
    payload: itineraryMealPayloadSchema,
  }),
  itineraryItemUiBaseSchema.extend({
    itemType: z.literal("transport"),
    payload: itineraryTransportPayloadSchema,
  }),
  itineraryItemUiBaseSchema.extend({
    itemType: z.literal("accommodation"),
    payload: itineraryAccommodationPayloadSchema,
  }),
  itineraryItemUiBaseSchema.extend({
    itemType: z.literal("event"),
    payload: itineraryEventPayloadSchema,
  }),
  itineraryItemUiBaseSchema.extend({
    itemType: z.literal("other"),
    payload: itineraryOtherPayloadSchema,
  }),
]);

/** TypeScript type for itinerary items returned by queries and actions. */
export type ItineraryItem = z.infer<typeof itineraryItemSchema>;

// ===== FORM SCHEMAS =====
// UI form validation schemas with user-friendly error messages

// Common form validation patterns - using shared primitives
const CURRENCY_SCHEMA = primitiveSchemas.isoCurrency;

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
 * Form schema for updating trip details from the trip detail page.
 *
 * This schema is intentionally UI-focused (Client Components) and should stay
 * aligned with the allowed `updateTrip()` action patch fields.
 */
export const tripSettingsFormSchema = z
  .strictObject({
    description: z.string().max(1000, { error: "Description too long" }).optional(),
    destination: z.string().max(200, { error: "Destination too long" }).optional(),
    endDate: z.iso.date().optional(),
    startDate: z.iso.date().optional(),
    title: z
      .string()
      .min(1, { error: "Trip title is required" })
      .max(200, { error: "Title too long" }),
  })
  .refine(
    (data) => !data.startDate || !data.endDate || data.endDate >= data.startDate,
    {
      error: "End date must be on or after start date",
      path: ["endDate"],
    }
  );

/** TypeScript type for trip settings form data. */
export type TripSettingsFormData = z.infer<typeof tripSettingsFormSchema>;

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
