/**
 * @fileoverview Supabase database table schemas. Generated from database.types.ts for runtime validation of database operations. Includes table row, insert, and update schemas for all Supabase tables.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core business logic schemas for Supabase database tables

/** Zod schema for JSON values (matches Supabase Json type). */
export const jsonSchema: z.ZodType<Json> = z.union([
  z.string(),
  z.number(),
  z.boolean(),
  z.null(),
  z.looseRecord(z.string(), z.unknown()),
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

/**
 * Zod schema for trip status enum.
 * Defines possible states for trip entities.
 */
export const tripStatusSchema = z.enum([
  "planning",
  "booked",
  "completed",
  "cancelled",
]);

/** TypeScript type for trip status. */
export type TripStatus = z.infer<typeof tripStatusSchema>;

/**
 * Zod schema for trip type enum.
 * Defines categories for trip entities.
 */
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
 * Note: All user_id fields use z.uuid() because Supabase Auth generates UUIDs
 * for all user accounts. This is guaranteed by Supabase's authentication system.
 */
export const userSettingsRowSchema = z.object({
  allow_gateway_fallback: z.boolean(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for user_settings Row. */
export type UserSettingsRow = z.infer<typeof userSettingsRowSchema>;

/**
 * Zod schema for user_settings table Insert.
 * Validates insert parameters for user_settings table.
 */
export const userSettingsInsertSchema = z.object({
  allow_gateway_fallback: z.boolean().optional(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for user_settings Insert. */
export type UserSettingsInsert = z.infer<typeof userSettingsInsertSchema>;

/**
 * Zod schema for user_settings table Update.
 * Validates update parameters for user_settings table.
 */
export const userSettingsUpdateSchema = z.object({
  allow_gateway_fallback: z.boolean().optional(),
  user_id: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for user_settings Update. */
export type UserSettingsUpdate = z.infer<typeof userSettingsUpdateSchema>;

/**
 * Zod schema for trips table Row.
 * Validates complete trip row data from database.
 */
export const tripsRowSchema = z.object({
  budget: z.number(),
  created_at: primitiveSchemas.isoDateTime,
  currency: primitiveSchemas.isoCurrency,
  description: z.string().nullable(),
  destination: z.string(),
  end_date: z.iso.date(),
  flexibility: jsonSchema.nullable(),
  id: z.number().int(),
  name: z.string(),
  search_metadata: jsonSchema.nullable(),
  start_date: z.iso.date(),
  status: tripStatusSchema,
  tags: z.array(z.string()).nullable().optional(),
  travelers: z.number().int(),
  trip_type: tripTypeSchema,
  updated_at: primitiveSchemas.isoDateTime,
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for trips Row. */
export type TripsRow = z.infer<typeof tripsRowSchema>;

/**
 * Zod schema for trips table Insert.
 * Validates insert parameters for trips table.
 */
export const tripsInsertSchema = z.object({
  budget: z.number(),
  created_at: primitiveSchemas.isoDateTime.optional(),
  currency: primitiveSchemas.isoCurrency.default("USD").optional(),
  description: z.string().nullable().optional(),
  destination: z.string(),
  end_date: z.iso.date(),
  flexibility: jsonSchema.nullable().optional(),
  id: z.never().optional(),
  name: z.string(),
  search_metadata: jsonSchema.nullable().optional(),
  start_date: z.iso.date(),
  status: tripStatusSchema.optional(),
  tags: z.array(z.string()).nullable().optional(),
  travelers: z.number().int(),
  trip_type: tripTypeSchema.optional(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for trips Insert. */
export type TripsInsert = z.infer<typeof tripsInsertSchema>;

/**
 * Zod schema for trips table Update.
 * Validates update parameters for trips table.
 */
export const tripsUpdateSchema = z.object({
  budget: z.number().optional(),
  created_at: primitiveSchemas.isoDateTime.optional(),
  currency: primitiveSchemas.isoCurrency.optional(),
  description: z.string().nullable().optional(),
  destination: z.string().optional(),
  end_date: z.iso.date().optional(),
  flexibility: jsonSchema.nullable().optional(),
  id: z.never().optional(),
  name: z.string().optional(),
  search_metadata: jsonSchema.nullable().optional(),
  start_date: z.iso.date().optional(),
  status: tripStatusSchema.optional(),
  tags: z.array(z.string()).nullable().optional(),
  travelers: z.number().int().optional(),
  trip_type: tripTypeSchema.optional(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
  user_id: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for trips Update. */
export type TripsUpdate = z.infer<typeof tripsUpdateSchema>;

/**
 * Zod schema for flight class enum.
 * Defines available flight classes.
 */
export const flightClassSchema = z.enum([
  "economy",
  "premium_economy",
  "business",
  "first",
]);

/** TypeScript type for flight class. */
export type FlightClass = z.infer<typeof flightClassSchema>;

/**
 * Zod schema for booking status enum.
 * Defines possible states for booking entities.
 */
export const bookingStatusSchema = z.enum([
  "available",
  "reserved",
  "booked",
  "cancelled",
]);

/** TypeScript type for booking status. */
export type BookingStatus = z.infer<typeof bookingStatusSchema>;

/**
 * Zod schema for flights table Row.
 * Validates complete flight row data from database.
 */
export const flightsRowSchema = z.object({
  airline: z.string().nullable(),
  booking_status: bookingStatusSchema,
  created_at: primitiveSchemas.isoDateTime,
  currency: primitiveSchemas.isoCurrency,
  departure_date: primitiveSchemas.isoDateTime,
  destination: z.string(),
  external_id: z.string().nullable(),
  flight_class: flightClassSchema,
  flight_number: z.string().nullable(),
  id: z.number().int(),
  metadata: jsonSchema,
  origin: z.string(),
  price: z.number(),
  return_date: primitiveSchemas.isoDateTime.nullable(),
  trip_id: z.number().int(),
  updated_at: primitiveSchemas.isoDateTime,
});

/** TypeScript type for flights Row. */
export type FlightsRow = z.infer<typeof flightsRowSchema>;

/**
 * Zod schema for flights table Insert.
 * Validates insert parameters for flights table.
 */
export const flightsInsertSchema = z.object({
  airline: z.string().nullable().optional(),
  booking_status: bookingStatusSchema.optional(),
  created_at: primitiveSchemas.isoDateTime.optional(),
  currency: primitiveSchemas.isoCurrency.optional(),
  departure_date: primitiveSchemas.isoDateTime,
  destination: z.string(),
  external_id: z.string().nullable().optional(),
  flight_class: flightClassSchema.optional(),
  flight_number: z.string().nullable().optional(),
  id: z.never().optional(),
  metadata: jsonSchema.optional(),
  origin: z.string(),
  price: z.number(),
  return_date: primitiveSchemas.isoDateTime.nullable().optional(),
  trip_id: z.number().int(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
});

/** TypeScript type for flights Insert. */
export type FlightsInsert = z.infer<typeof flightsInsertSchema>;

/**
 * Zod schema for flights table Update.
 * Validates update parameters for flights table.
 */
export const flightsUpdateSchema = z.object({
  airline: z.string().nullable().optional(),
  booking_status: bookingStatusSchema.optional(),
  created_at: primitiveSchemas.isoDateTime.optional(),
  currency: primitiveSchemas.isoCurrency.optional(),
  departure_date: primitiveSchemas.isoDateTime.optional(),
  destination: z.string().optional(),
  external_id: z.string().nullable().optional(),
  flight_class: flightClassSchema.optional(),
  flight_number: z.string().nullable().optional(),
  id: z.never().optional(),
  metadata: jsonSchema.optional(),
  origin: z.string().optional(),
  price: z.number().optional(),
  return_date: primitiveSchemas.isoDateTime.nullable().optional(),
  trip_id: z.number().int().optional(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
});

/** TypeScript type for flights Update. */
export type FlightsUpdate = z.infer<typeof flightsUpdateSchema>;

/**
 * Zod schema for accommodation source enum.
 * Defines available accommodation sources.
 */
export const accommodationSourceSchema = z.enum(["hotel", "vrbo"]);

/** TypeScript type for accommodation source. */
export type AccommodationSource = z.infer<typeof accommodationSourceSchema>;

/**
 * Zod schema for accommodations table Row.
 * Validates complete accommodation row data from database.
 */
export const accommodationsRowSchema = z.object({
  amenities: z.string().nullable(),
  created_at: primitiveSchemas.isoDateTime,
  description: z.string().nullable(),
  embedding: z.array(z.number()).nullable(),
  id: z.string(),
  name: z.string().nullable(),
  source: accommodationSourceSchema,
  updated_at: primitiveSchemas.isoDateTime,
});

/** TypeScript type for accommodations Row. */
export type AccommodationsRow = z.infer<typeof accommodationsRowSchema>;

/**
 * Zod schema for accommodations table Insert.
 * Validates insert parameters for accommodations table.
 */
export const accommodationsInsertSchema = z.object({
  amenities: z.string().nullable().optional(),
  created_at: primitiveSchemas.isoDateTime.optional(),
  description: z.string().nullable().optional(),
  embedding: z.array(z.number()).nullable().optional(),
  id: z.string(),
  name: z.string().nullable().optional(),
  source: accommodationSourceSchema,
  updated_at: primitiveSchemas.isoDateTime.optional(),
});

/** TypeScript type for accommodations Insert. */
export type AccommodationsInsert = z.infer<typeof accommodationsInsertSchema>;

/**
 * Zod schema for accommodations table Update.
 * Validates update parameters for accommodations table.
 */
export const accommodationsUpdateSchema = z.object({
  amenities: z.string().nullable().optional(),
  created_at: primitiveSchemas.isoDateTime.optional(),
  description: z.string().nullable().optional(),
  embedding: z.array(z.number()).nullable().optional(),
  id: z.string().optional(),
  name: z.string().nullable().optional(),
  source: accommodationSourceSchema.optional(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
});

/** TypeScript type for accommodations Update. */
export type AccommodationsUpdate = z.infer<typeof accommodationsUpdateSchema>;

/**
 * Zod schema for HTTP method enum.
 * Defines allowed HTTP methods for API metrics.
 */
export const httpMethodSchema = z.enum([
  "GET",
  "POST",
  "PUT",
  "PATCH",
  "DELETE",
  "OPTIONS",
  "HEAD",
]);

/** TypeScript type for HTTP method. */
export type HttpMethod = z.infer<typeof httpMethodSchema>;

/**
 * Zod schema for api_metrics table Row.
 * Validates complete api_metrics row data from database.
 */
export const apiMetricsRowSchema = z.object({
  created_at: primitiveSchemas.isoDateTime,
  duration_ms: z.number().nonnegative(),
  endpoint: z.string().min(1),
  error_type: z.string().nullable(),
  id: primitiveSchemas.uuid,
  method: httpMethodSchema,
  rate_limit_key: z.string().nullable(),
  status_code: z.number().int().min(100).max(599),
  user_id: primitiveSchemas.uuid.nullable(),
});

/** TypeScript type for api_metrics Row. */
export type ApiMetricsRow = z.infer<typeof apiMetricsRowSchema>;

/**
 * Zod schema for api_metrics table Insert.
 * Validates insert parameters for api_metrics table.
 */
export const apiMetricsInsertSchema = z.object({
  created_at: primitiveSchemas.isoDateTime.optional(),
  duration_ms: z.number().nonnegative(),
  endpoint: z.string().min(1),
  error_type: z.string().nullable().optional(),
  id: primitiveSchemas.uuid.optional(),
  method: httpMethodSchema,
  rate_limit_key: z.string().nullable().optional(),
  status_code: z.number().int().min(100).max(599),
  user_id: primitiveSchemas.uuid.nullable().optional(),
});

/** TypeScript type for api_metrics Insert. */
export type ApiMetricsInsert = z.infer<typeof apiMetricsInsertSchema>;

/**
 * Zod schema for api_metrics table Update.
 * Validates update parameters for api_metrics table.
 */
export const apiMetricsUpdateSchema = z.object({
  created_at: primitiveSchemas.isoDateTime.optional(),
  duration_ms: z.number().nonnegative().optional(),
  endpoint: z.string().min(1).optional(),
  error_type: z.string().nullable().optional(),
  id: primitiveSchemas.uuid.optional(),
  method: httpMethodSchema.optional(),
  rate_limit_key: z.string().nullable().optional(),
  status_code: z.number().int().min(100).max(599).optional(),
  user_id: primitiveSchemas.uuid.nullable().optional(),
});

/** TypeScript type for api_metrics Update. */
export type ApiMetricsUpdate = z.infer<typeof apiMetricsUpdateSchema>;

/**
 * Zod schema for agent_config table Row.
 * Stores active configuration snapshots for each agent type/scope.
 */
export const agentConfigRowSchema = z.object({
  agent_type: z.string(),
  config: jsonSchema,
  created_at: primitiveSchemas.isoDateTime,
  id: z.string(),
  scope: z.string(),
  updated_at: primitiveSchemas.isoDateTime,
  version_id: z.string(),
});

/** TypeScript type for agent_config Row. */
export type AgentConfigRow = z.infer<typeof agentConfigRowSchema>;

/**
 * Zod schema for agent_config table Insert.
 */
export const agentConfigInsertSchema = z.object({
  agent_type: z.string(),
  config: jsonSchema,
  created_at: primitiveSchemas.isoDateTime.optional(),
  id: z.string().optional(),
  scope: z.string().optional(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
  version_id: z.string(),
});

/** TypeScript type for agent_config Insert. */
export type AgentConfigInsert = z.infer<typeof agentConfigInsertSchema>;

/**
 * Zod schema for agent_config table Update.
 */
export const agentConfigUpdateSchema = z.object({
  agent_type: z.string().optional(),
  config: jsonSchema.optional(),
  created_at: primitiveSchemas.isoDateTime.optional(),
  id: z.string().optional(),
  scope: z.string().optional(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
  version_id: z.string().optional(),
});

/** TypeScript type for agent_config Update. */
export type AgentConfigUpdate = z.infer<typeof agentConfigUpdateSchema>;

/**
 * Zod schema for agent_config_versions table Row.
 */
export const agentConfigVersionsRowSchema = z.object({
  agent_type: z.string(),
  config: jsonSchema,
  created_at: primitiveSchemas.isoDateTime,
  created_by: primitiveSchemas.uuid.nullable(),
  id: z.string(),
  scope: z.string(),
  summary: z.string().nullable(),
});

/** TypeScript type for agent_config_versions Row. */
export type AgentConfigVersionsRow = z.infer<typeof agentConfigVersionsRowSchema>;

/**
 * Zod schema for agent_config_versions table Insert.
 */
export const agentConfigVersionsInsertSchema = z.object({
  agent_type: z.string(),
  config: jsonSchema,
  created_at: primitiveSchemas.isoDateTime.optional(),
  created_by: primitiveSchemas.uuid.nullable().optional(),
  id: z.string().optional(),
  scope: z.string().optional(),
  summary: z.string().nullable().optional(),
});

/** TypeScript type for agent_config_versions Insert. */
export type AgentConfigVersionsInsert = z.infer<typeof agentConfigVersionsInsertSchema>;

/**
 * Zod schema for agent_config_versions table Update.
 */
export const agentConfigVersionsUpdateSchema = z.object({
  agent_type: z.string().optional(),
  config: jsonSchema.optional(),
  created_at: primitiveSchemas.isoDateTime.optional(),
  created_by: primitiveSchemas.uuid.nullable().optional(),
  id: z.string().optional(),
  scope: z.string().optional(),
  summary: z.string().nullable().optional(),
});

/** TypeScript type for agent_config_versions Update. */
export type AgentConfigVersionsUpdate = z.infer<typeof agentConfigVersionsUpdateSchema>;

/**
 * Zod schema for chat_sessions table Row.
 */
export const chatSessionsRowSchema = z.object({
  created_at: primitiveSchemas.isoDateTime.nullable(),
  id: primitiveSchemas.uuid,
  metadata: jsonSchema.nullable(),
  trip_id: z.number().int().nullable(),
  updated_at: primitiveSchemas.isoDateTime.nullable(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for chat_sessions Row. */
export type ChatSessionsRow = z.infer<typeof chatSessionsRowSchema>;

/**
 * Zod schema for chat_sessions table Insert.
 */
export const chatSessionsInsertSchema = z.object({
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  id: primitiveSchemas.uuid.optional(),
  metadata: jsonSchema.nullable().optional(),
  trip_id: z.number().int().nullable().optional(),
  updated_at: primitiveSchemas.isoDateTime.nullable().optional(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for chat_sessions Insert. */
export type ChatSessionsInsert = z.infer<typeof chatSessionsInsertSchema>;

/**
 * Zod schema for chat_sessions table Update.
 */
export const chatSessionsUpdateSchema = z.object({
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  id: primitiveSchemas.uuid.optional(),
  metadata: jsonSchema.nullable().optional(),
  trip_id: z.number().int().nullable().optional(),
  updated_at: primitiveSchemas.isoDateTime.nullable().optional(),
  user_id: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for chat_sessions Update. */
export type ChatSessionsUpdate = z.infer<typeof chatSessionsUpdateSchema>;

/**
 * Zod schema for chat_messages table Row.
 */
const chatMessageRoleSchema = z.enum(["user", "assistant", "system", "tool"]);

export const chatMessagesRowSchema = z.object({
  content: z.string(),
  created_at: primitiveSchemas.isoDateTime.nullable(),
  id: z.number().int(),
  metadata: jsonSchema.nullable(),
  role: chatMessageRoleSchema,
  session_id: primitiveSchemas.uuid,
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for chat_messages Row. */
export type ChatMessagesRow = z.infer<typeof chatMessagesRowSchema>;

/**
 * Zod schema for chat_messages table Insert.
 */
export const chatMessagesInsertSchema = z.object({
  content: z.string(),
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  id: z.never().optional(),
  metadata: jsonSchema.nullable().optional(),
  role: chatMessageRoleSchema,
  session_id: primitiveSchemas.uuid,
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for chat_messages Insert. */
export type ChatMessagesInsert = z.infer<typeof chatMessagesInsertSchema>;

/**
 * Zod schema for chat_messages table Update.
 */
export const chatMessagesUpdateSchema = z.object({
  content: z.string().optional(),
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  id: z.never().optional(),
  metadata: jsonSchema.nullable().optional(),
  role: chatMessageRoleSchema.optional(),
  session_id: primitiveSchemas.uuid.optional(),
  user_id: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for chat_messages Update. */
export type ChatMessagesUpdate = z.infer<typeof chatMessagesUpdateSchema>;

/**
 * Zod schema for chat_tool_calls table Row.
 */
export const chatToolCallsRowSchema = z.object({
  arguments: jsonSchema,
  completed_at: primitiveSchemas.isoDateTime.nullable(),
  created_at: primitiveSchemas.isoDateTime.nullable(),
  error_message: z.string().nullable(),
  id: z.number().int(),
  message_id: z.number().int(),
  result: jsonSchema.nullable(),
  status: z.string(),
  tool_id: z.string(),
  tool_name: z.string(),
});

/** TypeScript type for chat_tool_calls Row. */
export type ChatToolCallsRow = z.infer<typeof chatToolCallsRowSchema>;

/**
 * Zod schema for chat_tool_calls table Insert.
 */
export const chatToolCallsInsertSchema = z.object({
  arguments: jsonSchema.optional(),
  completed_at: primitiveSchemas.isoDateTime.nullable().optional(),
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  error_message: z.string().nullable().optional(),
  id: z.never().optional(),
  message_id: z.number().int(),
  result: jsonSchema.nullable().optional(),
  status: z.string().optional(),
  tool_id: z.string(),
  tool_name: z.string(),
});

/** TypeScript type for chat_tool_calls Insert. */
export type ChatToolCallsInsert = z.infer<typeof chatToolCallsInsertSchema>;

/**
 * Zod schema for chat_tool_calls table Update.
 */
export const chatToolCallsUpdateSchema = z.object({
  arguments: jsonSchema.optional(),
  completed_at: primitiveSchemas.isoDateTime.nullable().optional(),
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  error_message: z.string().nullable().optional(),
  id: z.never().optional(),
  message_id: z.number().int().optional(),
  result: jsonSchema.nullable().optional(),
  status: z.string().optional(),
  tool_id: z.string().optional(),
  tool_name: z.string().optional(),
});

/** TypeScript type for chat_tool_calls Update. */
export type ChatToolCallsUpdate = z.infer<typeof chatToolCallsUpdateSchema>;

/**
 * Zod schema for file_attachments table Row.
 */
export const fileAttachmentsRowSchema = z.object({
  bucket_name: z.string(),
  chat_id: primitiveSchemas.uuid.nullable(),
  chat_message_id: z.number().int().nullable(),
  created_at: primitiveSchemas.isoDateTime.nullable(),
  file_path: z.string(),
  file_size: z.number().int(),
  filename: z.string(),
  id: primitiveSchemas.uuid,
  metadata: jsonSchema,
  mime_type: z.string(),
  original_filename: z.string(),
  trip_id: z.number().int().nullable(),
  updated_at: primitiveSchemas.isoDateTime.nullable(),
  upload_status: z.string(),
  user_id: primitiveSchemas.uuid,
  virus_scan_result: jsonSchema,
  virus_scan_status: z.string(),
});

/** TypeScript type for file_attachments Row. */
export type FileAttachmentsRow = z.infer<typeof fileAttachmentsRowSchema>;

/**
 * Zod schema for file_attachments table Insert.
 */
export const fileAttachmentsInsertSchema = z.object({
  bucket_name: z.string().optional(),
  chat_id: primitiveSchemas.uuid.nullable().optional(),
  chat_message_id: z.number().int().nullable().optional(),
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  file_path: z.string(),
  file_size: z.number().int(),
  filename: z.string(),
  id: primitiveSchemas.uuid.optional(),
  metadata: jsonSchema.optional(),
  mime_type: z.string(),
  original_filename: z.string(),
  trip_id: z.number().int().nullable().optional(),
  updated_at: primitiveSchemas.isoDateTime.nullable().optional(),
  upload_status: z.string().optional(),
  user_id: primitiveSchemas.uuid,
  virus_scan_result: jsonSchema.optional(),
  virus_scan_status: z.string().optional(),
});

/** TypeScript type for file_attachments Insert. */
export type FileAttachmentsInsert = z.infer<typeof fileAttachmentsInsertSchema>;

/**
 * Zod schema for file_attachments table Update.
 */
export const fileAttachmentsUpdateSchema = z.object({
  bucket_name: z.string().optional(),
  chat_id: primitiveSchemas.uuid.nullable().optional(),
  chat_message_id: z.number().int().nullable().optional(),
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  file_path: z.string().optional(),
  file_size: z.number().int().optional(),
  filename: z.string().optional(),
  id: primitiveSchemas.uuid.optional(),
  metadata: jsonSchema.optional(),
  mime_type: z.string().optional(),
  original_filename: z.string().optional(),
  trip_id: z.number().int().nullable().optional(),
  updated_at: primitiveSchemas.isoDateTime.nullable().optional(),
  upload_status: z.string().optional(),
  user_id: primitiveSchemas.uuid.optional(),
  virus_scan_result: jsonSchema.optional(),
  virus_scan_status: z.string().optional(),
});

/** TypeScript type for file_attachments Update. */
export type FileAttachmentsUpdate = z.infer<typeof fileAttachmentsUpdateSchema>;

/**
 * Zod schema for itinerary_items table Row.
 */
export const itineraryItemsRowSchema = z.object({
  booking_status: z.string().nullable(),
  created_at: primitiveSchemas.isoDateTime.nullable(),
  currency: primitiveSchemas.isoCurrency.nullable(),
  description: z.string().nullable(),
  end_time: primitiveSchemas.isoDateTime.nullable(),
  external_id: z.string().nullable(),
  id: z.number().int(),
  item_type: z.string(),
  location: z.string().nullable(),
  metadata: jsonSchema.nullable(),
  price: z.number().nullable(),
  start_time: primitiveSchemas.isoDateTime.nullable(),
  title: z.string(),
  trip_id: z.number().int(),
  updated_at: primitiveSchemas.isoDateTime.nullable(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for itinerary_items Row. */
export type ItineraryItemsRow = z.infer<typeof itineraryItemsRowSchema>;

/**
 * Zod schema for itinerary_items table Insert.
 */
export const itineraryItemsInsertSchema = z.object({
  booking_status: z.string().nullable().optional(),
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  currency: primitiveSchemas.isoCurrency.nullable().optional(),
  description: z.string().nullable().optional(),
  end_time: primitiveSchemas.isoDateTime.nullable().optional(),
  external_id: z.string().nullable().optional(),
  id: z.never().optional(),
  item_type: z.string(),
  location: z.string().nullable().optional(),
  metadata: jsonSchema.nullable().optional(),
  price: z.number().nullable().optional(),
  start_time: primitiveSchemas.isoDateTime.nullable().optional(),
  title: z.string(),
  trip_id: z.number().int(),
  updated_at: primitiveSchemas.isoDateTime.nullable().optional(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for itinerary_items Insert. */
export type ItineraryItemsInsert = z.infer<typeof itineraryItemsInsertSchema>;

/**
 * Zod schema for itinerary_items table Update.
 */
export const itineraryItemsUpdateSchema = z.object({
  booking_status: z.string().nullable().optional(),
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  currency: primitiveSchemas.isoCurrency.nullable().optional(),
  description: z.string().nullable().optional(),
  end_time: primitiveSchemas.isoDateTime.nullable().optional(),
  external_id: z.string().nullable().optional(),
  id: z.never().optional(),
  item_type: z.string().optional(),
  location: z.string().nullable().optional(),
  metadata: jsonSchema.nullable().optional(),
  price: z.number().nullable().optional(),
  start_time: primitiveSchemas.isoDateTime.nullable().optional(),
  title: z.string().optional(),
  trip_id: z.number().int().optional(),
  updated_at: primitiveSchemas.isoDateTime.nullable().optional(),
  user_id: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for itinerary_items Update. */
export type ItineraryItemsUpdate = z.infer<typeof itineraryItemsUpdateSchema>;

/**
 * Zod schema for rag_documents table Row.
 */
export const ragDocumentsRowSchema = z.object({
  chat_id: primitiveSchemas.uuid.nullable(),
  chunk_index: z.number().int(),
  content: z.string(),
  created_at: primitiveSchemas.isoDateTime,
  embedding: z.string().nullable(),
  // PostgreSQL tsvector - opaque at application layer.
  fts: z.unknown(),
  id: z.string(),
  metadata: jsonSchema.nullable(),
  namespace: z.string(),
  source_id: z.string().nullable(),
  trip_id: z.number().int().nullable(),
  updated_at: primitiveSchemas.isoDateTime,
  user_id: primitiveSchemas.uuid.nullable(),
});

/** TypeScript type for rag_documents Row. */
export type RagDocumentsRow = z.infer<typeof ragDocumentsRowSchema>;

/**
 * Zod schema for rag_documents table Insert.
 */
export const ragDocumentsInsertSchema = z.object({
  chat_id: primitiveSchemas.uuid.nullable().optional(),
  chunk_index: z.number().int().optional(),
  content: z.string(),
  created_at: primitiveSchemas.isoDateTime.optional(),
  embedding: z.string().nullable().optional(),
  fts: z.unknown().optional(),
  id: z.string().optional(),
  metadata: jsonSchema.nullable().optional(),
  namespace: z.string().optional(),
  source_id: z.string().nullable().optional(),
  trip_id: z.number().int().nullable().optional(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
  user_id: primitiveSchemas.uuid.nullable().optional(),
});

/** TypeScript type for rag_documents Insert. */
export type RagDocumentsInsert = z.infer<typeof ragDocumentsInsertSchema>;

/**
 * Zod schema for rag_documents table Update.
 */
export const ragDocumentsUpdateSchema = z.object({
  chat_id: primitiveSchemas.uuid.nullable().optional(),
  chunk_index: z.number().int().optional(),
  content: z.string().optional(),
  created_at: primitiveSchemas.isoDateTime.optional(),
  embedding: z.string().nullable().optional(),
  fts: z.unknown().optional(),
  id: z.string().optional(),
  metadata: jsonSchema.nullable().optional(),
  namespace: z.string().optional(),
  source_id: z.string().nullable().optional(),
  trip_id: z.number().int().nullable().optional(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
  user_id: primitiveSchemas.uuid.nullable().optional(),
});

/** TypeScript type for rag_documents Update. */
export type RagDocumentsUpdate = z.infer<typeof ragDocumentsUpdateSchema>;

/**
 * Zod schema for saved_places table Row.
 */
export const savedPlacesRowSchema = z.object({
  created_at: primitiveSchemas.isoDateTime,
  id: z.number().int(),
  place_id: z.string(),
  place_snapshot: jsonSchema,
  provider: z.string(),
  trip_id: z.number().int(),
  updated_at: primitiveSchemas.isoDateTime,
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for saved_places Row. */
export type SavedPlacesRow = z.infer<typeof savedPlacesRowSchema>;

/**
 * Zod schema for saved_places table Insert.
 */
export const savedPlacesInsertSchema = z.object({
  created_at: primitiveSchemas.isoDateTime.optional(),
  id: z.never().optional(),
  place_id: z.string(),
  place_snapshot: jsonSchema.optional(),
  provider: z.string().optional(),
  trip_id: z.number().int(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for saved_places Insert. */
export type SavedPlacesInsert = z.infer<typeof savedPlacesInsertSchema>;

/**
 * Zod schema for saved_places table Update.
 */
export const savedPlacesUpdateSchema = z.object({
  created_at: primitiveSchemas.isoDateTime.optional(),
  id: z.never().optional(),
  place_id: z.string().optional(),
  place_snapshot: jsonSchema.optional(),
  provider: z.string().optional(),
  trip_id: z.number().int().optional(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
  user_id: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for saved_places Update. */
export type SavedPlacesUpdate = z.infer<typeof savedPlacesUpdateSchema>;

/**
 * Zod schema for trip_collaborators table Row.
 */
export const tripCollaboratorsRowSchema = z.object({
  created_at: primitiveSchemas.isoDateTime.nullable(),
  id: z.number().int(),
  role: z.string(),
  trip_id: z.number().int(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for trip_collaborators Row. */
export type TripCollaboratorsRow = z.infer<typeof tripCollaboratorsRowSchema>;

/**
 * Zod schema for trip_collaborators table Insert.
 */
export const tripCollaboratorsInsertSchema = z.object({
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  id: z.never().optional(),
  role: z.string().optional(),
  trip_id: z.number().int(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for trip_collaborators Insert. */
export type TripCollaboratorsInsert = z.infer<typeof tripCollaboratorsInsertSchema>;

/**
 * Zod schema for trip_collaborators table Update.
 */
export const tripCollaboratorsUpdateSchema = z.object({
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  id: z.never().optional(),
  role: z.string().optional(),
  trip_id: z.number().int().optional(),
  user_id: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for trip_collaborators Update. */
export type TripCollaboratorsUpdate = z.infer<typeof tripCollaboratorsUpdateSchema>;

/**
 * Zod schema for mfa_enrollments table Row.
 */
export const mfaEnrollmentsRowSchema = z.object({
  challenge_id: z.string(),
  consumed_at: primitiveSchemas.isoDateTime.nullable(),
  expires_at: primitiveSchemas.isoDateTime,
  factor_id: z.string(),
  id: primitiveSchemas.uuid,
  issued_at: primitiveSchemas.isoDateTime,
  status: z.string(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for mfa_enrollments Row. */
export type MfaEnrollmentsRow = z.infer<typeof mfaEnrollmentsRowSchema>;

/**
 * Zod schema for mfa_enrollments table Insert.
 */
export const mfaEnrollmentsInsertSchema = z.object({
  challenge_id: z.string(),
  consumed_at: primitiveSchemas.isoDateTime.nullable().optional(),
  expires_at: primitiveSchemas.isoDateTime,
  factor_id: z.string(),
  id: primitiveSchemas.uuid.optional(),
  issued_at: primitiveSchemas.isoDateTime.optional(),
  status: z.string(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for mfa_enrollments Insert. */
export type MfaEnrollmentsInsert = z.infer<typeof mfaEnrollmentsInsertSchema>;

/**
 * Zod schema for mfa_enrollments table Update.
 */
export const mfaEnrollmentsUpdateSchema = z.object({
  challenge_id: z.string().optional(),
  consumed_at: primitiveSchemas.isoDateTime.nullable().optional(),
  expires_at: primitiveSchemas.isoDateTime.optional(),
  factor_id: z.string().optional(),
  id: primitiveSchemas.uuid.optional(),
  issued_at: primitiveSchemas.isoDateTime.optional(),
  status: z.string().optional(),
  user_id: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for mfa_enrollments Update. */
export type MfaEnrollmentsUpdate = z.infer<typeof mfaEnrollmentsUpdateSchema>;

/**
 * Zod schema for auth_backup_codes table Row.
 */
export const authBackupCodesRowSchema = z.object({
  code_hash: z.string(),
  consumed_at: primitiveSchemas.isoDateTime.nullable(),
  id: primitiveSchemas.uuid,
  issued_at: primitiveSchemas.isoDateTime,
  label: z.string().nullable(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for auth_backup_codes Row. */
export type AuthBackupCodesRow = z.infer<typeof authBackupCodesRowSchema>;

/**
 * Zod schema for auth_backup_codes table Insert.
 */
export const authBackupCodesInsertSchema = z.object({
  code_hash: z.string(),
  consumed_at: primitiveSchemas.isoDateTime.nullable().optional(),
  id: primitiveSchemas.uuid.optional(),
  issued_at: primitiveSchemas.isoDateTime.optional(),
  label: z.string().nullable().optional(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for auth_backup_codes Insert. */
export type AuthBackupCodesInsert = z.infer<typeof authBackupCodesInsertSchema>;

/**
 * Zod schema for auth_backup_codes table Update.
 */
export const authBackupCodesUpdateSchema = z.object({
  code_hash: z.string().optional(),
  consumed_at: primitiveSchemas.isoDateTime.nullable().optional(),
  id: primitiveSchemas.uuid.optional(),
  issued_at: primitiveSchemas.isoDateTime.optional(),
  label: z.string().nullable().optional(),
  user_id: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for auth_backup_codes Update. */
export type AuthBackupCodesUpdate = z.infer<typeof authBackupCodesUpdateSchema>;

/**
 * Zod schema for auth.sessions table Row.
 */
export const authSessionsRowSchema = z.object({
  aal: z.string().nullable(),
  created_at: primitiveSchemas.isoDateTime.nullable(),
  factor_id: z.string().nullable(),
  id: primitiveSchemas.uuid,
  // PostgreSQL inet - opaque at application layer.
  ip: z.unknown(),
  not_after: primitiveSchemas.isoDateTime.nullable(),
  oauth_client_id: z.string().nullable(),
  refreshed_at: primitiveSchemas.isoDateTime.nullable(),
  tag: z.string().nullable(),
  updated_at: primitiveSchemas.isoDateTime.nullable(),
  user_agent: z.string().nullable(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for auth.sessions Row. */
export type AuthSessionsRow = z.infer<typeof authSessionsRowSchema>;

/**
 * Zod schema for auth.sessions table Insert.
 */
export const authSessionsInsertSchema = z.object({
  aal: z.string().nullable().optional(),
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  factor_id: z.string().nullable().optional(),
  id: primitiveSchemas.uuid,
  ip: z.unknown().optional(),
  not_after: primitiveSchemas.isoDateTime.nullable().optional(),
  oauth_client_id: z.string().nullable().optional(),
  refreshed_at: primitiveSchemas.isoDateTime.nullable().optional(),
  tag: z.string().nullable().optional(),
  updated_at: primitiveSchemas.isoDateTime.nullable().optional(),
  user_agent: z.string().nullable().optional(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for auth.sessions Insert. */
export type AuthSessionsInsert = z.infer<typeof authSessionsInsertSchema>;

/**
 * Zod schema for auth.sessions table Update.
 */
export const authSessionsUpdateSchema = z.object({
  aal: z.string().nullable().optional(),
  created_at: primitiveSchemas.isoDateTime.nullable().optional(),
  factor_id: z.string().nullable().optional(),
  id: primitiveSchemas.uuid.optional(),
  ip: z.unknown().optional(),
  not_after: primitiveSchemas.isoDateTime.nullable().optional(),
  oauth_client_id: z.string().nullable().optional(),
  refreshed_at: primitiveSchemas.isoDateTime.nullable().optional(),
  tag: z.string().nullable().optional(),
  updated_at: primitiveSchemas.isoDateTime.nullable().optional(),
  user_agent: z.string().nullable().optional(),
  user_id: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for auth.sessions Update. */
export type AuthSessionsUpdate = z.infer<typeof authSessionsUpdateSchema>;

/**
 * Zod schema for memories.sessions table Row.
 */
export const memorySessionsRowSchema = z.object({
  created_at: primitiveSchemas.isoDateTime,
  id: primitiveSchemas.uuid,
  last_synced_at: primitiveSchemas.isoDateTime.nullable(),
  metadata: jsonSchema,
  title: z.string(),
  updated_at: primitiveSchemas.isoDateTime,
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for memories.sessions Row. */
export type MemorySessionsRow = z.infer<typeof memorySessionsRowSchema>;

/**
 * Zod schema for memories.sessions table Insert.
 */
export const memorySessionsInsertSchema = z.object({
  created_at: primitiveSchemas.isoDateTime.optional(),
  id: primitiveSchemas.uuid.optional(),
  last_synced_at: primitiveSchemas.isoDateTime.nullable().optional(),
  metadata: jsonSchema.optional(),
  title: z.string(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for memories.sessions Insert. */
export type MemorySessionsInsert = z.infer<typeof memorySessionsInsertSchema>;

/**
 * Zod schema for memories.sessions table Update.
 */
export const memorySessionsUpdateSchema = z.object({
  created_at: primitiveSchemas.isoDateTime.optional(),
  id: primitiveSchemas.uuid.optional(),
  last_synced_at: primitiveSchemas.isoDateTime.nullable().optional(),
  metadata: jsonSchema.optional(),
  title: z.string().optional(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
  user_id: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for memories.sessions Update. */
export type MemorySessionsUpdate = z.infer<typeof memorySessionsUpdateSchema>;

/**
 * Zod schema for memories.turns table Row.
 */
export const memoryTurnsRowSchema = z.object({
  attachments: jsonSchema,
  content: jsonSchema,
  created_at: primitiveSchemas.isoDateTime,
  id: primitiveSchemas.uuid,
  pii_scrubbed: z.boolean(),
  role: z.string(),
  session_id: primitiveSchemas.uuid,
  tool_calls: jsonSchema,
  tool_results: jsonSchema,
  updated_at: primitiveSchemas.isoDateTime,
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for memories.turns Row. */
export type MemoryTurnsRow = z.infer<typeof memoryTurnsRowSchema>;

/**
 * Zod schema for memories.turns table Insert.
 */
export const memoryTurnsInsertSchema = z.object({
  attachments: jsonSchema.optional(),
  content: jsonSchema,
  created_at: primitiveSchemas.isoDateTime.optional(),
  id: primitiveSchemas.uuid.optional(),
  pii_scrubbed: z.boolean().optional(),
  role: z.string(),
  session_id: primitiveSchemas.uuid,
  tool_calls: jsonSchema.optional(),
  tool_results: jsonSchema.optional(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for memories.turns Insert. */
export type MemoryTurnsInsert = z.infer<typeof memoryTurnsInsertSchema>;

/**
 * Zod schema for memories.turns table Update.
 */
export const memoryTurnsUpdateSchema = z.object({
  attachments: jsonSchema.optional(),
  content: jsonSchema.optional(),
  created_at: primitiveSchemas.isoDateTime.optional(),
  id: primitiveSchemas.uuid.optional(),
  pii_scrubbed: z.boolean().optional(),
  role: z.string().optional(),
  session_id: primitiveSchemas.uuid.optional(),
  tool_calls: jsonSchema.optional(),
  tool_results: jsonSchema.optional(),
  updated_at: primitiveSchemas.isoDateTime.optional(),
  user_id: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for memories.turns Update. */
export type MemoryTurnsUpdate = z.infer<typeof memoryTurnsUpdateSchema>;

// ===== UTILITY FUNCTIONS =====
// Schema registry and helper functions

/**
 * Schema registry for all Supabase tables.
 * Provides centralized access to table schemas for row, insert, and update operations.
 */
export const supabaseSchemas = {
  accommodations: {
    insert: accommodationsInsertSchema,
    row: accommodationsRowSchema,
    update: accommodationsUpdateSchema,
  },
  agent_config: {
    insert: agentConfigInsertSchema,
    row: agentConfigRowSchema,
    update: agentConfigUpdateSchema,
  },
  agent_config_versions: {
    insert: agentConfigVersionsInsertSchema,
    row: agentConfigVersionsRowSchema,
    update: agentConfigVersionsUpdateSchema,
  },
  api_metrics: {
    insert: apiMetricsInsertSchema,
    row: apiMetricsRowSchema,
    update: apiMetricsUpdateSchema,
  },
  auth_backup_codes: {
    insert: authBackupCodesInsertSchema,
    row: authBackupCodesRowSchema,
    update: authBackupCodesUpdateSchema,
  },
  chat_messages: {
    insert: chatMessagesInsertSchema,
    row: chatMessagesRowSchema,
    update: chatMessagesUpdateSchema,
  },
  chat_sessions: {
    insert: chatSessionsInsertSchema,
    row: chatSessionsRowSchema,
    update: chatSessionsUpdateSchema,
  },
  chat_tool_calls: {
    insert: chatToolCallsInsertSchema,
    row: chatToolCallsRowSchema,
    update: chatToolCallsUpdateSchema,
  },
  file_attachments: {
    insert: fileAttachmentsInsertSchema,
    row: fileAttachmentsRowSchema,
    update: fileAttachmentsUpdateSchema,
  },
  flights: {
    insert: flightsInsertSchema,
    row: flightsRowSchema,
    update: flightsUpdateSchema,
  },
  itinerary_items: {
    insert: itineraryItemsInsertSchema,
    row: itineraryItemsRowSchema,
    update: itineraryItemsUpdateSchema,
  },
  mfa_enrollments: {
    insert: mfaEnrollmentsInsertSchema,
    row: mfaEnrollmentsRowSchema,
    update: mfaEnrollmentsUpdateSchema,
  },
  rag_documents: {
    insert: ragDocumentsInsertSchema,
    row: ragDocumentsRowSchema,
    update: ragDocumentsUpdateSchema,
  },
  saved_places: {
    insert: savedPlacesInsertSchema,
    row: savedPlacesRowSchema,
    update: savedPlacesUpdateSchema,
  },
  trip_collaborators: {
    insert: tripCollaboratorsInsertSchema,
    row: tripCollaboratorsRowSchema,
    update: tripCollaboratorsUpdateSchema,
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

const authSupabaseSchemas = {
  sessions: {
    insert: authSessionsInsertSchema,
    row: authSessionsRowSchema,
    update: authSessionsUpdateSchema,
  },
} as const;

const memoriesSupabaseSchemas = {
  sessions: {
    insert: memorySessionsInsertSchema,
    row: memorySessionsRowSchema,
    update: memorySessionsUpdateSchema,
  },
  turns: {
    insert: memoryTurnsInsertSchema,
    row: memoryTurnsRowSchema,
    update: memoryTurnsUpdateSchema,
  },
} as const;

const supabaseSchemaRegistry = {
  auth: authSupabaseSchemas,
  memories: memoriesSupabaseSchemas,
  public: supabaseSchemas,
} as const;

type SupabaseSchemaRegistry = typeof supabaseSchemaRegistry;
/** Union type of all valid Supabase schema names in the registry. */
export type SupabaseSchemaName = keyof SupabaseSchemaRegistry;

/**
 * Helper to get schema for a table name.
 * Retrieves table schemas from the registry for validation operations.
 *
 * @param table - Table name to get schemas for
 * @param options - Optional schema selection (defaults to public)
 * @returns Table schemas (row, insert, update) or undefined if not found
 */
export function getSupabaseSchema<
  S extends SupabaseSchemaName = "public",
  T extends keyof SupabaseSchemaRegistry[S] = keyof SupabaseSchemaRegistry[S],
>(table: T, options?: { schema?: S }): SupabaseSchemaRegistry[S][T] | undefined {
  const schemaName = options?.schema ?? "public";
  const schemaTables = supabaseSchemaRegistry[schemaName];
  if (!schemaTables) return undefined;
  if (!Object.hasOwn(schemaTables, table)) return undefined;
  return schemaTables[table as keyof typeof schemaTables] as
    | SupabaseSchemaRegistry[S][T]
    | undefined;
}
