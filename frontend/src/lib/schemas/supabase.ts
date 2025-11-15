/**
 * @fileoverview Zod v4 schemas for Supabase database tables.
 * Generated from database.types.ts for runtime validation of database operations.
 */

import { z } from "zod";

/** Zod schema for JSON values (matches Supabase Json type). */
export const jsonSchema: z.ZodType<Json> = z.union([
  z.string(),
  z.number(),
  z.boolean(),
  z.null(),
  z.record(z.string(), z.unknown()),
  z.array(z.unknown()),
]) as z.ZodType<Json>;

/** TypeScript type for JSON (matches Supabase Json type). */
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

/** Zod schema for trip status enum. */
export const tripStatusSchema = z.enum([
  "planning",
  "booked",
  "completed",
  "cancelled",
]);
/** TypeScript type for trip status. */
export type TripStatus = z.infer<typeof tripStatusSchema>;

/** Zod schema for trip type enum. */
export const tripTypeSchema = z.enum([
  "leisure",
  "business",
  "family",
  "solo",
  "other",
]);
/** TypeScript type for trip type. */
export type TripType = z.infer<typeof tripTypeSchema>;

/**
 * Zod schema for user_settings table Row.
 *
 * Note: All user_id fields use z.uuid() because Supabase Auth generates UUIDs
 * for all user accounts. This is guaranteed by Supabase's authentication system.
 */
export const userSettingsRowSchema = z.object({
  allow_gateway_fallback: z.boolean(),
  user_id: z.uuid(),
});
/** TypeScript type for user_settings Row. */
export type UserSettingsRow = z.infer<typeof userSettingsRowSchema>;

/** Zod schema for user_settings table Insert. */
export const userSettingsInsertSchema = z.object({
  allow_gateway_fallback: z.boolean().optional(),
  user_id: z.uuid(),
});
/** TypeScript type for user_settings Insert. */
export type UserSettingsInsert = z.infer<typeof userSettingsInsertSchema>;

/** Zod schema for user_settings table Update. */
export const userSettingsUpdateSchema = z.object({
  allow_gateway_fallback: z.boolean().optional(),
  user_id: z.uuid().optional(),
});
/** TypeScript type for user_settings Update. */
export type UserSettingsUpdate = z.infer<typeof userSettingsUpdateSchema>;

/** Zod schema for trips table Row. */
export const tripsRowSchema = z.object({
  budget: z.number(),
  created_at: z.string(),
  destination: z.string(),
  end_date: z.string(),
  flexibility: jsonSchema.optional(),
  id: z.number().int(),
  name: z.string(),
  notes: z.array(z.string()).nullable(),
  search_metadata: jsonSchema.optional(),
  start_date: z.string(),
  status: tripStatusSchema,
  travelers: z.number().int(),
  trip_type: tripTypeSchema,
  updated_at: z.string(),
  user_id: z.uuid(),
});
/** TypeScript type for trips Row. */
export type TripsRow = z.infer<typeof tripsRowSchema>;

/** Zod schema for trips table Insert. */
export const tripsInsertSchema = z.object({
  budget: z.number(),
  created_at: z.string().optional(),
  destination: z.string(),
  end_date: z.string(),
  flexibility: jsonSchema.optional(),
  id: z.never().optional(),
  name: z.string(),
  notes: z.array(z.string()).nullable().optional(),
  search_metadata: jsonSchema.optional(),
  start_date: z.string(),
  status: tripStatusSchema.optional(),
  travelers: z.number().int(),
  trip_type: tripTypeSchema.optional(),
  updated_at: z.string().optional(),
  user_id: z.uuid(),
});
/** TypeScript type for trips Insert. */
export type TripsInsert = z.infer<typeof tripsInsertSchema>;

/** Zod schema for trips table Update. */
export const tripsUpdateSchema = z.object({
  budget: z.number().optional(),
  created_at: z.string().optional(),
  destination: z.string().optional(),
  end_date: z.string().optional(),
  flexibility: jsonSchema.optional(),
  id: z.never().optional(),
  name: z.string().optional(),
  notes: z.array(z.string()).nullable().optional(),
  search_metadata: jsonSchema.optional(),
  start_date: z.string().optional(),
  status: tripStatusSchema.optional(),
  travelers: z.number().int().optional(),
  trip_type: tripTypeSchema.optional(),
  updated_at: z.string().optional(),
  user_id: z.uuid().optional(),
});
/** TypeScript type for trips Update. */
export type TripsUpdate = z.infer<typeof tripsUpdateSchema>;

/** Zod schema for flight class enum. */
export const flightClassSchema = z.enum([
  "economy",
  "premium_economy",
  "business",
  "first",
]);
/** TypeScript type for flight class. */
export type FlightClass = z.infer<typeof flightClassSchema>;

/** Zod schema for booking status enum. */
export const bookingStatusSchema = z.enum([
  "available",
  "reserved",
  "booked",
  "cancelled",
]);
/** TypeScript type for booking status. */
export type BookingStatus = z.infer<typeof bookingStatusSchema>;

