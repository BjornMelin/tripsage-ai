/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Destination, Trip } from "@/stores/trip-store";
import {
  type ApiDestination,
  type ApiTrip,
  apiDestinationToFrontend,
  apiTripToFrontend,
  calculateTripDuration,
  createEmptyTrip,
  formatTripDate,
  frontendDestinationToApi,
  frontendTripToApi,
  handleApiError,
  normalizeTrip,
  validateTripForApi,
} from "../schema-adapters";

// Mock console.error to suppress error logs during testing
const MOCK_CONSOLE_ERROR = vi.spyOn(console, "error").mockImplementation(() => {
  // Suppress console.error during test
});

describe("schema-adapters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MOCK_CONSOLE_ERROR.mockClear();
  });

  describe("apiTripToFrontend", () => {
    const baseApiTrip: ApiTrip = {
      budget: 3000,
      created_at: "2025-01-01T00:00:00Z",
      description: "Amazing trip through Europe",
      destinations: [
        {
          arrival_date: "2025-06-01",
          city: "Paris",
          coordinates: { latitude: 48.8566, longitude: 2.3522 },
          country: "France",
          departure_date: "2025-06-05",
          duration_days: 4,
          name: "Paris",
        },
      ],
      end_date: "2025-06-15",
      id: "trip-123",
      preferences: { accommodation: { type: "hotel" } },
      start_date: "2025-06-01",
      status: "planning",
      tags: ["culture", "history"],
      title: "European Adventure",
      updated_at: "2025-01-01T12:00:00Z",
      user_id: "user-456",
      visibility: "private",
    };

    it("should convert API trip to frontend format with all fields", () => {
      const result = apiTripToFrontend(baseApiTrip);

      expect(result).toEqual({
        budget: 3000,
        created_at: "2025-01-01T00:00:00Z",
        createdAt: "2025-01-01T00:00:00Z", // Camel case version
        description: "Amazing trip through Europe",
        destinations: [
          {
            activities: [],
            coordinates: { latitude: 48.8566, longitude: 2.3522 },
            country: "France",
            endDate: "2025-06-05",
            estimatedCost: 0,
            id: expect.stringMatching(/^Paris-\d+$/), // Generated ID
            name: "Paris",
            startDate: "2025-06-01",
          },
        ],
        end_date: "2025-06-15",
        endDate: "2025-06-15", // Camel case version
        id: "trip-123",
        isPublic: false, // Legacy field derived from visibility
        name: "European Adventure", // API title -> frontend name
        preferences: { accommodation: { type: "hotel" } },
        start_date: "2025-06-01",
        startDate: "2025-06-01", // Camel case version
        status: "planning",
        tags: ["culture", "history"],
        title: "European Adventure", // Keep both for compatibility
        updated_at: "2025-01-01T12:00:00Z",
        updatedAt: "2025-01-01T12:00:00Z", // Camel case version
        user_id: "user-456",
        visibility: "private",
      });
    });

    it("should set isPublic to true when visibility is public", () => {
      const publicTrip = { ...baseApiTrip, visibility: "public" as const };
      const result = apiTripToFrontend(publicTrip);

      expect(result.visibility).toBe("public");
      expect(result.isPublic).toBe(true);
    });

    it("should handle optional fields gracefully", () => {
      const minimalTrip: ApiTrip = {
        created_at: "2025-01-01T00:00:00Z",
        destinations: [],
        end_date: "2025-06-15",
        id: "trip-minimal",
        preferences: {},
        start_date: "2025-06-01",
        status: "planning",
        tags: [],
        title: "Minimal Trip",
        updated_at: "2025-01-01T00:00:00Z",
        user_id: "user-123",
        visibility: "private",
      };

      const result = apiTripToFrontend(minimalTrip);

      expect(result.description).toBeUndefined();
      expect(result.budget).toBeUndefined();
      expect(result.destinations).toEqual([]);
      expect(result.tags).toEqual([]);
      expect(result.preferences).toEqual({});
    });

    it("should handle empty destinations array", () => {
      const tripWithNoDestinations = { ...baseApiTrip, destinations: [] };
      const result = apiTripToFrontend(tripWithNoDestinations);

      expect(result.destinations).toEqual([]);
    });

    it("should handle shared visibility correctly", () => {
      const sharedTrip = { ...baseApiTrip, visibility: "shared" as const };
      const result = apiTripToFrontend(sharedTrip);

      expect(result.visibility).toBe("shared");
      expect(result.isPublic).toBe(false);
    });
  });

  describe("frontendTripToApi", () => {
    const baseFrontendTrip: Trip = {
      budget: 3000,
      created_at: "2025-01-01T00:00:00Z",
      createdAt: "2025-01-01T00:00:00Z",
      description: "Amazing trip through Europe",
      destinations: [
        {
          activities: ["sightseeing"],
          coordinates: { latitude: 48.8566, longitude: 2.3522 },
          country: "France",
          endDate: "2025-06-05",
          estimatedCost: 1000,
          id: "dest-1",
          name: "Paris",
          startDate: "2025-06-01",
        },
      ],
      end_date: "2025-06-15",
      endDate: "2025-06-15",
      id: "trip-123",
      isPublic: false,
      name: "European Adventure",
      preferences: { accommodation: { type: "hotel" } },
      start_date: "2025-06-01",
      startDate: "2025-06-01",
      status: "planning",
      tags: ["culture", "history"],
      title: "European Adventure",
      updated_at: "2025-01-01T12:00:00Z",
      updatedAt: "2025-01-01T12:00:00Z",
      user_id: "user-456",
      visibility: "private",
    };

    it("should convert frontend trip to API format", () => {
      const result = frontendTripToApi(baseFrontendTrip);

      expect(result).toEqual({
        budget: 3000,
        description: "Amazing trip through Europe",
        destinations: [
          {
            arrival_date: "2025-06-01",
            city: "France", // Uses country as city fallback
            coordinates: { latitude: 48.8566, longitude: 2.3522 },
            country: "France",
            departure_date: "2025-06-05",
            name: "Paris",
          },
        ],
        end_date: "2025-06-15",
        id: "trip-123",
        preferences: { accommodation: { type: "hotel" } },
        start_date: "2025-06-01",
        status: "planning",
        tags: ["culture", "history"],
        title: "European Adventure",
        user_id: "user-456",
        visibility: "private",
      });
    });

    it("should use title if available, fallback to name", () => {
      const tripWithoutTitle = { ...baseFrontendTrip, title: undefined };
      const result = frontendTripToApi(tripWithoutTitle);

      expect(result.title).toBe("European Adventure"); // Falls back to name
    });

    it("should prefer snake_case dates over camelCase", () => {
      const tripWithDifferentDates = {
        ...baseFrontendTrip,
        end_date: "2025-07-15",
        endDate: "2025-06-15",
        start_date: "2025-07-01",
        startDate: "2025-06-01",
      };

      const result = frontendTripToApi(tripWithDifferentDates);

      expect(result.start_date).toBe("2025-07-01"); // Prefers snake_case
      expect(result.end_date).toBe("2025-07-15");
    });

    it("should fallback to camelCase dates when snake_case not available", () => {
      const tripWithCamelCaseDates = {
        ...baseFrontendTrip,
        end_date: undefined,
        start_date: undefined,
      };

      const result = frontendTripToApi(tripWithCamelCaseDates);

      expect(result.start_date).toBe("2025-06-01"); // Falls back to camelCase
      expect(result.end_date).toBe("2025-06-15");
    });

    it("should handle legacy isPublic field", () => {
      const publicTrip = {
        ...baseFrontendTrip,
        isPublic: true,
        visibility: undefined,
      };

      const result = frontendTripToApi(publicTrip);

      expect(result.visibility).toBe("public");
    });

    it("should provide default values for missing fields", () => {
      const minimalTrip: Trip = {
        destinations: [],
        id: "trip-minimal",
        name: "Minimal Trip",
        title: "Minimal Trip",
      };

      const result = frontendTripToApi(minimalTrip);

      expect(result.start_date).toBe("");
      expect(result.end_date).toBe("");
      expect(result.tags).toEqual([]);
      expect(result.preferences).toEqual({});
      expect(result.status).toBe("planning");
    });

    it("should handle empty destinations", () => {
      const tripWithEmptyDestinations = { ...baseFrontendTrip, destinations: [] };
      const result = frontendTripToApi(tripWithEmptyDestinations);

      expect(result.destinations).toEqual([]);
    });
  });

  describe("apiDestinationToFrontend", () => {
    const baseApiDestination: ApiDestination = {
      arrival_date: "2025-06-01",
      city: "Paris",
      coordinates: { latitude: 48.8566, longitude: 2.3522 },
      country: "France",
      departure_date: "2025-06-05",
      duration_days: 4,
      name: "Paris",
    };

    it("should convert API destination to frontend format", () => {
      const result = apiDestinationToFrontend(baseApiDestination);

      expect(result).toEqual({
        activities: [],
        coordinates: { latitude: 48.8566, longitude: 2.3522 },
        country: "France",
        endDate: "2025-06-05",
        estimatedCost: 0,
        id: expect.stringMatching(/^Paris-\d+$/), // Generated ID with timestamp
        name: "Paris",
        startDate: "2025-06-01",
      });
    });

    it("should generate unique IDs for destinations", () => {
      const dest1 = apiDestinationToFrontend(baseApiDestination);
      // Wait a small amount to ensure different timestamp
      const dest2 = apiDestinationToFrontend({
        ...baseApiDestination,
        name: "Rome", // Different name to potentially get different ID
      });

      expect(dest1.id).toMatch(/^Paris-\d+$/);
      expect(dest2.id).toMatch(/^Rome-\d+$/);
      // IDs should be different due to different names
      expect(dest1.id).not.toBe(dest2.id);
    });

    it("should handle missing optional fields", () => {
      const minimalDestination: ApiDestination = {
        name: "Rome",
      };

      const result = apiDestinationToFrontend(minimalDestination);

      expect(result).toEqual({
        activities: [],
        coordinates: undefined,
        country: "",
        endDate: undefined,
        estimatedCost: 0,
        id: expect.stringMatching(/^Rome-\d+$/),
        name: "Rome",
        startDate: undefined,
      });
    });

    it("should preserve coordinates when provided", () => {
      const result = apiDestinationToFrontend(baseApiDestination);

      expect(result.coordinates).toEqual({ latitude: 48.8566, longitude: 2.3522 });
    });
  });

  describe("frontendDestinationToApi", () => {
    const baseFrontendDestination: Destination = {
      activities: ["sightseeing", "museums"],
      coordinates: { latitude: 48.8566, longitude: 2.3522 },
      country: "France",
      endDate: "2025-06-05",
      estimatedCost: 1000,
      id: "dest-123",
      name: "Paris",
      startDate: "2025-06-01",
    };

    it("should convert frontend destination to API format", () => {
      const result = frontendDestinationToApi(baseFrontendDestination);

      expect(result).toEqual({
        arrival_date: "2025-06-01",
        city: "France", // Uses country as city fallback
        coordinates: { latitude: 48.8566, longitude: 2.3522 },
        country: "France",
        departure_date: "2025-06-05",
        name: "Paris",
      });
    });

    it("should handle missing optional fields", () => {
      const minimalDestination: Destination = {
        country: "Italy",
        id: "dest-minimal",
        name: "Rome",
      };

      const result = frontendDestinationToApi(minimalDestination);

      expect(result).toEqual({
        arrival_date: undefined,
        city: "Italy", // Uses country as city fallback
        coordinates: undefined,
        country: "Italy",
        departure_date: undefined,
        name: "Rome",
      });
    });

    it("should preserve coordinates", () => {
      const result = frontendDestinationToApi(baseFrontendDestination);

      expect(result.coordinates).toEqual({ latitude: 48.8566, longitude: 2.3522 });
    });
  });

  describe("normalizeTrip", () => {
    it("should normalize trip with complete data", () => {
      const partialTrip: Partial<Trip> = {
        budget: 2000,
        created_at: "2025-01-01T00:00:00Z",
        currency: "EUR",
        description: "Test description",
        destinations: [
          {
            country: "France",
            id: "dest-1",
            name: "Paris",
          },
        ],
        end_date: "2025-06-15",
        id: "trip-123",
        preferences: { test: "value" },
        start_date: "2025-06-01",
        status: "confirmed",
        tags: ["fun"],
        title: "Test Trip",
        updated_at: "2025-01-01T12:00:00Z",
        visibility: "public",
      };

      const result = normalizeTrip(partialTrip);

      expect(result).toEqual({
        budget: 2000,
        created_at: "2025-01-01T00:00:00Z",
        createdAt: "2025-01-01T00:00:00Z",
        currency: "EUR",
        description: "Test description",
        destinations: partialTrip.destinations,
        end_date: "2025-06-15",
        endDate: "2025-06-15",
        id: "trip-123",
        isPublic: true,
        name: "Test Trip",
        preferences: { test: "value" },
        start_date: "2025-06-01",
        startDate: "2025-06-01",
        status: "confirmed",
        tags: ["fun"],
        title: "Test Trip",
        updated_at: "2025-01-01T12:00:00Z",
        updatedAt: "2025-01-01T12:00:00Z",
        visibility: "public",
      });
    });

    it("should provide defaults for missing fields", () => {
      const emptyTrip: Partial<Trip> = {};

      const result = normalizeTrip(emptyTrip);

      expect(result.id).toBe("");
      expect(result.name).toBe("Untitled Trip");
      expect(result.title).toBe("Untitled Trip");
      expect(result.description).toBe("");
      expect(result.start_date).toBe("");
      expect(result.end_date).toBe("");
      expect(result.startDate).toBe("");
      expect(result.endDate).toBe("");
      expect(result.destinations).toEqual([]);
      expect(result.budget).toBe(0);
      expect(result.currency).toBe("USD");
      expect(result.visibility).toBe("private");
      expect(result.isPublic).toBe(false);
      expect(result.tags).toEqual([]);
      expect(result.preferences).toEqual({});
      expect(result.status).toBe("planning");
      expect(result.created_at).toMatch(
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/
      );
      expect(result.updated_at).toMatch(
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/
      );
      expect(result.createdAt).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
      expect(result.updatedAt).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
    });

    it("should prefer snake_case fields over camelCase", () => {
      const tripWithBothFormats: Partial<Trip> = {
        created_at: "2025-01-01T00:00:00Z",
        createdAt: "2025-02-01T00:00:00Z",
        start_date: "2025-07-01",
        startDate: "2025-06-01",
      };

      const result = normalizeTrip(tripWithBothFormats);

      // According to implementation: start_date || startDate
      expect(result.start_date).toBe("2025-07-01");
      // According to implementation: startDate || start_date
      expect(result.startDate).toBe("2025-06-01");
      expect(result.created_at).toBe("2025-01-01T00:00:00Z");
      // According to implementation: createdAt || created_at
      expect(result.createdAt).toBe("2025-02-01T00:00:00Z");
    });

    it("should set isPublic based on visibility", () => {
      const publicTrip = normalizeTrip({ visibility: "public" });
      const privateTrip = normalizeTrip({
        visibility: "private",
      });
      const sharedTrip = normalizeTrip({ visibility: "shared" });

      expect(publicTrip.isPublic).toBe(true);
      expect(privateTrip.isPublic).toBe(false);
      expect(sharedTrip.isPublic).toBe(false);
    });

    it("should handle legacy isPublic field", () => {
      const tripWithIsPublic = normalizeTrip({ isPublic: true });

      expect(tripWithIsPublic.isPublic).toBe(true);
      expect(tripWithIsPublic.visibility).toBe("private"); // Default visibility
    });
  });

  describe("createEmptyTrip", () => {
    it("should create empty trip with defaults", () => {
      const result = createEmptyTrip();

      expect(result.id).toBe("");
      expect(result.name).toBe("New Trip");
      expect(result.title).toBe("New Trip");
      expect(result.description).toBe("");
      expect(result.start_date).toBe("");
      expect(result.end_date).toBe("");
      expect(result.startDate).toBe("");
      expect(result.endDate).toBe("");
      expect(result.destinations).toEqual([]);
      expect(result.budget).toBe(0);
      expect(result.currency).toBe("USD");
      expect(result.visibility).toBe("private");
      expect(result.isPublic).toBe(false);
      expect(result.tags).toEqual([]);
      expect(result.preferences).toEqual({});
      expect(result.status).toBe("planning");
      expect(result.created_at).toMatch(
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/
      );
      expect(result.updated_at).toMatch(
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/
      );
      expect(result.createdAt).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
      expect(result.updatedAt).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
    });

    it("should apply overrides to default trip", () => {
      const overrides: Partial<Trip> = {
        budget: 5000,
        currency: "EUR",
        name: "Custom Trip",
        tags: ["adventure"],
        visibility: "public",
      };

      const result = createEmptyTrip(overrides);

      expect(result.name).toBe("Custom Trip");
      expect(result.title).toBe("New Trip"); // Still "New Trip" because title wasn't overridden
      expect(result.budget).toBe(5000);
      expect(result.currency).toBe("EUR");
      expect(result.visibility).toBe("public");
      expect(result.isPublic).toBe(true); // Derived from visibility
      expect(result.tags).toEqual(["adventure"]);
    });

    it("should generate consistent timestamps", () => {
      const trip1 = createEmptyTrip();
      const trip2 = createEmptyTrip();

      // Timestamps should be close but not necessarily identical
      const createdAt1 = trip1.created_at ?? "";
      const createdAt2 = trip2.created_at ?? "";
      const time1 = new Date(createdAt1).getTime();
      const time2 = new Date(createdAt2).getTime();
      expect(Math.abs(time1 - time2)).toBeLessThan(1000); // Within 1 second
    });
  });

  describe("validateTripForApi", () => {
    const validTrip: Trip = {
      destinations: [
        {
          country: "France",
          id: "dest-1",
          name: "Paris",
        },
      ],
      end_date: "2025-06-15",
      id: "trip-123",
      name: "Valid Trip",
      start_date: "2025-06-01",
      title: "Valid Trip",
    };

    it("should validate a complete valid trip", () => {
      const result = validateTripForApi(validTrip);

      expect(result.valid).toBe(true);
      expect(result.errors).toEqual([]);
    });

    it("should require name or title", () => {
      const tripWithoutName = { ...validTrip, name: "", title: undefined };
      const result = validateTripForApi(tripWithoutName);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain("Trip must have a name or title");
    });

    it("should require start date", () => {
      const tripWithoutStartDate = {
        ...validTrip,
        start_date: undefined,
        startDate: undefined,
      };
      const result = validateTripForApi(tripWithoutStartDate);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain("Trip must have a start date");
    });

    it("should require end date", () => {
      const tripWithoutEndDate = {
        ...validTrip,
        end_date: undefined,
        endDate: undefined,
      };
      const result = validateTripForApi(tripWithoutEndDate);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain("Trip must have an end date");
    });

    it("should validate end date is after start date", () => {
      const tripWithInvalidDates = {
        ...validTrip,
        end_date: "2025-06-01", // End before start
        start_date: "2025-06-15",
      };
      const result = validateTripForApi(tripWithInvalidDates);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain("End date must be after start date");
    });

    it("should validate end date equal to start date", () => {
      const tripWithSameDates = {
        ...validTrip,
        end_date: "2025-06-01", // Same dates
        start_date: "2025-06-01",
      };
      const result = validateTripForApi(tripWithSameDates);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain("End date must be after start date");
    });

    it("should require at least one destination", () => {
      const tripWithoutDestinations = { ...validTrip, destinations: [] };
      const result = validateTripForApi(tripWithoutDestinations);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain("Trip must have at least one destination");
    });

    it("should accumulate multiple validation errors", () => {
      const invalidTrip: Trip = {
        destinations: [], // No destinations
        end_date: "2025-06-01", // End before start
        id: "trip-invalid",
        name: "", // Empty name
        start_date: "2025-06-15",
      };

      const result = validateTripForApi(invalidTrip);

      expect(result.valid).toBe(false);
      expect(result.errors).toHaveLength(3);
      expect(result.errors).toContain("Trip must have a name or title");
      expect(result.errors).toContain("End date must be after start date");
      expect(result.errors).toContain("Trip must have at least one destination");
    });

    it("should work with camelCase date fields", () => {
      const tripWithCamelCaseDates = {
        ...validTrip,
        end_date: undefined,
        endDate: "2025-06-15",
        start_date: undefined,
        startDate: "2025-06-01",
      };

      const result = validateTripForApi(tripWithCamelCaseDates);

      expect(result.valid).toBe(true);
      expect(result.errors).toEqual([]);
    });

    it("should handle invalid date strings gracefully", () => {
      const tripWithInvalidDates = {
        ...validTrip,
        end_date: "another-invalid-date",
        start_date: "invalid-date",
      };

      const result = validateTripForApi(tripWithInvalidDates);

      // Should not crash, but might have validation issues
      expect(result).toBeDefined();
      expect(typeof result.valid).toBe("boolean");
      expect(Array.isArray(result.errors)).toBe(true);
    });
  });

  describe("handleApiError", () => {
    it("should handle detailed error responses", () => {
      const error = {
        response: {
          data: {
            detail: "Invalid trip data provided",
          },
        },
      };

      const result = handleApiError(error);

      expect(result).toBe("Invalid trip data provided");
    });

    it("should handle value_error type responses", () => {
      const error = {
        response: {
          data: {
            detail: {
              msg: "Start date must be in the future",
              type: "value_error",
            },
          },
        },
      };

      const result = handleApiError(error);

      expect(result).toBe("Validation error: Start date must be in the future");
    });

    it("should handle value_error without message", () => {
      const error = {
        response: {
          data: {
            detail: {
              type: "value_error",
            },
          },
        },
      };

      const result = handleApiError(error);

      expect(result).toBe("Validation error: Invalid data format");
    });

    it("should handle array of error details", () => {
      const error = {
        response: {
          data: {
            detail: [
              { msg: "Title is required" },
              { msg: "Start date is invalid" },
              "End date must be after start date",
            ],
          },
        },
      };

      const result = handleApiError(error);

      expect(result).toBe(
        "Title is required, Start date is invalid, End date must be after start date"
      );
    });

    it("should handle simple error messages", () => {
      const error = {
        message: "Network error occurred",
      };

      const result = handleApiError(error);

      expect(result).toBe("Network error occurred");
    });

    it("should handle unknown error format", () => {
      const error = {
        someUnknownProperty: "some value",
      };

      const result = handleApiError(error);

      expect(result).toBe("An unexpected error occurred");
    });

    it("should handle null/undefined errors", () => {
      expect(handleApiError(null)).toBe("An unexpected error occurred");
      expect(handleApiError(undefined)).toBe("An unexpected error occurred");
    });

    it("should handle string errors", () => {
      const result = handleApiError("Simple string error");

      expect(result).toBe("An unexpected error occurred");
    });
  });

  describe("Property-based testing", () => {
    const generateRandomTrip = (): Partial<Trip> => ({
      budget: Math.floor(Math.random() * 10000),
      end_date: new Date(
        Date.now() + Math.random() * 365 * 24 * 60 * 60 * 1000 + 24 * 60 * 60 * 1000
      )
        .toISOString()
        .split("T")[0],
      id: `trip-${Math.random().toString(36).substr(2, 9)}`,
      start_date: new Date(Date.now() + Math.random() * 365 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split("T")[0],
      tags: Array.from(
        { length: Math.floor(Math.random() * 5) },
        () => `tag-${Math.random().toString(36).substr(2, 5)}`
      ),
      title: `Trip ${Math.random().toString(36).substr(2, 9)}`,
      visibility: Math.random() > 0.5 ? "public" : ("private" as const),
    });

    it("should maintain data integrity through conversion cycles", () => {
      for (let i = 0; i < 10; i++) {
        const originalTrip = generateRandomTrip();
        const normalized = normalizeTrip(originalTrip);
        const apiFormat = frontendTripToApi(normalized);

        // Core fields should be preserved
        expect(apiFormat.title).toBe(normalized.title);
        expect(apiFormat.budget).toBe(normalized.budget);
        expect(apiFormat.visibility).toBe(normalized.visibility);
        expect(apiFormat.tags).toEqual(normalized.tags);
      }
    });

    it("should handle various destination configurations", () => {
      const generateDestination = (): ApiDestination => ({
        coordinates:
          Math.random() > 0.5
            ? {
                latitude: (Math.random() - 0.5) * 180,
                longitude: (Math.random() - 0.5) * 360,
              }
            : undefined,
        country:
          Math.random() > 0.5
            ? `Country-${Math.random().toString(36).substr(2, 5)}`
            : undefined,
        name: `City-${Math.random().toString(36).substr(2, 5)}`,
      });

      for (let i = 0; i < 10; i++) {
        const apiDestination = generateDestination();
        const frontendDestination = apiDestinationToFrontend(apiDestination);
        const backToApi = frontendDestinationToApi(frontendDestination);

        // Core data should be preserved
        expect(backToApi.name).toBe(apiDestination.name);
        expect(backToApi.coordinates).toEqual(apiDestination.coordinates);
      }
    });
  });

  describe("Edge Cases and Error Handling", () => {
    it("should handle extremely large datasets", () => {
      const largeTrip: ApiTrip = {
        created_at: "2025-01-01T00:00:00Z",
        destinations: Array.from({ length: 1000 }, (_, i) => ({
          country: `Country ${i}`,
          name: `Destination ${i}`,
        })),
        end_date: "2025-06-15",
        id: "large-trip",
        preferences: {},
        start_date: "2025-06-01",
        status: "planning",
        tags: Array.from({ length: 100 }, (_, i) => `tag-${i}`),
        title: "Large Trip",
        updated_at: "2025-01-01T00:00:00Z",
        user_id: "user-123",
        visibility: "private",
      };

      const result = apiTripToFrontend(largeTrip);

      expect(result.destinations).toHaveLength(1000);
      expect(result.tags).toHaveLength(100);
      expect(result.destinations[0].id).toMatch(/^Destination 0-\d+$/);
      expect(result.destinations[999].name).toBe("Destination 999");
    });

    it("should handle malformed coordinate data", () => {
      const destinationWithBadCoords: ApiDestination = {
        coordinates: {
          latitude: Number.NaN,
          longitude: Number.POSITIVE_INFINITY,
        },
        name: "Bad Coords City",
      };

      const result = apiDestinationToFrontend(destinationWithBadCoords);

      expect(result.coordinates).toEqual({
        latitude: Number.NaN,
        longitude: Number.POSITIVE_INFINITY,
      });
      // Should not crash, even with invalid coordinates
      expect(result.name).toBe("Bad Coords City");
    });

    it("should handle circular reference in preferences", () => {
      type CircularType = { a: number; self?: CircularType };
      const circularRef: CircularType = { a: 1 };
      circularRef.self = circularRef;

      const tripWithCircularRef: ApiTrip = {
        created_at: "2025-01-01T00:00:00Z",
        destinations: [],
        end_date: "2025-06-15",
        id: "circular-trip",
        preferences: circularRef,
        start_date: "2025-06-01",
        status: "planning",
        tags: [],
        title: "Circular Trip",
        updated_at: "2025-01-01T00:00:00Z",
        user_id: "user-123",
        visibility: "private",
      };

      // Should not crash even with circular references
      expect(() => {
        apiTripToFrontend(tripWithCircularRef);
      }).not.toThrow();
    });

    it("should handle null and undefined values in nested objects", () => {
      const tripWithNulls: Partial<Trip> = {
        destinations: null as unknown as Trip["destinations"],
        id: null as unknown as Trip["id"],
        preferences: null as unknown as Trip["preferences"],
        tags: undefined,
        title: undefined,
      };

      const result = normalizeTrip(tripWithNulls);

      expect(result.id).toBe("");
      expect(result.title).toBe("Untitled Trip");
      expect(result.destinations).toEqual([]);
      expect(result.tags).toEqual([]);
      expect(result.preferences).toEqual({});
    });

    it("should handle special characters in trip names and descriptions", () => {
      const specialCharsTrip: ApiTrip = {
        created_at: "2025-01-01T00:00:00Z",
        description: "Description with\nnewlines\tand\ttabs\r\nand more 特殊字符",
        destinations: [
          {
            name: "Pàris with àccents 巴黎",
          },
        ],
        end_date: "2025-06-15",
        id: "special-trip",
        preferences: {},
        start_date: "2025-06-01",
        status: "planning",
        tags: ["🏖️", "spécial", "中文标签"],
        title: "🌍 Trip with émojis & spëcial chârs! 中文",
        updated_at: "2025-01-01T00:00:00Z",
        user_id: "user-123",
        visibility: "private",
      };

      const result = apiTripToFrontend(specialCharsTrip);

      expect(result.title).toBe("🌍 Trip with émojis & spëcial chârs! 中文");
      expect(result.description).toBe(
        "Description with\nnewlines\tand\ttabs\r\nand more 特殊字符"
      );
      expect(result.destinations[0].name).toBe("Pàris with àccents 巴黎");
      expect(result.tags).toEqual(["🏖️", "spécial", "中文标签"]);
    });

    it("should handle extremely long strings", () => {
      const longString = "a".repeat(10000);
      const tripWithLongStrings: ApiTrip = {
        created_at: "2025-01-01T00:00:00Z",
        description: longString,
        destinations: [
          {
            country: longString,
            name: longString,
          },
        ],
        end_date: "2025-06-15",
        id: "long-trip",
        preferences: { longKey: longString },
        start_date: "2025-06-01",
        status: "planning",
        tags: [longString],
        title: longString,
        updated_at: "2025-01-01T00:00:00Z",
        user_id: "user-123",
        visibility: "private",
      };

      const result = apiTripToFrontend(tripWithLongStrings);

      expect(result.title).toBe(longString);
      expect(result.description).toBe(longString);
      expect(result.destinations[0].name).toBe(longString);
      expect(result.tags?.[0]).toBe(longString);
    });
  });

  describe("Performance Testing", () => {
    it("should handle conversions efficiently", () => {
      const startTime = performance.now();

      for (let i = 0; i < 1000; i++) {
        const trip: ApiTrip = {
          created_at: "2025-01-01T00:00:00Z",
          destinations: Array.from({ length: 10 }, (_, j) => ({
            country: `Country ${j}`,
            name: `Destination ${j}`,
          })),
          end_date: "2025-06-15",
          id: `trip-${i}`,
          preferences: { key: `value-${i}` },
          start_date: "2025-06-01",
          status: "planning",
          tags: [`tag-${i}`],
          title: `Trip ${i}`,
          updated_at: "2025-01-01T00:00:00Z",
          user_id: "user-123",
          visibility: "private",
        };

        apiTripToFrontend(trip);
      }

      const endTime = performance.now();
      const duration = endTime - startTime;

      // Should complete 1000 conversions in reasonable time (< 1 second)
      expect(duration).toBeLessThan(1000);
    });

    it("should handle validation efficiently", () => {
      const trips = Array.from({ length: 1000 }, (_, i) =>
        createEmptyTrip({
          destinations: [{ country: "Test", id: "dest-1", name: "Test" }],
          end_date: "2025-06-15",
          id: `trip-${i}`,
          start_date: "2025-06-01",
          title: `Trip ${i}`,
        })
      );

      const startTime = performance.now();

      for (const trip of trips) {
        validateTripForApi(trip);
      }

      const endTime = performance.now();
      const duration = endTime - startTime;

      // Should validate 1000 trips quickly
      expect(duration).toBeLessThan(500);
    });
  });

  describe("Backward Compatibility", () => {
    it("should handle legacy trip format", () => {
      // Simulate old trip format that might exist in storage
      type LegacyTrip = {
        destinations: Partial<Trip>["destinations"];
        endDate: string;
        id: string;
        isPublic: boolean;
        name: string;
        startDate: string;
      };
      const legacyTrip: LegacyTrip = {
        destinations: [
          {
            country: "France",
            id: "dest-1",
            name: "Paris",
          },
        ],
        endDate: "2025-06-15",
        id: "legacy-trip",
        isPublic: true, // Old format used boolean instead of visibility enum
        name: "Legacy Trip", // Old format used 'name' instead of 'title'
        startDate: "2025-06-01", // Old format used camelCase
      };

      const normalized = normalizeTrip(legacyTrip);

      expect(normalized.title).toBe("Legacy Trip");
      expect(normalized.name).toBe("Legacy Trip");
      expect(normalized.start_date).toBe("2025-06-01");
      expect(normalized.startDate).toBe("2025-06-01");
      expect(normalized.isPublic).toBe(true);
      expect(normalized.visibility).toBe("private"); // Default, not derived from isPublic
    });

    it("should handle mixed date formats", () => {
      const mixedTrip: Partial<Trip> = {
        created_at: "2025-01-01T00:00:00Z",
        endDate: "2025-06-15", // Mixed formats
        start_date: "2025-06-01",
        updatedAt: "2025-01-01T12:00:00Z", // Mixed formats
      };

      const normalized = normalizeTrip(mixedTrip);

      expect(normalized.start_date).toBe("2025-06-01");
      expect(normalized.startDate).toBe("2025-06-01");
      expect(normalized.end_date).toBe("2025-06-15");
      expect(normalized.endDate).toBe("2025-06-15");
      expect(normalized.created_at).toBe("2025-01-01T00:00:00Z");
      expect(normalized.createdAt).toBe("2025-01-01T00:00:00Z");
      expect(normalized.updated_at).toBe("2025-01-01T12:00:00Z");
      expect(normalized.updatedAt).toBe("2025-01-01T12:00:00Z");
    });
  });
});

