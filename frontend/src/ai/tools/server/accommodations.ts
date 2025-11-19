/**
 * @fileoverview Accommodation search, booking, and details tools.
 *
 * Implements Expedia Partner Solutions (EPS) Rapid API integrations for
 * accommodation discovery, details, availability checks, and bookings. The
 * tools use the shared createAiTool factory so rate limiting, caching, and
 * telemetry are uniform across all agents.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import {
  createToolError,
  TOOL_ERROR_CODES,
  type ToolErrorCode,
} from "@ai/tools/server/errors";
import {
  ExpediaApiError,
  type ExpediaRequestContext,
  getExpediaClient,
} from "@domain/expedia/client";
import {
  ACCOMMODATION_BOOKING_INPUT_SCHEMA,
  ACCOMMODATION_BOOKING_OUTPUT_SCHEMA,
  ACCOMMODATION_CHECK_AVAILABILITY_INPUT_SCHEMA,
  ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA,
  ACCOMMODATION_DETAILS_INPUT_SCHEMA,
  ACCOMMODATION_DETAILS_OUTPUT_SCHEMA,
  ACCOMMODATION_SEARCH_INPUT_SCHEMA,
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
  EpsCheckAvailabilityResponse,
  EpsCreateBookingRequest,
  RapidAvailabilityResponse,
  RapidPropertyContent,
  RapidRate,
} from "@schemas/expedia";
import { extractInclusiveTotal } from "@schemas/expedia";
import { parsePhoneNumberFromString } from "libphonenumber-js/min";
import { headers } from "next/headers";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import {
  generateEmbedding,
  getEmbeddingsApiUrl,
  getEmbeddingsRequestHeaders,
} from "@/lib/embeddings/generate";
import { processBookingPayment } from "@/lib/payments/booking-payment";
import { secureUuid } from "@/lib/security/random";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { requireApproval } from "./approvals";
import { ACCOM_SEARCH_CACHE_TTL_SECONDS } from "./constants";

const accommodationsLogger = createServerLogger("tools.accommodations");

export { ACCOMMODATION_SEARCH_INPUT_SCHEMA as searchAccommodationsInputSchema };

export const searchAccommodations = createAiTool<
  AccommodationSearchParams,
  AccommodationSearchResult
>({
  description:
    "Search for accommodations (hotels and Vrbo vacation rentals) using Expedia Partner Solutions API. " +
    "Supports semantic search via RAG for natural language queries (e.g., 'quiet place near the beach', 'good for families'). " +
    "Returns properties with pricing, availability, and metadata for downstream tools.",
  execute: async (params) => runAccommodationSearch(params),
  guardrails: {
    cache: {
      deserialize: (payload) => ACCOMMODATION_SEARCH_OUTPUT_SCHEMA.parse(payload ?? {}),
      key: (params) => buildSearchCacheKey(params),
      namespace: "tool:accom:search",
      onHit: (cached, _params, meta) => ({
        ...cached,
        fromCache: true,
        tookMs: Date.now() - meta.startedAt,
      }),
      serialize: (result) => ({ ...result, fromCache: false }),
      shouldBypass: (params) => Boolean(params.fresh),
      ttlSeconds: ACCOM_SEARCH_CACHE_TTL_SECONDS,
    },
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.accomSearchRateLimited,
      limit: 10,
      prefix: "ratelimit:accommodations:search",
      window: "1 m",
    },
    telemetry: {
      attributes: (params) => ({
        fresh: Boolean(params.fresh),
        hasSemanticQuery: Boolean(params.semanticQuery?.trim()),
        locationLength: params.location.length,
        priceFilters:
          Number(Boolean(params.priceMin)) + Number(Boolean(params.priceMax)),
      }),
      redactKeys: ["location", "semanticQuery"],
      workflow: "accommodationSearch",
    },
  },
  inputSchema: ACCOMMODATION_SEARCH_INPUT_SCHEMA,
  name: "searchAccommodations",
});

export const getAccommodationDetails = createAiTool<
  AccommodationDetailsParams,
  AccommodationDetailsResult
>({
  description:
    "Retrieve comprehensive details for a specific accommodation property from Expedia Partner Solutions. " +
    "Returns amenities, policies, reviews, photos, and rate information. Provide check-in/out dates for precise pricing.",
  execute: async (params) => {
    const expediaClient = getExpediaClient();
    let propertyDetails: RapidPropertyContent | null;
    try {
      propertyDetails = await expediaClient.getPropertyDetails({
        language: "en-US",
        propertyId: params.listingId,
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

    return ACCOMMODATION_DETAILS_OUTPUT_SCHEMA.parse({
      listing: propertyDetails,
      provider: "expedia" as const,
      status: "success" as const,
    });
  },
  inputSchema: ACCOMMODATION_DETAILS_INPUT_SCHEMA,
  name: "getAccommodationDetails",
});

export const checkAvailability = createAiTool<
  AccommodationCheckAvailabilityParams,
  AccommodationCheckAvailabilityResult
>({
  description:
    "Check final availability and lock pricing for a specific rate. Returns a booking token that must be used quickly to finalize the booking.",
  execute: async (params) => {
    const userId = await getUserIdFromHeadersOrThrow(
      TOOL_ERROR_CODES.accomBookingSessionRequired
    );
    const expediaClient = getExpediaClient();
    let availabilityResponse: EpsCheckAvailabilityResponse;
    try {
      availabilityResponse = await expediaClient.checkAvailability(
        {
          propertyId: params.propertyId,
          rateId: params.rateId,
          roomId: params.roomId,
          token: params.priceCheckToken,
        },
        buildExpediaContext(userId)
      );
    } catch (error) {
      if (error instanceof ExpediaApiError) {
        if (error.statusCode === 404) {
          throw createToolError(TOOL_ERROR_CODES.accomAvailabilityNotFound);
        }
        if (error.statusCode === 401) {
          throw createToolError(TOOL_ERROR_CODES.accomAvailabilityUnauthorized);
        }
        if (error.statusCode === 429) {
          throw createToolError(TOOL_ERROR_CODES.accomAvailabilityRateLimited);
        }
      }
      throw createToolError(TOOL_ERROR_CODES.accomAvailabilityFailed, undefined, {
        error: error instanceof Error ? error.message : "Unknown error",
      });
    }

    return ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA.parse({
      bookingToken: availabilityResponse.bookingToken,
      expiresAt: availabilityResponse.expiresAt,
      price: availabilityResponse.price,
      propertyId: availabilityResponse.propertyId,
      rateId: availabilityResponse.rateId,
      status: "success" as const,
    });
  },
  inputSchema: ACCOMMODATION_CHECK_AVAILABILITY_INPUT_SCHEMA,
  name: "checkAvailability",
});

export const bookAccommodation = createAiTool<
  AccommodationBookingRequest,
  AccommodationBookingResult
>({
  description:
    "Complete an accommodation booking via Expedia Partner Solutions. Requires a bookingToken from checkAvailability, payment method, and prior approval.",
  execute: async (params) => {
    const sessionId = params.sessionId;
    if (!sessionId) {
      throw createToolError(TOOL_ERROR_CODES.accomBookingSessionRequired);
    }

    const userId = await getUserIdFromHeadersOrThrow(
      TOOL_ERROR_CODES.accomBookingSessionRequired
    );
    const idempotencyKey = params.idempotencyKey || secureUuid();

    await requireApproval("bookAccommodation", {
      idempotencyKey,
      sessionId,
    });

    const bookingId = secureUuid();
    const supabase = await createServerSupabase();

    let paymentIntentId: string;
    let confirmationNumber: string;
    let epsItineraryId: string;
    try {
      const travelerName = splitGuestName(params.guestName);
      const normalizedPhone = normalizePhoneForRapid(params.guestPhone);
      const expediaPayload: EpsCreateBookingRequest = {
        affiliateReferenceId: params.tripId ?? bookingId,
        billingContact: {
          address: {
            city: "Unknown",
            countryCode: normalizedPhone.countryCode ?? "US",
            line1: "Not Provided",
          },
          familyName: travelerName.familyName,
          givenName: travelerName.givenName,
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
        traveler: travelerName,
      };

      const paymentResult = await processBookingPayment({
        amount: params.amount,
        currency: params.currency,
        customerId: userId,
        expediaRequest: expediaPayload,
        paymentMethodId: params.paymentMethodId,
        user: {
          email: params.guestEmail,
          name: params.guestName,
          phone: params.guestPhone,
        },
      });

      paymentIntentId = paymentResult.paymentIntentId;
      confirmationNumber = paymentResult.confirmationNumber;
      epsItineraryId = paymentResult.itineraryId;
    } catch (error) {
      throw createToolError(TOOL_ERROR_CODES.accomBookingFailed, undefined, {
        error: error instanceof Error ? error.message : "Unknown booking error",
      });
    }

    try {
      // biome-ignore lint/suspicious/noExplicitAny: Supabase types do not include bookings table entries yet
      const { error } = await (supabase as any).from("bookings").insert({
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        booking_token: params.bookingToken,
        checkin: params.checkin,
        checkout: params.checkout,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        eps_booking_id: epsItineraryId,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        guest_email: params.guestEmail,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        guest_name: params.guestName,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        guest_phone: params.guestPhone || null,
        guests: params.guests,
        id: bookingId,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        property_id: params.listingId,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        special_requests: params.specialRequests || null,
        status: "CONFIRMED",
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        stripe_payment_intent_id: paymentIntentId,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        trip_id: params.tripId || null,
        // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
        user_id: userId,
      });

      if (error) {
        accommodationsLogger.error("booking_insert_failed", {
          error: error instanceof Error ? error.message : "unknown_error",
        });
      }
    } catch (dbError) {
      accommodationsLogger.error("booking_database_error", {
        error: dbError instanceof Error ? dbError.message : "unknown_error",
      });
    }

    const bookingReference =
      confirmationNumber || `bk_${bookingId.replaceAll("-", "").slice(0, 10)}`;
    const confirmationDisplay = confirmationNumber ?? bookingReference;

    return ACCOMMODATION_BOOKING_OUTPUT_SCHEMA.parse({
      bookingId,
      bookingStatus: "confirmed" as const,
      checkin: params.checkin,
      checkout: params.checkout,
      epsBookingId: epsItineraryId,
      guestEmail: params.guestEmail,
      guestName: params.guestName,
      guestPhone: params.guestPhone,
      guests: params.guests,
      holdOnly: params.holdOnly || false,
      idempotencyKey,
      listingId: params.listingId,
      message: `Booking confirmed! Confirmation number: ${confirmationDisplay}`,
      paymentMethod: params.paymentMethodId,
      reference: bookingReference,
      specialRequests: params.specialRequests,
      status: "success" as const,
      stripePaymentIntentId: paymentIntentId,
      tripId: params.tripId,
    });
  },
  inputSchema: ACCOMMODATION_BOOKING_INPUT_SCHEMA,
  name: "bookAccommodation",
});

async function runAccommodationSearch(
  params: AccommodationSearchParams
): Promise<AccommodationSearchResult> {
  const supabase = await createServerSupabase();
  const startedAt = Date.now();

  const propertyIds = await resolvePropertyIds(params, supabase);
  if (!propertyIds || propertyIds.length === 0) {
    throw createToolError(TOOL_ERROR_CODES.accomSearchNotConfigured, undefined, {
      reason: "missing_expedia_property_ids",
    });
  }

  const expediaClient = getExpediaClient();
  const expediaContext = buildExpediaContext(await maybeGetUserIdentifier());

  let searchResponse: RapidAvailabilityResponse;
  try {
    searchResponse = await expediaClient.searchAvailability(
      {
        checkIn: params.checkin,
        checkOut: params.checkout,
        countryCode: "US",
        currency: params.currency ?? "USD",
        guests: params.guests,
        include: ["rooms.rates.current_refundability"],
        language: "en-US",
        propertyIds,
        ratePlanCount: params.propertyTypes ? 6 : 4,
      },
      expediaContext
    );
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

  const listings = mapAvailabilityToListings(searchResponse, {
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
    totalResults: searchResponse.total ?? listings.length,
  });

  triggerEmbeddingIngest(listings);
  return result;
}

async function resolvePropertyIds(
  params: AccommodationSearchParams,
  supabase: Awaited<ReturnType<typeof createServerSupabase>>
): Promise<string[] | undefined> {
  if (!params.semanticQuery || params.semanticQuery.trim().length === 0) {
    return undefined;
  }

  try {
    const queryEmbedding = await generateEmbedding(params.semanticQuery);
    // biome-ignore lint/suspicious/noExplicitAny: Supabase RPC types are not fully generated
    const { data: ragResults, error } = await (supabase as any).rpc(
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

    if (!error && ragResults && Array.isArray(ragResults)) {
      const ids = (ragResults as Array<{ id: string }>).map((item) => item.id);
      if (ids.length > 0) {
        accommodationsLogger.info("rag_semantic_matches", {
          matchCount: ids.length,
          query: params.semanticQuery,
        });
      }
      return ids;
    }
  } catch (ragErr) {
    accommodationsLogger.error("rag_semantic_search_failed", {
      error: ragErr instanceof Error ? ragErr.message : "unknown_error",
    });
  }

  return undefined;
}

function triggerEmbeddingIngest(listings: Array<Record<string, unknown>>) {
  if (listings.length === 0 || typeof fetch !== "function") {
    return;
  }

  const embeddingsUrl = getEmbeddingsApiUrl();
  const embeddingsHeaders = getEmbeddingsRequestHeaders();

  for (const property of listings) {
    const payload = {
      amenities: (property.amenities as string[]) ?? [],
      description: property.description,
      id: property.id,
      name: property.name,
      source: property.source,
    };

    fetch(embeddingsUrl, {
      body: JSON.stringify({ property: payload }),
      headers: embeddingsHeaders,
      method: "POST",
    })
      .then(() => undefined)
      .catch((error) => {
        accommodationsLogger.error("embedding_trigger_failed", {
          error: error instanceof Error ? error.message : "unknown_error",
          propertyId: property.id,
        });
      });
  }
}

function buildSearchCacheKey(params: AccommodationSearchParams): string {
  return canonicalizeParamsForCache(
    {
      ...params,
      semanticQuery: params.semanticQuery || "",
    },
    "accom_search"
  );
}

async function maybeGetUserIdentifier(): Promise<string | undefined> {
  try {
    const requestHeaders = await headers();
    const userId = requestHeaders.get("x-user-id");
    if (userId) {
      const trimmed = userId.trim();
      if (trimmed) {
        return trimmed;
      }
    }
  } catch {
    // headers() can throw outside of a request context.
  }
  return undefined;
}

async function getUserIdFromHeadersOrThrow(errorCode: ToolErrorCode): Promise<string> {
  const identifier = await maybeGetUserIdentifier();
  if (identifier) {
    return identifier;
  }
  throw createToolError(errorCode);
}

function buildExpediaContext(seed?: string): ExpediaRequestContext {
  return {
    customerSessionId: seed ?? secureUuid(),
  };
}

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

export function extractTokenFromHref(href?: string | null): string | undefined {
  if (!href) return undefined;
  try {
    const url = new URL(href, "https://test.ean.com");
    return url.searchParams.get("token") ?? undefined;
  } catch {
    return undefined;
  }
}

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

export function normalizePhoneForRapid(phone?: string) {
  if (!phone?.trim()) {
    return { countryCode: "1", number: "0000000" };
  }

  const parsed = parsePhoneNumberFromString(phone);
  if (parsed?.isValid()) {
    const nationalNumber = parsed.nationalNumber;
    const areaCode =
      nationalNumber.length > 7 ? nationalNumber.slice(0, -7) : undefined;
    const number = nationalNumber.slice(-7).padStart(7, "0");

    return {
      areaCode,
      countryCode: String(parsed.countryCallingCode),
      number,
    };
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
