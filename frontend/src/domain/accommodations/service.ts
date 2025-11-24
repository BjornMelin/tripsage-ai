/**
 * @fileoverview Accommodations domain service orchestrating provider calls, caching, and booking.
 *
 * Provider-neutral implementation for Amadeus + Google Places hybrid stack.
 */

import "server-only";

import { runBookingOrchestrator } from "@domain/accommodations/booking-orchestrator";
import { ProviderError } from "@domain/accommodations/errors";
import type {
  AccommodationProviderAdapter,
  ProviderContext,
  ProviderResult,
} from "@domain/accommodations/providers/types";
import {
  type AccommodationBookingRequest,
  type AccommodationBookingResult,
  type AccommodationCheckAvailabilityParams,
  type AccommodationCheckAvailabilityResult,
  type AccommodationDetailsParams,
  type AccommodationDetailsResult,
  type AccommodationSearchParams,
  type AccommodationSearchResult,
  accommodationBookingOutputSchema,
  accommodationCheckAvailabilityOutputSchema,
  accommodationDetailsOutputSchema,
  accommodationSearchOutputSchema,
} from "@schemas/accommodations";
import type { Ratelimit } from "@upstash/ratelimit";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { bumpTag, versionedKey } from "@/lib/cache/tags";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { enrichHotelListingWithPlaces } from "@/lib/google/places-enrichment";
import { resolveLocationToLatLng } from "@/lib/google/places-geocoding";
import { retryWithBackoff } from "@/lib/http/retry";
import type { ProcessedPayment } from "@/lib/payments/booking-payment";
import { secureUuid } from "@/lib/security/random";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";

// Extract Span type from withTelemetrySpan signature to avoid direct @opentelemetry/api import
type TelemetrySpan = Parameters<Parameters<typeof withTelemetrySpan>[2]>[0];

/** Dependencies for the accommodations service. */
export type AccommodationsServiceDeps = {
  provider: AccommodationProviderAdapter;
  supabase: () => Promise<TypedServerSupabase>;
  rateLimiter?: Ratelimit;
  cacheTtlSeconds: number;
};

/** Context for the accommodations service. */
export type ServiceContext = ProviderContext & {
  rateLimitKey?: string;
  processPayment?: (params: {
    amountCents: number;
    currency: string;
  }) => Promise<ProcessedPayment>;
  requestApproval?: () => Promise<void>;
};

const CACHE_NAMESPACE = "service:accom:search";
const BOOKING_CACHE_NAMESPACE = "service:accom:booking";
const CACHE_TAG_SEARCH = "accommodations:search";
const CACHE_TAG_BOOKING = "accommodations:booking";

/** Cached booking price data structure. */
type CachedBookingPrice = {
  bookingToken: string;
  price: { currency: string; total: string };
  propertyId: string;
  rateId: string;
  sessionId?: string;
  userId?: string;
};

/** Accommodations service class. */
export class AccommodationsService {
  constructor(private readonly deps: AccommodationsServiceDeps) {}

