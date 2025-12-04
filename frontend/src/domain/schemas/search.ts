/**
 * @fileoverview Search functionality schemas with validation.
 * Includes search parameters, results, filters, and form validation for flights, accommodations, activities, and destinations.
 */

import { z } from "zod";
import { propertyTypeSchema } from "./accommodations";
import { CABIN_CLASS_ENUM } from "./flights";
import { primitiveSchemas } from "./registry";
import { CURRENCY_CODE_SCHEMA } from "./shared/money";
import { ISO_DATE_STRING } from "./shared/time";

// ===== CORE SCHEMAS =====
// Core business logic schemas for search functionality

// Base validation helpers
const COORDINATES_SCHEMA = z.object({
  lat: z.number().min(-90).max(90),
  lng: z.number().min(-180).max(180),
});

const DATE_STRING_SCHEMA = ISO_DATE_STRING;
const POSITIVE_INT_SCHEMA = z.number().int().positive();
const NON_NEGATIVE_INT_SCHEMA = z.number().int().nonnegative();

/**
 * Zod schema for base search parameters shared across search types.
 * Includes common fields like dates, destination, and passenger counts.
 */
export const baseSearchParamsSchema = z.object({
  adults: POSITIVE_INT_SCHEMA.max(20, { error: "Too many adults" }),
  children: NON_NEGATIVE_INT_SCHEMA.max(20, { error: "Too many children" }),
  destination: z.string().min(1, { error: "Destination is required" }),
  endDate: DATE_STRING_SCHEMA,
  infants: NON_NEGATIVE_INT_SCHEMA.max(20, { error: "Too many infants" }),
  startDate: DATE_STRING_SCHEMA,
});

/** TypeScript type for base search parameters. */
export type BaseSearchParams = z.infer<typeof baseSearchParamsSchema>;

/**
 * Zod schema for flight-specific search parameters.
 * Includes cabin class, airline preferences, and routing options.
 */
export const flightSearchParamsSchema = z.object({
  adults: POSITIVE_INT_SCHEMA.max(20).optional(),
  cabinClass: CABIN_CLASS_ENUM.optional(),
  children: NON_NEGATIVE_INT_SCHEMA.max(20).optional(),
  departureDate: DATE_STRING_SCHEMA.optional(),
  destination: z.string().optional(),
  directOnly: z.boolean().optional(),
  excludedAirlines: z.array(z.string()).optional(),
  infants: NON_NEGATIVE_INT_SCHEMA.max(20).optional(),
  maxStops: z.number().int().nonnegative().max(3).optional(),
  origin: z.string().optional(),
  passengers: z
    .object({
      adults: POSITIVE_INT_SCHEMA.max(20),
      children: NON_NEGATIVE_INT_SCHEMA.max(20),
      infants: NON_NEGATIVE_INT_SCHEMA.max(20),
    })
    .optional(),
  preferredAirlines: z.array(z.string()).optional(),
  returnDate: DATE_STRING_SCHEMA.optional(),
});

/** TypeScript type for flight search parameters. */
export type FlightSearchParams = z.infer<typeof flightSearchParamsSchema>;

/**
 * Zod schema for accommodation-specific search parameters.
 * Includes property type, amenities, price range, and rating filters.
 */
export const searchAccommodationParamsSchema = z.object({
  adults: POSITIVE_INT_SCHEMA.max(20).optional(),
  amenities: z.array(z.string()).optional(),
  checkIn: DATE_STRING_SCHEMA.optional(),
  checkOut: DATE_STRING_SCHEMA.optional(),
  children: NON_NEGATIVE_INT_SCHEMA.max(20).optional(),
  currency: CURRENCY_CODE_SCHEMA.optional(),
  destination: z.string().optional(),
  infants: NON_NEGATIVE_INT_SCHEMA.max(20).optional(),
  minRating: z.number().min(0).max(5).optional(),
  priceRange: z
    .object({
      max: z.number().positive().optional(),
      min: z.number().nonnegative().optional(),
    })
    .refine((data) => !data.min || !data.max || data.min <= data.max, {
      error: "Min price must be less than or equal to max price",
    })
    .optional(),
  propertyType: z.enum(propertyTypeSchema.options as [string, ...string[]]).optional(),
  propertyTypes: z.array(propertyTypeSchema).optional(),
  rooms: POSITIVE_INT_SCHEMA.max(20, { error: "Too many rooms" }).optional(),
});

