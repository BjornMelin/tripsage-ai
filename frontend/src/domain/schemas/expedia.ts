/**
 * @fileoverview Expedia Rapid API schemas and helpers.
 *
 * Combines provider wire schemas (Rapid responses) with TripSage-owned
 * request/response schemas used by tools and the Expedia client. Uses loose
 * objects for provider payloads to tolerate field drift, and strict objects for
 * TripSage-controlled shapes. Keep all exports under this single module so
 * callers import via `@schemas/expedia`.
 */

import { z } from "zod";

import { primitiveSchemas } from "./registry";

// ===== RAPID WIRE SCHEMAS (LOOSE) =====

const EPS_AMOUNT_SCHEMA = z.looseObject({
  currency: z.string().optional(),
  value: z.string().optional(),
});

const EPS_CHARGE_SCHEMA = z.looseObject({
  billable_currency: EPS_AMOUNT_SCHEMA.optional(),
  request_currency: EPS_AMOUNT_SCHEMA.optional(),
});

/** Schema for Rapid API link objects. */
export const EPS_LINK_SCHEMA = z.looseObject({
  href: z.string(),
  method: z.string().optional(),
  rel: z.string().optional(),
  test: z.string().optional(),
});

const EPS_RATE_PRICING_SCHEMA = z.looseObject({
  fees: z.record(z.string(), EPS_CHARGE_SCHEMA).optional(),
  nightly: z.array(z.array(z.record(z.string(), z.unknown()))).optional(),
  stay: z.array(z.record(z.string(), z.unknown())).optional(),
  totals: z
    .looseObject({
      exclusive: EPS_CHARGE_SCHEMA.optional(),
      inclusive: EPS_CHARGE_SCHEMA.optional(),
      property_inclusive: EPS_CHARGE_SCHEMA.optional(),
    })
    .optional(),
});

/** Schema for Rapid API rate objects. */
export const EPS_RATE_SCHEMA = z.looseObject({
  available_rooms: z.number().optional(),
  bed_groups: z.record(z.string(), z.unknown()).optional(),
  cancel_penalties: z.array(z.record(z.string(), z.unknown())).optional(),
  current_refundability: z.string().optional(),
  id: z.string().optional(),
  inclusions: z.array(z.string()).optional(),
  links: z
    .looseObject({
      book: EPS_LINK_SCHEMA.optional(),
      payment_session: EPS_LINK_SCHEMA.optional(),
      price_check: EPS_LINK_SCHEMA.optional(),
    })
    .optional(),
  merchant_of_record: z.string().optional(),
  price: z.record(z.string(), z.unknown()).optional(),
  pricing: EPS_RATE_PRICING_SCHEMA.optional(),
  refundable: z.boolean().optional(),
  sale_scenario: z.record(z.string(), z.unknown()).optional(),
  taxes_and_fees: z.record(z.string(), z.unknown()).optional(),
});

const EPS_ROOM_AVAILABILITY_SCHEMA = z.looseObject({
  description: z.string().optional(),
  id: z.string().optional(),
  images: z.array(z.record(z.string(), z.unknown())).optional(),
  rates: z.array(EPS_RATE_SCHEMA).optional(),
  room_name: z.string().optional(),
});

const EPS_PROPERTY_ADDRESS_SCHEMA = z.looseObject({
  city: z.string().optional(),
  country_code: z.string().optional(),
  line_1: z.string().optional(),
  line_2: z.string().optional(),
  line_3: z.string().optional(),
  postal_code: z.string().optional(),
  state_province_code: z.string().optional(),
});

const EPS_PROPERTY_SUMMARY_SCHEMA = z.looseObject({
  location: z
    .looseObject({
      address: EPS_PROPERTY_ADDRESS_SCHEMA.optional(),
      coordinates: z
        .looseObject({
          latitude: z.number().optional(),
          longitude: z.number().optional(),
        })
        .optional(),
    })
    .optional(),
  name: z.string().optional(),
  short_description: z.looseObject({ value: z.string().optional() }).optional(),
  star_rating: z.looseObject({ value: z.number().optional() }).optional(),
});

/** Schema for Rapid API property availability objects. */
export const EPS_PROPERTY_AVAILABILITY_SCHEMA = z.looseObject({
  address: EPS_PROPERTY_ADDRESS_SCHEMA.optional(),
  amenities: z.record(z.string(), z.unknown()).optional(),
  links: z
    .looseObject({
      additional_rates: EPS_LINK_SCHEMA.optional(),
      property_details: EPS_LINK_SCHEMA.optional(),
    })
    .optional(),
  name: z.string().optional(),
  property_id: z.string().optional(),
  property_type: z.string().optional(),
  rooms: z.array(EPS_ROOM_AVAILABILITY_SCHEMA).optional(),
  score: z.number().optional(),
  star_rating: z.number().optional(),
  status: z.enum(["available", "partially_unavailable"]).optional(),
  summary: EPS_PROPERTY_SUMMARY_SCHEMA.optional(),
});

