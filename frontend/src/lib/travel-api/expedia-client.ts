/**
 * @fileoverview Expedia Partner Solutions (EPS) Rapid API client.
 *
 * Server-only module for interacting with EPS API. Handles authentication,
 * property search, details retrieval, availability checks, and booking creation.
 */

import "server-only";

import { getServerEnvVar, getServerEnvVarWithFallback } from "@/lib/env/server";
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

  constructor() {
    this.apiKey = getServerEnvVar("EPS_API_KEY") ?? "";
    this.apiSecret = getServerEnvVar("EPS_API_SECRET") ?? "";
    this.baseUrl =
      getServerEnvVarWithFallback(
        "EPS_BASE_URL",
        "https://api.expediapartnersolutions.com/v1"
      ) ?? "https://api.expediapartnersolutions.com/v1";

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
    return `Bearer ${this.apiKey}`;
  }

  /**
   * Make authenticated request to EPS API.
   *
   * @param endpoint - API endpoint path (relative to baseUrl)
   * @param options - Fetch options (method, body, etc.)
   * @returns Parsed JSON response
   * @throws {ExpediaApiError} On API errors
   */
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const authToken = await this.getAuthToken();

    const response = await fetch(url, {
      ...options,
      headers: {
        // biome-ignore lint/style/useNamingConvention: HTTP header names use PascalCase
        Authorization: authToken,
        "Content-Type": "application/json",
        "X-API-Key": this.apiKey, // Some EPS APIs use X-API-Key header
        ...options.headers,
      },
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
  async search(params: EpsSearchRequest): Promise<EpsSearchResponse> {
    // Build query parameters
    const queryParams = new URLSearchParams({
      checkIn: params.checkIn,
      checkOut: params.checkOut,
      guests: String(params.guests),
      location: params.location,
    });

    if (params.propertyIds && params.propertyIds.length > 0) {
      queryParams.append("propertyIds", params.propertyIds.join(","));
    }
    if (params.priceMin !== undefined) {
      queryParams.append("priceMin", String(params.priceMin));
    }
    if (params.priceMax !== undefined) {
      queryParams.append("priceMax", String(params.priceMax));
    }
    if (params.amenities && params.amenities.length > 0) {
      queryParams.append("amenities", params.amenities.join(","));
    }
    if (params.propertyTypes && params.propertyTypes.length > 0) {
      queryParams.append("propertyTypes", params.propertyTypes.join(","));
    }

    // TODO: Update endpoint path per actual EPS API documentation
    // This is a placeholder based on common REST API patterns
    const endpoint = `/properties/availability?${queryParams.toString()}`;

    return await this.request<EpsSearchResponse>(endpoint, {
      method: "GET",
    });
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
