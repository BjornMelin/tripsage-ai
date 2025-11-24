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
  ACCOMMODATION_BOOKING_OUTPUT_SCHEMA,
  ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA,
  ACCOMMODATION_DETAILS_OUTPUT_SCHEMA,
  ACCOMMODATION_SEARCH_OUTPUT_SCHEMA,
  type AccommodationBookingRequest,
  type AccommodationBookingResult,
  type AccommodationCheckAvailabilityParams,
  type AccommodationCheckAvailabilityResult,
  type AccommodationDetailsParams,
  type AccommodationDetailsResult,
  type AccommodationSearchParams,
  type AccommodationSearchResult,
} from "@schemas/accommodations";
import type { Ratelimit } from "@upstash/ratelimit";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { deleteCachedJson, getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { cacheLatLng, getCachedLatLng } from "@/lib/google/caching";
import { getPlaceDetails, postPlacesSearch } from "@/lib/google/client";
import { retryWithBackoff } from "@/lib/http/retry";
import type { ProcessedPayment } from "@/lib/payments/booking-payment";
import { secureUuid } from "@/lib/security/random";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";

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

        const cacheKey = this.buildCacheKey(params);
        if (cacheKey) {
          const cached = await getCachedJson<AccommodationSearchResult>(cacheKey);
          if (cached) {
            span.addEvent("cache.hit", { key: cacheKey });
            return {
              ...cached,
              fromCache: true,
            };
          }
          span.addEvent("cache.miss", { key: cacheKey });
        }

        let coords: { lat: number; lon: number } | null = null;
        try {
          coords = await resolveCoordinates(params.location);
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

        const result = ACCOMMODATION_SEARCH_OUTPUT_SCHEMA.parse({
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

        if (cacheKey) {
          await setCachedJson(cacheKey, result, this.deps.cacheTtlSeconds);
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

        const enriched = await enrichWithGooglePlaces(result.value.listing);

        span.addEvent("details.enriched", {
          hasPlace: Boolean((enriched as { place?: unknown }).place),
        });

        return ACCOMMODATION_DETAILS_OUTPUT_SCHEMA.parse({
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

        await setCachedJson(
          `${BOOKING_CACHE_NAMESPACE}:${availability.value.bookingToken}`,
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

        return ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA.parse({
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
        if (!ctx.processPayment || !ctx.requestApproval) {
          throw new Error("booking context missing payment or approval handlers");
        }
        if (this.deps.rateLimiter) {
          const rateKey = ctx.rateLimitKey ?? ctx.userId ?? params.listingId;
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

        const supabase = await this.deps.supabase();

        if (params.tripId) {
          const tripId = /^\d+$/.test(params.tripId)
            ? Number.parseInt(params.tripId, 10)
            : Number.NaN;
          if (!Number.isFinite(tripId)) {
            throw new ProviderError("validation_failed", "invalid_trip_id");
          }
          const { data: trip, error: tripError } = await supabase
            .from("trips")
            .select("id, user_id")
            .eq("id", tripId)
            .eq("user_id", ctx.userId)
            .single();
          if (tripError || !trip) {
            throw new ProviderError("not_found", "trip_not_found_or_not_owned");
          }
        }

        const cachedPrice = await getCachedJson<{
          bookingToken: string;
          price: { currency: string; total: string };
          propertyId: string;
          rateId: string;
          sessionId?: string;
          userId?: string;
        }>(`${BOOKING_CACHE_NAMESPACE}:${params.bookingToken}`);
        if (!cachedPrice) {
          throw new Error("booking_price_not_cached");
        }
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
        const amountCents = Math.round(
          Number.parseFloat(cachedPrice.price.total) * 100
        );
        if (!Number.isFinite(amountCents) || amountCents <= 0) {
          throw new Error("booking_price_invalid");
        }

        const providerPayloadBuilder = (payment: ProcessedPayment) =>
          this.deps.provider.buildBookingPayload(params, {
            currency: cachedPrice.price.currency,
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
            currency: cachedPrice.price.currency,
            guest: {
              email: params.guestEmail,
              name: params.guestName,
              phone: params.guestPhone,
            },
            idempotencyKey,
            paymentMethodId: params.paymentMethodId,
            persistBooking: async (payload) => {
              // bookingToken is required by ACCOMMODATION_BOOKING_INPUT_SCHEMA but TypeScript
              // infers it as optional. Runtime check ensures it's defined.
              if (!params.bookingToken) {
                throw new Error("bookingToken is required for booking persistence");
              }
              const bookingRow = {
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
                provider_booking_id: payload.providerBookingId,
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
                user_id: ctx.userId,
              } as const;

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
                currency: cachedPrice.price.currency,
              });
            },
            providerPayload: providerPayloadBuilder,
            requestApproval: ctx.requestApproval,
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

        // Invalidate search cache for this listing and date range to prevent stale results
        const searchCacheKey = this.buildCacheKey({
          checkin: params.checkin,
          checkout: params.checkout,
          guests: params.guests,
          location: params.listingId, // Use listingId as location hint for cache invalidation
        });
        if (searchCacheKey) {
          await deleteCachedJson(searchCacheKey);
          span.addEvent("cache.invalidated", { key: searchCacheKey });
        }

        return ACCOMMODATION_BOOKING_OUTPUT_SCHEMA.parse(result);
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
}

/**
 * Extracts numeric price values from accommodation listings.
 *
 * @param listings - Array of accommodation listing objects with nested rooms and rates.
 * @returns Array of numeric price values found in the listings.
 */
function collectPrices(listings: Array<Record<string, unknown>>): number[] {
  const values: number[] = [];
  for (const listing of listings) {
    const rooms = (listing.rooms as Array<Record<string, unknown>> | undefined) ?? [];
    for (const room of rooms) {
      const rates =
        (room.rates as Array<{ price?: { numeric?: number } }> | undefined) ?? [];
      for (const rate of rates) {
        const numeric = rate.price?.numeric;
        if (typeof numeric === "number" && Number.isFinite(numeric)) {
          values.push(numeric);
        }
      }
    }
  }
  return values;
}

/**
 * Filters listings to those whose first rate price falls within the provided bounds.
 *
 * @param listings - Unfiltered provider listings.
 * @param minPrice - Optional minimum total price.
 * @param maxPrice - Optional maximum total price.
 * @returns Listings constrained to the requested price band.
 */
function filterListingsByPrice(
  listings: Array<Record<string, unknown>>,
  minPrice?: number,
  maxPrice?: number
): Array<Record<string, unknown>> {
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

/**
 * Resolves a location string to geographic coordinates using Google Places API.
 *
 * Uses cached results when available to reduce API calls. Caches successful
 * lookups for 30 days.
 *
 * @param location - Location string to geocode (e.g., "New York, NY").
 * @returns Coordinates object with lat/lon, or null if location not found or API unavailable.
 */
async function resolveCoordinates(
  location: string
): Promise<{ lat: number; lon: number } | null> {
  const normalized = location.trim().toLowerCase().replace(/\s+/g, " ");
  const cacheKey = `googleplaces:geocode:${normalized}`;
  const cached = await getCachedLatLng(cacheKey);
  if (cached) return cached;

  let apiKey: string;
  try {
    apiKey = getGoogleMapsServerKey();
  } catch {
    return null;
  }

  const response = await withTelemetrySpan(
    "places.geocode",
    {
      attributes: { location: normalized },
      redactKeys: ["location"],
    },
    async () =>
      await postPlacesSearch({
        apiKey,
        body: { maxResultCount: 1, textQuery: location },
        fieldMask: "places.id,places.location",
      })
  );

  if (!response.ok) {
    throw new Error(`places_geocode_failed:${response.status}`);
  }
  const data = await response.json();
  const place = (data.places ?? [])[0];
  const coords =
    place?.location?.latitude !== undefined && place?.location?.longitude !== undefined
      ? { lat: place.location.latitude, lon: place.location.longitude }
      : null;
  if (coords) {
    await cacheLatLng(cacheKey, coords, 30 * 24 * 60 * 60);
  }
  return coords;
}

/**
 * Enriches an accommodation listing with Google Places data.
 *
 * Searches for the property by name and address, then fetches detailed place
 * information including ratings, photos, and contact details. Returns the
 * original listing if enrichment fails or API is unavailable.
 *
 * @param listing - Accommodation listing object from provider (expected hotel.name and hotel.address).
 * @returns Enriched listing with place and placeDetails properties, or original listing if enrichment fails.
 */
async function enrichWithGooglePlaces(
  listing: Record<string, unknown>
): Promise<Record<string, unknown>> {
  let apiKey: string;
  try {
    apiKey = getGoogleMapsServerKey();
  } catch {
    return listing;
  }

  const name = (listing as { hotel?: { name?: string } }).hotel?.name;
  const address = (
    listing as { hotel?: { address?: { cityName?: string; lines?: string[] } } }
  ).hotel?.address;
  const query = name
    ? `${name} ${address?.cityName ?? ""} ${(address?.lines ?? []).join(" ")}`
    : undefined;
  if (!query) return listing;

  const normalizedQuery = query.trim().toLowerCase().replace(/\s+/g, " ");
  const cachedDetails = await getCachedJson<{
    place?: unknown;
    placeDetails?: unknown;
  }>(`places:details:${normalizedQuery}`);
  if (cachedDetails) {
    return {
      ...listing,
      place: cachedDetails.place,
      placeDetails: cachedDetails.placeDetails,
    };
  }

  const searchRes = await withTelemetrySpan(
    "places.enrich.search",
    { attributes: { query } },
    async () =>
      await postPlacesSearch({
        apiKey,
        body: { maxResultCount: 1, textQuery: query },
        fieldMask:
          "places.id,places.displayName,places.rating,places.userRatingCount,places.photos.name,places.internationalPhoneNumber,places.formattedAddress,places.location",
      })
  );
  if (!searchRes.ok) return listing;
  const searchData = await searchRes.json();
  const place = (searchData.places ?? [])[0];
  if (!place?.id) return listing;

  const detailsCacheKey = `places:details:${place.id}`;
  const cachedPlaceDetails = await getCachedJson<{
    place?: unknown;
    placeDetails?: unknown;
  }>(detailsCacheKey);
  if (cachedPlaceDetails) {
    return {
      ...listing,
      place: cachedPlaceDetails.place,
      placeDetails: cachedPlaceDetails.placeDetails,
    };
  }

  const detailsRes = await withTelemetrySpan(
    "places.enrich.details",
    { attributes: { placeId: place.id } },
    async () =>
      await getPlaceDetails({
        apiKey,
        fieldMask:
          "id,displayName,formattedAddress,location,rating,userRatingCount,internationalPhoneNumber,photos.name,googleMapsUri",
        placeId: place.id,
      })
  );
  if (!detailsRes.ok) return { ...listing, place };
  const details = await detailsRes.json();
  await setCachedJson(detailsCacheKey, { place, placeDetails: details }, 24 * 60 * 60);
  return { ...listing, place, placeDetails: details };
}
