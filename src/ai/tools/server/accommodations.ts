/**
 * @fileoverview Accommodation search, booking, and details tools wired through the accommodations service.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import type { AccommodationModelOutput } from "@ai/tools/schemas/accommodations";
import {
  createToolError,
  TOOL_ERROR_CODES,
  type ToolErrorCode,
} from "@ai/tools/server/errors";
import { getAccommodationsService } from "@domain/accommodations/container";
import { ProviderError } from "@domain/accommodations/errors";
import {
  type AccommodationBookingRequest,
  type AccommodationBookingResult,
  type AccommodationCheckAvailabilityParams,
  type AccommodationCheckAvailabilityResult,
  type AccommodationDetailsParams,
  type AccommodationDetailsResult,
  type AccommodationSearchParams,
  type AccommodationSearchResult,
  accommodationBookingInputSchema,
  accommodationBookingOutputSchema,
  accommodationCheckAvailabilityInputSchema,
  accommodationCheckAvailabilityOutputSchema,
  accommodationDetailsInputSchema,
  accommodationDetailsOutputSchema,
  accommodationSearchInputSchema,
  accommodationSearchOutputSchema,
} from "@schemas/accommodations";
import { headers } from "next/headers";
import { processBookingPayment } from "@/lib/payments/booking-payment";
import { secureUuid } from "@/lib/security/random";
import { createServerSupabase } from "@/lib/supabase/server";
import { requireApproval } from "./approvals";

/**
 * Accommodations service instance for tool execution.
 *
 * This service is initialized at module scope, creating a singleton instance.
 * Singleton initialization is appropriate here because:
 * - The service manages connection pooling and shared adapters.
 * - Avoids redundant creation of service instances for each tool execution.
 * - The service is lightweight and always needed for all exported tools.
 *
 * If future requirements change and lazy initialization is needed, refactor accordingly.
 */
const accommodationsService = getAccommodationsService();

export { accommodationSearchInputSchema as searchAccommodationsInputSchema };

/** Search for accommodations using Amadeus Self-Service API with Google Places enrichment. */
export const searchAccommodations = createAiTool<
  AccommodationSearchParams,
  AccommodationSearchResult
>({
  description:
    "Search for accommodations (hotels and stays) using Amadeus Self-Service APIs with Google Places enrichment. Supports semantic search via RAG for natural language queries.",
  execute: async (params) => {
    return accommodationsService.search(params, {
      sessionId: await maybeGetUserIdentifier(),
    });
  },
  inputSchema: accommodationSearchInputSchema,
  name: "searchAccommodations",
  outputSchema: accommodationSearchOutputSchema,
  /**
   * Simplifies accommodation results for model consumption to reduce token usage.
   * Strips photos, searchParameters, and compresses nested rates to essential pricing.
   */
  toModelOutput: (result): AccommodationModelOutput => {
    /**
     * Coerce string or number to number, returning undefined for non-parseable values.
     */
    const coerceToNumber = (
      val: string | number | undefined
    ): number | undefined => {
      if (val === undefined || val === null) return undefined;
      if (typeof val === "number") return val;
      const parsed = Number(val);
      return Number.isNaN(parsed) ? undefined : parsed;
    };

    /**
     * Compute the actual lowest price across all rooms and rates for a listing.
     * Falls back to undefined if no valid prices found.
     */
    const computeLowestPrice = (
      rooms?: Array<{ rates?: Array<{ price?: { total?: number | string } }> }>
    ): number | undefined => {
      if (!rooms?.length) return undefined;
      let lowest: number | undefined;
      for (const room of rooms) {
        if (!room.rates?.length) continue;
        for (const rate of room.rates) {
          const total = rate.price?.total;
          if (total === undefined || total === null) continue;
          const numVal = typeof total === "number" ? total : Number(total);
          if (Number.isNaN(numVal)) continue;
          if (lowest === undefined || numVal < lowest) {
            lowest = numVal;
          }
        }
      }
      return lowest;
    };

    const slicedListings = result.listings.slice(0, 10);
    return {
      avgPrice: result.avgPrice,
      fromCache: result.fromCache,
      listingCount: slicedListings.length,
      listings: slicedListings.map((listing) => ({
        amenities: listing.amenities?.slice(0, 5),
        geoCode: listing.geoCode,
        id: coerceToNumber(listing.id),
        lowestPrice: computeLowestPrice(listing.rooms),
        name: listing.name,
        rating: listing.place?.rating,
        starRating: listing.starRating,
      })),
      maxPrice: result.maxPrice,
      minPrice: result.minPrice,
      provider: result.provider,
      resultsReturned: result.resultsReturned,
      totalResults: result.totalResults,
    };
  },
  validateOutput: true,
});

/** Retrieve comprehensive details for a specific accommodation property from Amadeus and Google Places. */
export const getAccommodationDetails = createAiTool<
  AccommodationDetailsParams,
  AccommodationDetailsResult
