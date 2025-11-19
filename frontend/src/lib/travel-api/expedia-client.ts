/**
 * @fileoverview Expedia Partner Solutions Rapid client.
 *
 * Implements authenticated helpers for the Rapid v3 API, covering property
 * availability (shopping), property content (details), price check, and booking
 * creation. Responses are validated with Zod schemas defined in
 * `expedia-types.ts` before being consumed by the tool layer.
 */

import "server-only";

import type { z } from "zod";

import { getServerEnvVar, getServerEnvVarWithFallback } from "@/lib/env/server";
import { secureUuid } from "@/lib/security/random";
import {
  EPS_AVAILABILITY_RESPONSE_SCHEMA,
  EPS_CHECK_AVAILABILITY_REQUEST_SCHEMA,
  EPS_CHECK_AVAILABILITY_RESPONSE_SCHEMA,
  EPS_CREATE_BOOKING_REQUEST_SCHEMA,
  EPS_CREATE_BOOKING_RESPONSE_SCHEMA,
  EPS_PRICE_CHECK_RESPONSE_SCHEMA,
  EPS_PROPERTY_CONTENT_RESPONSE_SCHEMA,
  EPS_PROPERTY_DETAILS_REQUEST_SCHEMA,
  EPS_SEARCH_REQUEST_SCHEMA,
  type EpsCheckAvailabilityRequest,
  type EpsCheckAvailabilityResponse,
  type EpsCreateBookingRequest,
  type EpsCreateBookingResponse,
  type EpsPropertyDetailsRequest,
  type EpsPropertyDetailsResponse,
  type EpsSearchRequest,
  type EpsSearchResponse,
  extractInclusiveTotal,
  type RapidLink,
  type RapidPriceCheckResponse,
  type RapidPropertyContentMap,
} from "@/lib/travel-api/expedia-types";

export type ExpediaRequestContext = {
  customerIp?: string;
  customerSessionId?: string;
  testScenario?: string;
  userAgent?: string;
};

/**
 * Custom error class for Expedia API errors.
 */
export class ExpediaApiError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode?: number,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ExpediaApiError";
  }
}

const RAPID_DEFAULT_BASE_URL = "https://test.ean.com/v3";

function ensureEnv(value: string | undefined, name: string): string {
  if (!value) {
    throw new Error(`${name} is required to call Expedia Rapid APIs`);
  }
  return value;
}

/**
 * Expedia Partner Solutions API client.
 */
export class ExpediaClient {
  private readonly apiKey: string;
  private readonly apiSecret: string;
  private readonly baseUrl: string;
  private readonly defaultCustomerIp: string;
  private readonly defaultUserAgent: string;

  constructor() {
    this.apiKey = ensureEnv(getServerEnvVar("EPS_API_KEY"), "EPS_API_KEY");
    this.apiSecret = ensureEnv(getServerEnvVar("EPS_API_SECRET"), "EPS_API_SECRET");
    this.baseUrl =
      getServerEnvVarWithFallback("EPS_BASE_URL", RAPID_DEFAULT_BASE_URL) ??
      RAPID_DEFAULT_BASE_URL;
    this.defaultCustomerIp =
      getServerEnvVarWithFallback("EPS_DEFAULT_CUSTOMER_IP", "0.0.0.0") ?? "0.0.0.0";
    this.defaultUserAgent =
      getServerEnvVarWithFallback(
        "EPS_DEFAULT_USER_AGENT",
        "TripSage/1.0 (+https://tripsage.ai)"
      ) ?? "TripSage/1.0 (+https://tripsage.ai)";
  }

  private getAuthHeader(): string {
    const credentials = Buffer.from(
      `${this.apiKey}:${this.apiSecret}`,
      "utf-8"
    ).toString("base64");
    return `Basic ${credentials}`;
  }