/** TypeScript type for accommodation search parameters. */
export type SearchAccommodationParams = z.infer<typeof searchAccommodationParamsSchema>;

/**
 * Zod schema for activity-specific search parameters.
 * Includes difficulty level, duration range, and category filters.
 */
export const activitySearchParamsSchema = z.object({
  adults: POSITIVE_INT_SCHEMA.max(20).optional(),
  category: z.string().optional(),
  children: NON_NEGATIVE_INT_SCHEMA.max(20).optional(),
  date: DATE_STRING_SCHEMA.optional(),
  dateRange: z
    .object({
      end: DATE_STRING_SCHEMA.optional(),
      start: DATE_STRING_SCHEMA.optional(),
    })
    .refine(
      (data) => !data.start || !data.end || new Date(data.end) > new Date(data.start),
      {
        error: "End date must be after start date",
        path: ["end"],
      }
    )
    .optional(),
  destination: z.string().min(1, { error: "destination is required" }),
  difficulty: z.enum(["easy", "moderate", "challenging", "extreme"]).optional(),
  duration: z
    .object({
      max: z.number().positive().optional(),
      min: z.number().positive().optional(),
    })
    .refine((data) => !data.min || !data.max || data.min <= data.max, {
      error: "Min duration must be less than or equal to max duration",
    })
    .optional(),
  indoor: z.boolean().optional(),
  infants: NON_NEGATIVE_INT_SCHEMA.max(20).optional(),
  priceRange: z
    .object({
      max: z.number().positive().optional(),
      min: z.number().min(0).optional(),
    })
    .refine((data) => !data.min || !data.max || data.min <= data.max, {
      error: "Min price must be less than or equal to max price",
      path: ["min"],
    })
    .optional(),
});

/** TypeScript type for activity search parameters. */
export type ActivitySearchParams = z.infer<typeof activitySearchParamsSchema>;

/**
 * Zod schema for destination-specific search parameters.
 * Includes location components, language, and result type filters.
 */
export const destinationSearchParamsSchema = z.object({
  components: z
    .object({
      country: z.array(z.string()).optional(),
    })
    .optional(),
  language: z.string().min(2).max(3).optional(),
  limit: z.number().int().positive().max(100).optional(),
  query: z.string().min(1, { error: "Search query is required" }),
  region: z.string().optional(),
  types: z
    .array(z.enum(["locality", "country", "administrative_area", "establishment"]))
    .optional(),
});

/** TypeScript type for destination search parameters. */
export type DestinationSearchParams = z.infer<typeof destinationSearchParamsSchema>;

/**
 * Zod schema for union of all search parameter types.
 * Supports flight, accommodation, activity, and destination searches.
 */
export const searchParamsSchema = z.union([
  flightSearchParamsSchema,
  searchAccommodationParamsSchema,
  activitySearchParamsSchema,
  destinationSearchParamsSchema,
]);

/** TypeScript type for search parameters. */
export type SearchParams = z.infer<typeof searchParamsSchema>;

/**
 * Zod schema for search type enumeration.
 * Defines supported search categories.
 */
export const searchTypeSchema = z.enum([
  "flight",
  "accommodation",
  "activity",
  "destination",
]);

/** TypeScript type for search types. */
export type SearchType = z.infer<typeof searchTypeSchema>;

/**
 * Zod schema for flight search results.
 * Includes airline, timing, pricing, and routing information.
 */
export const flightSchema = z.object({
  airline: z.string().min(1),
  arrivalTime: DATE_STRING_SCHEMA,
  cabinClass: z.string(),
  departureTime: DATE_STRING_SCHEMA,
  destination: z.string().min(1),
  duration: POSITIVE_INT_SCHEMA,
  flightNumber: z.string().min(1),
  id: z.string().min(1),
  layovers: z
    .array(
      z.object({
        airport: z.string().min(1),
        duration: POSITIVE_INT_SCHEMA,
      })
    )
    .optional(),
  origin: z.string().min(1),
  price: z.number().positive(),
  seatsAvailable: NON_NEGATIVE_INT_SCHEMA,
  stops: NON_NEGATIVE_INT_SCHEMA,
});

