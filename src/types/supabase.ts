/**
 * TripSage Database Types
 * 
 * This file contains TypeScript type definitions for the TripSage database schema.
 * These types should be used when interacting with the Supabase client.
 */

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: number
          name: string | null
          email: string | null
          preferences_json: Json | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: never
          name?: string | null
          email?: string | null
          preferences_json?: Json | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: never
          name?: string | null
          email?: string | null
          preferences_json?: Json | null
          created_at?: string
          updated_at?: string
        }
        Relationships: []
      }
      trips: {
        Row: {
          id: number
          name: string
          start_date: string
          end_date: string
          destination: string
          budget: number
          travelers: number
          status: string
          trip_type: string
          flexibility: Json | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: never
          name: string
          start_date: string
          end_date: string
          destination: string
          budget: number
          travelers: number
          status: string
          trip_type: string
          flexibility?: Json | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: never
          name?: string
          start_date?: string
          end_date?: string
          destination?: string
          budget?: number
          travelers?: number
          status?: string
          trip_type?: string
          flexibility?: Json | null
          created_at?: string
          updated_at?: string
        }
        Relationships: []
      }
      flights: {
        Row: {
          id: number
          trip_id: number
          origin: string
          destination: string
          airline: string | null
          departure_time: string
          arrival_time: string
          price: number
          booking_link: string | null
          segment_number: number | null
          search_timestamp: string
          booking_status: string
          data_source: string | null
        }
        Insert: {
          id?: never
          trip_id: number
          origin: string
          destination: string
          airline?: string | null
          departure_time: string
          arrival_time: string
          price: number
          booking_link?: string | null
          segment_number?: number | null
          search_timestamp?: string
          booking_status?: string
          data_source?: string | null
        }
        Update: {
          id?: never
          trip_id?: number
          origin?: string
          destination?: string
          airline?: string | null
          departure_time?: string
          arrival_time?: string
          price?: number
          booking_link?: string | null
          segment_number?: number | null
          search_timestamp?: string
          booking_status?: string
          data_source?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "flights_trip_id_fkey"
            columns: ["trip_id"]
            referencedRelation: "trips"
            referencedColumns: ["id"]
          }
        ]
      }
      accommodations: {
        Row: {
          id: number
          trip_id: number
          name: string
          type: string
          check_in: string
          check_out: string
          price_per_night: number
          total_price: number
          location: string
          rating: number | null
          amenities: Json | null
          booking_link: string | null
          search_timestamp: string
          booking_status: string
          cancellation_policy: string | null
          distance_to_center: number | null
          neighborhood: string | null
        }
        Insert: {
          id?: never
          trip_id: number
          name: string
          type: string
          check_in: string
          check_out: string
          price_per_night: number
          total_price: number
          location: string
          rating?: number | null
          amenities?: Json | null
          booking_link?: string | null
          search_timestamp?: string
          booking_status?: string
          cancellation_policy?: string | null
          distance_to_center?: number | null
          neighborhood?: string | null
        }
        Update: {
          id?: never
          trip_id?: number
          name?: string
          type?: string
          check_in?: string
          check_out?: string
          price_per_night?: number
          total_price?: number
          location?: string
          rating?: number | null
          amenities?: Json | null
          booking_link?: string | null
          search_timestamp?: string
          booking_status?: string
          cancellation_policy?: string | null
          distance_to_center?: number | null
          neighborhood?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "accommodations_trip_id_fkey"
            columns: ["trip_id"]
            referencedRelation: "trips"
            referencedColumns: ["id"]
          }
        ]
      }
      transportation: {
        Row: {
          id: number
          trip_id: number
          type: string
          provider: string | null
          pickup_date: string
          dropoff_date: string
          price: number
          notes: string | null
          booking_status: string
        }
        Insert: {
          id?: never
          trip_id: number
          type: string
          provider?: string | null
          pickup_date: string
          dropoff_date: string
          price: number
          notes?: string | null
          booking_status?: string
        }
        Update: {
          id?: never
          trip_id?: number
          type?: string
          provider?: string | null
          pickup_date?: string
          dropoff_date?: string
          price?: number
          notes?: string | null
          booking_status?: string
        }
        Relationships: [
          {
            foreignKeyName: "transportation_trip_id_fkey"
            columns: ["trip_id"]
            referencedRelation: "trips"
            referencedColumns: ["id"]
          }
        ]
      }
      itinerary_items: {
        Row: {
          id: number
          trip_id: number
          type: string
          date: string
          time: string | null
          description: string
          cost: number | null
          notes: string | null
        }
        Insert: {
          id?: never
          trip_id: number
          type: string
          date: string
          time?: string | null
          description: string
          cost?: number | null
          notes?: string | null
        }
        Update: {
          id?: never
          trip_id?: number
          type?: string
          date?: string
          time?: string | null
          description?: string
          cost?: number | null
          notes?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "itinerary_items_trip_id_fkey"
            columns: ["trip_id"]
            referencedRelation: "trips"
            referencedColumns: ["id"]
          }
        ]
      }
      search_parameters: {
        Row: {
          id: number
          trip_id: number
          timestamp: string
          parameter_json: Json
        }
        Insert: {
          id?: never
          trip_id: number
          timestamp?: string
          parameter_json: Json
        }
        Update: {
          id?: never
          trip_id?: number
          timestamp?: string
          parameter_json?: Json
        }
        Relationships: [
          {
            foreignKeyName: "search_parameters_trip_id_fkey"
            columns: ["trip_id"]
            referencedRelation: "trips"
            referencedColumns: ["id"]
          }
        ]
      }
      price_history: {
        Row: {
          id: number
          entity_type: string
          entity_id: number
          timestamp: string
          price: number
        }
        Insert: {
          id?: never
          entity_type: string
          entity_id: number
          timestamp?: string
          price: number
        }
        Update: {
          id?: never
          entity_type?: string
          entity_id?: number
          timestamp?: string
          price?: number
        }
        Relationships: []
      }
      trip_notes: {
        Row: {
          id: number
          trip_id: number
          timestamp: string
          content: string
        }
        Insert: {
          id?: never
          trip_id: number
          timestamp?: string
          content: string
        }
        Update: {
          id?: never
          trip_id?: number
          timestamp?: string
          content?: string
        }
        Relationships: [
          {
            foreignKeyName: "trip_notes_trip_id_fkey"
            columns: ["trip_id"]
            referencedRelation: "trips"
            referencedColumns: ["id"]
          }
        ]
      }
      saved_options: {
        Row: {
          id: number
          trip_id: number
          option_type: string
          option_id: number
          timestamp: string
          notes: string | null
        }
        Insert: {
          id?: never
          trip_id: number
          option_type: string
          option_id: number
          timestamp?: string
          notes?: string | null
        }
        Update: {
          id?: never
          trip_id?: number
          option_type?: string
          option_id?: number
          timestamp?: string
          notes?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "saved_options_trip_id_fkey"
            columns: ["trip_id"]
            referencedRelation: "trips"
            referencedColumns: ["id"]
          }
        ]
      }
      trip_comparison: {
        Row: {
          id: number
          trip_id: number
          comparison_json: Json
        }
        Insert: {
          id?: never
          trip_id: number
          comparison_json: Json
        }
        Update: {
          id?: never
          trip_id?: number
          comparison_json?: Json
        }
        Relationships: [
          {
            foreignKeyName: "trip_comparison_trip_id_fkey"
            columns: ["trip_id"]
            referencedRelation: "trips"
            referencedColumns: ["id"]
          }
        ]
      }
    }
    Views: {}
    Functions: {}
    Enums: {}
  }
}

