/**
 * @fileoverview Accommodation search, booking, and details tools.
 *
 * Integrates with Expedia Partner Solutions (EPS) Rapid API for accommodation
 * search, details retrieval, availability checks, and bookings. Supports RAG
 * semantic search via Supabase pg-vector for enhanced search capabilities.
 * Booking operations require user approval and use Stripe for payment processing.
 */

import "server-only";

import { Ratelimit } from "@upstash/ratelimit";
import { tool } from "ai";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import {
  generateEmbedding,
  getEmbeddingsApiUrl,
  getEmbeddingsRequestHeaders,
} from "@/lib/embeddings/generate";
import { processBookingPayment } from "@/lib/payments/booking-payment";
import { getRedis } from "@/lib/redis";
import {
  ACCOMMODATION_BOOKING_INPUT_SCHEMA,
  ACCOMMODATION_BOOKING_OUTPUT_SCHEMA,
  ACCOMMODATION_CHECK_AVAILABILITY_INPUT_SCHEMA,
  ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA,
  ACCOMMODATION_DETAILS_INPUT_SCHEMA,
  ACCOMMODATION_DETAILS_OUTPUT_SCHEMA,
  ACCOMMODATION_SEARCH_INPUT_SCHEMA,
  ACCOMMODATION_SEARCH_OUTPUT_SCHEMA,
  type AccommodationBookingResult,
  type AccommodationCheckAvailabilityResult,
  type AccommodationDetailsResult,
  type AccommodationSearchResult,
} from "@/lib/schemas/accommodations";
import { secureUuid } from "@/lib/security/random";
import { createServerSupabase } from "@/lib/supabase/server";
import { createToolError, TOOL_ERROR_CODES } from "@/lib/tools/errors";
import { ExpediaApiError, getExpediaClient } from "@/lib/travel-api/expedia-client";
import type {
  EpsCheckAvailabilityResponse,
  EpsProperty,
  EpsPropertyDetailsResponse,
  EpsSearchResponse,
} from "@/lib/travel-api/expedia-types";
import { requireApproval } from "./approvals";
import { ACCOM_SEARCH_CACHE_TTL_SECONDS } from "./constants";

/**
 * Zod input schema for accommodation search tool.
 *
 * Exported for use in guardrails validation and cache key generation.
 */
export { ACCOMMODATION_SEARCH_INPUT_SCHEMA as searchAccommodationsInputSchema };

/**
 * Get rate limiter for accommodation tools.
 */
function getRateLimiter(): Ratelimit | undefined {
  const redis = getRedis();
  if (!redis) return undefined;

  return new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(10, "1 m"),
    prefix: "ratelimit:accommodations",
    redis,
  });
}

/**
 * Search accommodations tool.
 *
 * Searches for accommodations using Expedia Partner Solutions API with optional
 * RAG semantic search for enhanced results. Supports comprehensive filtering by
 * property types, amenities, price range, guest counts, and more. Results are
 * cached for performance.
 *
 * @returns AccommodationSearchResult with listings, pricing metadata, and search parameters.
 */