/** TypeScript type for flight search results. */
export type Flight = z.infer<typeof flightSchema>;

/**
 * Zod schema for accommodation search results.
 * Includes property details, pricing, amenities, and location information.
 */
export const accommodationSchema = z.object({
  amenities: z.array(z.string()),
  checkIn: DATE_STRING_SCHEMA,
  checkOut: DATE_STRING_SCHEMA,
  coordinates: COORDINATES_SCHEMA.optional(),
  id: z.string().min(1),
  images: z.array(primitiveSchemas.url).optional(),
  location: z.string().min(1),
  name: z.string().min(1),
  pricePerNight: z.number().positive(),
  rating: z.number().min(0).max(5),
  totalPrice: z.number().positive(),
  type: z.string().min(1),
});

/** TypeScript type for accommodation search results. */
export type Accommodation = z.infer<typeof accommodationSchema>;

/**
 * Zod schema for activity search results.
 * Includes activity details, pricing, duration, and location information.
 */
export const activitySchema = z.object({
  coordinates: COORDINATES_SCHEMA.optional(),
  date: DATE_STRING_SCHEMA,
  description: z.string(),
  duration: POSITIVE_INT_SCHEMA,
  id: z.string().min(1),
  images: z.array(primitiveSchemas.url).optional(),
  location: z.string().min(1),
  name: z.string().min(1),
  price: z.number().nonnegative(),
  rating: z.number().min(0).max(5),
  type: z.string().min(1),
});

/** TypeScript type for activity search results. */
export type Activity = z.infer<typeof activitySchema>;

/**
 * Zod schema for destination search results.
 * Includes location details, attractions, climate, and metadata.
 */
export const destinationSchema = z.object({
  attractions: z.array(z.string()).optional(),
  bestTimeToVisit: z.array(z.string()).optional(),
  climate: z
    .object({
      averageTemp: z.number(),
      rainfall: z.number().nonnegative(),
      season: z.string(),
    })
    .optional(),
  coordinates: COORDINATES_SCHEMA,
  country: z.string().optional(),
  description: z.string(),
  formattedAddress: z.string().min(1),
  id: z.string().min(1),
  name: z.string().min(1),
  photos: z.array(primitiveSchemas.url).optional(),
  placeId: z.string().optional(),
  popularityScore: z.number().min(0).max(10).optional(),
  rating: z.number().min(0).max(5).optional(),
  region: z.string().optional(),
  types: z.array(z.string()),
});

/** TypeScript type for destination search results. */
export type Destination = z.infer<typeof destinationSchema>;

/**
 * Zod schema for union of all search result types.
 * Supports flights, accommodations, activities, and destinations.
 */
export const searchResultSchema = z.union([
  flightSchema,
  accommodationSchema,
  activitySchema,
  destinationSchema,
]);

/** TypeScript type for search results. */
export type SearchResult = z.infer<typeof searchResultSchema>;

/**
 * Zod schema for search results grouped by type.
 * Organizes results into separate arrays for each search category.
 */
export const searchResultsSchema = z.object({
  accommodations: z.array(accommodationSchema).optional(),
  activities: z.array(activitySchema).optional(),
  destinations: z.array(destinationSchema).optional(),
  flights: z.array(flightSchema).optional(),
});

/** TypeScript type for grouped search results. */
export type SearchResults = z.infer<typeof searchResultsSchema>;

/**
 * Zod schema for saved search configurations.
 * Stores search parameters and metadata for reuse.
 */
export const savedSearchSchema = z.object({
  createdAt: DATE_STRING_SCHEMA,
  id: z.string().min(1),
  lastUsed: DATE_STRING_SCHEMA.optional(),
  name: z
    .string()
    .min(1, { error: "Search name is required" })
    .max(100, { error: "Name too long" }),
  params: searchParamsSchema,
  type: searchTypeSchema,
});

