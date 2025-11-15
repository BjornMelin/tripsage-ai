/**
 * @fileoverview Zod schemas and TypeScript types for Expedia Partner Solutions (EPS) Rapid API.
 *
 * Defines request/response types aligned with EPS API structure for properties,
 * rates, availability, and bookings.
 */

import { z } from "zod";

/**
 * Property source type (hotel or vacation rental).
 */
export const PROPERTY_SOURCE_SCHEMA = z.enum(["hotel", "vrbo"]);

export type PropertySource = z.infer<typeof PROPERTY_SOURCE_SCHEMA>;

/**
 * EPS property search request parameters.
 */
export const EPS_SEARCH_REQUEST_SCHEMA = z.object({
  amenities: z.array(z.string()).optional(),
  checkIn: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  checkOut: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  guests: z.number().int().min(1).max(16),
  location: z.string().min(1),
  priceMax: z.number().nonnegative().optional(),
  priceMin: z.number().nonnegative().optional(),
  propertyIds: z.array(z.string()).optional(),
  propertyTypes: z.array(z.string()).optional(),
});

export type EpsSearchRequest = z.infer<typeof EPS_SEARCH_REQUEST_SCHEMA>;

/**
 * EPS property rate information.
 */
export const EPS_RATE_SCHEMA = z.object({
  bedTypes: z.array(z.string()).optional(),
  cancellationPolicy: z.string().optional(),
  id: z.string(),
  price: z.object({
    currency: z.string(),
    perNight: z.string().optional(),
    total: z.string(),
  }),
  roomType: z.string().optional(),
});

export type EpsRate = z.infer<typeof EPS_RATE_SCHEMA>;

/**
 * EPS property listing (from search results).
 */
export const EPS_PROPERTY_SCHEMA = z.object({
  address: z
    .object({
      addressLine1: z.string().optional(),
      city: z.string().optional(),
      country: z.string().optional(),
      state: z.string().optional(),
    })
    .optional(),
  amenities: z.array(z.string()).optional(),
  coordinates: z
    .object({
      latitude: z.number(),
      longitude: z.number(),
    })
    .optional(),
  description: z.string().optional(),
  id: z.string(), // e.g., 'eps:12345'
  images: z
    .array(
      z.object({
        caption: z.string().optional(),
        url: z.url(),
      })
    )
    .optional(),
  name: z.string(),
  rates: z.array(EPS_RATE_SCHEMA).optional(),
  rating: z
    .object({
      count: z.number().int().optional(),
      value: z.number().min(0).max(5),
    })
    .optional(),
  source: PROPERTY_SOURCE_SCHEMA,
});

export type EpsProperty = z.infer<typeof EPS_PROPERTY_SCHEMA>;

/**
 * EPS search response.
 */
export const EPS_SEARCH_RESPONSE_SCHEMA = z.object({
  properties: z.array(EPS_PROPERTY_SCHEMA),
  searchId: z.string().optional(),
  totalResults: z.number().int(),
});

export type EpsSearchResponse = z.infer<typeof EPS_SEARCH_RESPONSE_SCHEMA>;

/**
 * EPS property details request.
 */
export const EPS_PROPERTY_DETAILS_REQUEST_SCHEMA = z.object({
  checkIn: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .optional(),
  checkOut: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .optional(),
  guests: z.number().int().min(1).max(16).optional(),
  propertyId: z.string(),
});

export type EpsPropertyDetailsRequest = z.infer<
  typeof EPS_PROPERTY_DETAILS_REQUEST_SCHEMA
>;

/**
 * EPS property details response.
 */
export const EPS_PROPERTY_DETAILS_RESPONSE_SCHEMA = EPS_PROPERTY_SCHEMA.extend({
  policies: z
    .object({
      cancellation: z.string().optional(),
      checkIn: z.string().optional(),
      checkOut: z.string().optional(),
      houseRules: z.array(z.string()).optional(),
    })
    .optional(),
  reviews: z
    .array(
      z.object({
        author: z.string(),
        comment: z.string(),
        date: z.string(),
        rating: z.number().min(0).max(5),
      })
    )
    .optional(),
});

export type EpsPropertyDetailsResponse = z.infer<
  typeof EPS_PROPERTY_DETAILS_RESPONSE_SCHEMA
>;

/**
 * EPS check availability request.
 */
export const EPS_CHECK_AVAILABILITY_REQUEST_SCHEMA = z.object({
  checkIn: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  checkOut: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  guests: z.number().int().min(1).max(16),
  propertyId: z.string(),
  rateId: z.string(),
});

export type EpsCheckAvailabilityRequest = z.infer<
  typeof EPS_CHECK_AVAILABILITY_REQUEST_SCHEMA
>;

/**
 * EPS check availability response.
 */
export const EPS_CHECK_AVAILABILITY_RESPONSE_SCHEMA = z.object({
  bookingToken: z.string(),
  expiresAt: z.string(), // ISO 8601 timestamp
  price: z.object({
    breakdown: z
      .object({
        base: z.string().optional(),
        fees: z.string().optional(),
        taxes: z.string().optional(),
      })
      .optional(),
    currency: z.string(),
    total: z.string(),
  }),
  propertyId: z.string(),
  rateId: z.string(),
});

export type EpsCheckAvailabilityResponse = z.infer<
  typeof EPS_CHECK_AVAILABILITY_RESPONSE_SCHEMA
>;

/**
 * EPS create booking request.
 */
export const EPS_CREATE_BOOKING_REQUEST_SCHEMA = z.object({
  bookingToken: z.string(),
  payment: z.object({
    paymentIntentId: z.string().optional(), // Stripe payment intent ID
    paymentMethodId: z.string(), // Stripe payment method ID
  }),
  specialRequests: z.string().optional(),
  user: z.object({
    email: z.email(),
    name: z.string().min(1),
    phone: z.string().optional(),
  }),
});

export type EpsCreateBookingRequest = z.infer<typeof EPS_CREATE_BOOKING_REQUEST_SCHEMA>;

/**
 * EPS create booking response.
 */
export const EPS_CREATE_BOOKING_RESPONSE_SCHEMA = z.object({
  checkIn: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  checkOut: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  confirmationNumber: z.string(),
  guestEmail: z.email(),
  guestName: z.string(),
  id: z.string(), // EPS booking confirmation ID
  propertyId: z.string(),
  status: z.enum(["CONFIRMED", "PENDING"]),
});

export type EpsCreateBookingResponse = z.infer<
  typeof EPS_CREATE_BOOKING_RESPONSE_SCHEMA
>;

/**
 * EPS API error response.
 */
export const EPS_ERROR_RESPONSE_SCHEMA = z.object({
  error: z.object({
    code: z.string(),
    details: z.record(z.string(), z.unknown()).optional(),
    message: z.string(),
  }),
});

export type EpsErrorResponse = z.infer<typeof EPS_ERROR_RESPONSE_SCHEMA>;