describe("formatTripDate", () => {
  it("should format valid date strings", () => {
    // Date-only strings are formatted deterministically (no TZ shift)
    expect(formatTripDate("2025-06-01")).toBe("Jun 1, 2025");
    expect(formatTripDate("2025-12-25")).toBe("Dec 25, 2025");
    expect(formatTripDate("2025-01-01")).toBe("Jan 1, 2025");
  });

  it("should handle ISO datetime strings", () => {
    expect(formatTripDate("2025-06-01T10:30:00Z")).toBe("Jun 1, 2025");
    expect(formatTripDate("2025-06-01T10:30:00.000Z")).toBe("Jun 1, 2025");
  });

  it("should return empty string for empty input", () => {
    expect(formatTripDate("")).toBe("");
  });

  it("should return 'Invalid Date' for invalid dates", () => {
    expect(formatTripDate("invalid-date")).toBe("Invalid Date");
    expect(formatTripDate("2025-13-45")).toBe("Invalid Date");
    expect(formatTripDate("not-a-date")).toBe("Invalid Date");
  });

  it("should handle edge cases", () => {
    // Year 0000 is treated as invalid for determinism
    expect(formatTripDate("0000-01-01")).toBe("Invalid Date");
    expect(formatTripDate("9999-12-31")).toBe("Dec 31, 9999");
  });
});

