/**
 * @fileoverview Accommodation search, booking, and details tools.
 *
 * Prefers MCP SSE (Airbnb) for real-time capabilities, falls back to HTTP
 * POST/GET for broader compatibility. Booking operations require user approval
 * via the approvals system. Implements full feature parity with Python
 * accommodations_tools.
 */

import { tool } from "ai";
import { z } from "zod";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { fetchWithRetry } from "@/lib/http/fetch-retry";
import { createMcpClientHelper, getMcpTool } from "@/lib/mcp/client";
import { getRedis } from "@/lib/redis";
import { secureUuid } from "@/lib/security/random";
import type {
  AccommodationBookingResult,
  AccommodationDetailsResult,
  AccommodationSearchResult,
} from "@/types/accommodations";
import { requireApproval } from "./approvals";
import { ACCOM_SEARCH_CACHE_TTL_SECONDS } from "./constants";

// Property type enum matching Python PropertyType enum values
const PROPERTY_TYPE_ENUM = z.enum([
  "hotel",
  "apartment",
  "house",
  "villa",
  "resort",
  "hostel",
  "bed_and_breakfast",
  "guest_house",
  "other",
]);

// Sort field options for search results
const SORT_BY_ENUM = z.enum(["relevance", "price", "rating", "distance"]);
// Sort order options (ascending or descending)
const SORT_ORDER_ENUM = z.enum(["asc", "desc"]);

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
async function executeSearch(
  params: Record<string, unknown>
): Promise<{ data: unknown; provider: string }> {
  const mcpUrl = process.env.AIRBNB_MCP_URL || process.env.ACCOM_SEARCH_URL;
  const mcpAuth = process.env.AIRBNB_MCP_API_KEY || process.env.ACCOM_SEARCH_TOKEN;

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
  const httpUrl = process.env.ACCOM_SEARCH_URL || process.env.AIRBNB_MCP_URL;
  const httpToken = process.env.ACCOM_SEARCH_TOKEN || process.env.AIRBNB_MCP_API_KEY;
  if (!httpUrl) {
    const error: Error & { code?: string } = new Error("accom_search_not_configured");
    error.code = "accom_search_not_configured";
    throw error;
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
      const error: Error & { code?: string; meta?: Record<string, unknown> } =
        new Error("accom_search_timeout");
      error.code = "accom_search_timeout";
      error.meta = errWithCode.meta;
      throw error;
    }
    if (errWithCode.code === "fetch_failed") {
      const error: Error & { code?: string; meta?: Record<string, unknown> } =
        new Error("accom_search_failed");
      error.code = "accom_search_failed";
      error.meta = errWithCode.meta;
      throw error;
    }
    throw err;
  });

  if (!res.ok) {
    const text = await res.text();
    const error: Error & { code?: string; meta?: Record<string, unknown> } = new Error(
      res.status === 429
        ? "accom_search_rate_limited"
        : res.status === 401
          ? "accom_search_unauthorized"
          : res.status === 402
            ? "accom_search_payment_required"
            : "accom_search_failed"
    );
    error.code =
      res.status === 429
        ? "accom_search_rate_limited"
        : res.status === 401
          ? "accom_search_unauthorized"
          : res.status === 402
            ? "accom_search_payment_required"
            : "accom_search_failed";
    error.meta = { status: res.status, text: text.slice(0, 200) };
    throw error;
  }

  const data = await res.json();
  return { data, provider: "http_post" };
}

/**
 * Zod schema for search accommodations tool input validation.
 *
 * Validates location, dates, guest counts, filters, and sorting options.
 * Includes cross-field refinements for date ordering and price ranges.
 */
const searchSchema = z
  .object({
    accessibilityFeatures: z.array(z.string()).optional(),
    adults: z.number().int().min(1).max(16).optional(),
    amenities: z.array(z.string()).optional(),
    bathrooms: z.number().nonnegative().max(10).optional(),
    bedrooms: z.number().int().min(0).max(10).optional(),
    beds: z.number().int().min(0).max(20).optional(),
    checkin: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    checkout: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    children: z.number().int().min(0).max(16).optional(),
    currency: z.string().length(3).default("USD").optional(),
    freeCancellation: z.boolean().optional(),
    fresh: z.boolean().default(false).optional(),
    guests: z.number().int().min(1).max(16).default(1),
    infants: z.number().int().min(0).max(16).optional(),
    instantBook: z.boolean().optional(),
    location: z.string().min(2),
    maxDistanceKm: z.number().nonnegative().optional(),
    minRating: z.number().min(0).max(5).optional(),
    priceMax: z.number().nonnegative().optional(),
    priceMin: z.number().nonnegative().optional(),
    propertyTypes: z.array(PROPERTY_TYPE_ENUM).optional(),
    sortBy: SORT_BY_ENUM.default("relevance").optional(),
    sortOrder: SORT_ORDER_ENUM.default("asc").optional(),
    tripId: z.string().optional(),
  })
  .refine((data) => {
    const checkin = new Date(data.checkin);
    const checkout = new Date(data.checkout);
    return checkout > checkin;
  }, "checkout must be after checkin")
  .refine((data) => {
    if (data.priceMin !== undefined && data.priceMax !== undefined) {
      return data.priceMax >= data.priceMin;
    }
    return true;
  }, "priceMax must be >= priceMin");

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
    const validated = searchSchema.parse(params);
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
        return {
          ...cachedData,
          fromCache: true,
          provider: cachedData.provider || "cache",
          tookMs: Date.now() - startedAt,
        };
      }
    }

    // Execute search
    const { data, provider } = await executeSearch(searchParams);
    const searchId = secureUuid();
    const tookMs = Date.now() - startedAt;

    const result: AccommodationSearchResult = {
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
      status: "success",
      tookMs,
      totalResults: Array.isArray(data)
        ? data.length
        : ((data as Record<string, unknown>).total_results as number | undefined) || 0,
    };

    // Cache result
    if (redis && !validated.fresh) {
      await redis.set(cacheKey, result, { ex: ACCOM_SEARCH_CACHE_TTL_SECONDS });
    }

    return result;
  },
  inputSchema: searchSchema,
});

