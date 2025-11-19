/**
 * @fileoverview Expedia Rapid API client implementation.
 *
 * Provides a complete client for interacting with Expedia's Rapid API including
 * authentication, request building, and API method wrappers for availability,
 * property details, pricing, and booking operations.
 */

import "server-only";

import { createHash } from "node:crypto";

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
  type RapidPriceCheckResponse,
  type RapidPropertyContentMap,
} from "@/domain/schemas/expedia";
import { getServerEnvVar, getServerEnvVarWithFallback } from "@/lib/env/server";
import { secureUuid } from "@/lib/security/random";
import { ExpediaApiError, type ExpediaRequestContext } from "./client-types";
import { RAPID_PROD_DEFAULT_BASE_URL } from "./constants";
import { buildCreateItineraryPayload } from "./payload";
import { performRapidRequest } from "./request";
import { extractExpiration, extractTokenFromLink } from "./utils";

/**
 * Ensures environment variable is set and returns its value.
 *
 * @param value - Environment variable value.
 * @param name - Variable name for error message.
 * @returns Environment variable value.
 * @throws {Error} When environment variable is not set.
 */
function ensureEnv(value: string | undefined, name: string): string {
  if (!value) throw new Error(`${name} is required to call Expedia Rapid APIs`);
  return value;
}

/**
 * Client for Expedia Rapid API operations.
 *
 * Handles authentication, request signing, and all Rapid API endpoints
 * including property search, availability, booking, and price checking.
 */
export class ExpediaClient {
  private readonly apiKey: string;
  private readonly apiSecret: string;
  private readonly baseUrl: string;
  private readonly defaultCustomerIp: string;
  private readonly defaultUserAgent: string;

  /**
   * Creates Expedia Rapid API client with environment configuration.
   *
   * Initializes API credentials, base URL, and default request parameters
   * from environment variables with fallback defaults.
   */
  constructor() {
    this.apiKey = ensureEnv(getServerEnvVar("EPS_API_KEY"), "EPS_API_KEY");
    this.apiSecret = ensureEnv(getServerEnvVar("EPS_API_SECRET"), "EPS_API_SECRET");
    this.baseUrl =
      getServerEnvVarWithFallback("EPS_BASE_URL", RAPID_PROD_DEFAULT_BASE_URL) ??
      RAPID_PROD_DEFAULT_BASE_URL;
    this.defaultCustomerIp =
      getServerEnvVarWithFallback("EPS_DEFAULT_CUSTOMER_IP", "0.0.0.0") ?? "0.0.0.0";
    this.defaultUserAgent =
      getServerEnvVarWithFallback(
        "EPS_DEFAULT_USER_AGENT",
        "TripSage/1.0 (+https://tripsage.ai)"
      ) ?? "TripSage/1.0 (+https://tripsage.ai)";
  }

  /**
   * Generates Expedia API authentication header.
   *
   * Creates HMAC-SHA512 signature using API key, secret, and timestamp
   * as required by Rapid API authentication specification.
   *
   * @returns Authentication header string.
   * @private
   */
  private getAuthHeader(): string {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const toBeHashed = `${this.apiKey}${this.apiSecret}${timestamp}`;
    const signature = createHash("sha512").update(toBeHashed, "utf-8").digest("hex");
    return `EAN APIKey=${this.apiKey},Signature=${signature},timestamp=${timestamp}`;
  }