export const searchAccommodations = tool({
  description:
    "Search for accommodations (hotels and Vrbo vacation rentals) using Expedia Partner Solutions API. " +
    "Supports semantic search via RAG for natural language queries (e.g., 'quiet place near the beach', " +
    "'good for families with kids', 'has a full kitchen'). Returns properties with pricing, availability, " +
    "and detailed information. Use this tool first to find properties, then use getAccommodationDetails " +
    "for more information, checkAvailability to get booking tokens, and bookAccommodation to complete reservations. " +
    "Filters supported: property types (hotel, apartment, house, villa, resort), amenities, price range, " +
    "guest counts, instant book availability, cancellation policy, distance, rating, and sorting options.",
  execute: async (params): Promise<AccommodationSearchResult> => {
    const validated = ACCOMMODATION_SEARCH_INPUT_SCHEMA.parse(params);
    const startedAt = Date.now();

    // 1. Auth check
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const user = auth?.user;
    if (!user) {
      throw createToolError(TOOL_ERROR_CODES.accomSearchUnauthorized);
    }

    // 2. Rate limiting
    const ratelimit = getRateLimiter();
    if (ratelimit) {
      const { success } = await ratelimit.limit(user.id);
      if (!success) {
        throw createToolError(TOOL_ERROR_CODES.accomSearchRateLimited);
      }
    }

    // 3. Cache check
    const redis = getRedis();
    const cacheKey = canonicalizeParamsForCache(
      {
        ...validated,
        semanticQuery: validated.semanticQuery || "",
      },
      "accom_search"
    );

    if (!validated.fresh && redis) {
      const cached = await redis.get(cacheKey);
      if (cached) {
        const cachedData = cached as AccommodationSearchResult;
        const rawOut = {
          ...cachedData,
          fromCache: true,
          provider: "cache" as const,
          tookMs: Date.now() - startedAt,
        };
        return ACCOMMODATION_SEARCH_OUTPUT_SCHEMA.parse(rawOut);
      }
    }

    // 4. Hybrid RAG Search (if semanticQuery provided)
    let propertyIds: string[] | undefined;
    if (validated.semanticQuery && validated.semanticQuery.trim().length > 0) {
      try {
        const queryEmbedding = await generateEmbedding(validated.semanticQuery);
        // biome-ignore lint/suspicious/noExplicitAny: Supabase RPC types are not fully generated
        const { data: ragResults, error: ragError } = await (supabase as any).rpc(
          "match_accommodation_embeddings",
          {
            // biome-ignore lint/style/useNamingConvention: Database function parameters use snake_case
            match_count: 20,
            // biome-ignore lint/style/useNamingConvention: Database function parameters use snake_case
            match_threshold: 0.75,
            // biome-ignore lint/style/useNamingConvention: Database function parameters use snake_case
            query_embedding: queryEmbedding,
          }
        );

        if (!ragError && ragResults && Array.isArray(ragResults)) {
          propertyIds = (ragResults as Array<{ id: string }>).map((item) => item.id);
          if (propertyIds.length > 0) {
            console.log(
              `[RAG] Found ${propertyIds.length} semantic matches for: ${validated.semanticQuery}`
            );
          }
        }
      } catch (ragErr) {
        console.error("[RAG] Semantic search error:", ragErr);
        // Continue without RAG filtering if it fails
      }
    }

    // 5. Live API call to Expedia
    const expediaClient = getExpediaClient();
    let searchResponse: EpsSearchResponse;
    try {
      searchResponse = await expediaClient.search({
        amenities: validated.amenities,
        checkIn: validated.checkin,
        checkOut: validated.checkout,
        guests: validated.guests,
        location: validated.location.trim(),
        priceMax: validated.priceMax,
        priceMin: validated.priceMin,
        propertyIds: propertyIds && propertyIds.length > 0 ? propertyIds : undefined,
        propertyTypes: validated.propertyTypes,
      });
    } catch (error) {
      if (error instanceof ExpediaApiError) {
        if (error.statusCode === 429) {
          throw createToolError(TOOL_ERROR_CODES.accomSearchRateLimited);
        }
        if (error.statusCode === 401) {
          throw createToolError(TOOL_ERROR_CODES.accomSearchUnauthorized);
        }
      }
      throw createToolError(TOOL_ERROR_CODES.accomSearchFailed, undefined, {
        error: error instanceof Error ? error.message : "Unknown error",
      });
    }

    const searchId = secureUuid();
    const tookMs = Date.now() - startedAt;

    // Transform EPS response to our schema format
    const listings: EpsProperty[] = searchResponse.properties || [];
    const prices = listings
      .flatMap(
        (p: EpsProperty) =>
          p.rates?.map((r: { price: { total: string } }) =>
            parseFloat(r.price.total.replace(/[^0-9.]/g, ""))
          ) || []
      )
      .filter(
        (p: number | string): p is number => typeof p === "number" && !Number.isNaN(p)
      );

    const rawOut = {
      avgPrice:
        prices.length > 0
          ? prices.reduce((a: number, b: number) => a + b, 0) / prices.length
          : undefined,
      fromCache: false,
      listings: listings.map((p) => ({
        ...p,
        source: p.source, // 'hotel' or 'vrbo'
      })),
      maxPrice: prices.length > 0 ? Math.max(...prices) : undefined,
      minPrice: prices.length > 0 ? Math.min(...prices) : undefined,
      provider: "expedia" as const,
      resultsReturned: listings.length,
      searchId,
      searchParameters: {
        checkin: validated.checkin,
        checkout: validated.checkout,
        guests: validated.guests,
        location: validated.location,
        semanticQuery: validated.semanticQuery,
      },
      status: "success" as const,
      tookMs,
      totalResults: searchResponse.totalResults || listings.length,
    };

    // Validate against strict schema
    const validatedResult = ACCOMMODATION_SEARCH_OUTPUT_SCHEMA.parse(rawOut);

    // 6. Cache result
    if (redis && !validated.fresh) {
      await redis.set(cacheKey, validatedResult, {
        ex: ACCOM_SEARCH_CACHE_TTL_SECONDS,
      });
    }

    // 7. Async embedding generation for new properties (fire-and-forget)
    if (listings.length > 0 && typeof fetch === "function") {
      const embeddingsUrl = getEmbeddingsApiUrl();
      const embeddingsHeaders = getEmbeddingsRequestHeaders();

      for (const property of listings) {
        fetch(embeddingsUrl, {
          body: JSON.stringify({
            property: {
              amenities: property.amenities || [],
              description: property.description,
              id: property.id,
              name: property.name,
              source: property.source,
            },
          }),
          headers: embeddingsHeaders,
          method: "POST",
        })
          .then(() => undefined)
          .catch((err) => {
            console.error(`Failed to trigger embedding for ${property.id}:`, err);
          });
      }
    }

    return validatedResult;
  },
  inputSchema: ACCOMMODATION_SEARCH_INPUT_SCHEMA,
});

