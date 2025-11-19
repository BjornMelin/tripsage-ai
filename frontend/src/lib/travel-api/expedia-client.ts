/**
 * @fileoverview Expedia Partner Solutions (EPS) Rapid API client.
 *
 * Server-only module for interacting with EPS API. Handles authentication,
 * property search, details retrieval, availability checks, and booking creation.
 */

import "server-only";

import { getServerEnvVar, getServerEnvVarWithFallback } from "@/lib/env/server";
import { secureUuid } from "@/lib/security/random";
import type {
  EpsCheckAvailabilityRequest,
  EpsCheckAvailabilityResponse,
  EpsCreateBookingRequest,
  EpsCreateBookingResponse,
  EpsPropertyDetailsRequest,
  EpsPropertyDetailsResponse,
  EpsSearchRequest,
  EpsSearchResponse,
} from "./expedia-types";

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

/**
 * Expedia Partner Solutions API client.
 *
 * Provides methods for searching properties, retrieving details,
 * checking availability, and creating bookings.
 */
export class ExpediaClient {
  private readonly apiKey: string;
  private readonly apiSecret: string;
  private readonly baseUrl: string;
  private readonly defaultCustomerIp: string;
  private readonly defaultUserAgent: string;

  constructor() {
    this.apiKey = getServerEnvVar("EPS_API_KEY") ?? "";
    this.apiSecret = getServerEnvVar("EPS_API_SECRET") ?? "";
    this.baseUrl =
      getServerEnvVarWithFallback("EPS_BASE_URL", "https://api.ean.com/v3") ??
      "https://api.ean.com/v3";
    this.defaultCustomerIp = String(
      getServerEnvVarWithFallback("EPS_DEFAULT_CUSTOMER_IP", "0.0.0.0") ?? "0.0.0.0"
    );
    this.defaultUserAgent = String(
      getServerEnvVarWithFallback(
        "EPS_DEFAULT_USER_AGENT",
        "TripSage/1.0 (+https://tripsage.ai)"
      ) ?? "TripSage/1.0 (+https://tripsage.ai)"
    );

    if (!this.apiKey || !this.apiSecret) {
      throw new Error(
        "EPS_API_KEY and EPS_API_SECRET environment variables are required"
      );
    }
  }

  /**
   * Get authentication token for EPS API.
   *
   * EPS Rapid API typically uses OAuth 2.0 or API key authentication.
   * This is a placeholder implementation; actual auth method depends on
   * EPS API documentation.
   *
   * @returns Authorization header value
   */
  private getAuthToken(): string {
    // TODO: Implement actual OAuth 2.0 flow or API key auth per EPS docs
    // For now, using simple API key header format (common pattern)
    // Real implementation should follow EPS API authentication spec
    // return `Bearer ${this.apiKey}`;

    // Placeholder: EPS typically requires Basic auth or OAuth; encode key+secret for now.
    const credentials = Buffer.from(
      `${this.apiKey}:${this.apiSecret}`,
      "utf-8"
    ).toString("base64");
    return `Basic ${credentials}`;
  }

  private buildHeaders(
    existingHeaders: HeadersInit | undefined,
    context: ExpediaRequestContext | undefined,
    authToken: string
  ): Headers {
    const resolvedContext: Required<Omit<ExpediaRequestContext, "testScenario">> & {
      testScenario?: string;
    } = {
      customerIp: context?.customerIp ?? this.defaultCustomerIp,
      customerSessionId: context?.customerSessionId ?? secureUuid(),
      testScenario: context?.testScenario,
      userAgent: context?.userAgent ?? this.defaultUserAgent,
    };

    const headers = new Headers({
      // biome-ignore lint/style/useNamingConvention: HTTP header names use PascalCase
      Accept: "application/json",
      "Accept-Encoding": "gzip",
      // biome-ignore lint/style/useNamingConvention: HTTP header names use PascalCase
      Authorization: authToken,
      "Content-Type": "application/json",
      "Customer-Ip": resolvedContext.customerIp,
      "Customer-Session-Id": resolvedContext.customerSessionId,
      "User-Agent": resolvedContext.userAgent,
      "X-API-Key": this.apiKey, // Some EPS APIs use X-API-Key header
    });

    if (resolvedContext.testScenario) {
      headers.set("Test", resolvedContext.testScenario);
    }

    if (existingHeaders) {
      const overrides = new Headers(existingHeaders);
      overrides.forEach((value, key) => {
        headers.set(key, value);
      });
    }

    return headers;
  }

