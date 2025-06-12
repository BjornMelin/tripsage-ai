export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

// Table row types for easy access
export type Tables<T extends keyof Database['public']['Tables']> = Database['public']['Tables'][T]['Row'];
export type TablesInsert<T extends keyof Database['public']['Tables']> = Database['public']['Tables'][T]['Insert'];
export type TablesUpdate<T extends keyof Database['public']['Tables']> = Database['public']['Tables'][T]['Update'];
export type Enums<T extends keyof Database['public']['Enums']> = Database['public']['Enums'][T];

// Specific table type exports for common usage
export type Trip = Tables<'trips'>;
export type TripInsert = TablesInsert<'trips'>;
export type TripUpdate = TablesUpdate<'trips'>;

export type Flight = Tables<'flights'>;
export type FlightInsert = TablesInsert<'flights'>;
export type FlightUpdate = TablesUpdate<'flights'>;

export type Accommodation = Tables<'accommodations'>;
export type AccommodationInsert = TablesInsert<'accommodations'>;
export type AccommodationUpdate = TablesUpdate<'accommodations'>;

export type ChatSession = Tables<'chat_sessions'>;
export type ChatSessionInsert = TablesInsert<'chat_sessions'>;
export type ChatSessionUpdate = TablesUpdate<'chat_sessions'>;

export type ChatMessage = Tables<'chat_messages'>;
export type ChatMessageInsert = TablesInsert<'chat_messages'>;
export type ChatMessageUpdate = TablesUpdate<'chat_messages'>;

export type ChatToolCall = Tables<'chat_tool_calls'>;
export type ChatToolCallInsert = TablesInsert<'chat_tool_calls'>;
export type ChatToolCallUpdate = TablesUpdate<'chat_tool_calls'>;

export type TripCollaborator = Tables<'trip_collaborators'>;
export type TripCollaboratorInsert = TablesInsert<'trip_collaborators'>;
export type TripCollaboratorUpdate = TablesUpdate<'trip_collaborators'>;

export type FileAttachment = Tables<'file_attachments'>;
export type FileAttachmentInsert = TablesInsert<'file_attachments'>;
export type FileAttachmentUpdate = TablesUpdate<'file_attachments'>;

export type Memory = Tables<'memories'>;
export type MemoryInsert = TablesInsert<'memories'>;
export type MemoryUpdate = TablesUpdate<'memories'>;

export type SessionMemory = Tables<'session_memories'>;
export type SessionMemoryInsert = TablesInsert<'session_memories'>;
export type SessionMemoryUpdate = TablesUpdate<'session_memories'>;

export type ApiKey = Tables<'api_keys'>;
export type ApiKeyInsert = TablesInsert<'api_keys'>;
export type ApiKeyUpdate = TablesUpdate<'api_keys'>;

export type ItineraryItem = Tables<'itinerary_items'>;
export type ItineraryItemInsert = TablesInsert<'itinerary_items'>;
export type ItineraryItemUpdate = TablesUpdate<'itinerary_items'>;

export type Transportation = Tables<'transportation'>;
export type TransportationInsert = TablesInsert<'transportation'>;
export type TransportationUpdate = TablesUpdate<'transportation'>;

// Search cache types
export type SearchDestination = Tables<'search_destinations'>;
export type SearchActivity = Tables<'search_activities'>;
export type SearchFlight = Tables<'search_flights'>;
export type SearchHotel = Tables<'search_hotels'>;

// Enum types
export type TripStatus = Enums<'trip_status'>;
export type TripType = Enums<'trip_type'>;
export type FlightClass = Enums<'flight_class'>;
export type BookingStatus = Enums<'booking_status'>;
export type TransportType = Enums<'transport_type'>;
export type ItemType = Enums<'item_type'>;
export type ChatRole = Enums<'chat_role'>;
export type ToolCallStatus = Enums<'tool_call_status'>;
export type MemoryType = Enums<'memory_type'>;
export type PermissionLevel = Enums<'permission_level'>;
export type UploadStatus = Enums<'upload_status'>;
export type VirusScanStatus = Enums<'virus_scan_status'>;
export type SearchSource = Enums<'search_source'>;