/**
 * Get accommodation details tool.
 *
 * Retrieves detailed information for a specific accommodation listing from
 * Expedia Partner Solutions. Optionally accepts check-in/out dates and guest
 * counts for accurate pricing and availability.
 *
 * @returns AccommodationDetailsResult with full listing information and provider metadata.
 */
export const getAccommodationDetails = tool({
  description:
    "Retrieve comprehensive details for a specific accommodation property from Expedia Partner Solutions. " +
    "Returns full property information including amenities, policies, reviews, photos, and current rates. " +
    "Optionally provide check-in/out dates and guest counts for accurate pricing and availability. " +
    "Use this after searchAccommodations to get more information about a specific property before booking.",
  execute: async (params): Promise<AccommodationDetailsResult> => {
    const validated = ACCOMMODATION_DETAILS_INPUT_SCHEMA.parse(params);

    const expediaClient = getExpediaClient();
    let propertyDetails: EpsPropertyDetailsResponse | null;
    try {
      propertyDetails = await expediaClient.getPropertyDetails({
        checkIn: validated.checkin,
        checkOut: validated.checkout,
        guests: validated.adults || 1,
        propertyId: validated.listingId,
      });
    } catch (error) {
      if (error instanceof ExpediaApiError) {
        if (error.statusCode === 404) {
          throw createToolError(TOOL_ERROR_CODES.accomDetailsNotFound);
        }
        if (error.statusCode === 429) {
          throw createToolError(TOOL_ERROR_CODES.accomDetailsRateLimited);
        }
        if (error.statusCode === 401) {
          throw createToolError(TOOL_ERROR_CODES.accomDetailsUnauthorized);
        }
      }
      throw createToolError(TOOL_ERROR_CODES.accomDetailsFailed, undefined, {
        error: error instanceof Error ? error.message : "Unknown error",
      });
    }

    const rawOut = {
      listing: propertyDetails,
      provider: "expedia" as const,
      status: "success" as const,
    };

    return ACCOMMODATION_DETAILS_OUTPUT_SCHEMA.parse(rawOut);
  },
  inputSchema: ACCOMMODATION_DETAILS_INPUT_SCHEMA,
});

