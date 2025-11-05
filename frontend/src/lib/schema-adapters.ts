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
  // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
  user_id: string;
  title: string;
  description?: string;
  // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
  start_date: string;
  // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
  end_date: string;
  destinations: ApiDestination[];
  budget?: number;
  visibility: "private" | "shared" | "public";
  tags: string[];
  preferences: Record<string, unknown>;
  status: string;
  // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
  created_at: string;
  // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
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
  // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
  arrival_date?: string;
  // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
  departure_date?: string;
  // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
  duration_days?: number;
}

/**
 * Convert API response to frontend Trip format
 */
export function apiTripToFrontend(apiTrip: ApiTrip): Trip {
  return {
    budget: apiTrip.budget,
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    created_at: apiTrip.created_at,
    createdAt: apiTrip.created_at, // Camel case version
    description: apiTrip.description,
    destinations: apiTrip.destinations.map(apiDestinationToFrontend),
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    end_date: apiTrip.end_date,
    endDate: apiTrip.end_date, // Camel case version
    id: apiTrip.id,
    isPublic: apiTrip.visibility === "public", // Legacy field
    name: apiTrip.title, // API uses 'title', frontend uses 'name'
    preferences: apiTrip.preferences,
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    start_date: apiTrip.start_date,
    startDate: apiTrip.start_date, // Camel case version
    status: apiTrip.status,
    tags: apiTrip.tags,
    title: apiTrip.title, // Keep both for compatibility
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    updated_at: apiTrip.updated_at,
    updatedAt: apiTrip.updated_at, // Camel case version
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    user_id: apiTrip.user_id,
    visibility: apiTrip.visibility,
  };
}

/**
 * Convert frontend Trip to API request format
 */
export function frontendTripToApi(trip: Trip): Partial<ApiTrip> {
  return {
    budget: trip.budget,
    description: trip.description,
    destinations: trip.destinations.map(frontendDestinationToApi),
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    end_date: trip.end_date || trip.endDate || "",
    id: trip.id,
    preferences: trip.preferences || {},
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    start_date: trip.start_date || trip.startDate || "",
    status: trip.status || "planning",
    tags: trip.tags || [],
    title: trip.title || trip.name, // Use title if available, fallback to name
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    user_id: trip.user_id,
    visibility: trip.visibility || (trip.isPublic ? "public" : "private"),
  };
}

/**
 * Convert API destination to frontend format
 */
export function apiDestinationToFrontend(apiDest: ApiDestination): Destination {
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
export function frontendDestinationToApi(dest: Destination): ApiDestination {
  return {
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    arrival_date: dest.startDate,
    city: dest.country, // Use country as city fallback
    coordinates: dest.coordinates,
    country: dest.country,
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    departure_date: dest.endDate,
    name: dest.name,
  };
}

/**
 * Normalize trip data for consistent frontend usage
 */
export function normalizeTrip(trip: Partial<Trip>): Trip {
  return {
    budget: trip.budget || 0,
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    created_at: trip.created_at || trip.createdAt || new Date().toISOString(),
    createdAt: trip.createdAt || trip.created_at || new Date().toISOString(),
    currency: trip.currency || "USD",
    description: trip.description || "",
    destinations: trip.destinations || [],
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    end_date: trip.end_date || trip.endDate || "",
    endDate: trip.endDate || trip.end_date || "",
    id: trip.id || "",
    isPublic: trip.isPublic || trip.visibility === "public",
    name: trip.name || trip.title || "Untitled Trip",
    preferences: trip.preferences || {},
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    start_date: trip.start_date || trip.startDate || "",
    startDate: trip.startDate || trip.start_date || "",
    status: trip.status || "planning",
    tags: trip.tags || [],
    title: trip.title || trip.name || "Untitled Trip",
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    updated_at: trip.updated_at || trip.updatedAt || new Date().toISOString(),
    updatedAt: trip.updatedAt || trip.updated_at || new Date().toISOString(),
    visibility: trip.visibility || "private",
  };
}

/**
 * Create a new trip with proper defaults
 */
export function createEmptyTrip(overrides: Partial<Trip> = {}): Trip {
  const now = new Date().toISOString();

  return normalizeTrip({
    budget: 0,
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    created_at: now,
    createdAt: now,
    currency: "USD",
    description: "",
    destinations: [],
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    end_date: "",
    endDate: "",
    id: "",
    isPublic: false,
    name: "New Trip",
    preferences: {},
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    start_date: "",
    startDate: "",
    status: "planning",
    tags: [],
    title: "New Trip",
    // biome-ignore lint/style/useNamingConvention: Matches backend API snake_case format
    updated_at: now,
    updatedAt: now,
    visibility: "private",
    ...overrides,
  });
}

/**
 * Validate trip data for API submission
 */
export function validateTripForApi(trip: Trip): {
  errors: string[];
  valid: boolean;
} {
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
export function handleApiError(error: unknown): string {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    "data" in error.response &&
    error.response.data &&
    typeof error.response.data === "object" &&
    "detail" in error.response.data
  ) {
    const detail = error.response.data.detail;

    // Handle field validation errors
    if (
      typeof detail === "object" &&
      detail !== null &&
      "type" in detail &&
      detail.type === "value_error"
    ) {
      const msg =
        "msg" in detail && typeof detail.msg === "string"
          ? detail.msg
          : "Invalid data format";
      return `Validation error: ${msg}`;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((err) => {
          if (typeof err === "object" && err !== null && "msg" in err) {
            return String(err.msg);
          }
          return String(err);
        })
        .join(", ");
    }

    return String(detail);
  }

  if (error && typeof error === "object" && "message" in error) {
    return String(error.message);
  }

  return "An unexpected error occurred";
}

/**
 * Hook for consistent date formatting across the app
 */
export function formatTripDate(dateString: string): string {
  if (!dateString) return "";

  // Fast path for canonical date-only strings to avoid timezone ambiguity.
  // Example: "2025-06-01" → "Jun 1, 2025" regardless of local TZ.
  const DateOnlyRe = /^(\d{4})-(\d{2})-(\d{2})$/;
  const match = DateOnlyRe.exec(dateString);
  if (match) {
    const year = Number.parseInt(match[1] ?? "", 10);
    const month = Number.parseInt(match[2] ?? "", 10); // 1-12
    const day = Number.parseInt(match[3] ?? "", 10); // 1-31

    // Treat year 0000 as invalid for consistency across environments.
    if (!Number.isFinite(year) || year <= 0) return "Invalid Date";

    // Validate month/day minimally (including leap-year for February)
    const monthLengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
    const maxDay = month === 2 ? (isLeap ? 29 : 28) : (monthLengths[month - 1] ?? 31);
    if (month < 1 || month > 12 || day < 1 || day > maxDay) return "Invalid Date";

    const months = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ] as const;
    const mon = months[month - 1] ?? "Jan";
    return `${mon} ${day}, ${year}`;
  }

  // For full ISO strings with time/offset, format deterministically in UTC.
  try {
    const d = new Date(dateString);
    if (Number.isNaN(d.getTime())) return "Invalid Date";
    return new Intl.DateTimeFormat("en-US", {
      day: "numeric",
      month: "short",
      timeZone: "UTC",
      year: "numeric",
    }).format(d);
  } catch {
    return "Invalid Date";
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