/** Schema for Rapid API availability response. */
export const EPS_AVAILABILITY_RESPONSE_SCHEMA = z.looseObject({
  properties: z.array(EPS_PROPERTY_AVAILABILITY_SCHEMA).optional(),
  total: z.number().optional(),
  unavailable: z.array(z.record(z.string(), z.unknown())).optional(),
  unfulfilled: z.array(z.record(z.string(), z.unknown())).optional(),
});

/** Schema for Rapid API property content objects. */
export const EPS_PROPERTY_CONTENT_SCHEMA = z.looseObject({
  address: EPS_PROPERTY_ADDRESS_SCHEMA.optional(),
  amenities: z.array(z.string()).optional(),
  descriptions: z
    .looseObject({
      amenities: z.array(z.string()).optional(),
      overview: z.string().optional(),
    })
    .optional(),
  images: z
    .looseObject({
      property: z.array(z.record(z.string(), z.unknown())).optional(),
      rooms: z.array(z.record(z.string(), z.unknown())).optional(),
    })
    .optional(),
  name: z.string().optional(),
  policies: z
    .looseObject({
      cancellation: z.string().optional(),
      check_in: z.string().optional(),
      check_out: z.string().optional(),
      house_rules: z.array(z.string()).optional(),
    })
    .optional(),
  property_id: z.string(),
  reviews: z
    .looseObject({
      count: z.number().optional(),
      guest_review_details: z.record(z.string(), z.unknown()).optional(),
      rating: z.number().optional(),
    })
    .optional(),
  summary: EPS_PROPERTY_SUMMARY_SCHEMA.optional(),
});

/** Schema for Rapid API property content response. */
export const EPS_PROPERTY_CONTENT_RESPONSE_SCHEMA = z.record(
  z.string(),
  EPS_PROPERTY_CONTENT_SCHEMA
);

/** Schema for Rapid API price check response. */
export const EPS_PRICE_CHECK_RESPONSE_SCHEMA = z.looseObject({
  amount_owed: EPS_CHARGE_SCHEMA.optional(),
  links: z
    .looseObject({
      additional_rates: EPS_LINK_SCHEMA.optional(),
      book: EPS_LINK_SCHEMA.optional(),
      commit: EPS_LINK_SCHEMA.optional(),
      payment_session: EPS_LINK_SCHEMA.optional(),
    })
    .optional(),
  occupancy_pricing: z.record(z.string(), EPS_RATE_PRICING_SCHEMA).optional(),
  penalty: EPS_CHARGE_SCHEMA.optional(),
  refundable_damage_deposit: EPS_AMOUNT_SCHEMA.optional(),
  status: z.enum(["available", "available_no_change", "price_changed", "sold_out"]),
});

/** Schema for Rapid API booking creation response. */
export const EPS_CREATE_BOOKING_RESPONSE_SCHEMA = z.looseObject({
  creation_date_time: z.string().optional(),
  itinerary_id: z.string().optional(),
  links: z.record(z.string(), EPS_LINK_SCHEMA).optional(),
  rooms: z
    .array(
      z.looseObject({
        confirmation_id: z
          .looseObject({
            expedia: z.string().optional(),
            property: z.string().optional(),
          })
          .optional(),
        id: z.string().optional(),
      })
    )
    .optional(),
});

// ===== TRIPSAGE REQUEST / RESPONSE SCHEMAS (STRICT) =====

/** Schema for TripSage property search requests. */
export const EPS_SEARCH_REQUEST_SCHEMA = z.strictObject({
  amenityCategory: z.array(z.string()).optional(),
  checkIn: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  checkOut: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  countryCode: z.string().length(2).optional(),
  currency: primitiveSchemas.isoCurrency.optional(),
  guests: z.number().int().min(1).max(16),
  include: z
    .array(z.enum(["unavailable_reason", "rooms.rates.current_refundability"]))
    .optional(),
  language: z.string().optional(),
  propertyIds: z.array(z.string()).min(1),
  ratePlanCount: z.number().int().min(1).max(250).optional(),
  salesChannel: z
    .enum(["website", "agent_tool", "mobile_app", "mobile_web", "meta", "cache"])
    .optional(),
  salesEnvironment: z.enum(["hotel_package", "hotel_only", "loyalty"]).optional(),
  travelPurpose: z.enum(["leisure", "business"]).optional(),
});

/** Schema for TripSage property details requests. */
export const EPS_PROPERTY_DETAILS_REQUEST_SCHEMA = z.strictObject({
  language: z.string().optional(),
  propertyId: z.string(),
});

/** Schema for TripSage availability check requests. */
export const EPS_CHECK_AVAILABILITY_REQUEST_SCHEMA = z.strictObject({
  propertyId: z.string(),
  rateId: z.string(),
  roomId: z.string(),
  token: z.string(),
});

