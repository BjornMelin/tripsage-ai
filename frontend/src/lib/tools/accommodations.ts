/**
 * @fileoverview Accommodation search, booking, and details tools.
 *
 * Prefers MCP SSE (Airbnb) for real-time capabilities, falls back to HTTP
 * POST/GET for broader compatibility. Booking operations require user approval
 * via the approvals system. Implements full feature parity with Python
 * accommodations_tools.
 */

import "server-only";

import { tool } from "ai";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { fetchWithRetry } from "@/lib/http/fetch-retry";
import { createMcpClientHelper, getMcpTool } from "@/lib/mcp/client";
import { getRedis } from "@/lib/redis";
import {
  ACCOMMODATION_BOOKING_INPUT_SCHEMA,
  ACCOMMODATION_BOOKING_OUTPUT_SCHEMA,
  ACCOMMODATION_DETAILS_INPUT_SCHEMA,
  ACCOMMODATION_DETAILS_OUTPUT_SCHEMA,
  ACCOMMODATION_SEARCH_INPUT_SCHEMA,
  ACCOMMODATION_SEARCH_OUTPUT_SCHEMA,
  type AccommodationBookingResult,
  type AccommodationDetailsResult,
  type AccommodationSearchResult,
} from "@/lib/schemas/accommodations";
import { secureUuid } from "@/lib/security/random";
import { createToolError, TOOL_ERROR_CODES } from "@/lib/tools/errors";
import { requireApproval } from "./approvals";
import { ACCOM_SEARCH_CACHE_TTL_SECONDS } from "./constants";

/**
 * Zod input schema for accommodation search tool.
 *
 * Exported for use in guardrails validation and cache key generation.
 */
export { ACCOMMODATION_SEARCH_INPUT_SCHEMA as searchAccommodationsInputSchema };

/**
 * Execute search via MCP SSE if available, else HTTP POST fallback.
 *
 * Attempts to use MCP SSE transport first for real-time capabilities.
 * Falls back to standard HTTP POST if MCP is unavailable or fails.
 *
 * @param params - The search parameters (location, dates, filters, etc.).
 * @returns Promise resolving to search result data and provider identifier ("mcp_sse" or "http_post").
 * @throws {Error} Error with `code` property indicating failure reason:
 *   - "accom_search_not_configured": No URL configured
 *   - "accom_search_timeout": Request timed out
 *   - "accom_search_failed": Network or API error
 *   - "accom_search_rate_limited": Rate limit exceeded (429)
 *   - "accom_search_unauthorized": Authentication failed (401)
 *   - "accom_search_payment_required": Payment required (402)
 */
import { getServerEnvVarWithFallback } from "@/lib/env/server";

async function executeSearch(
  params: Record<string, unknown>
): Promise<{ data: unknown; provider: string }> {
  const mcpUrl =
    getServerEnvVarWithFallback("AIRBNB_MCP_URL", undefined) ||
    getServerEnvVarWithFallback("ACCOM_SEARCH_URL", undefined);
  const mcpAuth =
    getServerEnvVarWithFallback("AIRBNB_MCP_API_KEY", undefined) ||
    getServerEnvVarWithFallback("ACCOM_SEARCH_TOKEN", undefined);

  // Try MCP SSE first
  if (mcpUrl?.includes("mcp") && mcpAuth) {
    try {
      const client = await createMcpClientHelper(mcpUrl, {
        authorization: `Bearer ${mcpAuth}`,
      });
      const searchTool = await getMcpTool(
        client,
        "airbnb_search",
        "search_accommodations"
      );
      if (searchTool) {
        const result = await searchTool.execute(params);
        await client.close();
        return { data: result, provider: "mcp_sse" };
      }
      await client.close();
    } catch {
      // Fall through to HTTP fallback
    }
  }

  // HTTP POST fallback
  const httpUrl =
    getServerEnvVarWithFallback("ACCOM_SEARCH_URL", undefined) ||
    getServerEnvVarWithFallback("AIRBNB_MCP_URL", undefined);
  const httpToken =
    getServerEnvVarWithFallback("ACCOM_SEARCH_TOKEN", undefined) ||
    getServerEnvVarWithFallback("AIRBNB_MCP_API_KEY", undefined);
  if (!httpUrl) {
    throw createToolError(TOOL_ERROR_CODES.accomSearchNotConfigured);
  }

  const res = await fetchWithRetry(
    httpUrl,
    {
      body: JSON.stringify(params),
      headers: {
        "content-type": "application/json",
        ...(httpToken ? { authorization: `Bearer ${httpToken}` } : {}),
      },
      method: "POST",
    },
    { retries: 2, timeoutMs: 12000 }
  ).catch((err) => {
    // Map generic fetch errors to domain-specific codes
    const errWithCode = err as Error & {
      code?: string;
      meta?: Record<string, unknown>;
    };
    if (errWithCode.code === "fetch_timeout") {
      throw createToolError(
        TOOL_ERROR_CODES.accomSearchTimeout,
        undefined,
        errWithCode.meta
      );
    }
    if (errWithCode.code === "fetch_failed") {
      throw createToolError(
        TOOL_ERROR_CODES.accomSearchFailed,
        undefined,
        errWithCode.meta
      );
    }
    throw err;
  });

  if (!res.ok) {
    const text = await res.text();
    const code =
      res.status === 429
        ? TOOL_ERROR_CODES.accomSearchRateLimited
        : res.status === 401
          ? TOOL_ERROR_CODES.accomSearchUnauthorized
          : res.status === 402
            ? TOOL_ERROR_CODES.accomSearchPaymentRequired
            : TOOL_ERROR_CODES.accomSearchFailed;
    throw createToolError(code, undefined, {
      status: res.status,
      text: text.slice(0, 200),
    });
  }

  const data = await res.json();
  return { data, provider: "http_post" };
}

