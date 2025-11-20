/**
 * @fileoverview Accommodations domain service orchestrating provider calls, RAG lookup, caching, and booking.
 *
 * This service centralizes accommodation operations: search, details, availability, and booking.
 * It applies cache-aside via Upstash, optional rate limiting, RAG property ID resolution, and
 * funnels bookings through the booking orchestrator for approvals, payments, and persistence.
 */

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
import type {
  EpsCheckAvailabilityRequest,
  EpsCreateBookingRequest,
  RapidAvailabilityResponse,
  RapidRate,
} from "@schemas/expedia";
import { extractInclusiveTotal } from "@schemas/expedia";
import type { Ratelimit } from "@upstash/ratelimit";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import { generateEmbedding } from "@/lib/embeddings/generate";
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
  processPayment?: () => Promise<ProcessedPayment>;
  requestApproval?: () => Promise<void>;
};

const CACHE_NAMESPACE = "service:accom:search";

/** Accommodations service class. */
export class AccommodationsService {
  constructor(private readonly deps: AccommodationsServiceDeps) {}

  /** Executes an availability search, optionally using semantic RAG IDs and cache-aside. */
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

        const supabase = await this.deps.supabase();
        const propertyIds = await resolvePropertyIds(params, supabase);

        const availability = await this.callProvider(
          (providerCtx) =>
            this.deps.provider.searchAvailability(
              {
                checkIn: params.checkin,
                checkOut: params.checkout,
                currency: params.currency ?? "USD",
                guests: params.guests,
                include: ["rooms.rates.current_refundability"],
                language: "en-US",
                propertyIds: propertyIds ?? [],
                ratePlanCount: params.propertyTypes ? 6 : 4,
              },
              providerCtx
            ),
          { ...ctx, sessionId: ctx?.sessionId }
        );

        const listings = mapAvailabilityToListings(availability.value, {
          checkin: params.checkin,
          checkout: params.checkout,
          guests: params.guests,
          propertyIds,
        });
        const prices = collectListingPrices(listings);

        const result = ACCOMMODATION_SEARCH_OUTPUT_SCHEMA.parse({
          avgPrice:
            prices.length > 0
              ? prices.reduce((sum, value) => sum + value, 0) / prices.length
              : undefined,
          fromCache: false,
          listings,
          maxPrice: prices.length > 0 ? Math.max(...prices) : undefined,
          minPrice: prices.length > 0 ? Math.min(...prices) : undefined,
          provider: "expedia" as const,
          resultsReturned: listings.length,
          searchId: secureUuid(),
          searchParameters: {
            checkin: params.checkin,
            checkout: params.checkout,
            guests: params.guests,
            location: params.location,
            semanticQuery: params.semanticQuery,
          },
          status: "success" as const,
          tookMs: Date.now() - startedAt,
          totalResults: availability.value.total ?? listings.length,
        });