/** Schema for TripSage availability check responses. */
export const EPS_CHECK_AVAILABILITY_RESPONSE_SCHEMA = z.strictObject({
  bookingToken: z.string(),
  expiresAt: z.string(),
  price: z.strictObject({
    currency: primitiveSchemas.isoCurrency,
    total: z.string(),
  }),
  propertyId: z.string(),
  rateId: z.string(),
  roomId: z.string(),
});

/** Schema for TripSage booking creation requests. */
export const EPS_CREATE_BOOKING_REQUEST_SCHEMA = z.strictObject({
  affiliateReferenceId: z.string().optional(),
  billingContact: z
    .strictObject({
      address: z
        .strictObject({
          city: z.string().optional(),
          countryCode: z.string().length(2),
          line1: z.string().optional(),
          line2: z.string().optional(),
          line3: z.string().optional(),
          postalCode: z.string().optional(),
          stateProvinceCode: z.string().optional(),
        })
        .partial(),
      familyName: z.string(),
      givenName: z.string(),
    })
    .optional(),
  bookingToken: z.string(),
  contact: z.strictObject({
    email: z.email(),
    phoneAreaCode: z.string().optional(),
    phoneCountryCode: z.string().optional(),
    phoneNumber: z.string().optional(),
  }),
  hold: z.boolean().optional(),
  specialRequests: z.string().optional(),
  stay: z.strictObject({
    adults: z.number().int().min(1),
    checkIn: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    checkOut: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    childAges: z.array(z.number().int()).optional(),
  }),
  traveler: z.strictObject({
    familyName: z.string(),
    givenName: z.string(),
  }),
});

// ===== TYPES =====

/** Type for Rapid API availability search response. */
export type RapidAvailabilityResponse = z.infer<
  typeof EPS_AVAILABILITY_RESPONSE_SCHEMA
>;
/** Type for individual property in availability response. */
export type RapidProperty = z.infer<typeof EPS_PROPERTY_AVAILABILITY_SCHEMA>;
/** Type for room information within property availability. */
export type RapidRoom = z.infer<typeof EPS_ROOM_AVAILABILITY_SCHEMA>;
/** Type for rate information within room availability. */
export type RapidRate = z.infer<typeof EPS_RATE_SCHEMA>;
/** Type for links in Rapid API responses. */
export type RapidLink = z.infer<typeof EPS_LINK_SCHEMA>;
/** Type for property content API response map. */
export type RapidPropertyContentMap = z.infer<
  typeof EPS_PROPERTY_CONTENT_RESPONSE_SCHEMA
>;
/** Type for individual property content information. */
export type RapidPropertyContent = z.infer<typeof EPS_PROPERTY_CONTENT_SCHEMA>;
/** Type for price check API response. */
export type RapidPriceCheckResponse = z.infer<typeof EPS_PRICE_CHECK_RESPONSE_SCHEMA>;
/** Type for booking creation API response. */
export type RapidCreateBookingResponse = z.infer<
  typeof EPS_CREATE_BOOKING_RESPONSE_SCHEMA
>;

/** Type for TripSage property search request. */
export type EpsSearchRequest = z.infer<typeof EPS_SEARCH_REQUEST_SCHEMA>;
/** Type for TripSage property search response (alias for Rapid response). */
export type EpsSearchResponse = RapidAvailabilityResponse;
/** Type for TripSage property details request. */
export type EpsPropertyDetailsRequest = z.infer<
  typeof EPS_PROPERTY_DETAILS_REQUEST_SCHEMA
>;
/** Type for TripSage property details response (alias for Rapid content). */
export type EpsPropertyDetailsResponse = RapidPropertyContent;
/** Type for TripSage availability check request. */
export type EpsCheckAvailabilityRequest = z.infer<
  typeof EPS_CHECK_AVAILABILITY_REQUEST_SCHEMA
>;
/** Type for TripSage availability check response. */
export type EpsCheckAvailabilityResponse = z.infer<
  typeof EPS_CHECK_AVAILABILITY_RESPONSE_SCHEMA
>;
/** Type for TripSage booking creation request. */
export type EpsCreateBookingRequest = z.infer<typeof EPS_CREATE_BOOKING_REQUEST_SCHEMA>;
/** Type for TripSage booking creation response (alias for Rapid response). */
export type EpsCreateBookingResponse = RapidCreateBookingResponse;

// ===== HELPERS =====

/**
 * Extracts inclusive total amount from rate pricing.
 *
 * @param pricing - Rate pricing structure from Rapid API response.
 * @returns Currency and total amount if available, undefined otherwise.
 */
export function extractInclusiveTotal(
  pricing?: z.infer<typeof EPS_RATE_PRICING_SCHEMA>
): { currency: string; total: string } | undefined {
  const inclusive = pricing?.totals?.inclusive;
  const amount =
    inclusive?.request_currency ?? inclusive?.billable_currency ?? undefined;
  if (!amount?.value || !amount?.currency) {
    return undefined;
  }
  return { currency: amount.currency, total: amount.value };
}
