/**
 * @fileoverview Schema adapters for frontend API compatibility.
 *
 * Handles conversion between different field naming conventions:
 * - Backend snake_case vs Frontend camelCase
 * - Legacy field names vs current schema
 * - Missing field defaults
 */

import type { Destination, Trip } from "@/stores/trip-store";

export interface ApiTrip {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  start_date: string;
  end_date: string;
  destinations: ApiDestination[];
  budget?: number;
  visibility: "private" | "shared" | "public";
  tags: string[];
  preferences: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ApiDestination {
  name: string;
  country?: string;
  city?: string;
  coordinates?: {
    latitude: number;
    longitude: number;
  };
  arrival_date?: string;
  departure_date?: string;
  duration_days?: number;
}

export class FrontendSchemaAdapter {
  /**
   * Convert API response to frontend Trip format
   */
  static apiTripToFrontend(apiTrip: ApiTrip): Trip {
    return {
      budget: apiTrip.budget,
      created_at: apiTrip.created_at,
      createdAt: apiTrip.created_at, // Camel case version
      description: apiTrip.description,
      destinations: apiTrip.destinations.map(
        FrontendSchemaAdapter.apiDestinationToFrontend
      ),
      end_date: apiTrip.end_date,
      endDate: apiTrip.end_date, // Camel case version
      id: apiTrip.id,
      isPublic: apiTrip.visibility === "public", // Legacy field
      name: apiTrip.title, // API uses 'title', frontend uses 'name'
      preferences: apiTrip.preferences,
      start_date: apiTrip.start_date,
      startDate: apiTrip.start_date, // Camel case version
      status: apiTrip.status,
      tags: apiTrip.tags,
      title: apiTrip.title, // Keep both for compatibility
      updated_at: apiTrip.updated_at,
      updatedAt: apiTrip.updated_at, // Camel case version
      user_id: apiTrip.user_id,
      visibility: apiTrip.visibility,
    };
  }

  /**
   * Convert frontend Trip to API request format
   */
  static frontendTripToApi(trip: Trip): Partial<ApiTrip> {
    return {
      budget: trip.budget,
      description: trip.description,
      destinations: trip.destinations.map(
        FrontendSchemaAdapter.frontendDestinationToApi
      ),
      end_date: trip.end_date || trip.endDate || "",
      id: trip.id,
      preferences: trip.preferences || {},
      start_date: trip.start_date || trip.startDate || "",
      status: trip.status || "planning",
      tags: trip.tags || [],
      title: trip.title || trip.name, // Use title if available, fallback to name
      user_id: trip.user_id,
      visibility: trip.visibility || (trip.isPublic ? "public" : "private"),
    };
  }

  /**
   * Convert API destination to frontend format
   */
  static apiDestinationToFrontend(apiDest: ApiDestination): Destination {
    return {
      activities: [], // Default empty array
      coordinates: apiDest.coordinates,
      country: apiDest.country || "",
      endDate: apiDest.departure_date,
      estimatedCost: 0, // Default value
      id: `${apiDest.name}-${Date.now()}`, // Generate ID if not provided
      name: apiDest.name,
      startDate: apiDest.arrival_date,
    };
  }

  /**
   * Convert frontend destination to API format
   */
  static frontendDestinationToApi(dest: Destination): ApiDestination {
    return {
      arrival_date: dest.startDate,
      city: dest.country, // Use country as city fallback
      coordinates: dest.coordinates,
      country: dest.country,
      departure_date: dest.endDate,
      name: dest.name,
    };
  }

  /**
   * Normalize trip data for consistent frontend usage
   */
  static normalizeTrip(trip: Partial<Trip>): Trip {
    return {
      budget: trip.budget || 0,
      created_at: trip.created_at || trip.createdAt || new Date().toISOString(),
      createdAt: trip.createdAt || trip.created_at || new Date().toISOString(),
      currency: trip.currency || "USD",
      description: trip.description || "",
      destinations: trip.destinations || [],
      end_date: trip.end_date || trip.endDate || "",
      endDate: trip.endDate || trip.end_date || "",
      id: trip.id || "",
      isPublic: trip.isPublic || trip.visibility === "public",
      name: trip.name || trip.title || "Untitled Trip",
      preferences: trip.preferences || {},
      start_date: trip.start_date || trip.startDate || "",
      startDate: trip.startDate || trip.start_date || "",
      status: trip.status || "planning",
      tags: trip.tags || [],
      title: trip.title || trip.name || "Untitled Trip",
      updated_at: trip.updated_at || trip.updatedAt || new Date().toISOString(),
      updatedAt: trip.updatedAt || trip.updated_at || new Date().toISOString(),
      visibility: trip.visibility || "private",
    };
  }

  /**
   * Create a new trip with proper defaults
   */
  static createEmptyTrip(overrides: Partial<Trip> = {}): Trip {
    const now = new Date().toISOString();

    return FrontendSchemaAdapter.normalizeTrip({
      budget: 0,
      created_at: now,
      createdAt: now,
      currency: "USD",
      description: "",
      destinations: [],
      end_date: "",
      endDate: "",
      id: "",
      isPublic: false,
      name: "New Trip",
      preferences: {},
      start_date: "",
      startDate: "",
      status: "planning",
      tags: [],
      title: "New Trip",
      updated_at: now,
      updatedAt: now,
      visibility: "private",
      ...overrides,
    });
  }

  /**
   * Validate trip data for API submission
   */
  static validateTripForApi(trip: Trip): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (!trip.name && !trip.title) {
      errors.push("Trip must have a name or title");
    }

    if (!trip.start_date && !trip.startDate) {
      errors.push("Trip must have a start date");
    }

    if (!trip.end_date && !trip.endDate) {
      errors.push("Trip must have an end date");
    }

    // Validate dates
    const startDate = new Date(trip.start_date || trip.startDate || "");
    const endDate = new Date(trip.end_date || trip.endDate || "");

    if (startDate && endDate && endDate <= startDate) {
      errors.push("End date must be after start date");
    }

    if (trip.destinations.length === 0) {
      errors.push("Trip must have at least one destination");
    }

    return {
      errors,
      valid: errors.length === 0,
    };
  }

  /**
   * Handle API error responses with schema context
   */
  static handleApiError(error: any): string {
    if (error?.response?.data?.detail) {
      const detail = error.response.data.detail;

      // Handle field validation errors
      if (typeof detail === "object" && detail.type === "value_error") {
        return `Validation error: ${detail.msg || "Invalid data format"}`;
      }

      if (Array.isArray(detail)) {
        return detail.map((err: any) => err.msg || err).join(", ");
      }

      return detail;
    }

    if (error?.message) {
      return error.message;
    }

    return "An unexpected error occurred";
  }
}

/**
 * Hook for consistent date formatting across the app
 */
export function formatTripDate(dateString: string): string {
  if (!dateString) return "";

  try {
    return new Date(dateString).toLocaleDateString("en-US", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateString; // Return original if parsing fails
  }
}

/**
 * Hook for consistent trip duration calculation
 */
export function calculateTripDuration(startDate: string, endDate: string): number {
  if (!startDate || !endDate) return 0;

  try {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  } catch {
    return 0;
  }
}