        if (cacheKey) {
          await setCachedJson(cacheKey, result, this.deps.cacheTtlSeconds);
        }
        return result;
      }
    );
  }

  /** Retrieve details for a specific accommodation property from Expedia Rapid. */
  async details(
    params: AccommodationDetailsParams,
    ctx?: ServiceContext
  ): Promise<AccommodationDetailsResult> {
    const result = await this.callProvider(
      (providerCtx) =>
        this.deps.provider.getPropertyDetails(
          {
            language: "en-US",
            propertyId: params.listingId,
          },
          providerCtx
        ),
      ctx
    );

    return ACCOMMODATION_DETAILS_OUTPUT_SCHEMA.parse({
      listing: result.value,
      provider: "expedia" as const,
      status: "success" as const,
    });
  }

  /** Check final availability and lock pricing for a specific rate. */
  async checkAvailability(
    params: AccommodationCheckAvailabilityParams,
    ctx: ServiceContext
  ): Promise<AccommodationCheckAvailabilityResult> {
    const request: EpsCheckAvailabilityRequest = {
      propertyId: params.propertyId,
      rateId: params.rateId,
      roomId: params.roomId,
      token: params.priceCheckToken,
    };

    const availability = await this.callProvider(
      (providerCtx) => this.deps.provider.checkAvailability(request, providerCtx),
      ctx
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

  /** Complete an accommodation booking via Expedia Partner Solutions. */
  async book(
    params: AccommodationBookingRequest,
    ctx: ServiceContext & { userId: string }
  ): Promise<AccommodationBookingResult> {
    if (!ctx.processPayment || !ctx.requestApproval) {
      throw new Error("booking context missing payment or approval handlers");
    }
    const supabase = await this.deps.supabase();

    const providerPayload = this.buildExpediaBookingPayload(params);
    const idempotencyKey = params.idempotencyKey ?? secureUuid();

    const result = await runBookingOrchestrator(
      { provider: this.deps.provider, supabase },
      {
        amount: params.amount,
        approvalKey: "bookAccommodation",
        bookingToken: params.bookingToken,
        currency: params.currency,
        guest: {
          email: params.guestEmail,
          name: params.guestName,
          phone: params.guestPhone,
        },
        idempotencyKey,
        paymentMethodId: params.paymentMethodId,
        persistBooking: async (payload) => {
          // biome-ignore lint/suspicious/noExplicitAny: Supabase types may not include table
          const { error } = await (supabase as any).from("bookings").insert({
            // biome-ignore lint/style/useNamingConvention: database columns use snake_case
            booking_token: params.bookingToken,
            checkin: params.checkin,
            checkout: params.checkout,
            // biome-ignore lint/style/useNamingConvention: database columns use snake_case
            eps_booking_id: payload.epsItineraryId,
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
            special_requests: params.specialRequests ?? null,
            status: "CONFIRMED",
            // biome-ignore lint/style/useNamingConvention: database columns use snake_case
            stripe_payment_intent_id: payload.stripePaymentIntentId,
            // biome-ignore lint/style/useNamingConvention: database columns use snake_case
            trip_id: params.tripId ?? null,
            // biome-ignore lint/style/useNamingConvention: database columns use snake_case
            user_id: ctx.userId,
          });
          if (error) {
            throw error;
          }
        },
        processPayment: ctx.processPayment,
        providerPayload,
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

  /** Build a Expedia Partner Solutions booking payload. */
  private buildExpediaBookingPayload(
    params: AccommodationBookingRequest
  ): EpsCreateBookingRequest {
    const traveler = splitGuestName(params.guestName);
    const normalizedPhone = normalizePhoneForRapid(params.guestPhone);

    return {
      affiliateReferenceId: params.tripId ?? params.listingId,
      billingContact: {
        address: {
          city: "Unknown",
          countryCode: normalizedPhone.countryCode ?? "US",
          line1: "Not Provided",
        },
        familyName: traveler.familyName,
        givenName: traveler.givenName,
      },
      bookingToken: params.bookingToken,
      contact: {
        email: params.guestEmail,
        phoneAreaCode: normalizedPhone.areaCode,
        phoneCountryCode: normalizedPhone.countryCode,
        phoneNumber: normalizedPhone.number,
      },
      specialRequests: params.specialRequests,
      stay: {
        adults: params.guests,
        checkIn: params.checkin,
        checkOut: params.checkout,
      },
      traveler,
    };
  }
}

/** Resolve property IDs using semantic RAG matching. */
async function resolvePropertyIds(
  params: AccommodationSearchParams,
  supabase: TypedServerSupabase
): Promise<string[] | undefined> {
  if (!params.semanticQuery || params.semanticQuery.trim().length === 0) {
    return undefined;
  }

  // biome-ignore lint/suspicious/noExplicitAny: Supabase RPC types are not fully generated
  const { data: ragResults } = await (supabase as any).rpc(
    "match_accommodation_embeddings",
    {
      // biome-ignore lint/style/useNamingConvention: Supabase function arguments use snake_case
      match_count: 20,
      // biome-ignore lint/style/useNamingConvention: Supabase function arguments use snake_case
      match_threshold: 0.75,
      // biome-ignore lint/style/useNamingConvention: Supabase function arguments use snake_case
      query_embedding: await generateEmbedding(params.semanticQuery),
    }
  );

  if (!ragResults || !Array.isArray(ragResults)) {
    return undefined;
  }

  const ids = (ragResults as Array<{ id: string }>).map((item) => item.id);
  return ids.length > 0 ? ids : undefined;
}

/** Map availability response to a list of listings. */
function mapAvailabilityToListings(
  response: RapidAvailabilityResponse,
  meta: Record<string, unknown>
): Array<Record<string, unknown>> {
  return (response.properties ?? []).map((property) => {
    const rooms = (property.rooms ?? []).map((room) => ({
      description: room.description,
      id: room.id,
      rates: (room.rates ?? []).map((rate) =>
        normalizeRate(property.property_id ?? "", room.id ?? "", rate)
      ),
      roomName: room.room_name,
    }));

    return {
      address: property.address ?? property.summary?.location?.address,
      amenities: property.amenities,
      coordinates: property.summary?.location?.coordinates,
      id: property.property_id,
      links: property.links,
      name: property.summary?.name ?? property.name,
      propertyType: property.property_type,
      provider: "expedia" as const,
      rooms,
      score: property.score,
      searchMeta: meta,
      starRating: property.summary?.star_rating?.value ?? property.star_rating,
      status: property.status,
      summary: property.summary,
    };
  });
}

/** Normalize a rate object. */
function normalizeRate(propertyId: string, roomId: string, rate: RapidRate) {
  const totals = extractInclusiveTotal(rate.pricing);
  const numeric = totals?.total ? Number.parseFloat(totals.total) : undefined;
  const priceCheckLink = rate.links?.price_check;
  const token = extractTokenFromHref(priceCheckLink?.href);

  return {
    availableRooms: rate.available_rooms,
    id: rate.id,
    original: rate,
    price: totals
      ? {
          currency: totals.currency,
          numeric: Number.isFinite(numeric) ? numeric : undefined,
          total: totals.total,
        }
      : undefined,
    priceCheck: priceCheckLink
      ? {
          href: priceCheckLink.href,
          propertyId,
          rateId: rate.id ?? "",
          roomId,
          token,
        }
      : undefined,
    refundability: rate.current_refundability,
    refundable: rate.refundable,
  };
}

/** Collect prices from a list of listings. */
function collectListingPrices(listings: Array<Record<string, unknown>>): number[] {
  const values: number[] = [];
  for (const listing of listings) {
    const rooms = (listing.rooms as Array<Record<string, unknown>> | undefined) ?? [];
    for (const room of rooms) {
      const rates =
        (room.rates as Array<Record<string, { numeric?: number }>> | undefined) ?? [];
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

/** Extract a token from a href. */
export function extractTokenFromHref(href?: string | null): string | undefined {
  if (!href) return undefined;
  try {
    const url = new URL(href, "https://test.ean.com");
    return url.searchParams.get("token") ?? undefined;
  } catch {
    return undefined;
  }
}

/** Split a guest name into given and family names. */
export function splitGuestName(name: string): {
  givenName: string;
  familyName: string;
} {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) {
    return { familyName: parts[0], givenName: parts[0] };
  }
  return {
    familyName: parts.slice(-1)[0],
    givenName: parts.slice(0, -1).join(" "),
  };
}

/** Normalize a phone number for Rapid API. */
export function normalizePhoneForRapid(phone?: string) {
  if (!phone?.trim()) {
    return { countryCode: "1", number: "0000000" };
  }

  const digits = phone.replace(/\D/g, "");
  if (digits.length === 0) {
    return { countryCode: "1", number: "0000000" };
  }

  if (digits.length <= 7) {
    return { countryCode: "1", number: digits.padStart(7, "0") };
  }

  if (digits.length <= 10) {
    return {
      areaCode: digits.slice(0, digits.length - 7),
      countryCode: "1",
      number: digits.slice(-7),
    };
  }

  return {
    areaCode: digits.slice(digits.length - 10, digits.length - 7),
    countryCode: digits.slice(0, digits.length - 10),
    number: digits.slice(-7),
  };
}
