/**
 * @fileoverview Expedia Rapid API schemas and helper types.
 *
 * Defines the subset of Rapid structures that TripSage consumes so we can
 * validate responses with Zod v4 and share strongly-typed helpers across the
 * Expedia client, tools, and payment orchestration.
 */

import { z } from "zod";

/**
 * Common schemas
 */
const EPS_AMOUNT_SCHEMA = z
  .object({
    currency: z.string().optional(),
    value: z.string().optional(),
  })
  .partial();

const EPS_CHARGE_SCHEMA = z
  .object({
    // biome-ignore lint/style/useNamingConvention: API field name
    billable_currency: EPS_AMOUNT_SCHEMA.optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    request_currency: EPS_AMOUNT_SCHEMA.optional(),
  })
  .partial();

export const EPS_LINK_SCHEMA = z
  .object({
    href: z.string(),
    method: z.string().optional(),
    rel: z.string().optional(),
    test: z.string().optional(),
  })
  .partial();

/**
 * Availability / Shopping schemas
 */
const EPS_RATE_PRICING_SCHEMA = z
  .object({
    fees: z.record(z.string(), EPS_CHARGE_SCHEMA).optional(),
    nightly: z.array(z.array(z.record(z.string(), z.unknown()))).optional(),
    stay: z.array(z.record(z.string(), z.unknown())).optional(),
    totals: z
      .object({
        exclusive: EPS_CHARGE_SCHEMA.optional(),
        inclusive: EPS_CHARGE_SCHEMA.optional(),
        // biome-ignore lint/style/useNamingConvention: API field name
        property_inclusive: EPS_CHARGE_SCHEMA.optional(),
      })
      .partial()
      .optional(),
  })
  .partial();

export const EPS_RATE_SCHEMA = z
  .object({
    // biome-ignore lint/style/useNamingConvention: API field name
    available_rooms: z.number().optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    bed_groups: z.record(z.string(), z.unknown()).optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    cancel_penalties: z.array(z.record(z.string(), z.unknown())).optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    current_refundability: z.string().optional(),
    id: z.string(),
    inclusions: z.array(z.string()).optional(),
    links: z
      .object({
        book: EPS_LINK_SCHEMA.optional(),
        // biome-ignore lint/style/useNamingConvention: API field name
        payment_session: EPS_LINK_SCHEMA.optional(),
        // biome-ignore lint/style/useNamingConvention: API field name
        price_check: EPS_LINK_SCHEMA.optional(),
      })
      .partial()
      .optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    merchant_of_record: z.string().optional(),
    price: z.record(z.string(), z.unknown()).optional(),
    pricing: EPS_RATE_PRICING_SCHEMA.optional(),
    refundable: z.boolean().optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    sale_scenario: z.record(z.string(), z.unknown()).optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    taxes_and_fees: z.record(z.string(), z.unknown()).optional(),
  })
  .partial();

const EPS_ROOM_AVAILABILITY_SCHEMA = z
  .object({
    description: z.string().optional(),
    id: z.string(),
    images: z.array(z.record(z.string(), z.unknown())).optional(),
    rates: z.array(EPS_RATE_SCHEMA).optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    room_name: z.string().optional(),
  })
  .partial();

const EPS_PROPERTY_ADDRESS_SCHEMA = z
  .object({
    city: z.string().optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    country_code: z.string().optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    line_1: z.string().optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    line_2: z.string().optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    line_3: z.string().optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    postal_code: z.string().optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    state_province_code: z.string().optional(),
  })
  .partial();

const EPS_PROPERTY_SUMMARY_SCHEMA = z
  .object({
    location: z
      .object({
        address: EPS_PROPERTY_ADDRESS_SCHEMA.optional(),
        coordinates: z
          .object({
            latitude: z.number().optional(),
            longitude: z.number().optional(),
          })
          .partial()
          .optional(),
      })
      .partial()
      .optional(),
    name: z.string().optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    short_description: z.object({ value: z.string().optional() }).partial().optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    star_rating: z.object({ value: z.number().optional() }).partial().optional(),
  })
  .partial();

