/**
 * @fileoverview Accommodation search, booking, and details tools wired through the accommodations service.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import {
  createToolError,
  TOOL_ERROR_CODES,
  type ToolErrorCode,
} from "@ai/tools/server/errors";
import {
  ACCOMMODATION_BOOKING_INPUT_SCHEMA,
  ACCOMMODATION_CHECK_AVAILABILITY_INPUT_SCHEMA,
  ACCOMMODATION_DETAILS_INPUT_SCHEMA,
  ACCOMMODATION_SEARCH_INPUT_SCHEMA,
  type AccommodationBookingRequest,
  type AccommodationBookingResult,
  type AccommodationCheckAvailabilityParams,
  type AccommodationCheckAvailabilityResult,
  type AccommodationDetailsParams,
  type AccommodationDetailsResult,
  type AccommodationSearchParams,
  type AccommodationSearchResult,
} from "@schemas/accommodations";
import { Ratelimit } from "@upstash/ratelimit";
import { headers } from "next/headers";
import { ProviderError } from "@/domain/accommodations/errors";
import { ExpediaProviderAdapter } from "@/domain/accommodations/providers/expedia-adapter";
import {
  AccommodationsService,
  extractTokenFromHref,
  normalizePhoneForRapid,
  splitGuestName,
} from "@/domain/accommodations/service";
import { processBookingPayment } from "@/lib/payments/booking-payment";
import { getRedis } from "@/lib/redis";
import { secureUuid } from "@/lib/security/random";
import { createServerSupabase } from "@/lib/supabase/server";
import { requireApproval } from "./approvals";
import { ACCOM_SEARCH_CACHE_TTL_SECONDS } from "./constants";

const redis = getRedis();
const rateLimiter = redis
  ? new Ratelimit({
      analytics: false,
      limiter: Ratelimit.slidingWindow(10, "1 m"),
      prefix: "ratelimit:accommodations:service",
      redis,
    })
  : undefined;

const provider = new ExpediaProviderAdapter();
const accommodationsService = new AccommodationsService({
  cacheTtlSeconds: ACCOM_SEARCH_CACHE_TTL_SECONDS,
  provider,
  rateLimiter,
  supabase: createServerSupabase,
});

export { ACCOMMODATION_SEARCH_INPUT_SCHEMA as searchAccommodationsInputSchema };

export const searchAccommodations = createAiTool<
  AccommodationSearchParams,
  AccommodationSearchResult
>({
  description:
    "Search for accommodations (hotels and Vrbo vacation rentals) using Expedia Partner Solutions API. Supports semantic search via RAG for natural language queries.",
  execute: async (params) => {
    return accommodationsService.search(params, {
      sessionId: await maybeGetUserIdentifier(),
    });
  },
  inputSchema: ACCOMMODATION_SEARCH_INPUT_SCHEMA,
  name: "searchAccommodations",
});

export const getAccommodationDetails = createAiTool<
  AccommodationDetailsParams,
  AccommodationDetailsResult
>({
  description:
    "Retrieve comprehensive details for a specific accommodation property from Expedia Rapid.",
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
    const sessionId = params.sessionId ?? (await maybeGetUserIdentifier());
    if (!sessionId) {
      throw createToolError(TOOL_ERROR_CODES.accomBookingSessionRequired);
    }
    const userId = await getUserIdFromHeadersOrThrow(
      TOOL_ERROR_CODES.accomBookingSessionRequired
    );
    const idempotencyKey = params.idempotencyKey ?? secureUuid();

    try {
      return await accommodationsService.book(params, {
        processPayment: () =>
          processBookingPayment({
            amount: params.amount,
            currency: params.currency,
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
  inputSchema: ACCOMMODATION_BOOKING_INPUT_SCHEMA,
  name: "bookAccommodation",
});

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

export { extractTokenFromHref, normalizePhoneForRapid, splitGuestName };