  /** Executes an availability search with cache-aside. */
  async search(
    params: AccommodationSearchParams,
    ctx?: ServiceContext
  ): Promise<AccommodationSearchResult> {
    return await withTelemetrySpan(
      "accommodations.search",
      {
        attributes: {
          hasSemanticQuery: Boolean(params.semanticQuery?.trim()),
        },
        redactKeys: ["location", "semanticQuery"],
      },
      async (span) => {
        const startedAt = Date.now();
        if (this.deps.rateLimiter) {
          const limit = await this.deps.rateLimiter.limit(
            ctx?.rateLimitKey ?? `anon:${params.location}`
          );
          span.addEvent("ratelimit.checked", {
            key: ctx?.rateLimitKey ?? "anon",
            remaining: limit?.remaining ?? 0,
          });
          if (!limit?.success) {
            throw new ProviderError("rate_limited", "rate limit exceeded", {
              retryAfterMs: limit?.reset,
            });
          }
        }

        const baseCacheKey = this.buildCacheKey(params);
        if (baseCacheKey) {
          const versionedCacheKey = await versionedKey(CACHE_TAG_SEARCH, baseCacheKey);
          const cached =
            await getCachedJson<AccommodationSearchResult>(versionedCacheKey);
          if (cached) {
            span.addEvent("cache.hit", { key: versionedCacheKey });
            return {
              ...cached,
              fromCache: true,
            };
          }
          span.addEvent("cache.miss", { key: versionedCacheKey });
        }

        let coords: { lat: number; lon: number } | null = null;
        try {
          coords = await resolveLocationToLatLng(params.location);
        } catch (error) {
          span.recordException(error as Error);
          coords = null;
        }
        if (!coords) {
          throw new ProviderError("not_found", "location_not_found");
        }

        const enrichedParams = {
          ...params,
          lat: coords?.lat,
          lng: coords?.lon,
        };

        const providerResult = await this.callProvider(
          (providerCtx) => this.deps.provider.search(enrichedParams, providerCtx),
          ctx
        );

        const filteredListings = filterListingsByPrice(
          providerResult.value.listings,
          params.priceMin,
          params.priceMax
        );

        const prices = collectPrices(filteredListings);

        const result = accommodationSearchOutputSchema.parse({
          avgPrice:
            prices.length > 0
              ? prices.reduce((sum, value) => sum + value, 0) / prices.length
              : undefined,
          fromCache: false,
          listings: filteredListings,
          maxPrice: prices.length > 0 ? Math.max(...prices) : undefined,
          minPrice: prices.length > 0 ? Math.min(...prices) : undefined,
          provider: this.deps.provider.name,
          resultsReturned: filteredListings.length,
          searchId: secureUuid(),
          searchParameters: {
            checkin: params.checkin,
            checkout: params.checkout,
            guests: params.guests,
            lat: coords.lat,
            lng: coords.lon,
            location: params.location,
            semanticQuery: params.semanticQuery,
          },
          status: "success" as const,
          tookMs: Date.now() - startedAt,
          totalResults: filteredListings.length,
        });

        if (baseCacheKey) {
          const versionedCacheKey = await versionedKey(CACHE_TAG_SEARCH, baseCacheKey);
          await setCachedJson(versionedCacheKey, result, this.deps.cacheTtlSeconds);
        }
        return result;
      }
    );
  }

  /** Retrieve details for a specific accommodation property. */
  async details(
    params: AccommodationDetailsParams,
    ctx?: ServiceContext
  ): Promise<AccommodationDetailsResult> {
    return await withTelemetrySpan(
      "accommodations.details",
      {
        attributes: { listingId: params.listingId },
        redactKeys: ["listingId"],
      },
      async (span) => {
        if (this.deps.rateLimiter) {
          const rateKey = ctx?.rateLimitKey ?? ctx?.userId ?? params.listingId;
          const limit = await this.deps.rateLimiter.limit(rateKey ?? "anon");
          span.addEvent("ratelimit.checked", {
            key: rateKey ?? "anon",
            remaining: limit?.remaining ?? 0,
          });
          if (!limit?.success) {
            throw new ProviderError("rate_limited", "rate limit exceeded", {
              retryAfterMs: limit?.reset,
            });
          }
        }

        const result = await this.callProvider(
          (providerCtx) => this.deps.provider.getDetails(params, providerCtx),
          ctx
        );

        const enriched = await enrichHotelListingWithPlaces(result.value.listing);

        span.addEvent("details.enriched", {
          hasPlace: Boolean((enriched as { place?: unknown }).place),
        });

        return accommodationDetailsOutputSchema.parse({
          listing: enriched,
          provider: this.deps.provider.name,
          status: "success" as const,
        });
      }
    );
  }