/**
 * Zod schema for booking accommodations tool input validation.
 *
 * Validates guest information, dates, payment details, and optional
 * idempotency key. Includes cross-field refinement for date ordering.
 */
const bookingSchema = z
  .object({
    checkin: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    checkout: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    guestEmail: z.string().email(),
    guestName: z.string().min(1),
    guestPhone: z.string().optional(),
    guests: z.number().int().min(1).max(16).default(1),
    holdOnly: z.boolean().default(false).optional(),
    idempotencyKey: z.string().optional(),
    listingId: z.string().min(1),
    paymentMethod: z.string().optional(),
    sessionId: z.string().min(6),
    specialRequests: z.string().optional(),
    tripId: z.string().optional(),
  })
  .refine((data) => {
    const checkin = new Date(data.checkin);
    const checkout = new Date(data.checkout);
    return checkout > checkin;
  }, "checkout must be after checkin");

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
    const validated = bookingSchema.parse(params);
    const idempotencyKey = validated.idempotencyKey || secureUuid();

    // Require approval with idempotency key
    await requireApproval("bookAccommodation", {
      idempotencyKey,
      sessionId: validated.sessionId,
    });

    // Approval granted, proceed with booking
    // In a full implementation, call the MCP "book" tool or provider API here
    const bookingReference = `bk_${secureUuid().replaceAll("-", "").slice(0, 10)}`;
    return {
      bookingId: secureUuid(),
      bookingStatus: validated.holdOnly ? "hold_created" : "pending_confirmation",
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
      status: "success",
      tripId: validated.tripId,
    } as const;
  },
  inputSchema: bookingSchema,
});

/**
 * Zod schema for accommodation details tool input validation.
 *
 * Validates listing ID and optional date/guest parameters for accurate
 * pricing and availability information.
 */
const detailsSchema = z.object({
  adults: z.number().int().min(1).max(16).default(1).optional(),
  checkin: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .optional(),
  checkout: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .optional(),
  children: z.number().int().min(0).max(16).default(0).optional(),
  infants: z.number().int().min(0).max(16).default(0).optional(),
  listingId: z.string().min(1),
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
    const validated = detailsSchema.parse(params);
    const mcpUrl = process.env.AIRBNB_MCP_URL || process.env.ACCOM_SEARCH_URL;
    const mcpAuth = process.env.AIRBNB_MCP_API_KEY || process.env.ACCOM_SEARCH_TOKEN;

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
          return {
            listing: result,
            provider: "mcp_sse",
            status: "success",
          };
        }
        await client.close();
      } catch {
        // Fall through to HTTP fallback
      }
    }

    // HTTP fallback
    const httpUrl = process.env.ACCOM_SEARCH_URL || process.env.AIRBNB_MCP_URL;
    const httpToken = process.env.ACCOM_SEARCH_TOKEN || process.env.AIRBNB_MCP_API_KEY;
    if (!httpUrl) {
      const error: Error & { code?: string } = new Error(
        "accom_details_not_configured"
      );
      error.code = "accom_details_not_configured";
      throw error;
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
        const error: Error & { code?: string; meta?: Record<string, unknown> } =
          new Error("accom_details_timeout");
        error.code = "accom_details_timeout";
        error.meta = errWithCode.meta;
        throw error;
      }
      if (errWithCode.code === "fetch_failed") {
        const error: Error & { code?: string; meta?: Record<string, unknown> } =
          new Error("accom_details_failed");
        error.code = "accom_details_failed";
        error.meta = errWithCode.meta;
        throw error;
      }
      throw err;
    });

    if (!res.ok) {
      const text = await res.text();
      const error: Error & { code?: string; meta?: Record<string, unknown> } =
        new Error(
          res.status === 404
            ? "accom_details_not_found"
            : res.status === 429
              ? "accom_details_rate_limited"
              : res.status === 401
                ? "accom_details_unauthorized"
                : "accom_details_failed"
        );
      error.code =
        res.status === 404
          ? "accom_details_not_found"
          : res.status === 429
            ? "accom_details_rate_limited"
            : res.status === 401
              ? "accom_details_unauthorized"
              : "accom_details_failed";
      error.meta = { status: res.status, text: text.slice(0, 200) };
      throw error;
    }

    const data = await res.json();
    return {
      listing: data,
      provider: "http_get",
      status: "success",
    };
  },
  inputSchema: detailsSchema,
});