/**
 * Check availability tool.
 *
 * Confirms final price and availability for a specific property rate, returning
 * a booking token required for booking. Requires user authentication.
 *
 * @returns AccommodationCheckAvailabilityResult with booking token and final price.
 */
export const checkAvailability = tool({
  description:
    "Check final availability and lock pricing for a specific accommodation rate. " +
    "Returns a booking token that must be used within a short time window (typically 5-15 minutes) " +
    "to complete the booking. This token locks the price and confirms availability. " +
    "Requires user authentication. Use this after getAccommodationDetails to get a bookable rate. " +
    "The returned bookingToken must be passed to bookAccommodation to finalize the reservation.",
  execute: async (params): Promise<AccommodationCheckAvailabilityResult> => {
    const validated = ACCOMMODATION_CHECK_AVAILABILITY_INPUT_SCHEMA.parse(params);

    // Auth check (required for booking)
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const user = auth?.user;
    if (!user) {
      throw createToolError(TOOL_ERROR_CODES.accomBookingSessionRequired);
    }

    const expediaClient = getExpediaClient();
    let availabilityResponse: EpsCheckAvailabilityResponse;
    try {
      availabilityResponse = await expediaClient.checkAvailability({
        checkIn: validated.checkIn,
        checkOut: validated.checkOut,
        guests: validated.guests,
        propertyId: validated.propertyId,
        rateId: validated.rateId,
      });
    } catch (error) {
      if (error instanceof ExpediaApiError) {
        if (error.statusCode === 404) {
          throw createToolError(TOOL_ERROR_CODES.accomDetailsNotFound);
        }
        if (error.statusCode === 401) {
          throw createToolError(TOOL_ERROR_CODES.accomDetailsUnauthorized);
        }
      }
      throw createToolError(TOOL_ERROR_CODES.accomDetailsFailed, undefined, {
        error: error instanceof Error ? error.message : "Unknown error",
      });
    }

    const rawOut = {
      bookingToken: availabilityResponse.bookingToken,
      expiresAt: availabilityResponse.expiresAt,
      price: availabilityResponse.price,
      propertyId: availabilityResponse.propertyId,
      rateId: availabilityResponse.rateId,
      status: "success" as const,
    };

    return ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA.parse(rawOut);
  },
  inputSchema: ACCOMMODATION_CHECK_AVAILABILITY_INPUT_SCHEMA,
});

/**
 * Book accommodation tool.
 *
 * Creates a booking request for an accommodation listing using Expedia Partner
 * Solutions. Requires user approval via the approvals system before proceeding.
 * Implements two-phase commit: charge customer via Stripe, then create booking
 * via EPS. If booking fails, payment is automatically refunded.
 *
 * @returns AccommodationBookingResult with booking confirmation details, status, and reference number.
 */