/** TypeScript type for saved searches. */
export type SavedSearch = z.infer<typeof savedSearchSchema>;

/**
 * Zod schema for filter values used in search filtering.
 * Supports strings, numbers, booleans, and arrays.
 */
export const filterValueSchema = z.union([
  z.string(),
  z.number(),
  z.boolean(),
  z.array(z.string()),
  z.array(z.number()),
]);

/** TypeScript type for filter values. */
export type FilterValue = z.infer<typeof filterValueSchema>;

/**
 * Zod schema for metadata values in search responses.
 * Supports various data types including nested objects.
 */
export const metadataValueSchema = z.union([
  z.string(),
  z.number(),
  z.boolean(),
  z.record(z.string(), z.unknown()),
]);

/** TypeScript type for metadata values. */
export type MetadataValue = z.infer<typeof metadataValueSchema>;

/**
 * Zod schema for search API response structure.
 * Includes results, filters, metadata, and pagination information.
 */
export const searchResponseSchema = z.object({
  filters: z.record(z.string(), filterValueSchema).optional(),
  metadata: z.record(z.string(), metadataValueSchema).optional(),
  results: searchResultsSchema,
  totalResults: NON_NEGATIVE_INT_SCHEMA,
});

/** TypeScript type for search API responses. */
export type SearchResponse = z.infer<typeof searchResponseSchema>;

/**
 * Zod schema for filter options in search UI.
 * Defines filter configuration with options and counts.
 */
export const filterOptionSchema = z.object({
  count: NON_NEGATIVE_INT_SCHEMA.optional(),
  id: z.string().min(1),
  label: z.string().min(1),
  options: z
    .array(
      z.object({
        count: NON_NEGATIVE_INT_SCHEMA.optional(),
        label: z.string().min(1),
        value: filterValueSchema,
      })
    )
    .optional(),
  type: z.enum(["checkbox", "radio", "range", "select"]),
  value: filterValueSchema,
});

/** TypeScript type for filter options. */
export type FilterOption = z.infer<typeof filterOptionSchema>;

/**
 * Zod schema for sort options in search UI.
 * Defines sorting configuration with direction and field.
 */
export const sortOptionSchema = z.object({
  direction: z.enum(["asc", "desc"]),
  id: z.string().min(1),
  label: z.string().min(1),
  value: z.string().min(1),
});

/** TypeScript type for sort options. */
export type SortOption = z.infer<typeof sortOptionSchema>;

// ===== FORM SCHEMAS =====
// UI form validation schemas with user-friendly error messages

// Common form validation patterns
const FUTURE_DATE_SCHEMA = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, { error: "Please enter a valid date (YYYY-MM-DD)" })
  .refine((date) => !Number.isNaN(new Date(date).getTime()), {
    error: "Please enter a valid date",
  })
  .refine((date) => new Date(date) > new Date(), {
    error: "Date must be in the future",
  });

/**
 * Form schema for flight search with validation.
 * Includes passenger details, routing preferences, and date validation.
 */
export const flightSearchFormSchema = z
  .object({
    cabinClass: z.enum(["economy", "premium_economy", "business", "first"]),
    departureDate: FUTURE_DATE_SCHEMA,
    destination: z.string().min(1, { error: "Destination is required" }),
    directOnly: z.boolean(),
    excludedAirlines: z.array(z.string()).optional(),
    maxStops: z.number().int().min(0).max(3).optional(),
    origin: z.string().min(1, { error: "Departure location is required" }),
    passengers: z.object({
      adults: z
        .number()
        .int()
        .min(1, { error: "At least 1 adult required" })
        .max(20, { error: "Too many passengers" }),
      children: z.number().int().min(0).max(20, { error: "Too many passengers" }),
      infants: z.number().int().min(0).max(20, { error: "Too many passengers" }),
    }),
    preferredAirlines: z.array(z.string()).optional(),
    returnDate: FUTURE_DATE_SCHEMA.optional(),
    tripType: z.enum(["round-trip", "one-way", "multi-city"]),
  })
  .refine(
    (data) => {
      if (data.tripType === "round-trip" && !data.returnDate) {
        return false;
      }
      return true;
    },
    {
      error: "Return date is required for round-trip flights",
      path: ["returnDate"],
    }
  )
  .refine(
    (data) => {
      if (data.returnDate && data.departureDate) {
        return new Date(data.returnDate) > new Date(data.departureDate);
      }
      return true;
    },
    {
      error: "Return date must be after departure date",
      path: ["returnDate"],
    }
  );