  private buildHeaders(
    existingHeaders: HeadersInit | undefined,
    context: ExpediaRequestContext | undefined
  ): Headers {
    const headers = new Headers({
      // biome-ignore lint/style/useNamingConvention: HTTP header name
      Accept: "application/json",
      "Accept-Encoding": "gzip",
      // biome-ignore lint/style/useNamingConvention: HTTP header name
      Authorization: this.getAuthHeader(),
      "Content-Type": "application/json",
      "Customer-Ip": context?.customerIp ?? this.defaultCustomerIp,
      "Customer-Session-Id": context?.customerSessionId ?? secureUuid(),
      "User-Agent": context?.userAgent ?? this.defaultUserAgent,
      "X-API-Key": this.apiKey,
    });

    if (context?.testScenario) {
      headers.set("Test", context.testScenario);
    }

    if (existingHeaders) {
      const overrides = new Headers(existingHeaders);
      // biome-ignore lint/suspicious/useIterableCallbackReturn: Headers.forEach returns undefined
      overrides.forEach((value, key) => headers.set(key, value));
    }

    return headers;
  }

  private async request<T>(
    path: string,
    init: RequestInit = {},
    context?: ExpediaRequestContext,
    schema?: z.ZodSchema<T>
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const response = await fetch(url, {
      ...init,
      headers: this.buildHeaders(init.headers, context),
    });

    if (!response.ok) {
      const errorBody = await response
        .json()
        .catch(async () => ({ message: await response.text().catch(() => "") }));
      const message =
        typeof errorBody?.message === "string"
          ? errorBody.message
          : response.statusText;
      const code =
        typeof errorBody?.code === "string" ? errorBody.code : "EPS_API_ERROR";
      throw new ExpediaApiError(message, code, response.status, { path });
    }

    const body = (await response.json()) as T;
    return schema ? schema.parse(body) : body;
  }

  /**
   * Call Rapid availability endpoint for a set of property IDs and dates.
   */
  // biome-ignore lint/suspicious/useAwait: Interface method that may be overridden
  async searchAvailability(
    params: EpsSearchRequest,
    context?: ExpediaRequestContext
  ): Promise<EpsSearchResponse> {
    const validated = EPS_SEARCH_REQUEST_SCHEMA.parse(params);
    const query = new URLSearchParams({
      checkin: validated.checkIn,
      checkout: validated.checkOut,
      // biome-ignore lint/style/useNamingConvention: Rapid expects snake_case query params
      country_code: validated.countryCode ?? "US",
      currency: validated.currency ?? "USD",
      language: validated.language ?? "en-US",
      occupancy: String(validated.guests),
      // biome-ignore lint/style/useNamingConvention: Rapid expects snake_case query params
      rate_plan_count: String(validated.ratePlanCount ?? 4),
      // biome-ignore lint/style/useNamingConvention: Rapid expects snake_case query params
      sales_channel: validated.salesChannel ?? "website",
      // biome-ignore lint/style/useNamingConvention: Rapid expects snake_case query params
      sales_environment: validated.salesEnvironment ?? "hotel_only",
      // biome-ignore lint/style/useNamingConvention: Rapid expects snake_case query params
      travel_purpose: validated.travelPurpose ?? "leisure",
    });

    for (const propertyId of validated.propertyIds) {
      query.append("property_id", propertyId);
    }
    // biome-ignore lint/suspicious/useIterableCallbackReturn: URLSearchParams.append returns URLSearchParams
    validated.include?.forEach((flag) => query.append("include", flag));
    // biome-ignore lint/suspicious/useIterableCallbackReturn: URLSearchParams.append returns URLSearchParams
    validated.amenityCategory?.forEach((category) =>
      query.append("amenity_category", category)
    );

    const path = `/properties/availability?${query.toString()}`;
    return this.request(
      path,
      { method: "GET" },
      context,
      EPS_AVAILABILITY_RESPONSE_SCHEMA
    );
  }