  /**
   * Make authenticated request to EPS API.
   *
   * SECURITY NOTE: If adding logging/telemetry to this method, ensure the
   * Authorization and X-API-Key headers are redacted to prevent credential
   * exposure. The headers object contains sensitive authentication data.
   *
   * @param endpoint - API endpoint path (relative to baseUrl)
   * @param options - Fetch options (method, body, etc.)
   * @returns Parsed JSON response
   * @throws {ExpediaApiError} On API errors
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    context?: ExpediaRequestContext
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const authToken = await this.getAuthToken();
    const headers = this.buildHeaders(options.headers, context, authToken);

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unknown error");
      let errorData: { code?: string; message?: string } = {};
      try {
        errorData = JSON.parse(errorText);
      } catch {
        // Ignore JSON parse errors
      }

      throw new ExpediaApiError(
        errorData.message ?? `EPS API error: ${response.statusText}`,
        errorData.code ?? "EPS_API_ERROR",
        response.status,
        { endpoint, statusText: response.statusText }
      );
    }

    return response.json() as Promise<T>;
  }

  /**
   * Search for accommodations (hotels and Vrbo properties).
   *
   * @param params - Search parameters (location, dates, guests, filters)
   * @returns Search results with properties
   * @throws {ExpediaApiError} On API errors
   */
  async search(
    params: EpsSearchRequest,
    context?: ExpediaRequestContext
  ): Promise<EpsSearchResponse> {
    if (!params.propertyIds || params.propertyIds.length === 0) {
      throw new ExpediaApiError(
        "Rapid Shopping API requires at least one propertyId per request",
        "EPS_INVALID_REQUEST"
      );
    }

    const queryParams = new URLSearchParams({
      checkin: params.checkIn,
      checkout: params.checkOut,
      // biome-ignore lint/style/useNamingConvention: EPS query parameters use snake_case
      country_code: params.countryCode ?? "US",
      currency: params.currency ?? "USD",
      language: params.language ?? "en-US",
      // biome-ignore lint/style/useNamingConvention: EPS query parameters use snake_case
      rate_plan_count: String(params.ratePlanCount ?? 4),
      // biome-ignore lint/style/useNamingConvention: EPS query parameters use snake_case
      sales_channel: params.salesChannel ?? "website",
      // biome-ignore lint/style/useNamingConvention: EPS query parameters use snake_case
      sales_environment: params.salesEnvironment ?? "hotel_only",
      // biome-ignore lint/style/useNamingConvention: EPS query parameters use snake_case
      travel_purpose: params.travelPurpose ?? "leisure",
    });

    queryParams.append("occupancy", String(params.guests));
    for (const id of params.propertyIds) {
      queryParams.append("property_id", id);
    }

    if (params.include) {
      for (const flag of params.include) {
        queryParams.append("include", flag);
      }
    }
    if (params.amenityCategory) {
      for (const category of params.amenityCategory) {
        queryParams.append("amenity_category", category);
      }
    }

    const endpoint = `/properties/availability?${queryParams.toString()}`;

    return await this.request<EpsSearchResponse>(endpoint, { method: "GET" }, context);
  }

  /**
   * Get detailed information for a specific property.
   *
   * @param params - Property details request (propertyId, optional dates/guests)
   * @returns Property details with full information
   * @throws {ExpediaApiError} On API errors
   */
  async getPropertyDetails(
    params: EpsPropertyDetailsRequest
  ): Promise<EpsPropertyDetailsResponse> {
    const queryParams = new URLSearchParams({
      propertyId: params.propertyId,
    });

    if (params.checkIn) {
      queryParams.append("checkIn", params.checkIn);
    }
    if (params.checkOut) {
      queryParams.append("checkOut", params.checkOut);
    }
    if (params.guests !== undefined) {
      queryParams.append("guests", String(params.guests));
    }

    // TODO: Update endpoint path per actual EPS API documentation
    const endpoint = `/properties/${params.propertyId}?${queryParams.toString()}`;

    return await this.request<EpsPropertyDetailsResponse>(endpoint, {
      method: "GET",
    });
  }

  /**
   * Check availability and get booking token for a specific rate.
   *
   * @param params - Availability check parameters (propertyId, rateId, dates, guests)
   * @returns Booking token and final price
   * @throws {ExpediaApiError} On API errors
   */
  async checkAvailability(
    params: EpsCheckAvailabilityRequest
  ): Promise<EpsCheckAvailabilityResponse> {
    // TODO: Update endpoint path per actual EPS API documentation
    // This endpoint typically returns a booking token that locks the price
    const endpoint = `/properties/${params.propertyId}/rates/${params.rateId}/availability`;

    return await this.request<EpsCheckAvailabilityResponse>(endpoint, {
      body: JSON.stringify({
        checkIn: params.checkIn,
        checkOut: params.checkOut,
        guests: params.guests,
      }),
      method: "POST",
    });
  }

  /**
   * Create a booking using a valid booking token.
   *
   * @param params - Booking request (bookingToken, payment, user details)
   * @returns Booking confirmation
   * @throws {ExpediaApiError} On API errors
   */
  async createBooking(
    params: EpsCreateBookingRequest
  ): Promise<EpsCreateBookingResponse> {
    // TODO: Update endpoint path per actual EPS API documentation
    const endpoint = "/bookings";

    return await this.request<EpsCreateBookingResponse>(endpoint, {
      body: JSON.stringify({
        bookingToken: params.bookingToken,
        guest: {
          email: params.user.email,
          name: params.user.name,
          phone: params.user.phone,
        },
        payment: {
          method: "stripe",
          paymentIntentId: params.payment.paymentIntentId,
          paymentMethodId: params.payment.paymentMethodId,
        },
        specialRequests: params.specialRequests,
      }),
      method: "POST",
    });
  }
}

/**
 * Singleton Expedia client instance.
 *
 * Creates a single instance per server process to reuse connections.
 */
let expediaClientInstance: ExpediaClient | undefined;

/**
 * Get or create the Expedia client instance.
 *
 * @returns ExpediaClient instance
 * @throws {Error} If EPS API keys are not configured
 */
export function getExpediaClient(): ExpediaClient {
  if (!expediaClientInstance) {
    expediaClientInstance = new ExpediaClient();
  }
  return expediaClientInstance;
}
