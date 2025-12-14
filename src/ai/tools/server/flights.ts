/**
 * @fileoverview Flight search tool using Duffel API v2 (offers request).
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import {
  createToolError,
  isToolError,
  TOOL_ERROR_CODES,
} from "@ai/tools/server/errors";
import { searchFlightsService } from "@domain/flights/service";
import type { FlightSearchRequest, FlightSearchResult } from "@schemas/flights";
import { flightSearchRequestSchema } from "@schemas/flights";
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
});