/**
 * Type aliases for easier usage
 */

// Core entities
export type User = Database["public"]["Tables"]["users"]["Row"]
export type Trip = Database["public"]["Tables"]["trips"]["Row"]

// Travel options
export type Flight = Database["public"]["Tables"]["flights"]["Row"]
export type Accommodation = Database["public"]["Tables"]["accommodations"]["Row"]
export type Transportation = Database["public"]["Tables"]["transportation"]["Row"]

// Planning entities
export type ItineraryItem = Database["public"]["Tables"]["itinerary_items"]["Row"]
export type SearchParameters = Database["public"]["Tables"]["search_parameters"]["Row"]
export type TripNote = Database["public"]["Tables"]["trip_notes"]["Row"]

// Analysis entities
export type PriceHistory = Database["public"]["Tables"]["price_history"]["Row"]
export type SavedOption = Database["public"]["Tables"]["saved_options"]["Row"]
export type TripComparison = Database["public"]["Tables"]["trip_comparison"]["Row"]

// Insert types
export type UserInsert = Database["public"]["Tables"]["users"]["Insert"]
export type TripInsert = Database["public"]["Tables"]["trips"]["Insert"]
export type FlightInsert = Database["public"]["Tables"]["flights"]["Insert"]
export type AccommodationInsert = Database["public"]["Tables"]["accommodations"]["Insert"]
export type TransportationInsert = Database["public"]["Tables"]["transportation"]["Insert"]
export type ItineraryItemInsert = Database["public"]["Tables"]["itinerary_items"]["Insert"]
export type SearchParametersInsert = Database["public"]["Tables"]["search_parameters"]["Insert"]
export type TripNoteInsert = Database["public"]["Tables"]["trip_notes"]["Insert"]
export type PriceHistoryInsert = Database["public"]["Tables"]["price_history"]["Insert"]
export type SavedOptionInsert = Database["public"]["Tables"]["saved_options"]["Insert"]
export type TripComparisonInsert = Database["public"]["Tables"]["trip_comparison"]["Insert"]

// Update types
export type UserUpdate = Database["public"]["Tables"]["users"]["Update"]
export type TripUpdate = Database["public"]["Tables"]["trips"]["Update"]
export type FlightUpdate = Database["public"]["Tables"]["flights"]["Update"]
export type AccommodationUpdate = Database["public"]["Tables"]["accommodations"]["Update"]
export type TransportationUpdate = Database["public"]["Tables"]["transportation"]["Update"]
export type ItineraryItemUpdate = Database["public"]["Tables"]["itinerary_items"]["Update"]
export type SearchParametersUpdate = Database["public"]["Tables"]["search_parameters"]["Update"]
export type TripNoteUpdate = Database["public"]["Tables"]["trip_notes"]["Update"]
export type PriceHistoryUpdate = Database["public"]["Tables"]["price_history"]["Update"]
export type SavedOptionUpdate = Database["public"]["Tables"]["saved_options"]["Update"]
export type TripComparisonUpdate = Database["public"]["Tables"]["trip_comparison"]["Update"]