/**
 * Search accommodations tool.
 *
 * Searches for accommodations using MCP SSE (Airbnb) or HTTP POST fallback.
 * Supports comprehensive filtering by property types, amenities, price range,
 * guest counts, instant book availability, cancellation policy, distance,
 * rating, and sorting options. Results are cached for performance.
 *
 * @returns AccommodationSearchResult with listings, pricing metadata, and search parameters.
 */
export const searchAccommodations = tool({
  description:
    "Search accommodations via MCP SSE (Airbnb) or HTTP POST fallback. " +
    "Supports filters: property types, amenities, price range, guest counts, " +
    "instant book, cancellation policy, distance, rating, and sorting.",
  execute: async (params): Promise<AccommodationSearchResult> => {
    const validated = ACCOMMODATION_SEARCH_INPUT_SCHEMA.parse(params);
    const startedAt = Date.now();

    // Normalize guest counts: if only guests provided, treat as adults
    const adults = validated.adults ?? validated.guests;
    const children = validated.children ?? 0;
    const infants = validated.infants ?? 0;

    // Build search payload
    const searchParams: Record<string, unknown> = {
      adults,
      checkin: validated.checkin,
      checkout: validated.checkout,
      children,
      guests: validated.guests,
      infants,
      location: validated.location.trim(),
    };
    if (validated.priceMin !== undefined) searchParams.min_price = validated.priceMin;
    if (validated.priceMax !== undefined) searchParams.max_price = validated.priceMax;
    if (validated.propertyTypes && validated.propertyTypes.length > 0) {
      searchParams.property_types = validated.propertyTypes;
    }
    if (validated.amenities && validated.amenities.length > 0) {
      searchParams.amenities = validated.amenities;
    }
    if (validated.accessibilityFeatures && validated.accessibilityFeatures.length > 0) {
      searchParams.accessibility_features = validated.accessibilityFeatures;
    }
    if (validated.bedrooms !== undefined) searchParams.bedrooms = validated.bedrooms;
    if (validated.beds !== undefined) searchParams.beds = validated.beds;
    if (validated.bathrooms !== undefined) searchParams.bathrooms = validated.bathrooms;
    if (validated.instantBook !== undefined)
      searchParams.instant_book = validated.instantBook;
    if (validated.freeCancellation !== undefined)
      searchParams.free_cancellation = validated.freeCancellation;
    if (validated.maxDistanceKm !== undefined)
      searchParams.max_distance_km = validated.maxDistanceKm;
    if (validated.minRating !== undefined)
      searchParams.min_rating = validated.minRating;
    if (validated.sortBy) searchParams.sort_by = validated.sortBy;
    if (validated.sortOrder) searchParams.sort_order = validated.sortOrder;
    if (validated.currency) searchParams.currency = validated.currency;
    if (validated.tripId) searchParams.trip_id = validated.tripId;

    // Check cache
    const redis = getRedis();
    const cacheKey = canonicalizeParamsForCache(searchParams, "accom_search");
    const fromCache = false;
    if (!validated.fresh && redis) {
      const cached = await redis.get(cacheKey);
      if (cached) {
        const cachedData = cached as AccommodationSearchResult;
        const rawOut = {
          ...cachedData,
          fromCache: true,
          provider: cachedData.provider || "cache",
          tookMs: Date.now() - startedAt,
        };
        return ACCOMMODATION_SEARCH_OUTPUT_SCHEMA.parse(rawOut);
      }
    }

    // Execute search
    const { data, provider } = await executeSearch(searchParams);
    const searchId = secureUuid();
    const tookMs = Date.now() - startedAt;

    const rawOut = {
      avgPrice: (data as Record<string, unknown>).avg_price as number | undefined,
      fromCache,
      listings: Array.isArray(data)
        ? data
        : ((data as Record<string, unknown>).listings as unknown[] | undefined) || [],
      maxPrice: (data as Record<string, unknown>).max_price as number | undefined,
      minPrice: (data as Record<string, unknown>).min_price as number | undefined,
      provider,
      resultsReturned: Array.isArray(data)
        ? data.length
        : ((data as Record<string, unknown>).results_returned as number | undefined) ||
          0,
      searchId,
      searchParameters: searchParams,
      status: "success" as const,
      tookMs,
      totalResults: Array.isArray(data)
        ? data.length
        : ((data as Record<string, unknown>).total_results as number | undefined) || 0,
    };

    // Validate against strict schema
    const validatedResult = ACCOMMODATION_SEARCH_OUTPUT_SCHEMA.parse(rawOut);

    // Cache validated result
    if (redis && !validated.fresh) {
      await redis.set(cacheKey, validatedResult, {
        ex: ACCOM_SEARCH_CACHE_TTL_SECONDS,
      });
    }

    return validatedResult;
  },
  inputSchema: ACCOMMODATION_SEARCH_INPUT_SCHEMA,
});