describe("calculateTripDuration", () => {
  it("should calculate duration between valid dates", () => {
    expect(calculateTripDuration("2025-06-01", "2025-06-15")).toBe(14);
    expect(calculateTripDuration("2025-06-01", "2025-06-02")).toBe(1);
    expect(calculateTripDuration("2025-06-01", "2025-06-01")).toBe(0);
  });

  it("should handle datetime strings", () => {
    expect(calculateTripDuration("2025-06-01T00:00:00Z", "2025-06-02T23:59:59Z")).toBe(
      2
    );
    expect(calculateTripDuration("2025-06-01T12:00:00Z", "2025-06-02T11:59:59Z")).toBe(
      1
    );
  });

  it("should handle reverse order dates", () => {
    // Should calculate absolute difference
    expect(calculateTripDuration("2025-06-15", "2025-06-01")).toBe(14);
  });

  it("should return 0 for empty or missing dates", () => {
    expect(calculateTripDuration("", "2025-06-15")).toBe(0);
    expect(calculateTripDuration("2025-06-01", "")).toBe(0);
    expect(calculateTripDuration("", "")).toBe(0);
  });

  it("should return NaN for invalid dates", () => {
    // Invalid dates result in NaN due to JavaScript Date behavior
    // The current implementation doesn't handle this properly
    expect(Number.isNaN(calculateTripDuration("invalid-date", "2025-06-15"))).toBe(
      true
    );
    expect(Number.isNaN(calculateTripDuration("2025-06-01", "invalid-date"))).toBe(
      true
    );
    expect(Number.isNaN(calculateTripDuration("invalid", "also-invalid"))).toBe(true);
  });

  it("should handle leap years correctly", () => {
    expect(calculateTripDuration("2024-02-28", "2024-03-01")).toBe(2); // 2024 is leap year
    expect(calculateTripDuration("2025-02-28", "2025-03-01")).toBe(1); // 2025 is not leap year
  });

  it("should handle year boundaries", () => {
    expect(calculateTripDuration("2024-12-31", "2025-01-01")).toBe(1);
    expect(calculateTripDuration("2024-12-01", "2025-01-01")).toBe(31);
  });

  it("should handle large date ranges", () => {
    expect(calculateTripDuration("2025-01-01", "2026-01-01")).toBe(365);
    expect(calculateTripDuration("2024-01-01", "2025-01-01")).toBe(366); // 2024 is leap year
  });
});
