/**
 * @fileoverview TypeScript types for accommodation tools.
 *
 * Types mirror the Zod schemas in accommodations.ts to provide type-safe
 * interfaces without requiring Zod imports at call sites.
 */

/**
 * Parameters for searching accommodations.
 *
 * Supports filtering by location, dates, property types, amenities, price
 * range, guest counts, and various other criteria.
 */
export type AccommodationSearchParams = {
  accessibilityFeatures?: string[];
  adults?: number;
  amenities?: string[];
  bathrooms?: number;
  bedrooms?: number;
  beds?: number;
  checkin: string;
  checkout: string;
  children?: number;
  currency?: string;
  freeCancellation?: boolean;
  fresh?: boolean;
  guests?: number;
  infants?: number;
  instantBook?: boolean;
  location: string;
  maxDistanceKm?: number;
  minRating?: number;
  priceMax?: number;
  priceMin?: number;
  propertyTypes?: Array<
    | "hotel"
    | "apartment"
    | "house"
    | "villa"
    | "resort"
    | "hostel"
    | "bed_and_breakfast"
    | "guest_house"
    | "other"
  >;
  sortBy?: "relevance" | "price" | "rating" | "distance";
  sortOrder?: "asc" | "desc";
  tripId?: string;
};

/**
 * Result of an accommodation search operation.
 *
 * Contains listings, pricing information, metadata, and provider details.
 */
export type AccommodationSearchResult = {
  avgPrice?: number;
  fromCache: boolean;
  listings: unknown[];
  maxPrice?: number;
  minPrice?: number;
  provider: string;
  resultsReturned: number;
  searchId: string;
  searchParameters: Record<string, unknown>;
  status: "success";
  tookMs: number;
  totalResults: number;
};

/**
 * Parameters for retrieving detailed information about a specific listing.
 *
 * Optionally includes check-in/out dates and guest counts for accurate
 * pricing and availability.
 */
export type AccommodationDetailsParams = {
  adults?: number;
  checkin?: string;
  checkout?: string;
  children?: number;
  infants?: number;
  listingId: string;
};

/**
 * Result of retrieving accommodation details.
 *
 * Contains the full listing information and provider metadata.
 */
export type AccommodationDetailsResult = {
  listing: unknown;
  provider: string;
  status: "success";
};

/**
 * Parameters for booking an accommodation.
 *
 * Includes guest information, dates, payment details, and optional
 * idempotency key for safe retries.
 */
export type AccommodationBookingRequest = {
  checkin: string;
  checkout: string;
  guestEmail: string;
  guestName: string;
  guestPhone?: string;
  guests?: number;
  holdOnly?: boolean;
  idempotencyKey?: string;
  listingId: string;
  paymentMethod?: string;
  sessionId: string;
  specialRequests?: string;
  tripId?: string;
};

/**
 * Result of a booking operation.
 *
 * Contains booking confirmation details, status, reference number, and
 * provider information.
 */
export type AccommodationBookingResult = {
  bookingId: string;
  bookingStatus: "hold_created" | "pending_confirmation";
  checkin: string;
  checkout: string;
  guestEmail: string;
  guestName: string;
  guestPhone?: string;
  guests: number;
  holdOnly: boolean;
  idempotencyKey: string;
  listingId: string;
  message: string;
  paymentMethod?: string;
  reference: string;
  specialRequests?: string;
  status: "success";
  tripId?: string;
};
