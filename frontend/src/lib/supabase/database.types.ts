/**
 * @fileoverview Complete TypeScript definitions for all Supabase database tables
 * Generated from database schema for type-safe database operations
 */

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

type SupabaseRelationship = {
  foreignKeyName: string;
  columns: string[];
  referencedRelation: string;
  referencedColumns: string[];
  isOneToOne?: boolean;
};

type SupabaseTableShape = {
  Row: unknown;
  Insert: unknown;
  Update: unknown;
  Relationships?: SupabaseRelationship[];
};

type SupabaseTables<T extends Record<string, SupabaseTableShape>> = {
  [K in keyof T]: Omit<T[K], "Relationships"> & {
    Relationships: T[K] extends { Relationships: infer R }
      ? R extends SupabaseRelationship[]
        ? R
        : SupabaseRelationship[]
      : SupabaseRelationship[];
  };
};

export type Database = {
  public: {
    Tables: SupabaseTables<{
      user_settings: {
        Row: {
          user_id: string;
          allow_gateway_fallback: boolean;
        };
        Insert: {
          user_id: string;
          allow_gateway_fallback?: boolean;
        };
        Update: {
          user_id?: string;
          allow_gateway_fallback?: boolean;
        };
      };
      // Core Trip Management
      trips: {
        Row: {
          id: number;
          user_id: string;
          name: string;
          start_date: string;
          end_date: string;
          destination: string;
          budget: number;
          travelers: number;
          status: "planning" | "booked" | "completed" | "cancelled";
          trip_type: "leisure" | "business" | "family" | "solo" | "other";
          flexibility: Json;
          notes: string[] | null;
          search_metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: never;
          user_id: string;
          name: string;
          start_date: string;
          end_date: string;
          destination: string;
          budget: number;
          travelers: number;
          status?: "planning" | "booked" | "completed" | "cancelled";
          trip_type?: "leisure" | "business" | "family" | "solo" | "other";
          flexibility?: Json;
          notes?: string[] | null;
          search_metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: never;
          user_id?: string;
          name?: string;
          start_date?: string;
          end_date?: string;
          destination?: string;
          budget?: number;
          travelers?: number;
          status?: "planning" | "booked" | "completed" | "cancelled";
          trip_type?: "leisure" | "business" | "family" | "solo" | "other";
          flexibility?: Json;
          notes?: string[] | null;
          search_metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
      };

      // Travel Options
      flights: {
        Row: {
          id: number;
          trip_id: number;
          origin: string;
          destination: string;
          departure_date: string;
          return_date: string | null;
          flight_class: "economy" | "premium_economy" | "business" | "first";
          price: number;
          currency: string;
          airline: string | null;
          flight_number: string | null;
          booking_status: "available" | "reserved" | "booked" | "cancelled";
          external_id: string | null;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: never;
          trip_id: number;
          origin: string;
          destination: string;
          departure_date: string;
          return_date?: string | null;
          flight_class?: "economy" | "premium_economy" | "business" | "first";
          price: number;
          currency?: string;
          airline?: string | null;
          flight_number?: string | null;
          booking_status?: "available" | "reserved" | "booked" | "cancelled";
          external_id?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: never;
          trip_id?: number;
          origin?: string;
          destination?: string;
          departure_date?: string;
          return_date?: string | null;
          flight_class?: "economy" | "premium_economy" | "business" | "first";
          price?: number;
          currency?: string;
          airline?: string | null;
          flight_number?: string | null;
          booking_status?: "available" | "reserved" | "booked" | "cancelled";
          external_id?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
      };

      accommodation_embeddings: {
        Row: {
          amenities: string | null;
          created_at: string | null;
          description: string | null;
          embedding: number[] | null;
          id: string;
          name: string | null;
          source: "hotel" | "vrbo";
          updated_at: string | null;
        };
        Insert: {
          amenities?: string | null;
          created_at?: string | null;
          description?: string | null;
          embedding?: number[] | null;
          id: string;
          name?: string | null;
          source: "hotel" | "vrbo";
          updated_at?: string | null;
        };
        Update: {
          amenities?: string | null;
          created_at?: string | null;
          description?: string | null;
          embedding?: number[] | null;
          id?: string;
          name?: string | null;
          source?: "hotel" | "vrbo";
          updated_at?: string | null;
        };
      };

      accommodations: {
        Row: {
          id: string;
          amenities: string | null;
          created_at: string;
          description: string | null;
          embedding: number[] | null;
          name: string | null;
          source: "hotel" | "vrbo";
          updated_at: string;
        };
        Insert: {
          id: string;
          amenities?: string | null;
          created_at?: string;
          description?: string | null;
          embedding?: number[] | null;
          name?: string | null;
          source: "hotel" | "vrbo";
          updated_at?: string;
        };
        Update: {
          id?: string;
          amenities?: string | null;
          created_at?: string;
          description?: string | null;
          embedding?: number[] | null;
          name?: string | null;
          source?: "hotel" | "vrbo";
          updated_at?: string;
        };
      };

      transportation: {
        Row: {
          id: number;
          trip_id: number;
          transport_type: "flight" | "train" | "bus" | "car_rental" | "taxi" | "other";
          origin: string;
          destination: string;
          departure_time: string | null;
          arrival_time: string | null;
          price: number;
          currency: string;
          booking_status: "available" | "reserved" | "booked" | "cancelled";
          external_id: string | null;
          metadata: Json;
          created_at: string;
        };
        Insert: {
          id?: never;
          trip_id: number;
          transport_type: "flight" | "train" | "bus" | "car_rental" | "taxi" | "other";
          origin: string;
          destination: string;
          departure_time?: string | null;
          arrival_time?: string | null;
          price: number;
          currency?: string;
          booking_status?: "available" | "reserved" | "booked" | "cancelled";
          external_id?: string | null;
          metadata?: Json;
          created_at?: string;
        };
        Update: {
          id?: never;
          trip_id?: number;
          transport_type?: "flight" | "train" | "bus" | "car_rental" | "taxi" | "other";
          origin?: string;
          destination?: string;
          departure_time?: string | null;
          arrival_time?: string | null;
          price?: number;
          currency?: string;
          booking_status?: "available" | "reserved" | "booked" | "cancelled";
          external_id?: string | null;
          metadata?: Json;
          created_at?: string;
        };
      };

      itinerary_items: {
        Row: {
          id: number;
          trip_id: number;
          title: string;
          description: string | null;
          item_type:
            | "activity"
            | "meal"
            | "transport"
            | "accommodation"
            | "event"
            | "other";
          start_time: string | null;
          end_time: string | null;
          location: string | null;
          price: number;
          currency: string;
          booking_status: "planned" | "reserved" | "booked" | "completed" | "cancelled";
          external_id: string | null;
          metadata: Json;
          created_at: string;
        };
        Insert: {
          id?: never;
          trip_id: number;
          title: string;
          description?: string | null;
          item_type:
            | "activity"
            | "meal"
            | "transport"
            | "accommodation"
            | "event"
            | "other";
          start_time?: string | null;
          end_time?: string | null;
          location?: string | null;
          price?: number;
          currency?: string;
          booking_status?:
            | "planned"
            | "reserved"
            | "booked"
            | "completed"
            | "cancelled";
          external_id?: string | null;
          metadata?: Json;
          created_at?: string;
        };
        Update: {
          id?: never;
          trip_id?: number;
          title?: string;
          description?: string | null;
          item_type?:
            | "activity"
            | "meal"
            | "transport"
            | "accommodation"
            | "event"
            | "other";
          start_time?: string | null;
          end_time?: string | null;
          location?: string | null;
          price?: number;
          currency?: string;
          booking_status?:
            | "planned"
            | "reserved"
            | "booked"
            | "completed"
            | "cancelled";
          external_id?: string | null;
          metadata?: Json;
          created_at?: string;
        };
      };

      // Chat System
      chat_sessions: {
        Row: {
          id: string;
          user_id: string;
          trip_id: number | null;
          created_at: string;
          updated_at: string;
          ended_at: string | null;
          metadata: Json;
        };
        Insert: {
          id?: string;
          user_id: string;
          trip_id?: number | null;
          created_at?: string;
          updated_at?: string;
          ended_at?: string | null;
          metadata?: Json;
        };
        Update: {
          id?: string;
          user_id?: string;
          trip_id?: number | null;
          created_at?: string;
          updated_at?: string;
          ended_at?: string | null;
          metadata?: Json;
        };
        Relationships: [
          {
            foreignKeyName: "chat_sessions_trip_id_fkey";
            columns: ["trip_id"];
            referencedRelation: "trips";
            referencedColumns: ["id"];
          },
        ];
      };

      chat_messages: {
        Row: {
          id: number;
          session_id: string;
          role: "user" | "assistant" | "system";
          content: string;
          created_at: string;
          metadata: Json;
        };
        Insert: {
          id?: never;
          session_id: string;
          role: "user" | "assistant" | "system";
          content: string;
          created_at?: string;
          metadata?: Json;
        };
        Update: {
          id?: never;
          session_id?: string;
          role?: "user" | "assistant" | "system";
          content?: string;
          created_at?: string;
          metadata?: Json;
        };
        Relationships: [
          {
            foreignKeyName: "chat_messages_session_id_fkey";
            columns: ["session_id"];
            referencedRelation: "chat_sessions";
            referencedColumns: ["id"];
          },
        ];
      };

      chat_tool_calls: {
        Row: {
          id: number;
          message_id: number;
          tool_id: string;
          tool_name: string;
          arguments: Json;
          result: Json | null;
          status: "pending" | "running" | "completed" | "failed";
          created_at: string;
          completed_at: string | null;
          error_message: string | null;
        };
        Insert: {
          id?: never;
          message_id: number;
          tool_id: string;
          tool_name: string;
          arguments?: Json;
          result?: Json | null;
          status?: "pending" | "running" | "completed" | "failed";
          created_at?: string;
          completed_at?: string | null;
          error_message?: string | null;
        };
        Update: {
          id?: never;
          message_id?: number;
          tool_id?: string;
          tool_name?: string;
          arguments?: Json;
          result?: Json | null;
          status?: "pending" | "running" | "completed" | "failed";
          created_at?: string;
          completed_at?: string | null;
          error_message?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "chat_tool_calls_message_id_fkey";
            columns: ["message_id"];
            referencedRelation: "chat_messages";
            referencedColumns: ["id"];
          },
        ];
      };

      // API Keys (BYOK)
      api_keys: {
        Row: {
          id: number;
          user_id: string;
          service_name: string;
          key_name: string;
          encrypted_key: string;
          key_hash: string;
          is_active: boolean;
          last_used_at: string | null;
          expires_at: string | null;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: never;
          user_id: string;
          service_name: string;
          key_name: string;
          encrypted_key: string;
          key_hash: string;
          is_active?: boolean;
          last_used_at?: string | null;
          expires_at?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: never;
          user_id?: string;
          service_name?: string;
          key_name?: string;
          encrypted_key?: string;
          key_hash?: string;
          is_active?: boolean;
          last_used_at?: string | null;
          expires_at?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
      };

      // Memory System
      memories: {
        Row: {
          id: number;
          user_id: string;
          memory_type:
            | "user_preference"
            | "trip_history"
            | "search_pattern"
            | "conversation_context"
            | "other";
          content: string;
          embedding: string | null;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: never;
          user_id: string;
          memory_type?:
            | "user_preference"
            | "trip_history"
            | "search_pattern"
            | "conversation_context"
            | "other";
          content: string;
          embedding?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: never;
          user_id?: string;
          memory_type?:
            | "user_preference"
            | "trip_history"
            | "search_pattern"
            | "conversation_context"
            | "other";
          content?: string;
          embedding?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
      };

      session_memories: {
        Row: {
          id: number;
          session_id: string;
          user_id: string;
          content: string;
          embedding: string | null;
          metadata: Json;
          created_at: string;
        };
        Insert: {
          id?: never;
          session_id: string;
          user_id: string;
          content: string;
          embedding?: string | null;
          metadata?: Json;
          created_at?: string;
        };
        Update: {
          id?: never;
          session_id?: string;
          user_id?: string;
          content?: string;
          embedding?: string | null;
          metadata?: Json;
          created_at?: string;
        };
      };

      // Trip Collaboration
      trip_collaborators: {
        Row: {
          id: number;
          trip_id: number;
          user_id: string;
          permission_level: "view" | "edit" | "admin";
          added_by: string;
          added_at: string;
          updated_at: string;
        };
        Insert: {
          id?: never;
          trip_id: number;
          user_id: string;
          permission_level?: "view" | "edit" | "admin";
          added_by: string;
          added_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: never;
          trip_id?: number;
          user_id?: string;
          permission_level?: "view" | "edit" | "admin";
          added_by?: string;
          added_at?: string;
          updated_at?: string;
        };
      };

      // File Storage
      file_attachments: {
        Row: {
          id: string;
          user_id: string;
          trip_id: number | null;
          chat_message_id: number | null;
          filename: string;
          original_filename: string;
          file_size: number;
          mime_type: string;
          file_path: string;
          bucket_name: string;
          upload_status: "uploading" | "completed" | "failed";
          virus_scan_status: "pending" | "clean" | "infected" | "failed";
          virus_scan_result: Json;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          trip_id?: number | null;
          chat_message_id?: number | null;
          filename: string;
          original_filename: string;
          file_size: number;
          mime_type: string;
          file_path: string;
          bucket_name?: string;
          upload_status?: "uploading" | "completed" | "failed";
          virus_scan_status?: "pending" | "clean" | "infected" | "failed";
          virus_scan_result?: Json;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          trip_id?: number | null;
          chat_message_id?: number | null;
          filename?: string;
          original_filename?: string;
          file_size?: number;
          mime_type?: string;
          file_path?: string;
          bucket_name?: string;
          upload_status?: "uploading" | "completed" | "failed";
          virus_scan_status?: "pending" | "clean" | "infected" | "failed";
          virus_scan_result?: Json;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
      };

      // Search Cache Tables
      search_destinations: {
        Row: {
          id: number;
          user_id: string;
          query: string;
          query_hash: string;
          results: Json;
          source: "google_maps" | "external_api" | "cached";
          search_metadata: Json;
          expires_at: string;
          created_at: string;
        };
        Insert: {
          id?: never;
          user_id: string;
          query: string;
          query_hash: string;
          results: Json;
          source: "google_maps" | "external_api" | "cached";
          search_metadata?: Json;
          expires_at: string;
          created_at?: string;
        };
        Update: {
          id?: never;
          user_id?: string;
          query?: string;
          query_hash?: string;
          results?: Json;
          source?: "google_maps" | "external_api" | "cached";
          search_metadata?: Json;
          expires_at?: string;
          created_at?: string;
        };
      };

      search_activities: {
        Row: {
          id: number;
          user_id: string;
          destination: string;
          activity_type: string | null;
          query_parameters: Json;
          query_hash: string;
          results: Json;
          source: "viator" | "getyourguide" | "external_api" | "cached";
          search_metadata: Json;
          expires_at: string;
          created_at: string;
        };
        Insert: {
          id?: never;
          user_id: string;
          destination: string;
          activity_type?: string | null;
          query_parameters: Json;
          query_hash: string;
          results: Json;
          source: "viator" | "getyourguide" | "external_api" | "cached";
          search_metadata?: Json;
          expires_at: string;
          created_at?: string;
        };
        Update: {
          id?: never;
          user_id?: string;
          destination?: string;
          activity_type?: string | null;
          query_parameters?: Json;
          query_hash?: string;
          results?: Json;
          source?: "viator" | "getyourguide" | "external_api" | "cached";
          search_metadata?: Json;
          expires_at?: string;
          created_at?: string;
        };
      };

      search_flights: {
        Row: {
          id: number;
          user_id: string;
          origin: string;
          destination: string;
          departure_date: string;
          return_date: string | null;
          passengers: number;
          cabin_class: "economy" | "premium_economy" | "business" | "first";
          query_parameters: Json;
          query_hash: string;
          results: Json;
          source: "duffel" | "amadeus" | "external_api" | "cached";
          search_metadata: Json;
          expires_at: string;
          created_at: string;
        };
        Insert: {
          id?: never;
          user_id: string;
          origin: string;
          destination: string;
          departure_date: string;
          return_date?: string | null;
          passengers?: number;
          cabin_class?: "economy" | "premium_economy" | "business" | "first";
          query_parameters: Json;
          query_hash: string;
          results: Json;
          source: "duffel" | "amadeus" | "external_api" | "cached";
          search_metadata?: Json;
          expires_at: string;
          created_at?: string;
        };
        Update: {
          id?: never;
          user_id?: string;
          origin?: string;
          destination?: string;
          departure_date?: string;
          return_date?: string | null;
          passengers?: number;
          cabin_class?: "economy" | "premium_economy" | "business" | "first";
          query_parameters?: Json;
          query_hash?: string;
          results?: Json;
          source?: "duffel" | "amadeus" | "external_api" | "cached";
          search_metadata?: Json;
          expires_at?: string;
          created_at?: string;
        };
      };

      search_hotels: {
        Row: {
          id: number;
          user_id: string;
          destination: string;
          check_in_date: string;
          check_out_date: string;
          guests: number;
          rooms: number;
          query_parameters: Json;
          query_hash: string;
          results: Json;
          source: "booking" | "expedia" | "airbnb_mcp" | "external_api" | "cached";
          search_metadata: Json;
          expires_at: string;
          created_at: string;
        };
        Insert: {
          id?: never;
          user_id: string;
          destination: string;
          check_in_date: string;
          check_out_date: string;
          guests?: number;
          rooms?: number;
          query_parameters: Json;
          query_hash: string;
          results: Json;
          source: "booking" | "expedia" | "airbnb_mcp" | "external_api" | "cached";
          search_metadata?: Json;
          expires_at: string;
          created_at?: string;
        };
        Update: {
          id?: never;
          user_id?: string;
          destination?: string;
          check_in_date?: string;
          check_out_date?: string;
          guests?: number;
          rooms?: number;
          query_parameters?: Json;
          query_hash?: string;
          results?: Json;
          source?: "booking" | "expedia" | "airbnb_mcp" | "external_api" | "cached";
          search_metadata?: Json;
          expires_at?: string;
          created_at?: string;
        };
      };
    }>;
    Views: {
      [_ in never]: never;
    };
    Functions: {
      [_ in never]: never;
    };
    Enums: {
      trip_status: "planning" | "booked" | "completed" | "cancelled";
      trip_type: "leisure" | "business" | "family" | "solo" | "other";
      flight_class: "economy" | "premium_economy" | "business" | "first";
      booking_status: "available" | "reserved" | "booked" | "cancelled";
      transport_type: "flight" | "train" | "bus" | "car_rental" | "taxi" | "other";
      item_type:
        | "activity"
        | "meal"
        | "transport"
        | "accommodation"
        | "event"
        | "other";
      chat_role: "user" | "assistant" | "system";
      tool_call_status: "pending" | "running" | "completed" | "failed";
      memory_type:
        | "user_preference"
        | "trip_history"
        | "search_pattern"
        | "conversation_context"
        | "other";
      permission_level: "view" | "edit" | "admin";
      upload_status: "uploading" | "completed" | "failed";
      virus_scan_status: "pending" | "clean" | "infected" | "failed";
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
};

// Helper types for better developer experience
export type Tables<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T] extends { Row: infer R } ? R : never;

export type InsertTables<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T] extends { Insert: infer I } ? I : never;

export type UpdateTables<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T] extends { Update: infer U } ? U : never;

export type Enums<T extends keyof Database["public"]["Enums"]> =
  Database["public"]["Enums"][T];

// Specific table types for convenience
export type Trip = Tables<"trips">;
export type Flight = Tables<"flights">;
export type Accommodation = Tables<"accommodations">;
export type AccommodationEmbedding = Tables<"accommodation_embeddings">;
export type Transportation = Tables<"transportation">;
export type ItineraryItem = Tables<"itinerary_items">;
export type ChatSession = Tables<"chat_sessions">;
export type ChatSessionInsert = InsertTables<"chat_sessions">;
export type ChatMessage = Tables<"chat_messages">;
export type ChatMessageInsert = InsertTables<"chat_messages">;
export type ChatToolCall = Tables<"chat_tool_calls">;
export type ChatToolCallInsert = InsertTables<"chat_tool_calls">;
export type ApiKey = Tables<"api_keys">;
export type Memory = Tables<"memories">;
export type SessionMemory = Tables<"session_memories">;
export type TripCollaborator = Tables<"trip_collaborators">;
export type FileAttachment = Tables<"file_attachments">;
export type FileAttachmentInsert = InsertTables<"file_attachments">;
export type FileAttachmentUpdate = UpdateTables<"file_attachments">;
export type SearchDestination = Tables<"search_destinations">;
export type SearchActivity = Tables<"search_activities">;
export type SearchFlight = Tables<"search_flights">;
export type SearchHotel = Tables<"search_hotels">;

// Enum shortcuts
export type ChatRole = Enums<"chat_role">;
export type UploadStatus = Enums<"upload_status">;
export type VirusScanStatus = Enums<"virus_scan_status">;