export interface Database {
  public: {
    Tables: {
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
          status: string;
          trip_type: string;
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
          status?: string;
          trip_type?: string;
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
          status?: string;
          trip_type?: string;
          flexibility?: Json;
          notes?: string[] | null;
          search_metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
      };
      flights: {
        Row: {
          id: number;
          trip_id: number;
          origin: string;
          destination: string;
          departure_date: string;
          return_date: string | null;
          flight_class: string;
          price: number;
          currency: string;
          airline: string | null;
          flight_number: string | null;
          booking_status: string;
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
          flight_class?: string;
          price: number;
          currency?: string;
          airline?: string | null;
          flight_number?: string | null;
          booking_status?: string;
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
          flight_class?: string;
          price?: number;
          currency?: string;
          airline?: string | null;
          flight_number?: string | null;
          booking_status?: string;
          external_id?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
      };
      accommodations: {
        Row: {
          id: number;
          trip_id: number;
          name: string;
          address: string | null;
          check_in_date: string;
          check_out_date: string;
          room_type: string | null;
          price_per_night: number;
          total_price: number;
          currency: string;
          rating: number | null;
          amenities: string[] | null;
          booking_status: string;
          external_id: string | null;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: never;
          trip_id: number;
          name: string;
          address?: string | null;
          check_in_date: string;
          check_out_date: string;
          room_type?: string | null;
          price_per_night: number;
          total_price: number;
          currency?: string;
          rating?: number | null;
          amenities?: string[] | null;
          booking_status?: string;
          external_id?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: never;
          trip_id?: number;
          name?: string;
          address?: string | null;
          check_in_date?: string;
          check_out_date?: string;
          room_type?: string | null;
          price_per_night?: number;
          total_price?: number;
          currency?: string;
          rating?: number | null;
          amenities?: string[] | null;
          booking_status?: string;
          external_id?: string | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
      };
      transportation: {
        Row: {
          id: number;
          trip_id: number;
          transport_type: string;
          origin: string;
          destination: string;
          departure_time: string | null;
          arrival_time: string | null;
          price: number;
          currency: string;
          booking_status: string;
          external_id: string | null;
          metadata: Json;
          created_at: string;
        };
        Insert: {
          id?: never;
          trip_id: number;
          transport_type: string;
          origin: string;
          destination: string;
          departure_time?: string | null;
          arrival_time?: string | null;
          price: number;
          currency?: string;
          booking_status?: string;
          external_id?: string | null;
          metadata?: Json;
          created_at?: string;
        };
        Update: {
          id?: never;
          trip_id?: number;
          transport_type?: string;
          origin?: string;
          destination?: string;
          departure_time?: string | null;
          arrival_time?: string | null;
          price?: number;
          currency?: string;
          booking_status?: string;
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
          item_type: string;
          start_time: string | null;
          end_time: string | null;
          location: string | null;
          price: number | null;
          currency: string | null;
          booking_status: string;
          external_id: string | null;
          metadata: Json;
          created_at: string;
        };
        Insert: {
          id?: never;
          trip_id: number;
          title: string;
          description?: string | null;
          item_type: string;
          start_time?: string | null;
          end_time?: string | null;
          location?: string | null;
          price?: number | null;
          currency?: string | null;
          booking_status?: string;
          external_id?: string | null;
          metadata?: Json;
          created_at?: string;
        };
        Update: {
          id?: never;
          trip_id?: number;
          title?: string;
          description?: string | null;
          item_type?: string;
          start_time?: string | null;
          end_time?: string | null;
          location?: string | null;
          price?: number | null;
          currency?: string | null;
          booking_status?: string;
          external_id?: string | null;
          metadata?: Json;
          created_at?: string;
        };
      };
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
      };
      chat_messages: {
        Row: {
          id: number;
          session_id: string;
          role: string;
          content: string;
          created_at: string;
          metadata: Json;
        };
        Insert: {
          id?: never;
          session_id: string;
          role: string;
          content: string;
          created_at?: string;
          metadata?: Json;
        };
        Update: {
          id?: never;
          session_id?: string;
          role?: string;
          content?: string;
          created_at?: string;
          metadata?: Json;
        };
      };
      chat_tool_calls: {
        Row: {
          id: number;
          message_id: number;
          tool_id: string;
          tool_name: string;
          arguments: Json;
          result: Json | null;
          status: string;
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
          status?: string;
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
          status?: string;
          created_at?: string;
          completed_at?: string | null;
          error_message?: string | null;
        };
      };
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
      memories: {
        Row: {
          id: number;
          user_id: string;
          memory_type: string;
          content: string;
          embedding: number[] | null;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: never;
          user_id: string;
          memory_type?: string;
          content: string;
          embedding?: number[] | null;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: never;
          user_id?: string;
          memory_type?: string;
          content?: string;
          embedding?: number[] | null;
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
          embedding: number[] | null;
          metadata: Json;
          created_at: string;
        };
        Insert: {
          id?: never;
          session_id: string;
          user_id: string;
          content: string;
          embedding?: number[] | null;
          metadata?: Json;
          created_at?: string;
        };
        Update: {
          id?: never;
          session_id?: string;
          user_id?: string;
          content?: string;
          embedding?: number[] | null;
          metadata?: Json;
          created_at?: string;
        };
      };
      trip_collaborators: {
        Row: {
          id: number;
          trip_id: number;
          user_id: string;
          permission_level: string;
          added_by: string;
          added_at: string;
          updated_at: string;
        };
        Insert: {
          id?: never;
          trip_id: number;
          user_id: string;
          permission_level?: string;
          added_by: string;
          added_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: never;
          trip_id?: number;
          user_id?: string;
          permission_level?: string;
          added_by?: string;
          added_at?: string;
          updated_at?: string;
        };
      };
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
          upload_status: string;
          virus_scan_status: string | null;
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
          upload_status?: string;
          virus_scan_status?: string | null;
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
          upload_status?: string;
          virus_scan_status?: string | null;
          virus_scan_result?: Json;
          metadata?: Json;
          created_at?: string;
          updated_at?: string;
        };
      };
      search_destinations: {
        Row: {
          id: number;
          user_id: string;
          query: string;
          query_hash: string;
          results: Json;
          source: string;
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
          source: string;
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
          source?: string;
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
          source: string;
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
          source: string;
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
          source?: string;
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
          cabin_class: string;
          query_parameters: Json;
          query_hash: string;
          results: Json;
          source: string;
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
          cabin_class?: string;
          query_parameters: Json;
          query_hash: string;
          results: Json;
          source: string;
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
          cabin_class?: string;
          query_parameters?: Json;
          query_hash?: string;
          results?: Json;
          source?: string;
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
          source: string;
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
          source: string;
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
          source?: string;
          search_metadata?: Json;
          expires_at?: string;
          created_at?: string;
        };
      };
    };
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
      item_type: "activity" | "meal" | "transport" | "accommodation" | "event" | "other";
      chat_role: "user" | "assistant" | "system";
      tool_call_status: "pending" | "running" | "completed" | "failed";
      memory_type: "user_preference" | "trip_history" | "search_pattern" | "conversation_context" | "other";
      permission_level: "view" | "edit" | "admin";
      upload_status: "uploading" | "completed" | "failed";
      virus_scan_status: "pending" | "clean" | "infected" | "failed";
      search_source: "google_maps" | "external_api" | "cached" | "viator" | "getyourguide" | "duffel" | "amadeus" | "booking" | "expedia" | "airbnb_mcp";
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
}
