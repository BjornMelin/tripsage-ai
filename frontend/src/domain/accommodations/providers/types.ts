/**
 * @fileoverview Type definitions for accommodation provider adapters.
 *
 * Defines interfaces and types for integrating with external accommodation
 * providers, including error handling and result types.
 */

import type { ProviderError } from "@domain/accommodations/errors";
import type {
  EpsCheckAvailabilityRequest,
  EpsCheckAvailabilityResponse,
  EpsCreateBookingRequest,
  EpsCreateBookingResponse,
  EpsPropertyDetailsResponse,
  EpsSearchRequest,
  EpsSearchResponse,
  RapidPriceCheckResponse,
} from "@schemas/expedia";

/** Supported accommodation provider names. */
export type ProviderName = "expedia";

/** Context information passed to provider operations. */
export type ProviderContext = {
  userId?: string;
  sessionId?: string;
  userAgent?: string;
  clientIp?: string;
  testScenario?: string;
};

/** Result of a provider operation with success/failure states and retry tracking. */
export type ProviderResult<T> =
  | { ok: true; value: T; retries: number }
  | { ok: false; error: ProviderError; retries: number };

/**
 * Abstraction for any accommodation supply provider.
 *
 * Implementations must wrap provider-specific errors into {@link ProviderError}
 * and surface retry counts for telemetry.
 */
export interface AccommodationProviderAdapter {
  /** Provider identifier for telemetry and error tracking. */
  readonly name: ProviderName;

  /**
   * Search for available accommodations matching criteria.
   * 
   * @param params - Search criteria including dates, guests, and property IDs
   * @param ctx - Optional context for the operation
   * @returns Search results or error with retry count
   */
  searchAvailability(
    params: EpsSearchRequest,
    ctx?: ProviderContext
  ): Promise<ProviderResult<EpsSearchResponse>>;

  /**
   * Get detailed information for a specific property.
   * 
   * @param params - Property identifier and optional language preference
   * @param ctx - Optional context for the operation
   * @returns Property details or error with retry count
   */
  getPropertyDetails(
    params: { propertyId: string; language?: string },
    ctx?: ProviderContext
  ): Promise<ProviderResult<EpsPropertyDetailsResponse>>;

  /**
   * Verify room availability and get booking token.
   * 
   * @param params - Availability check parameters with property, room, and rate IDs
   * @param ctx - Optional context for the operation
   * @returns Availability confirmation with token or error with retry count
   */
  checkAvailability(
    params: EpsCheckAvailabilityRequest,
    ctx?: ProviderContext
  ): Promise<ProviderResult<EpsCheckAvailabilityResponse>>;

  /**
   * Check current pricing for a room/rate combination.
   * 
   * @param params - Pricing check parameters including token from availability check
   * @param ctx - Optional context for the operation
   * @returns Current pricing information or error with retry count
   */
  priceCheck(
    params: { propertyId: string; roomId: string; rateId: string; token: string },
    ctx?: ProviderContext
  ): Promise<ProviderResult<RapidPriceCheckResponse>>;

  /**
   * Create a booking reservation.
   * 
   * @param params - Complete booking request with guest and payment information
   * @param ctx - Optional context for the operation
   * @returns Booking confirmation or error with retry count
   */
  createBooking(
    params: EpsCreateBookingRequest,
    ctx?: ProviderContext
  ): Promise<ProviderResult<EpsCreateBookingResponse>>;
}