export const EPS_PROPERTY_AVAILABILITY_SCHEMA = z
  .object({
    address: EPS_PROPERTY_ADDRESS_SCHEMA.optional(),
    amenities: z.record(z.string(), z.unknown()).optional(),
    links: z
      .object({
        // biome-ignore lint/style/useNamingConvention: API field name
        additional_rates: EPS_LINK_SCHEMA.optional(),
        // biome-ignore lint/style/useNamingConvention: API field name
        property_details: EPS_LINK_SCHEMA.optional(),
      })
      .partial()
      .optional(),
    name: z.string().optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    property_id: z.string(),
    // biome-ignore lint/style/useNamingConvention: API field name
    property_type: z.string().optional(),
    rooms: z.array(EPS_ROOM_AVAILABILITY_SCHEMA).optional(),
    score: z.number().optional(),
    // biome-ignore lint/style/useNamingConvention: API field name
    star_rating: z.number().optional(),
    status: z.enum(["available", "partially_unavailable"]).optional(),
    summary: EPS_PROPERTY_SUMMARY_SCHEMA.optional(),
  })
  .partial();

export const EPS_AVAILABILITY_RESPONSE_SCHEMA = z
  .object({
    properties: z.array(EPS_PROPERTY_AVAILABILITY_SCHEMA).optional(),
    total: z.number().optional(),
    unavailable: z.array(z.record(z.string(), z.unknown())).optional(),
    unfulfilled: z.array(z.record(z.string(), z.unknown())).optional(),
  })
  .partial();

export type RapidAvailabilityResponse = z.infer<
  typeof EPS_AVAILABILITY_RESPONSE_SCHEMA
>;
export type RapidProperty = z.infer<typeof EPS_PROPERTY_AVAILABILITY_SCHEMA>;
export type RapidRoom = z.infer<typeof EPS_ROOM_AVAILABILITY_SCHEMA>;
export type RapidRate = z.infer<typeof EPS_RATE_SCHEMA>;
export type RapidLink = z.infer<typeof EPS_LINK_SCHEMA>;

/**
 * Property content (details) schemas
 */
export const EPS_PROPERTY_CONTENT_SCHEMA = z
  .object({
    address: EPS_PROPERTY_ADDRESS_SCHEMA.optional(),
    amenities: z.array(z.string()).optional(),
    descriptions: z
      .object({
        amenities: z.array(z.string()).optional(),
        overview: z.string().optional(),
      })
      .partial()
      .optional(),
    images: z
      .object({
        property: z.array(z.record(z.string(), z.unknown())).optional(),
        rooms: z.array(z.record(z.string(), z.unknown())).optional(),
      })
      .partial()
      .optional(),
    name: z.string().optional(),
    policies: z
      .object({
        cancellation: z.string().optional(),
        check_in: z.string().optional(),
        check_out: z.string().optional(),
        house_rules: z.array(z.string()).optional(),
      })
      .partial()
      .optional(),
    property_id: z.string(),
    reviews: z
      .object({
        count: z.number().optional(),
        guest_review_details: z.record(z.string(), z.unknown()).optional(),
        rating: z.number().optional(),
      })
      .partial()
      .optional(),
    summary: EPS_PROPERTY_SUMMARY_SCHEMA.optional(),
  })
  .partial();

export const EPS_PROPERTY_CONTENT_RESPONSE_SCHEMA = z.record(
  z.string(),
  EPS_PROPERTY_CONTENT_SCHEMA
);

export type RapidPropertyContentMap = z.infer<
  typeof EPS_PROPERTY_CONTENT_RESPONSE_SCHEMA
>;
export type RapidPropertyContent = z.infer<typeof EPS_PROPERTY_CONTENT_SCHEMA>;

/**
 * Price check / booking token schemas
 */
export const EPS_PRICE_CHECK_RESPONSE_SCHEMA = z
  .object({
    amount_owed: EPS_CHARGE_SCHEMA.optional(),
    links: z
      .object({
        additional_rates: EPS_LINK_SCHEMA.optional(),
        book: EPS_LINK_SCHEMA.optional(),
        commit: EPS_LINK_SCHEMA.optional(),
        payment_session: EPS_LINK_SCHEMA.optional(),
      })
      .partial()
      .optional(),
    occupancy_pricing: z.record(z.string(), EPS_RATE_PRICING_SCHEMA).optional(),
    penalty: EPS_CHARGE_SCHEMA.optional(),
    refundable_damage_deposit: EPS_AMOUNT_SCHEMA.optional(),
    status: z.enum(["available", "available_no_change", "price_changed", "sold_out"]),
  })
  .partial();