/** Zod schema for flights table Row. */
export const flightsRowSchema = z.object({
  airline: z.string().nullable(),
  booking_status: bookingStatusSchema,
  created_at: z.string(),
  currency: z.string(),
  departure_date: z.string(),
  destination: z.string(),
  external_id: z.string().nullable(),
  flight_class: flightClassSchema,
  flight_number: z.string().nullable(),
  id: z.number().int(),
  metadata: jsonSchema,
  origin: z.string(),
  price: z.number(),
  return_date: z.string().nullable(),
  trip_id: z.number().int(),
  updated_at: z.string(),
});
/** TypeScript type for flights Row. */
export type FlightsRow = z.infer<typeof flightsRowSchema>;

/** Zod schema for flights table Insert. */
export const flightsInsertSchema = z.object({
  airline: z.string().nullable().optional(),
  booking_status: bookingStatusSchema.optional(),
  created_at: z.string().optional(),
  currency: z.string().optional(),
  departure_date: z.string(),
  destination: z.string(),
  external_id: z.string().nullable().optional(),
  flight_class: flightClassSchema.optional(),
  flight_number: z.string().nullable().optional(),
  id: z.never().optional(),
  metadata: jsonSchema.optional(),
  origin: z.string(),
  price: z.number(),
  return_date: z.string().nullable().optional(),
  trip_id: z.number().int(),
  updated_at: z.string().optional(),
});
/** TypeScript type for flights Insert. */
export type FlightsInsert = z.infer<typeof flightsInsertSchema>;

/** Zod schema for flights table Update. */
export const flightsUpdateSchema = z.object({
  airline: z.string().nullable().optional(),
  booking_status: bookingStatusSchema.optional(),
  created_at: z.string().optional(),
  currency: z.string().optional(),
  departure_date: z.string().optional(),
  destination: z.string().optional(),
  external_id: z.string().nullable().optional(),
  flight_class: flightClassSchema.optional(),
  flight_number: z.string().nullable().optional(),
  id: z.never().optional(),
  metadata: jsonSchema.optional(),
  origin: z.string().optional(),
  price: z.number().optional(),
  return_date: z.string().nullable().optional(),
  trip_id: z.number().int().optional(),
  updated_at: z.string().optional(),
});
/** TypeScript type for flights Update. */
export type FlightsUpdate = z.infer<typeof flightsUpdateSchema>;

/** Zod schema for accommodation source enum. */
export const accommodationSourceSchema = z.enum(["hotel", "vrbo"]);
/** TypeScript type for accommodation source. */
export type AccommodationSource = z.infer<typeof accommodationSourceSchema>;

/** Zod schema for accommodations table Row. */
export const accommodationsRowSchema = z.object({
  amenities: z.string().nullable(),
  created_at: z.string(),
  description: z.string().nullable(),
  embedding: z.array(z.number()).nullable(),
  id: z.string(),
  name: z.string().nullable(),
  source: accommodationSourceSchema,
  updated_at: z.string(),
});
/** TypeScript type for accommodations Row. */
export type AccommodationsRow = z.infer<typeof accommodationsRowSchema>;

/** Zod schema for accommodations table Insert. */
export const accommodationsInsertSchema = z.object({
  amenities: z.string().nullable().optional(),
  created_at: z.string().optional(),
  description: z.string().nullable().optional(),
  embedding: z.array(z.number()).nullable().optional(),
  id: z.string(),
  name: z.string().nullable().optional(),
  source: accommodationSourceSchema,
  updated_at: z.string().optional(),
});
/** TypeScript type for accommodations Insert. */
export type AccommodationsInsert = z.infer<typeof accommodationsInsertSchema>;

/** Zod schema for accommodations table Update. */
export const accommodationsUpdateSchema = z.object({
  amenities: z.string().nullable().optional(),
  created_at: z.string().optional(),
  description: z.string().nullable().optional(),
  embedding: z.array(z.number()).nullable().optional(),
  id: z.string().optional(),
  name: z.string().nullable().optional(),
  source: accommodationSourceSchema.optional(),
  updated_at: z.string().optional(),
});
/** TypeScript type for accommodations Update. */
export type AccommodationsUpdate = z.infer<typeof accommodationsUpdateSchema>;

/** Schema registry for all Supabase tables. */
export const supabaseSchemas = {
  accommodations: {
    insert: accommodationsInsertSchema,
    row: accommodationsRowSchema,
    update: accommodationsUpdateSchema,
  },
  flights: {
    insert: flightsInsertSchema,
    row: flightsRowSchema,
    update: flightsUpdateSchema,
  },
  trips: {
    insert: tripsInsertSchema,
    row: tripsRowSchema,
    update: tripsUpdateSchema,
  },
  user_settings: {
    insert: userSettingsInsertSchema,
    row: userSettingsRowSchema,
    update: userSettingsUpdateSchema,
  },
} as const;

/** Helper to get schema for a table name. */
export function getSupabaseSchema<T extends keyof typeof supabaseSchemas>(
  table: T
): (typeof supabaseSchemas)[T] | undefined {
  return supabaseSchemas[table];
}