  /**
   * Builds HTTP headers for Rapid API requests.
   *
   * Constructs headers with authentication, content type, and request context
   * including customer IP, session ID, and user agent. Merges with existing headers.
   *
   * @param existingHeaders - Additional headers to merge.
   * @param context - Request context for customer-specific parameters.
   * @returns Headers object for fetch request.
   * @private
   */
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
    });

    if (context?.testScenario) {
      headers.set("Test", context.testScenario);
    }

    if (existingHeaders) {
      const overrides = new Headers(existingHeaders);
      for (const [key, value] of overrides.entries()) {
        headers.set(key, value);
      }
    }

    return headers;
  }

  /**
   * Searches for property availability using Rapid Shopping API.
   *
   * Queries available accommodations based on dates, occupancy, and property filters.
   * Returns detailed property information including rates, amenities, and availability.
   *
   * @param params - Search parameters including dates, guests, and property IDs.
   * @param context - Optional request context for customer-specific parameters.
   * @returns Promise resolving to availability search response.
   */
  searchAvailability(
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
    if (validated.include) {
      for (const flag of validated.include) {
        query.append("include", flag);
      }
    }
    if (validated.amenityCategory) {
      for (const category of validated.amenityCategory) {
        query.append("amenity_category", category);
      }
    }

    const path = `/properties/availability?${query.toString()}`;
    return performRapidRequest({
      baseUrl: this.baseUrl,
      buildHeaders: this.buildHeaders.bind(this),
      context,
      init: { method: "GET" },
      path,
      schema: EPS_AVAILABILITY_RESPONSE_SCHEMA,
      spanName: "rapid.shopping.availability",
    });
  }

  /**
   * Retrieves property details using Rapid Content API.
   *
   * @param params - Property details request with property ID and language.
   * @param context - Optional request context for customer-specific parameters.
   * @returns Promise resolving to property information.
   * @throws {ExpediaApiError} When property is not found.
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
    const content = await performRapidRequest<RapidPropertyContentMap>({
      baseUrl: this.baseUrl,
      buildHeaders: this.buildHeaders.bind(this),
      context,
      init: { method: "GET" },
      path,
      schema: EPS_PROPERTY_CONTENT_RESPONSE_SCHEMA,
      spanName: "rapid.content.property",
    });

    const property = content[validated.propertyId];
    if (!property) {
      throw new ExpediaApiError("Property not found", "EPS_PROPERTY_NOT_FOUND", 404);
    }
    return property;
  }

  /**
   * Checks pricing for a specific rate using Rapid Shopping API.
   *
   * @param params - Price check parameters with property, room, rate IDs and token.
   * @param context - Optional request context for customer-specific parameters.
   * @returns Promise resolving to price check response.
   */
  priceCheck(
    params: { propertyId: string; roomId: string; rateId: string; token: string },
    context?: ExpediaRequestContext
  ): Promise<RapidPriceCheckResponse> {
    const validated = EPS_CHECK_AVAILABILITY_REQUEST_SCHEMA.parse(params);
    const path = `/properties/${validated.propertyId}/rooms/${validated.roomId}/rates/${validated.rateId}?token=${encodeURIComponent(
      validated.token
    )}`;
    return performRapidRequest({
      baseUrl: this.baseUrl,
      buildHeaders: this.buildHeaders.bind(this),
      context,
      init: { method: "GET" },
      path,
      schema: EPS_PRICE_CHECK_RESPONSE_SCHEMA,
      spanName: "rapid.shopping.price_check",
    });
  }

  /**
   * Validates rate availability and extracts booking information.
   *
   * @param params - Availability check parameters with property, room, rate IDs and token.
   * @param context - Optional request context for customer-specific parameters.
   * @returns Promise resolving to availability check response with booking token and price.
   * @throws {ExpediaApiError} When booking link or price is unavailable.
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
   * Creates booking reservation using Rapid Booking API.
   *
   * @param request - Complete booking request with traveler, payment, and stay details.
   * @param context - Optional request context for customer-specific parameters.
   * @returns Promise resolving to booking confirmation response.
   */
  async createBooking(
    request: EpsCreateBookingRequest,
    context?: ExpediaRequestContext
  ): Promise<EpsCreateBookingResponse> {
    const validated = EPS_CREATE_BOOKING_REQUEST_SCHEMA.parse(request);
    const path = `/itineraries?token=${encodeURIComponent(validated.bookingToken)}`;
    const payload = buildCreateItineraryPayload(validated);

    return await performRapidRequest({
      baseUrl: this.baseUrl,
      buildHeaders: this.buildHeaders.bind(this),
      context,
      init: {
        body: JSON.stringify(payload),
        method: "POST",
      },
      path,
      schema: EPS_CREATE_BOOKING_RESPONSE_SCHEMA,
      spanName: "rapid.booking.create",
    });
  }
}

let expediaClientInstance: ExpediaClient | undefined;

/**
 * Gets singleton instance of Expedia Rapid API client.
 *
 * Creates client on first call and returns cached instance for subsequent calls.
 * Use this for most operations to avoid multiple client instantiations.
 *
 * @returns ExpediaClient singleton instance.
 */
export function getExpediaClient(): ExpediaClient {
  if (!expediaClientInstance) {
    expediaClientInstance = new ExpediaClient();
  }
  return expediaClientInstance;
}

/**
 * Creates new instance of Expedia Rapid API client.
 *
 * Use this when you need a fresh client instance with custom configuration.
 * Most use cases should use getExpediaClient() instead.
 *
 * @returns New ExpediaClient instance.
 */
export function createExpediaClient(): ExpediaClient {
  return new ExpediaClient();
}

export type { ExpediaRequestContext } from "./client-types";
export { ExpediaApiError } from "./client-types";