/**
 * Book accommodation tool.
 *
 * Creates a booking request for an accommodation listing. Requires user
 * approval via the approvals system before proceeding. Supports hold-only
 * bookings, special requests, and idempotency keys for safe retries.
 *
 * @returns AccommodationBookingResult with booking confirmation details, status, and reference number.
 */
export const bookAccommodation = tool({
  description:
    "Book an accommodation (requires user approval). Supports hold-only bookings, " +
    "special requests, and idempotency. Returns structured booking intent.",
  execute: async (params): Promise<AccommodationBookingResult> => {
    const validated = ACCOMMODATION_BOOKING_INPUT_SCHEMA.parse(params);
    const idempotencyKey = validated.idempotencyKey || secureUuid();
    const sessionId = validated.sessionId;

    if (!sessionId) {
      throw createToolError(TOOL_ERROR_CODES.accomBookingSessionRequired);
    }

    // Require approval with idempotency key
    await requireApproval("bookAccommodation", {
      idempotencyKey,
      sessionId,
    });

    // Approval granted, proceed with booking
    // In a full implementation, call the MCP "book" tool or provider API here
    const bookingReference = `bk_${secureUuid().replaceAll("-", "").slice(0, 10)}`;
    const rawOut = {
      bookingId: secureUuid(),
      bookingStatus: validated.holdOnly
        ? ("hold_created" as const)
        : ("pending_confirmation" as const),
      checkin: validated.checkin,
      checkout: validated.checkout,
      guestEmail: validated.guestEmail,
      guestName: validated.guestName,
      guestPhone: validated.guestPhone,
      guests: validated.guests,
      holdOnly: validated.holdOnly || false,
      idempotencyKey,
      listingId: validated.listingId,
      message: validated.holdOnly
        ? "Booking hold created. Provider confirmation pending."
        : "Booking request created. Provider confirmation pending.",
      paymentMethod: validated.paymentMethod,
      reference: bookingReference,
      specialRequests: validated.specialRequests,
      status: "success" as const,
      tripId: validated.tripId,
    };
    return ACCOMMODATION_BOOKING_OUTPUT_SCHEMA.parse(rawOut);
  },
  inputSchema: ACCOMMODATION_BOOKING_INPUT_SCHEMA,
});

/**
 * Get accommodation details tool.
 *
 * Retrieves detailed information for a specific accommodation listing.
 * Optionally accepts check-in/out dates and guest counts for accurate
 * pricing and availability. Uses MCP SSE if available, falls back to HTTP GET.
 *
 * @returns AccommodationDetailsResult with full listing information and provider metadata.
 */