export const bookAccommodation = tool({
  description:
    "Complete an accommodation booking via Expedia Partner Solutions. This is the final step in the booking flow. " +
    "Requires a valid bookingToken from checkAvailability, Stripe payment method ID, and user approval. " +
    "Implements two-phase commit: charges customer via Stripe first, then creates booking via Expedia. " +
    "If booking fails, payment is automatically refunded. Supports special requests and idempotency keys " +
    "for safe retries. Returns booking confirmation with confirmation number and status. " +
    "Use this only after checkAvailability has returned a valid bookingToken.",
  execute: async (params): Promise<AccommodationBookingResult> => {
    const validated = ACCOMMODATION_BOOKING_INPUT_SCHEMA.parse(params);
    const idempotencyKey = validated.idempotencyKey || secureUuid();
    const sessionId = validated.sessionId;

    if (!sessionId) {
      throw createToolError(TOOL_ERROR_CODES.accomBookingSessionRequired);
    }

    // 1. Auth check
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    const user = auth?.user;
    if (!user) {
      throw createToolError(TOOL_ERROR_CODES.accomBookingSessionRequired);
    }

    // 2. Approval gate
    await requireApproval("bookAccommodation", {
      idempotencyKey,
      sessionId,
    });

    // 3. Generate single booking ID for consistency
    const bookingId = secureUuid();

    // 4. Two-phase commit: Payment + Booking
    let paymentIntentId: string;
    let epsBookingId: string;
    let confirmationNumber: string;

    try {
      // Use real amount and currency from checkAvailability result
      const priceInCents = validated.amount;
      const currency = validated.currency;

      // Phase 1: Process payment
      const paymentResult = await processBookingPayment({
        amount: priceInCents,
        bookingToken: validated.bookingToken,
        currency,
        customerId: user.id, // Could be Stripe customer ID if stored
        paymentMethodId: validated.paymentMethodId,
        specialRequests: validated.specialRequests,
        user: {
          email: validated.guestEmail,
          name: validated.guestName,
          phone: validated.guestPhone,
        },
      });

      paymentIntentId = paymentResult.paymentIntentId;
      epsBookingId = paymentResult.bookingId;
      confirmationNumber = paymentResult.confirmationNumber;
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown booking error";
      throw createToolError(TOOL_ERROR_CODES.accomBookingFailed, undefined, {
        error: errorMessage,
      });
    }

    // 5. Save booking to Supabase
    try {
      // biome-ignore lint/suspicious/noExplicitAny: Supabase types don't include bookings table yet
      const { error: insertError } = await (supabase as any).from("bookings").insert({
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        booking_token: validated.bookingToken,
        checkin: validated.checkin,
        checkout: validated.checkout,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        eps_booking_id: epsBookingId,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        guest_email: validated.guestEmail,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        guest_name: validated.guestName,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        guest_phone: validated.guestPhone || null,
        guests: validated.guests,
        id: bookingId, // Use the same bookingId generated above
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        property_id: validated.listingId,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        special_requests: validated.specialRequests || null,
        status: "CONFIRMED",
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        stripe_payment_intent_id: paymentIntentId,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        trip_id: validated.tripId || null,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        user_id: user.id,
      });

      if (insertError) {
        console.error("Failed to save booking to database:", insertError);
        // Don't fail the booking if DB save fails - booking is already confirmed
      }
    } catch (dbError) {
      console.error("Database error saving booking:", dbError);
      // Don't fail the booking if DB save fails
    }

    const bookingReference =
      confirmationNumber || `bk_${bookingId.replaceAll("-", "").slice(0, 10)}`;
    const rawOut = {
      bookingId, // Use the same bookingId for consistency
      bookingStatus: "confirmed" as const,
      checkin: validated.checkin,
      checkout: validated.checkout,
      epsBookingId,
      guestEmail: validated.guestEmail,
      guestName: validated.guestName,
      guestPhone: validated.guestPhone,
      guests: validated.guests,
      holdOnly: validated.holdOnly || false,
      idempotencyKey,
      listingId: validated.listingId,
      message: `Booking confirmed! Confirmation number: ${confirmationNumber}`,
      paymentMethod: validated.paymentMethodId,
      reference: bookingReference,
      specialRequests: validated.specialRequests,
      status: "success" as const,
      stripePaymentIntentId: paymentIntentId,
      tripId: validated.tripId,
    };

    return ACCOMMODATION_BOOKING_OUTPUT_SCHEMA.parse(rawOut);
  },
  inputSchema: ACCOMMODATION_BOOKING_INPUT_SCHEMA,
});
