/**
 * @fileoverview Accommodations domain service orchestrating provider calls, caching, and booking.
 *
 * Provider-neutral implementation for Amadeus + Google Places hybrid stack.
 */

import "server-only";

import { runBookingOrchestrator } from "@domain/accommodations/booking-orchestrator";
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
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { cacheLatLng, getCachedLatLng } from "@/lib/google/caching";
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
          await this.deps.rateLimiter.limit(
            ctx?.rateLimitKey ?? `anon:${params.location}`
          );
          span.addEvent("ratelimit.checked", {
            key: ctx?.rateLimitKey ?? "anon",
          });
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
          throw error;
        }
        if (!coords) {
          throw new Error("location_not_found");
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

        const prices = collectPrices(providerResult.value.listings);

        const result = ACCOMMODATION_SEARCH_OUTPUT_SCHEMA.parse({
          avgPrice:
            prices.length > 0
              ? prices.reduce((sum, value) => sum + value, 0) / prices.length
              : undefined,
          fromCache: false,
          listings: providerResult.value.listings,
          maxPrice: prices.length > 0 ? Math.max(...prices) : undefined,
          minPrice: prices.length > 0 ? Math.min(...prices) : undefined,
          provider: "amadeus" as const,
          resultsReturned: providerResult.value.listings.length,
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
          totalResults:
            providerResult.value.total ?? providerResult.value.listings.length,
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
    const result = await this.callProvider(
      (providerCtx) => this.deps.provider.getDetails(params, providerCtx),
      ctx
    );

    const enriched = await enrichWithGooglePlaces(result.value.listing);

    return ACCOMMODATION_DETAILS_OUTPUT_SCHEMA.parse({
      listing: enriched,
      provider: "amadeus" as const,
      status: "success" as const,
    });
  }

  /** Check final availability and pricing. */
  async checkAvailability(
    params: AccommodationCheckAvailabilityParams,
    ctx: ServiceContext
  ): Promise<AccommodationCheckAvailabilityResult> {
    const availability = await this.callProvider(
      (providerCtx) => this.deps.provider.checkAvailability(params, providerCtx),
      ctx
    );

    await setCachedJson(
      `${BOOKING_CACHE_NAMESPACE}:${availability.value.bookingToken}`,
      availability.value.price,
      10 * 60
    );

    return ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA.parse({
      bookingToken: availability.value.bookingToken,
      expiresAt: availability.value.expiresAt,
      price: availability.value.price,
      propertyId: availability.value.propertyId,
      rateId: availability.value.rateId,
      status: "success" as const,
    });
  }

  /** Complete an accommodation booking. */
  async book(
    params: AccommodationBookingRequest,
    ctx: ServiceContext & { userId: string }
  ): Promise<AccommodationBookingResult> {
    if (!ctx.processPayment || !ctx.requestApproval) {
      throw new Error("booking context missing payment or approval handlers");
    }
    const supabase = await this.deps.supabase();

    const cachedPrice = await getCachedJson<{
      currency: string;
      total: string;
    }>(`${BOOKING_CACHE_NAMESPACE}:${params.bookingToken}`);
    if (!cachedPrice) {
      throw new Error("booking_price_not_cached");
    }
    const amountCents = Math.round(Number.parseFloat(cachedPrice.total) * 100);
    if (!Number.isFinite(amountCents) || amountCents <= 0) {
      throw new Error("booking_price_invalid");
    }

    const providerPayloadBuilder = (payment: ProcessedPayment) =>
      this.deps.provider.buildBookingPayload(params, {
        currency: cachedPrice.currency,
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
        currency: cachedPrice.currency,
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
          // @ts-expect-error - bookingToken is required by schema but TS infers as optional
          const { error } = await supabase.from("bookings").insert({
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
            stripe_payment_intent_id: payload.stripePaymentIntentId,
            // biome-ignore lint/style/useNamingConvention: database columns use snake_case
            trip_id: params.tripId ? Number.parseInt(params.tripId, 10) : null,
            // biome-ignore lint/style/useNamingConvention: database columns use snake_case
            user_id: ctx.userId,
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
            currency: cachedPrice.currency,
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

    return ACCOMMODATION_BOOKING_OUTPUT_SCHEMA.parse(result);
  }

  /** Call a provider function and return the result. */
  private async callProvider<T>(
    fn: (ctx?: ProviderContext) => Promise<ProviderResult<T>>,
    ctx?: ServiceContext
  ): Promise<{ ok: true; value: T; retries: number }> {
    const result = await fn(ctx);
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
      await retryWithBackoff(
        () =>
          fetch("https://places.googleapis.com/v1/places:searchText", {
            body: JSON.stringify({ maxResultCount: 1, textQuery: location }),
            headers: {
              "Content-Type": "application/json",
              "X-Goog-Api-Key": apiKey,
              "X-Goog-FieldMask": "places.id,places.location",
            },
            method: "POST",
          }),
        { attempts: 3, baseDelayMs: 200, maxDelayMs: 1000 }
      )
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

  const searchRes = await withTelemetrySpan(
    "places.enrich.search",
    { attributes: { query } },
    async () =>
      await retryWithBackoff(
        () =>
          fetch("https://places.googleapis.com/v1/places:searchText", {
            body: JSON.stringify({ maxResultCount: 1, textQuery: query }),
            headers: {
              "Content-Type": "application/json",
              "X-Goog-Api-Key": apiKey,
              "X-Goog-FieldMask":
                "places.id,places.displayName,places.rating,places.userRatingCount,places.photos.name,places.internationalPhoneNumber,places.formattedAddress,places.location",
            },
            method: "POST",
          }),
        { attempts: 3, baseDelayMs: 200, maxDelayMs: 1000 }
      )
  );
  if (!searchRes.ok) return listing;
  const searchData = await searchRes.json();
  const place = (searchData.places ?? [])[0];
  if (!place?.id) return listing;

  const detailsRes = await withTelemetrySpan(
    "places.enrich.details",
    { attributes: { placeId: place.id } },
    async () =>
      await retryWithBackoff(
        () =>
          fetch(`https://places.googleapis.com/v1/${place.id}`, {
            headers: {
              "Content-Type": "application/json",
              "X-Goog-Api-Key": apiKey,
              "X-Goog-FieldMask":
                "id,displayName,formattedAddress,location,rating,userRatingCount,internationalPhoneNumber,photos.name,googleMapsUri",
            },
            method: "GET",
          }),
        { attempts: 3, baseDelayMs: 200, maxDelayMs: 1000 }
      )
  );
  if (!detailsRes.ok) return { ...listing, place };
  const details = await detailsRes.json();
  return { ...listing, place, placeDetails: details };
}