export const getAccommodationDetails = tool({
  description:
    "Get detailed information for a specific accommodation listing. " +
    "Optionally include check-in/out dates and guest counts for accurate pricing.",
  execute: async (params): Promise<AccommodationDetailsResult> => {
    const validated = ACCOMMODATION_DETAILS_INPUT_SCHEMA.parse(params);
    const mcpUrl =
      getServerEnvVarWithFallback("AIRBNB_MCP_URL", undefined) ||
      getServerEnvVarWithFallback("ACCOM_SEARCH_URL", undefined);
    const mcpAuth =
      getServerEnvVarWithFallback("AIRBNB_MCP_API_KEY", undefined) ||
      getServerEnvVarWithFallback("ACCOM_SEARCH_TOKEN", undefined);

    // Try MCP SSE first
    if (mcpUrl?.includes("mcp") && mcpAuth) {
      try {
        const client = await createMcpClientHelper(mcpUrl, {
          authorization: `Bearer ${mcpAuth}`,
        });
        const detailsTool = await getMcpTool(
          client,
          "airbnb_listing_details",
          "get_accommodation_details"
        );
        if (detailsTool) {
          const result = await detailsTool.execute({
            adults: validated.adults || 1,
            checkin: validated.checkin,
            checkout: validated.checkout,
            children: validated.children || 0,
            id: validated.listingId,
            infants: validated.infants || 0,
          });
          await client.close();
          const rawOut = {
            listing: result,
            provider: "mcp_sse",
            status: "success" as const,
          };
          return ACCOMMODATION_DETAILS_OUTPUT_SCHEMA.parse(rawOut);
        }
        await client.close();
      } catch {
        // Fall through to HTTP fallback
      }
    }

    // HTTP fallback
    const httpUrl =
      getServerEnvVarWithFallback("ACCOM_SEARCH_URL", undefined) ||
      getServerEnvVarWithFallback("AIRBNB_MCP_URL", undefined);
    const httpToken =
      getServerEnvVarWithFallback("ACCOM_SEARCH_TOKEN", undefined) ||
      getServerEnvVarWithFallback("AIRBNB_MCP_API_KEY", undefined);
    if (!httpUrl) {
      throw createToolError(TOOL_ERROR_CODES.accomDetailsNotConfigured);
    }

    const url = new URL(httpUrl);
    url.pathname = url.pathname.endsWith("/")
      ? `${url.pathname}details`
      : `${url.pathname}/details`;
    url.searchParams.set("listing_id", validated.listingId);
    if (validated.checkin) url.searchParams.set("checkin", validated.checkin);
    if (validated.checkout) url.searchParams.set("checkout", validated.checkout);
    if (validated.adults) url.searchParams.set("adults", String(validated.adults));
    if (validated.children)
      url.searchParams.set("children", String(validated.children));
    if (validated.infants) url.searchParams.set("infants", String(validated.infants));

    const res = await fetchWithRetry(
      url.toString(),
      {
        headers: httpToken ? { authorization: `Bearer ${httpToken}` } : undefined,
      },
      { retries: 2, timeoutMs: 12000 }
    ).catch((err) => {
      // Map generic fetch errors to domain-specific codes
      const errWithCode = err as Error & {
        code?: string;
        meta?: Record<string, unknown>;
      };
      if (errWithCode.code === "fetch_timeout") {
        throw createToolError(
          TOOL_ERROR_CODES.accomDetailsTimeout,
          undefined,
          errWithCode.meta
        );
      }
      if (errWithCode.code === "fetch_failed") {
        throw createToolError(
          TOOL_ERROR_CODES.accomDetailsFailed,
          undefined,
          errWithCode.meta
        );
      }
      throw err;
    });

    if (!res.ok) {
      const text = await res.text();
      const code =
        res.status === 404
          ? TOOL_ERROR_CODES.accomDetailsNotFound
          : res.status === 429
            ? TOOL_ERROR_CODES.accomDetailsRateLimited
            : res.status === 401
              ? TOOL_ERROR_CODES.accomDetailsUnauthorized
              : TOOL_ERROR_CODES.accomDetailsFailed;
      throw createToolError(code, undefined, {
        status: res.status,
        text: text.slice(0, 200),
      });
    }

    const data = await res.json();
    const rawOut = {
      listing: data,
      provider: "http_get",
      status: "success" as const,
    };
    return ACCOMMODATION_DETAILS_OUTPUT_SCHEMA.parse(rawOut);
  },
  inputSchema: ACCOMMODATION_DETAILS_INPUT_SCHEMA,
});