  /**
   * Retrieve property content (details, reviews, amenities).
   */
  async getPropertyDetails(
    params: EpsPropertyDetailsRequest,
    context?: ExpediaRequestContext
  ): Promise<EpsPropertyDetailsResponse> {
    const validated = EPS_PROPERTY_DETAILS_REQUEST_SCHEMA.parse(params);
    const query = new URLSearchParams({
      language: validated.language ?? "en-US",
      // biome-ignore lint/style/useNamingConvention: API query parameter
      supply_source: "expedia",
    });
    query.append("property_id", validated.propertyId);

    const path = `/properties/content?${query.toString()}`;
    const content = await this.request<RapidPropertyContentMap>(
      path,
      { method: "GET" },
      context,
      EPS_PROPERTY_CONTENT_RESPONSE_SCHEMA
    );

    const property = content[validated.propertyId];
    if (!property) {
      throw new ExpediaApiError("Property not found", "EPS_PROPERTY_NOT_FOUND", 404);
    }
    return property;
  }

  /**
   * Rapid price check for a room/rate combination. Returns booking links/tokens.
   */
  // biome-ignore lint/suspicious/useAwait: Interface method that may be overridden
  async priceCheck(
    params: { propertyId: string; roomId: string; rateId: string; token: string },
    context?: ExpediaRequestContext
  ): Promise<RapidPriceCheckResponse> {
    const validated = EPS_CHECK_AVAILABILITY_REQUEST_SCHEMA.parse(params);
    const path = `/properties/${validated.propertyId}/rooms/${validated.roomId}/rates/${validated.rateId}?token=${encodeURIComponent(
      validated.token
    )}`;
    return this.request(
      path,
      { method: "GET" },
      context,
      EPS_PRICE_CHECK_RESPONSE_SCHEMA
    );
  }

  /**
   * Wrap price-check to expose TripSage-friendly shape.
   */
  async checkAvailability(
    params: EpsCheckAvailabilityRequest,
    context?: ExpediaRequestContext
  ): Promise<EpsCheckAvailabilityResponse> {
    const response = await this.priceCheck(params, context);

    if (!response.links?.book && !response.links?.payment_session) {
      throw new ExpediaApiError(
        "Price check did not return a booking link",
        "EPS_PRICE_CHECK_NO_LINK",
        409
      );
    }

    const bookingLink = response.links.book ?? response.links.payment_session;
    const bookingToken = extractTokenFromLink(bookingLink);
    const expiresAt =
      extractExpiration(bookingLink) ??
      new Date(Date.now() + 15 * 60 * 1000).toISOString();
    const price =
      extractInclusiveTotal(response.occupancy_pricing?.["1"]) ??
      extractInclusiveTotal(
        response.occupancy_pricing
          ? Object.values(response.occupancy_pricing)[0]
          : undefined
      );

    if (!price) {
      throw new ExpediaApiError(
        "Unable to determine price from price check response",
        "EPS_PRICE_MISSING",
        422
      );
    }

    return EPS_CHECK_AVAILABILITY_RESPONSE_SCHEMA.parse({
      bookingToken,
      expiresAt,
      price,
      propertyId: params.propertyId,
      rateId: params.rateId,
      roomId: params.roomId,
    });
  }

  /**
   * Create itinerary/booking via Rapid.
   */
  // biome-ignore lint/suspicious/useAwait: Interface method that may be overridden
  async createBooking(
    request: EpsCreateBookingRequest,
    context?: ExpediaRequestContext
  ): Promise<EpsCreateBookingResponse> {
    const validated = EPS_CREATE_BOOKING_REQUEST_SCHEMA.parse(request);

    const path = `/itineraries?token=${encodeURIComponent(validated.bookingToken)}`;
    const payload = buildCreateItineraryPayload(validated);

    return this.request(
      path,
      {
        body: JSON.stringify(payload),
        method: "POST",
      },
      context,
      EPS_CREATE_BOOKING_RESPONSE_SCHEMA
    );
  }
}