>({
  description:
    "Retrieve details for a specific accommodation property from Amadeus hotel offers and Google Places content.",
  execute: async (params) => {
    try {
      return await accommodationsService.details(params);
    } catch (error) {
      throw mapProviderError(error, {
        failed: TOOL_ERROR_CODES.accomDetailsFailed,
        notFound: TOOL_ERROR_CODES.accomDetailsNotFound,
        rateLimited: TOOL_ERROR_CODES.accomDetailsRateLimited,
        unauthorized: TOOL_ERROR_CODES.accomDetailsUnauthorized,
      });
    }
  },
  inputSchema: accommodationDetailsInputSchema,
  name: "getAccommodationDetails",
  outputSchema: accommodationDetailsOutputSchema,
  validateOutput: true,
});

/** Check final availability and lock pricing for a specific rate. Returns a booking token that must be used quickly to finalize the booking. */
export const checkAvailability = createAiTool<
  AccommodationCheckAvailabilityParams,
  AccommodationCheckAvailabilityResult
>({
  description:
    "Check final availability and lock pricing for a specific rate. Returns a booking token that must be used quickly to finalize the booking.",
  execute: async (params) => {
    const userId = await getAuthenticatedUserId(
      TOOL_ERROR_CODES.accomBookingSessionRequired
    );
    try {
      return await accommodationsService.checkAvailability(params, {
        sessionId: userId,
        userId,
      });
    } catch (error) {
      throw mapProviderError(error, {
        failed: TOOL_ERROR_CODES.accomAvailabilityFailed,
        notFound: TOOL_ERROR_CODES.accomAvailabilityNotFound,
        rateLimited: TOOL_ERROR_CODES.accomAvailabilityRateLimited,
        unauthorized: TOOL_ERROR_CODES.accomAvailabilityUnauthorized,
      });
    }
  },
  inputSchema: accommodationCheckAvailabilityInputSchema,
  name: "checkAvailability",
  outputSchema: accommodationCheckAvailabilityOutputSchema,
  validateOutput: true,
});

/** Complete an accommodation booking via Amadeus. Requires a bookingToken from checkAvailability, payment method, and prior approval. */
export const bookAccommodation = createAiTool<
  AccommodationBookingRequest,
  AccommodationBookingResult
>({
  description:
    "Complete an accommodation booking via Amadeus Self-Service APIs. Requires a bookingToken from checkAvailability, payment method, and prior approval.",
  execute: async (params) => {
    const sessionId = params.sessionId ?? (await maybeGetUserIdentifier());
    if (!sessionId) {
      throw createToolError(TOOL_ERROR_CODES.accomBookingSessionRequired);
    }
    const userId = await getAuthenticatedUserId(
      TOOL_ERROR_CODES.accomBookingSessionRequired
    );
    const idempotencyKey = params.idempotencyKey ?? secureUuid();

    try {
      return await accommodationsService.book(params, {
        processPayment: ({ amountCents, currency }) =>
          processBookingPayment({
            amount: amountCents,
            currency,
            customerId: userId,
            paymentMethodId: params.paymentMethodId,
            user: {
              email: params.guestEmail,
              name: params.guestName,
              phone: params.guestPhone,
            },
          }),
        requestApproval: () =>
          requireApproval("bookAccommodation", {
            idempotencyKey,
            sessionId,
          }),
        sessionId,
        userId,
      });
    } catch (error) {
      throw mapProviderError(error, {
        failed: TOOL_ERROR_CODES.accomBookingFailed,
        notFound: TOOL_ERROR_CODES.accomBookingFailed,
        rateLimited: TOOL_ERROR_CODES.accomBookingFailed,
        unauthorized: TOOL_ERROR_CODES.accomBookingFailed,
      });
    }
  },
  inputSchema: accommodationBookingInputSchema,
  name: "bookAccommodation",
  outputSchema: accommodationBookingOutputSchema,
  validateOutput: true,
});

/** Extract user identifier from request headers or return undefined if not found. */
async function maybeGetUserIdentifier(): Promise<string | undefined> {
  try {
    const supabase = await createServerSupabase();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (user?.id) return user.id;
  } catch {
    // Fall back to header inspection below.
  }

  try {
    const requestHeaders = await headers();
    const userId = requestHeaders.get("x-user-id");
    const trimmed = userId?.trim();
    if (trimmed) {
      return trimmed;
    }
  } catch {
    // headers() can throw outside of a request context.
  }
  return undefined;
}

/** Get user identifier from request headers or throw an error if not found. */
async function getAuthenticatedUserId(errorCode: ToolErrorCode): Promise<string> {
  const supabase = await createServerSupabase();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (user?.id) {
    return user.id;
  }
  throw createToolError(errorCode);
}

/**
 * Map provider errors to tool errors.
 *
 * @param error Provider error to map.
 * @param codes Error code mappings for different provider error types.
 * @returns ToolError instance with appropriate error code and message.
 */
function mapProviderError(
  error: unknown,
  codes: {
    notFound: ToolErrorCode;
    rateLimited: ToolErrorCode;
    unauthorized: ToolErrorCode;
    failed: ToolErrorCode;
  }
) {
  if (error instanceof ProviderError) {
    if (error.code === "not_found") {
      return createToolError(codes.notFound);
    }
    if (error.code === "rate_limited") {
      return createToolError(codes.rateLimited);
    }
    if (error.code === "unauthorized") {
      return createToolError(codes.unauthorized);
    }
  }
  return createToolError(codes.failed, undefined, {
    error: error instanceof Error ? error.message : "Unknown error",
  });
}