  /** Check final availability and pricing. */
  async checkAvailability(
    params: AccommodationCheckAvailabilityParams,
    ctx: ServiceContext
  ): Promise<AccommodationCheckAvailabilityResult> {
    return await withTelemetrySpan(
      "accommodations.checkAvailability",
      {
        attributes: {
          propertyId: params.propertyId,
          rateId: params.rateId,
          ...(ctx.sessionId ? { sessionId: ctx.sessionId } : {}),
          ...(ctx.userId ? { userId: ctx.userId } : {}),
        },
        redactKeys: ["userId", "sessionId"],
      },
      async (span) => {
        if (this.deps.rateLimiter) {
          const rateKey = ctx?.rateLimitKey ?? ctx?.userId ?? params.propertyId;
          const limit = await this.deps.rateLimiter.limit(rateKey ?? "anon");
          span.addEvent("ratelimit.checked", {
            key: rateKey ?? "anon",
            remaining: limit?.remaining ?? 0,
          });
          if (!limit?.success) {
            throw new ProviderError("rate_limited", "rate limit exceeded", {
              retryAfterMs: limit?.reset,
            });
          }
        }

        const availability = await this.callProvider(
          (providerCtx) => this.deps.provider.checkAvailability(params, providerCtx),
          ctx
        );

        const bookingCacheKey = `${BOOKING_CACHE_NAMESPACE}:${availability.value.bookingToken}`;
        const versionedBookingKey = await versionedKey(
          CACHE_TAG_BOOKING,
          bookingCacheKey
        );
        await setCachedJson(
          versionedBookingKey,
          {
            bookingToken: availability.value.bookingToken,
            price: availability.value.price,
            propertyId: availability.value.propertyId,
            rateId: availability.value.rateId,
            sessionId: ctx.sessionId,
            userId: ctx.userId,
          },
          10 * 60
        );

        span.addEvent("availability.cached", {
          bookingToken: availability.value.bookingToken,
        });

        return accommodationCheckAvailabilityOutputSchema.parse({
          bookingToken: availability.value.bookingToken,
          expiresAt: availability.value.expiresAt,
          price: availability.value.price,
          propertyId: availability.value.propertyId,
          rateId: availability.value.rateId,
          status: "success" as const,
        });
      }
    );
  }

  /** Complete an accommodation booking. */
  async book(
    params: AccommodationBookingRequest,
    ctx: ServiceContext & { userId: string }
  ): Promise<AccommodationBookingResult> {
    return await withTelemetrySpan(
      "accommodations.book",
      {
        attributes: {
          listingId: params.listingId,
          ...(ctx.sessionId ? { sessionId: ctx.sessionId } : {}),
          ...(params.tripId ? { tripId: params.tripId } : {}),
          ...(ctx.userId ? { userId: ctx.userId } : {}),
        },
        redactKeys: ["userId", "sessionId"],
      },
      async (span) => {
        await this.validateBookingContext(ctx, span, params.listingId);

        const supabase = await this.deps.supabase();
        await this.validateTripOwnership(supabase, params.tripId, ctx.userId);

        const bookingCacheKey = `${BOOKING_CACHE_NAMESPACE}:${params.bookingToken}`;
        const versionedBookingKey = await versionedKey(
          CACHE_TAG_BOOKING,
          bookingCacheKey
        );
        const cachedPrice =
          await getCachedJson<CachedBookingPrice>(versionedBookingKey);

        if (!cachedPrice) {
          throw new Error("booking_price_not_cached");
        }

        const { amountCents, currency } = this.validateCachedPrice(
          cachedPrice,
          params,
          ctx
        );

        const providerPayloadBuilder = (payment: ProcessedPayment) =>
          this.deps.provider.buildBookingPayload(params, {
            currency,
            paymentIntentId: payment.paymentIntentId,
            totalCents: amountCents,
          });
        const idempotencyKey = params.idempotencyKey ?? secureUuid();

        const result = await runBookingOrchestrator(
          { provider: this.deps.provider, supabase },
          {
            amount: amountCents,
            approvalKey: "bookAccommodation",
            bookingToken: params.bookingToken,
            currency,
            guest: {
              email: params.guestEmail,
              name: params.guestName,
              phone: params.guestPhone,
            },
            idempotencyKey,
            paymentMethodId: params.paymentMethodId,
            persistBooking: async (payload) => {
              const bookingRow = this.buildBookingRow(params, payload, ctx.userId);

              const persist = async () =>
                await supabase.from("bookings").insert(bookingRow as never);

              const { error } = await retryWithBackoff(persist, {
                attempts: 3,
                baseDelayMs: 200,
                maxDelayMs: 1_000,
              });
              if (error) {
                throw error;
              }
            },
            processPayment: () => {
              if (!ctx.processPayment) {
                throw new Error("processPayment handler missing");
              }
              return ctx.processPayment({
                amountCents,
                currency,
              });
            },
            providerPayload: providerPayloadBuilder,
            requestApproval: () => {
              if (!ctx.requestApproval) {
                throw new Error("requestApproval handler missing");
              }
              return ctx.requestApproval();
            },
            sessionId: ctx.sessionId ?? secureUuid(),
            stay: {
              checkin: params.checkin,
              checkout: params.checkout,
              guests: params.guests,
              listingId: params.listingId,
              specialRequests: params.specialRequests,
              tripId: params.tripId,
            },
            userId: ctx.userId,
          }
        );

        span.addEvent("booking.persisted", {
          listingId: params.listingId,
          priceCents: amountCents,
        });

        // Invalidate search cache using tag-based invalidation
        // Bumping the tag invalidates all search cache entries for this tag
        await bumpTag(CACHE_TAG_SEARCH);
        span.addEvent("cache.invalidated", { tag: CACHE_TAG_SEARCH });

        return accommodationBookingOutputSchema.parse(result);
      }
    );
  }

