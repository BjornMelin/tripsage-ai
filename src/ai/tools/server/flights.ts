/**
 * @fileoverview Flight search tool using Duffel API v2 (offers request).
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import type { FlightModelOutput } from "@ai/tools/schemas/flights";
import {
  createToolError,
  isToolError,
  TOOL_ERROR_CODES,
} from "@ai/tools/server/errors";
import { searchFlightsService } from "@domain/flights/service";
import type { FlightSearchRequest, FlightSearchResult } from "@schemas/flights";
import { flightSearchRequestSchema, flightSearchResultSchema } from "@schemas/flights";
import { hashInputForCache } from "@/lib/cache/hash";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";

export const searchFlightsInputSchema = flightSearchRequestSchema;

type SearchFlightsInput = FlightSearchRequest;
type SearchFlightsResult = FlightSearchResult;

export const searchFlights = createAiTool<SearchFlightsInput, SearchFlightsResult>({
  description:
    "Search flights using Duffel Offer Requests (simple one-way or round-trip).",
  execute: async (params) => {
    try {
      return await searchFlightsService(params);
    } catch (err) {
      if (isToolError(err)) {
        throw err;
      }

      // Map provider errors to canonical ToolErrors for consistency and observability
      const message = err instanceof Error ? err.message : "unknown_error";
      const errorMeta = {
        messageHash: hashInputForCache(message),
        messageLength: message.length,
        provider: "duffel",
      };

      if (message.includes("duffel_not_configured")) {
        throw createToolError(
          TOOL_ERROR_CODES.toolExecutionFailed,
          "Duffel API key is not configured",
          {
            ...errorMeta,
            reason: "not_configured",
          }
        );
      }
      if (message.startsWith("duffel_offer_request_failed")) {
        throw createToolError(TOOL_ERROR_CODES.toolExecutionFailed, message, {
          ...errorMeta,
          reason: "offer_request_failed",
        });
      }
      throw createToolError(TOOL_ERROR_CODES.toolExecutionFailed, message, {
        ...errorMeta,
        reason: "unknown",
      });
    }
  },
  guardrails: {
    cache: {
      key: (params) =>
        `v1:${hashInputForCache(
          canonicalizeParamsForCache({
            cabinClass: params.cabinClass,
            currency: params.currency,
            departureDate: params.departureDate,
            destination: params.destination,
            origin: params.origin,
            passengers: params.passengers,
            returnDate: params.returnDate ?? "none",
          })
        )}`,
      namespace: "agent:flight:search",
      ttlSeconds: 60 * 30,
    },
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 8,
      prefix: "ratelimit:agent:flight:search",
      window: "1 m",
    },
    telemetry: {
      attributes: (params) => ({
        cabinClass: params.cabinClass,
        hasReturn: Boolean(params.returnDate),
        passengers: params.passengers,
        provider: "duffel",
      }),
      workflow: "flightSearch",
    },
  },
  inputSchema: searchFlightsInputSchema,
  name: "searchFlights",
  outputSchema: flightSearchResultSchema,
  /**
   * Simplifies flight results for model consumption to reduce token usage.
   * Strips sources, bookingUrl, schemaVersion, and simplifies segment details.
   */
  toModelOutput: (result): FlightModelOutput => ({
    currency: result.currency,
    fromCache: result.fromCache,
    itineraries: result.itineraries.slice(0, 10).map((itinerary) => ({
      id: itinerary.id,
      price: itinerary.price,
      segments: itinerary.segments.map((seg) => ({
        carrier: seg.carrier,
        departure: seg.departure,
        destination: seg.destination,
        flightNumber: seg.flightNumber,
        origin: seg.origin,
      })),
    })),
    itineraryCount: result.itineraries.length,
    offerCount: result.offers.length,
    offers: result.offers.slice(0, 5).map((offer) => ({
      id: offer.id,
      price: offer.price.amount,
      provider: offer.provider,
      slices: offer.slices.map((slice) => ({
        cabinClass: slice.cabinClass,
        segmentCount: slice.segments.length,
        segments: slice.segments.slice(0, 2).map((seg) => ({
          carrier: seg.carrier,
          departureTime: seg.departureTime,
          destination: seg.destination.iata,
          flightNumber: seg.flightNumber,
          origin: seg.origin.iata,
        })),
      })),
    })),
    provider: result.provider,
  }),
  validateOutput: true,
});