/**
 * Utility helpers
 */
function extractTokenFromLink(link?: RapidLink): string {
  if (!link?.href) {
    throw new ExpediaApiError("Missing booking link", "EPS_BOOKING_LINK_MISSING", 409);
  }
  const url = new URL(link.href, "https://test.ean.com");
  const token = url.searchParams.get("token");
  if (!token) {
    throw new ExpediaApiError(
      "Booking token missing from link",
      "EPS_TOKEN_MISSING",
      409
    );
  }
  return token;
}

function extractExpiration(link?: RapidLink): string | undefined {
  const expirationParam = link?.href
    ? new URL(link.href, "https://test.ean.com")
    : null;
  const expiry = expirationParam?.searchParams.get("expires_at");
  return expiry ?? undefined;
}

function buildCreateItineraryPayload(request: EpsCreateBookingRequest) {
  const affiliateReference =
    request.affiliateReferenceId ?? request.bookingToken.slice(0, 28);
  const { givenName, familyName } = request.traveler;
  const billing = request.billingContact ?? {
    address: {
      city: "Unknown",
      countryCode: "US",
      line1: "Not Provided",
    },
    familyName,
    givenName,
  };

  return {
    // biome-ignore lint/style/useNamingConvention: API field name
    affiliate_reference_id: affiliateReference,
    email: request.contact.email,
    hold: request.hold ?? false,
    payments: [
      {
        // biome-ignore lint/style/useNamingConvention: API field name
        billing_contact: {
          address: {
            city: billing.address?.city ?? "Unknown",
            // biome-ignore lint/style/useNamingConvention: API field name
            country_code: billing.address?.countryCode ?? "US",
            // Rapid expects snake_case keys
            // biome-ignore lint/style/useNamingConvention: API field name
            line_1: billing.address?.line1 ?? "Not Provided",
            // biome-ignore lint/style/useNamingConvention: API field name
            line_2: billing.address?.line2,
            // biome-ignore lint/style/useNamingConvention: API field name
            line_3: billing.address?.line3,
            // biome-ignore lint/style/useNamingConvention: API field name
            postal_code: billing.address?.postalCode,
            // biome-ignore lint/style/useNamingConvention: API field name
            state_province_code: billing.address?.stateProvinceCode,
          },
          // biome-ignore lint/style/useNamingConvention: API field name
          family_name: billing.familyName,
          // biome-ignore lint/style/useNamingConvention: API field name
          given_name: billing.givenName,
        },
        type: "affiliate_collect",
      },
    ],
    phone: {
      // biome-ignore lint/style/useNamingConvention: API field name
      area_code: request.contact.phoneAreaCode,
      // biome-ignore lint/style/useNamingConvention: API field name
      country_code: request.contact.phoneCountryCode ?? "1",
      number: request.contact.phoneNumber ?? "0000000",
    },
    rooms: [
      {
        // biome-ignore lint/style/useNamingConvention: API field name
        child_ages: request.stay.childAges,
        // biome-ignore lint/style/useNamingConvention: API field name
        family_name: familyName,
        // biome-ignore lint/style/useNamingConvention: API field name
        given_name: givenName,
        // biome-ignore lint/style/useNamingConvention: API field name
        number_of_adults: request.stay.adults,
        // biome-ignore lint/style/useNamingConvention: API field name
        special_request: request.specialRequests,
      },
    ],
    // biome-ignore lint/style/useNamingConvention: API field name
    special_requests: request.specialRequests,
    // biome-ignore lint/style/useNamingConvention: API field name
    traveler_handling_instructions: undefined,
  };
}

/**
 * Singleton helper.
 */
let expediaClientInstance: ExpediaClient | undefined;

export function getExpediaClient(): ExpediaClient {
  if (!expediaClientInstance) {
    expediaClientInstance = new ExpediaClient();
  }
  return expediaClientInstance;
}