  /** Call a provider function and return the result. */
  private async callProvider<T>(
    fn: (ctx?: ProviderContext) => Promise<ProviderResult<T>>,
    ctx?: ServiceContext
  ): Promise<{ ok: true; value: T; retries: number }> {
    const providerCtx: ProviderContext | undefined = ctx
      ? {
          clientIp: ctx.clientIp,
          sessionId: ctx.sessionId ?? ctx.userId,
          testScenario: ctx.testScenario,
          userAgent: ctx.userAgent,
          userId: ctx.userId,
        }
      : undefined;

    const result = await fn(providerCtx);
    if (!result.ok) {
      throw result.error;
    }
    return result;
  }

  /** Build a cache key for a search parameters object. */
  private buildCacheKey(params: AccommodationSearchParams): string | undefined {
    return canonicalizeParamsForCache(
      {
        ...params,
        semanticQuery: params.semanticQuery || "",
      },
      CACHE_NAMESPACE
    );
  }

  /**
   * Validates booking context including payment/approval handlers and rate limiting.
   *
   * @param ctx - Service context with payment and approval handlers
   * @param span - Telemetry span for event recording
   * @throws Error if handlers are missing
   * @throws ProviderError if rate limit exceeded
   */
  private async validateBookingContext(
    ctx: ServiceContext & { userId: string },
    span: TelemetrySpan,
    listingId: string
  ): Promise<void> {
    if (!ctx.processPayment || !ctx.requestApproval) {
      throw new Error("booking context missing payment or approval handlers");
    }
    if (this.deps.rateLimiter) {
      const rateKey = ctx.rateLimitKey ?? ctx.userId ?? listingId;
      const limit = await this.deps.rateLimiter.limit(rateKey ?? "anon");
      span.addEvent("ratelimit.checked", {
        key: rateKey ?? "anon",
        remaining: limit?.remaining ?? 0,
      });
      if (!limit?.success) {
        throw new ProviderError("rate_limited", "rate limit exceeded", {
          retryAfterMs: limit?.reset,
        });
      }
    }
  }

  /**
   * Validates that a trip exists and belongs to the user.
   *
   * @param supabase - Supabase client instance
   * @param tripId - Trip ID string to validate
   * @param userId - User ID to verify ownership
   * @throws ProviderError if trip ID is invalid or trip not found/not owned
   */
  private async validateTripOwnership(
    supabase: TypedServerSupabase,
    tripId: string | undefined,
    userId: string
  ): Promise<void> {
    if (!tripId) return;

    const parsedTripId = /^\d+$/.test(tripId)
      ? Number.parseInt(tripId, 10)
      : Number.NaN;
    if (!Number.isFinite(parsedTripId)) {
      throw new ProviderError("validation_failed", "invalid_trip_id");
    }

    const { data: trip, error: tripError } = await supabase
      .from("trips")
      .select("id, user_id")
      .eq("id", parsedTripId)
      .eq("user_id", userId)
      .single();

    if (tripError || !trip) {
      throw new ProviderError("not_found", "trip_not_found_or_not_owned");
    }
  }

  /**
   * Validates cached booking price and context.
   *
   * @param cachedPrice - Cached price data from booking cache (must not be null)
   * @param params - Booking request parameters
   * @param ctx - Service context with user/session info
   * @returns Validated amount in cents
   * @throws Error if validation fails
   */
  private validateCachedPrice(
    cachedPrice: CachedBookingPrice,
    params: AccommodationBookingRequest,
    ctx: ServiceContext & { userId: string }
  ): { amountCents: number; currency: string } {
    if (cachedPrice.userId && cachedPrice.userId !== ctx.userId) {
      throw new Error("booking_context_mismatch");
    }
    if (
      cachedPrice.sessionId &&
      ctx.sessionId &&
      cachedPrice.sessionId !== ctx.sessionId
    ) {
      throw new Error("booking_context_mismatch");
    }
    if (cachedPrice.propertyId !== params.listingId) {
      throw new Error("booking_price_mismatch");
    }

    const amountCents = Math.round(Number.parseFloat(cachedPrice.price.total) * 100);
    if (!Number.isFinite(amountCents) || amountCents <= 0) {
      throw new Error("booking_price_invalid");
    }

    return { amountCents, currency: cachedPrice.price.currency };
  }