/** TypeScript type for flight search form data. */
export type FlightSearchFormData = z.infer<typeof flightSearchFormSchema>;

/**
 * Form schema for accommodation search with validation.
 * Includes guest details, dates, price range, and property filters.
 */
export const accommodationSearchFormSchema = z
  .object({
    amenities: z.array(z.string()).optional(),
    checkIn: FUTURE_DATE_SCHEMA,
    checkOut: FUTURE_DATE_SCHEMA,
    destination: z.string().min(1, { error: "Destination is required" }),
    guests: z.object({
      adults: z
        .number()
        .int()
        .min(1, { error: "At least 1 adult required" })
        .max(20, { error: "Too many guests" }),
      children: z.number().int().min(0).max(20, { error: "Too many guests" }),
      infants: z.number().int().min(0).max(20, { error: "Too many guests" }),
    }),
    minRating: z.number().min(0).max(5).optional(),
    priceRange: z
      .object({
        max: z
          .number()
          .positive({ error: "Maximum price must be positive" })
          .optional(),
        min: z
          .number()
          .min(0, { error: "Minimum price cannot be negative" })
          .optional(),
      })
      .refine(
        (data) => {
          if (data.min && data.max) {
            return data.min <= data.max;
          }
          return true;
        },
        {
          error: "Minimum price must be less than or equal to maximum price",
          path: ["min"],
        }
      )
      .optional(),
    propertyType: z
      .enum(["hotel", "apartment", "villa", "hostel", "resort"])
      .optional(),
    rooms: z
      .number()
      .int()
      .min(1, { error: "At least 1 room required" })
      .max(20, { error: "Too many rooms" }),
  })
  .refine((data) => new Date(data.checkOut) > new Date(data.checkIn), {
    error: "Check-out date must be after check-in date",
    path: ["checkOut"],
  });

/** TypeScript type for accommodation search form data. */
export type AccommodationSearchFormData = z.infer<typeof accommodationSearchFormSchema>;

/**
 * Form schema for activity search with validation.
 * Includes participant details, date ranges, difficulty, and price filters.
 */
export const activitySearchFormSchema = z.object({
  category: z.string().optional(),
  date: FUTURE_DATE_SCHEMA.optional(),
  dateRange: z
    .object({
      end: FUTURE_DATE_SCHEMA.optional(),
      start: FUTURE_DATE_SCHEMA.optional(),
    })
    .refine(
      (data) => {
        // Only validate if both dates are present
        if (data.start && data.end) {
          return new Date(data.end) > new Date(data.start);
        }
        return true;
      },
      {
        error: "End date must be after start date",
        path: ["end"],
      }
    )
    .optional(),
  destination: z.string().min(1, { error: "Destination is required" }),
  difficulty: z.enum(["easy", "moderate", "challenging", "extreme"]).optional(),
  duration: z
    .object({
      max: z.number().positive().optional(),
      min: z.number().positive().optional(),
    })
    .refine(
      (data) => {
        if (data.min && data.max) {
          return data.min <= data.max;
        }
        return true;
      },
      {
        error: "Minimum duration must be less than or equal to maximum duration",
        path: ["min"],
      }
    )
    .optional(),
  indoor: z.boolean().optional(),
  participants: z.object({
    adults: z
      .number()
      .int()
      .min(1, { error: "At least 1 adult required" })
      .max(50, { error: "Too many participants" }),
    children: z.number().int().min(0).max(50, { error: "Too many participants" }),
  }),
  priceRange: z
    .object({
      max: z.number().positive().optional(),
      min: z.number().min(0).optional(),
    })
    .refine(
      (data) => {
        if (data.min && data.max) {
          return data.min <= data.max;
        }
        return true;
      },
      {
        error: "Minimum price must be less than or equal to maximum price",
        path: ["min"],
      }
    )
    .optional(),
});

