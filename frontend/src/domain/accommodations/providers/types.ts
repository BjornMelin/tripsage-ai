/**
 * @fileoverview Provider-agnostic accommodation adapter types.
 *
 * Replaces Expedia-specific DTOs with neutral contracts used by Amadeus + Google Places stack.
 */

import type { ProviderError } from "@domain/accommodations/errors";
import type {
  AccommodationBookingRequest,
  AccommodationCheckAvailabilityParams,
  AccommodationDetailsParams,
  AccommodationSearchParams,
} from "@schemas/accommodations";

/** Supported accommodation provider names. */
export type ProviderName = "amadeus";

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

/** Result of a provider search operation. */
export type ProviderSearchResult = {
  listings: Array<Record<string, unknown>>;
  total?: number;
  currency?: string;
};

/** Result of a provider details operation. */
export type ProviderDetailsResult = {
  listing: Record<string, unknown>;
};

/** Result of a provider availability operation. */
export type ProviderAvailabilityResult = {
  bookingToken: string;
  expiresAt: string;
  price: {
    currency: string;
    total: string;
    breakdown?: {
      base?: string;
      fees?: string;
      taxes?: string;
    };
  };
  propertyId: string;
  rateId: string;
};

/** Payload for a provider booking operation. */
export type ProviderBookingPayload = Record<string, unknown>;

/** Result of a provider booking operation. */
export type ProviderBookingResult = {
  itineraryId?: string;
  confirmationNumber?: string;
  providerBookingId?: string;
  message?: string;
};

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
   */
  search(
    params: AccommodationSearchParams,
    ctx?: ProviderContext
  ): Promise<ProviderResult<ProviderSearchResult>>;

  /**
   * Get detailed information for a specific property.
   */
  getDetails(
    params: AccommodationDetailsParams,
    ctx?: ProviderContext
  ): Promise<ProviderResult<ProviderDetailsResult>>;

  /**
   * Verify room availability and get booking token.
   */
  checkAvailability(
    params: AccommodationCheckAvailabilityParams,
    ctx?: ProviderContext
  ): Promise<ProviderResult<ProviderAvailabilityResult>>;

  /**
   * Create a booking reservation.
   */
  createBooking(
    payload: ProviderBookingPayload,
    ctx?: ProviderContext
  ): Promise<ProviderResult<ProviderBookingResult>>;

  /**
   * Build provider-specific booking payload from normalized request.
   */
  buildBookingPayload(
    params: AccommodationBookingRequest,
    options?: {
      paymentIntentId?: string;
      currency?: string;
      totalCents?: number;
    }
  ): ProviderBookingPayload;
}