  /**
   * Builds a database row for booking persistence.
   *
   * @param params - Booking request parameters
   * @param payload - Booking orchestrator payload with booking ID
   * @param userId - User ID for the booking
   * @returns Database row object ready for insertion
   */
  private buildBookingRow(
    params: AccommodationBookingRequest,
    payload: {
      bookingId: string;
      providerBookingId?: string;
      stripePaymentIntentId?: string | null;
    },
    userId: string
  ): Record<string, unknown> {
    if (!params.bookingToken) {
      throw new Error("bookingToken is required for booking persistence");
    }

    return {
      // biome-ignore lint/style/useNamingConvention: database columns use snake_case
      booking_token: params.bookingToken,
      checkin: params.checkin,
      checkout: params.checkout,
      // biome-ignore lint/style/useNamingConvention: database columns use snake_case
      guest_email: params.guestEmail,
      // biome-ignore lint/style/useNamingConvention: database columns use snake_case
      guest_name: params.guestName,
      // biome-ignore lint/style/useNamingConvention: database columns use snake_case
      guest_phone: params.guestPhone ?? null,
      guests: params.guests,
      id: payload.bookingId,
      // biome-ignore lint/style/useNamingConvention: database columns use snake_case
      property_id: params.listingId,
      // biome-ignore lint/style/useNamingConvention: database columns use snake_case
      provider_booking_id: payload.providerBookingId ?? null,
      // biome-ignore lint/style/useNamingConvention: database columns use snake_case
      special_requests: params.specialRequests ?? null,
      status: "CONFIRMED",
      // biome-ignore lint/style/useNamingConvention: database columns use snake_case
      stripe_payment_intent_id: payload.stripePaymentIntentId ?? null,
      // biome-ignore lint/style/useNamingConvention: database columns use snake_case
      trip_id:
        params.tripId !== undefined && /^\d+$/.test(params.tripId)
          ? Number.parseInt(params.tripId, 10)
          : null,
      // biome-ignore lint/style/useNamingConvention: database columns use snake_case
      user_id: userId,
    } as const;
  }
}

/** Internal type for price extraction from provider listings. */
type ProviderListingWithPrices = {
  rooms?: Array<{
    rates?: Array<{
      price?: {
        numeric?: number;
        total?: string;
      };
    }>;
  }>;
};

/**
 * Extracts numeric price values from accommodation listings.
 *
 * @param listings - Array of accommodation listing objects with nested rooms and rates.
 * @returns Array of numeric price values found in the listings.
 */
function collectPrices(listings: Array<ProviderListingWithPrices>): number[] {
  const values: number[] = [];
  for (const listing of listings) {
    if (!Array.isArray(listing.rooms)) continue;
    for (const room of listing.rooms) {
      if (!room || typeof room !== "object") continue;
      if (!Array.isArray(room.rates)) continue;
      for (const rate of room.rates) {
        if (!rate || typeof rate !== "object") continue;
        const price = rate.price;
        const numeric =
          typeof price?.numeric === "number"
            ? price.numeric
            : price?.total
              ? Number.parseFloat(price.total)
              : undefined;
        if (typeof numeric === "number" && Number.isFinite(numeric)) {
          values.push(numeric);
        }
      }
    }
  }
  return values;
}

/**
 * Filters listings to those whose price range overlaps with the provided bounds.
 *
 * @param listings - Unfiltered provider listings.
 * @param minPrice - Optional minimum total price.
 * @param maxPrice - Optional maximum total price.
 * @returns Listings constrained to the requested price band.
 */
function filterListingsByPrice(
  listings: Array<ProviderListingWithPrices>,
  minPrice?: number,
  maxPrice?: number
): Array<ProviderListingWithPrices> {
  if (minPrice === undefined && maxPrice === undefined) return listings;

  return listings.filter((listing) => {
    const prices = collectPrices([listing]);
    if (prices.length === 0) return true;
    const minListingPrice = Math.min(...prices);
    const maxListingPrice = Math.max(...prices);
    if (minPrice !== undefined && maxListingPrice < minPrice) return false;
    if (maxPrice !== undefined && minListingPrice > maxPrice) return false;
    return true;
  });
}
