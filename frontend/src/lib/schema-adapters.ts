/**
 * Schema adapters for frontend API compatibility.
 *
 * Handles conversion between different field naming conventions:
 * - Backend snake_case vs Frontend camelCase
 * - Legacy field names vs current schema
 * - Missing field defaults
 */

import type { Trip, Destination } from "@/stores/trip-store";

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
  preferences: Record<string, any>;
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
      id: apiTrip.id,
      user_id: apiTrip.user_id,
      name: apiTrip.title, // API uses 'title', frontend uses 'name'
      title: apiTrip.title, // Keep both for compatibility
      description: apiTrip.description,
      start_date: apiTrip.start_date,
      end_date: apiTrip.end_date,
      startDate: apiTrip.start_date, // Camel case version
      endDate: apiTrip.end_date, // Camel case version
      destinations: apiTrip.destinations.map(this.apiDestinationToFrontend),
      budget: apiTrip.budget,
      visibility: apiTrip.visibility,
      isPublic: apiTrip.visibility === "public", // Legacy field
      tags: apiTrip.tags,
      preferences: apiTrip.preferences,
      status: apiTrip.status,
      created_at: apiTrip.created_at,
      updated_at: apiTrip.updated_at,
      createdAt: apiTrip.created_at, // Camel case version
      updatedAt: apiTrip.updated_at, // Camel case version
    };
  }

  /**
   * Convert frontend Trip to API request format
   */
  static frontendTripToApi(trip: Trip): Partial<ApiTrip> {
    return {
      id: trip.id,
      user_id: trip.user_id,
      title: trip.title || trip.name, // Use title if available, fallback to name
      description: trip.description,
      start_date: trip.start_date || trip.startDate || "",
      end_date: trip.end_date || trip.endDate || "",
      destinations: trip.destinations.map(this.frontendDestinationToApi),
      budget: trip.budget,
      visibility: trip.visibility || (trip.isPublic ? "public" : "private"),
      tags: trip.tags || [],
      preferences: trip.preferences || {},
      status: trip.status || "planning",
    };
  }

  /**
   * Convert API destination to frontend format
   */
  static apiDestinationToFrontend(apiDest: ApiDestination): Destination {
    return {
      id: `${apiDest.name}-${Date.now()}`, // Generate ID if not provided
      name: apiDest.name,
      country: apiDest.country || "",
      coordinates: apiDest.coordinates,
      startDate: apiDest.arrival_date,
      endDate: apiDest.departure_date,
      activities: [], // Default empty array
      estimatedCost: 0, // Default value
    };
  }

  /**
   * Convert frontend destination to API format
   */
  static frontendDestinationToApi(dest: Destination): ApiDestination {
    return {
      name: dest.name,
      country: dest.country,
      city: dest.country, // Use country as city fallback
      coordinates: dest.coordinates,
      arrival_date: dest.startDate,
      departure_date: dest.endDate,
    };
  }

  /**
   * Normalize trip data for consistent frontend usage
   */
  static normalizeTrip(trip: Partial<Trip>): Trip {
    return {
      id: trip.id || "",
      name: trip.name || trip.title || "Untitled Trip",
      title: trip.title || trip.name || "Untitled Trip",
      description: trip.description || "",
      start_date: trip.start_date || trip.startDate || "",
      end_date: trip.end_date || trip.endDate || "",
      startDate: trip.startDate || trip.start_date || "",
      endDate: trip.endDate || trip.end_date || "",
      destinations: trip.destinations || [],
      budget: trip.budget || 0,
      currency: trip.currency || "USD",
      visibility: trip.visibility || "private",
      isPublic: trip.isPublic || trip.visibility === "public",
      tags: trip.tags || [],
      preferences: trip.preferences || {},
      status: trip.status || "planning",
      created_at: trip.created_at || trip.createdAt || new Date().toISOString(),
      updated_at: trip.updated_at || trip.updatedAt || new Date().toISOString(),
      createdAt: trip.createdAt || trip.created_at || new Date().toISOString(),
      updatedAt: trip.updatedAt || trip.updated_at || new Date().toISOString(),
    };
  }

  /**
   * Create a new trip with proper defaults
   */
  static createEmptyTrip(overrides: Partial<Trip> = {}): Trip {
    const now = new Date().toISOString();

    return this.normalizeTrip({
      id: "",
      name: "New Trip",
      title: "New Trip",
      description: "",
      start_date: "",
      end_date: "",
      startDate: "",
      endDate: "",
      destinations: [],
      budget: 0,
      currency: "USD",
      visibility: "private",
      isPublic: false,
      tags: [],
      preferences: {},
      status: "planning",
      created_at: now,
      updated_at: now,
      createdAt: now,
      updatedAt: now,
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
      valid: errors.length === 0,
      errors,
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
      year: "numeric",
      month: "short",
      day: "numeric",
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