/** TypeScript type for activity search form data. */
export type ActivitySearchFormData = z.infer<typeof activitySearchFormSchema>;

/**
 * Form schema for hotel search with validation.
 * Includes guest details, dates, price range, amenities, and rating filters.
 * Date fields use FUTURE_DATE_SCHEMA to match database DATE type (YYYY-MM-DD).
 */
export const hotelSearchFormSchema = z
  .strictObject({
    adults: z.number().int().min(1, { error: "At least 1 adult required" }).max(6),
    amenities: z.array(z.string()),
    checkIn: FUTURE_DATE_SCHEMA,
    checkOut: FUTURE_DATE_SCHEMA,
    children: z.number().int().min(0).max(4),
    currency: CURRENCY_CODE_SCHEMA.optional(),
    location: z.string().min(1, { error: "Location is required" }),
    priceRange: z.strictObject({
      max: z.number().min(0),
      min: z.number().min(0),
    }),
    rating: z.number().int().min(0).max(5),
    rooms: z.number().int().min(1).max(5),
  })
  .refine((data) => new Date(data.checkOut) > new Date(data.checkIn), {
    error: "Check-out date must be after check-in date",
    path: ["checkOut"],
  })
  .refine(
    (data) => {
      if (data.priceRange.min && data.priceRange.max) {
        return data.priceRange.min <= data.priceRange.max;
      }
      return true;
    },
    {
      error: "Minimum price must be less than or equal to maximum price",
      path: ["priceRange", "min"],
    }
  );

/** TypeScript type for hotel search form data. */
export type HotelSearchFormData = z.infer<typeof hotelSearchFormSchema>;

/**
 * Form schema for destination search with validation.
 * Includes query, types, language, region, and limit filters.
 */
export const destinationSearchFormSchema = z.strictObject({
  language: z.string().optional(),
  limit: z
    .number()
    .int()
    .min(1, { error: "Limit must be at least 1" })
    .max(20, { error: "Limit must be at most 20" }),
  query: z.string().min(1, { error: "Destination is required" }),
  region: z.string().optional(),
  types: z.array(
    z.enum(["locality", "country", "administrative_area", "establishment"])
  ),
});

/** TypeScript type for destination search form data. */
export type DestinationSearchFormData = z.infer<typeof destinationSearchFormSchema>;

// ===== UI RESULT SCHEMAS =====
// UI-specific result schemas for component display

/**
 * Zod schema for hotel search results displayed in UI.
 * Includes detailed hotel information, pricing, amenities, and AI recommendations.
 */
export const hotelResultSchema = z.strictObject({
  ai: z.strictObject({
    personalizedTags: z.array(z.string()),
    reason: z.string(),
    recommendation: z.number().int().min(1).max(10),
  }),
  allInclusive: z
    .strictObject({
      available: z.boolean(),
      inclusions: z.array(z.string()),
      tier: z.enum(["basic", "premium", "luxury"]),
    })
    .optional(),
  amenities: z.strictObject({
    essential: z.array(z.string()),
    premium: z.array(z.string()),
    unique: z.array(z.string()),
  }),
  availability: z.strictObject({
    flexible: z.boolean(),
    roomsLeft: z.number().int().nonnegative(),
    urgency: z.enum(["low", "medium", "high"]),
  }),
  brand: z.string().optional(),
  category: z.enum(["hotel", "resort", "apartment", "villa", "boutique"]),
  guestExperience: z.strictObject({
    highlights: z.array(z.string()),
    recentMentions: z.array(z.string()),
    vibe: z.enum(["luxury", "business", "family", "romantic", "adventure"]),
  }),
  id: z.string().min(1),
  images: z.strictObject({
    count: z.number().int().nonnegative(),
    gallery: z.array(z.string()),
    main: z.string(),
  }),
  location: z.strictObject({
    address: z.string(),
    city: z.string(),
    coordinates: z
      .strictObject({
        lat: z.number(),
        lng: z.number(),
      })
      .optional(),
    district: z.string(),
    landmarks: z.array(z.string()),
    walkScore: z.number().optional(),
  }),
  name: z.string().min(1),
  pricing: z.strictObject({
    basePrice: z.number().nonnegative(),
    currency: z.string(),
    deals: z
      .strictObject({
        description: z.string(),
        originalPrice: z.number().nonnegative(),
        savings: z.number().nonnegative(),
        type: z.enum(["early_bird", "last_minute", "extended_stay", "all_inclusive"]),
      })
      .optional(),
    priceHistory: z.enum(["rising", "falling", "stable"]),
    pricePerNight: z.number().nonnegative(),
    taxes: z.number().nonnegative(),
    totalPrice: z.number().nonnegative(),
  }),
  reviewCount: z.number().int().nonnegative(),
  starRating: z.number().min(0).max(5),
  sustainability: z.strictObject({
    certified: z.boolean(),
    practices: z.array(z.string()),
    score: z.number().int().min(1).max(10),
  }),
  userRating: z.number().min(0).max(5),
});

