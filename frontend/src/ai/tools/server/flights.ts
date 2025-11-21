/**
 * @fileoverview Flight search tool using Duffel API v2 (offers request).
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { searchFlightsService } from "@domain/flights/service";
import type { FlightSearchRequest, FlightSearchResult } from "@schemas/flights";
import { flightSearchRequestSchema } from "@schemas/flights";
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
      // Map provider errors to tool error codes for consistency
      const message = err instanceof Error ? err.message : "unknown_error";
      if (message.includes("duffel_not_configured")) {
        const error = new Error(message);
        (error as Error & { code?: string }).code =
          TOOL_ERROR_CODES.toolExecutionFailed;
        throw error;
      }
      if (message.startsWith("duffel_offer_request_failed")) {
        const error = new Error(message);
        (error as Error & { code?: string }).code =
          TOOL_ERROR_CODES.toolExecutionFailed;
        throw error;
      }
      throw err;
    }
  },
  guardrails: {
    cache: {
      hashInput: true,
      key: (params) =>
        canonicalizeParamsForCache({
          cabinClass: params.cabinClass,
          currency: params.currency,
          departureDate: params.departureDate,
          destination: params.destination,
          origin: params.origin,
          passengers: params.passengers,
          returnDate: params.returnDate ?? "none",
        }),
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
      redactKeys: ["origin", "destination"],
      workflow: "flightSearch",
    },
  },
  inputSchema: searchFlightsInputSchema,
  name: "searchFlights",
});