export type RapidPriceCheckResponse = z.infer<typeof EPS_PRICE_CHECK_RESPONSE_SCHEMA>;

/**
 * Booking / itinerary schemas
 */
export const EPS_CREATE_BOOKING_REQUEST_SCHEMA = z.object({
  affiliateReferenceId: z.string().optional(),
  billingContact: z
    .object({
      address: z
        .object({
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
  contact: z.object({
    email: z.string().email(),
    phoneAreaCode: z.string().optional(),
    phoneCountryCode: z.string().optional(),
    phoneNumber: z.string().optional(),
  }),
  hold: z.boolean().optional(),
  specialRequests: z.string().optional(),
  stay: z.object({
    adults: z.number().int().min(1),
    checkIn: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    checkOut: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    childAges: z.array(z.number().int()).optional(),
  }),
  traveler: z.object({
    familyName: z.string(),
    givenName: z.string(),
  }),
});

export type ExpediaCreateBookingRequest = z.infer<
  typeof EPS_CREATE_BOOKING_REQUEST_SCHEMA
>;

export const EPS_CREATE_BOOKING_RESPONSE_SCHEMA = z
  .object({
    creation_date_time: z.string().optional(),
    itinerary_id: z.string().optional(),
    links: z.record(z.string(), EPS_LINK_SCHEMA).optional(),
    rooms: z
      .array(
        z.object({
          confirmation_id: z
            .object({
              expedia: z.string().optional(),
              property: z.string().optional(),
            })
            .partial()
            .optional(),
          id: z.string().optional(),
        })
      )
      .optional(),
  })
  .partial();

export type RapidCreateBookingResponse = z.infer<
  typeof EPS_CREATE_BOOKING_RESPONSE_SCHEMA
>;

/**
 * Helper to extract totals from pricing information.
 */
export function extractInclusiveTotal(
  pricing?: z.infer<typeof EPS_RATE_PRICING_SCHEMA>
) {
  const inclusive = pricing?.totals?.inclusive;
  const amount =
    inclusive?.request_currency ?? inclusive?.billable_currency ?? undefined;
  if (!amount?.value || !amount?.currency) {
    return undefined;
  }
  return {
    currency: amount.currency,
    total: amount.value,
  };
}

/**
 * Request/response helper schemas exported for other modules.
 */
export const EPS_SEARCH_REQUEST_SCHEMA = z.object({
  amenityCategory: z.array(z.string()).optional(),
  checkIn: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  checkOut: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  countryCode: z.string().length(2).optional(),
  currency: z.string().length(3).optional(),
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

export type EpsSearchRequest = z.infer<typeof EPS_SEARCH_REQUEST_SCHEMA>;
export type EpsSearchResponse = RapidAvailabilityResponse;

export const EPS_PROPERTY_DETAILS_REQUEST_SCHEMA = z.object({
  language: z.string().optional(),
  propertyId: z.string(),
});

export type EpsPropertyDetailsRequest = z.infer<
  typeof EPS_PROPERTY_DETAILS_REQUEST_SCHEMA
>;
export type EpsPropertyDetailsResponse = RapidPropertyContent;

export const EPS_CHECK_AVAILABILITY_REQUEST_SCHEMA = z.object({
  propertyId: z.string(),
  rateId: z.string(),
  roomId: z.string(),
  token: z.string(),
});

export type EpsCheckAvailabilityRequest = z.infer<
  typeof EPS_CHECK_AVAILABILITY_REQUEST_SCHEMA
>;

export const EPS_CHECK_AVAILABILITY_RESPONSE_SCHEMA = z.object({
  bookingToken: z.string(),
  expiresAt: z.string(),
  price: z.object({
    currency: z.string(),
    total: z.string(),
  }),
  propertyId: z.string(),
  rateId: z.string(),
  roomId: z.string(),
});

export type EpsCheckAvailabilityResponse = z.infer<
  typeof EPS_CHECK_AVAILABILITY_RESPONSE_SCHEMA
>;

export type EpsCreateBookingRequest = ExpediaCreateBookingRequest;
export type EpsCreateBookingResponse = RapidCreateBookingResponse;