/** TypeScript type for hotel search results. */
export type HotelResult = z.infer<typeof hotelResultSchema>;

/**
 * Zod schema for flight search results displayed in UI.
 * Includes detailed flight information, pricing, emissions, and AI predictions.
 */
export const flightResultSchema = z.strictObject({
  aircraft: z.string(),
  airline: z.string().min(1),
  amenities: z.array(z.string()),
  arrival: z.strictObject({
    date: z.string(),
    time: z.string(),
  }),
  departure: z.strictObject({
    date: z.string(),
    time: z.string(),
  }),
  destination: z.strictObject({
    city: z.string(),
    code: z.string(),
    terminal: z.string().optional(),
  }),
  duration: z.number().int().positive(), // minutes
  emissions: z.strictObject({
    compared: z.enum(["low", "average", "high"]),
    kg: z.number().nonnegative(),
  }),
  flexibility: z.strictObject({
    changeable: z.boolean(),
    cost: z.number().nonnegative().optional(),
    refundable: z.boolean(),
  }),
  flightNumber: z.string().min(1),
  id: z.string().min(1),
  origin: z.strictObject({
    city: z.string(),
    code: z.string(),
    terminal: z.string().optional(),
  }),
  prediction: z.strictObject({
    confidence: z.number().int().min(0).max(100),
    priceAlert: z.enum(["buy_now", "wait", "neutral"]),
    reason: z.string(),
  }),
  price: z.strictObject({
    base: z.number().nonnegative(),
    currency: z.string(),
    dealScore: z.number().int().min(1).max(10).optional(),
    priceChange: z.enum(["up", "down", "stable"]).optional(),
    total: z.number().nonnegative(),
  }),
  promotions: z
    .strictObject({
      description: z.string(),
      savings: z.number().nonnegative(),
      type: z.enum(["flash_deal", "early_bird", "limited_time"]),
    })
    .optional(),
  stops: z.strictObject({
    cities: z.array(z.string()).optional(),
    count: z.number().int().nonnegative(),
    duration: z.number().int().nonnegative().optional(),
  }),
});

/** TypeScript type for flight search results. */
export type FlightResult = z.infer<typeof flightResultSchema>;

// ===== DATABASE ROW SCHEMAS =====
// Schemas for database table rows matching Supabase structure

/**
 * Zod schema for search_hotels table row.
 * Matches database structure with snake_case column names.
 */
export const searchHotelsRowSchema = z.strictObject({
  check_in_date: DATE_STRING_SCHEMA,
  check_out_date: DATE_STRING_SCHEMA,
  created_at: z.string().nullable(),
  destination: z.string().min(1),
  expires_at: z.string(),
  guests: z.number().int().positive(),
  id: z.number().int().positive(),
  query_hash: z.string().min(1),
  query_parameters: z.record(z.string(), z.unknown()),
  results: z.record(z.string(), z.unknown()),
  rooms: z.number().int().positive(),
  search_metadata: z.record(z.string(), z.unknown()),
  source: z.enum(["amadeus", "external_api", "cached"]),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for search_hotels table row. */
export type SearchHotelsRow = z.infer<typeof searchHotelsRowSchema>;

/**
 * Zod schema for search_flights table row.
 * Matches database structure with snake_case column names.
 */
export const searchFlightsRowSchema = z.strictObject({
  cabin_class: z.enum(["economy", "premium_economy", "business", "first"]),
  created_at: z.string().nullable(),
  departure_date: DATE_STRING_SCHEMA,
  destination: z.string().min(1),
  expires_at: z.string(),
  id: z.number().int().positive(),
  origin: z.string().min(1),
  passengers: z.number().int().positive(),
  query_hash: z.string().min(1),
  query_parameters: z.record(z.string(), z.unknown()),
  results: z.record(z.string(), z.unknown()),
  return_date: DATE_STRING_SCHEMA.nullable(),
  search_metadata: z.record(z.string(), z.unknown()),
  source: z.enum(["duffel", "amadeus", "external_api", "cached"]),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for search_flights table row. */
export type SearchFlightsRow = z.infer<typeof searchFlightsRowSchema>;

/**
 * Zod schema for search_activities table row.
 * Matches database structure with snake_case column names.
 */
export const searchActivitiesRowSchema = z.strictObject({
  activity_type: z.string().nullable(),
  created_at: z.string().nullable(),
  destination: z.string().min(1),
  expires_at: z.string(),
  id: z.number().int().positive(),
  query_hash: z.string().min(1),
  query_parameters: z.record(z.string(), z.unknown()),
  results: z.record(z.string(), z.unknown()),
  search_metadata: z.record(z.string(), z.unknown()),
  source: z.enum([
    "viator",
    "getyourguide",
    "googleplaces",
    "ai_fallback",
    "external_api",
    "cached",
  ]),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for search_activities table row. */
export type SearchActivitiesRow = z.infer<typeof searchActivitiesRowSchema>;

/**
 * Zod schema for search_destinations table row.
 * Matches database structure with snake_case column names.
 */
export const searchDestinationsRowSchema = z.strictObject({
  created_at: z.string().nullable(),
  expires_at: z.string(),
  id: z.number().int().positive(),
  query: z.string().min(1),
  query_hash: z.string().min(1),
  results: z.record(z.string(), z.unknown()),
  search_metadata: z.record(z.string(), z.unknown()),
  source: z.enum(["google_maps", "external_api", "cached"]),
  user_id: primitiveSchemas.uuid,
});

/** TypeScript type for search_destinations table row. */
export type SearchDestinationsRow = z.infer<typeof searchDestinationsRowSchema>;

// ===== UTILITY FUNCTIONS =====
// Validation helpers and business logic functions

/**
 * Validates search parameters based on search type.
 * Performs type-specific validation and returns parsed parameters.
 *
 * @param data - Raw search parameters to validate
 * @param searchType - Type of search (flight, accommodation, activity, destination)
 * @returns Parsed and validated search parameters
 * @throws {Error} When validation fails or search type is unknown
 */
export const validateSearchParams = (data: unknown, searchType: string) => {
  try {
    switch (searchType) {
      case "flight":
        return flightSearchParamsSchema.parse(data);
      case "accommodation":
        return searchAccommodationParamsSchema.parse(data);
      case "activity":
        return activitySearchParamsSchema.parse(data);
      case "destination":
        return destinationSearchParamsSchema.parse(data);
      default:
        throw new Error(`Unknown search type: ${searchType}`);
    }
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new Error(
        `Search parameters validation failed: ${error.issues.map((i) => i.message).join(", ")}`
      );
    }
    throw error;
  }
};

/**
 * Safely validates search parameters with error handling.
 * Returns a result object with success/error information instead of throwing.
 *
 * @param data - Raw search parameters to validate
 * @param searchType - Type of search (flight, accommodation, activity, destination)
 * @returns Validation result with success/error information
 */
export const safeValidateSearchParams = (data: unknown, searchType: string) => {
  try {
    return { data: validateSearchParams(data, searchType), success: true as const };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Validation failed",
      success: false as const,
    };
  }
};
