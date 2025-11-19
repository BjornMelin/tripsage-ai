/**
 * @fileoverview Flight search tool using Duffel API v2 (offers request).
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import type { FlightSearchRequest } from "@schemas/agents";
import { flightSearchRequestSchema } from "@schemas/agents";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { getServerEnvVarWithFallback } from "@/lib/env/server";

// Prefer DUFFEL_ACCESS_TOKEN (commonly used in templates), fall back to DUFFEL_API_KEY.
function getDuffelKey(): string | undefined {
  return (
    getServerEnvVarWithFallback("DUFFEL_ACCESS_TOKEN", undefined) ||
    getServerEnvVarWithFallback("DUFFEL_API_KEY", undefined)
  );
}

export const searchFlightsInputSchema = flightSearchRequestSchema;

type SearchFlightsInput = FlightSearchRequest;
type SearchFlightsResult = {
  currency: string;
  offers: unknown[];
};

export const searchFlights = createAiTool<SearchFlightsInput, SearchFlightsResult>({
  description:
    "Search flights using Duffel Offer Requests (simple one-way or round-trip).",
  execute: async (params) => {
    const {
      cabinClass,
      currency,
      departureDate,
      destination,
      origin,
      passengers,
      returnDate,
    } = searchFlightsInputSchema.parse(params);

    const DuffelKey = getDuffelKey();
    if (!DuffelKey) throw new Error("duffel_not_configured");

    type CamelSlice = {
      origin: string;
      destination: string;
      departureDate: string;
    };
    const slicesCamel: CamelSlice[] = [{ departureDate, destination, origin }];
    if (returnDate) {
      slicesCamel.push({
        departureDate: returnDate,
        destination: origin,
        origin: destination,
      });
    }

    const camel = {
      cabinClass,
      maxConnections: 1,
      passengers: Array.from({ length: passengers }, () => ({ type: "adult" })),
      paymentCurrency: currency,
      returnOffers: true,
      slices: slicesCamel,
    };

    const snake = (value: unknown): unknown => {
      if (Array.isArray(value)) return value.map(snake);
      if (value && typeof value === "object") {
        return Object.fromEntries(
          Object.entries(value as Record<string, unknown>).map(([key, val]) => [
            key
              .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
              .replace(/__/g, "_")
              .toLowerCase(),
            snake(val),
          ])
        );
      }
      return value;
    };

    const body = snake(camel) as Record<string, unknown>;
    const endpoint = "https://api.duffel.com/air/offer_requests";
    const res = await fetch(endpoint, {
      body: JSON.stringify(body),
      headers: {
        authorization: `Bearer ${DuffelKey}`,
        "content-type": "application/json",
        "duffel-version": "v2",
      },
      method: "POST",
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`duffel_offer_request_failed:${res.status}:${text}`);
    }
    const json = await res.json();
    const offers: unknown[] = Array.isArray(json?.data?.offers)
      ? json.data.offers
      : Array.isArray(json?.data)
        ? json.data
        : [];
    const resolvedCurrency =
      offers
        .map((offer) => {
          if (typeof offer !== "object" || offer === null) return null;
          // biome-ignore lint/complexity/useLiteralKeys: Duffel responses use snake_case fields
          const totalCurrency = (offer as Record<string, unknown>)["total_currency"];
          return typeof totalCurrency === "string" ? totalCurrency : null;
        })
        .find((value): value is string => typeof value === "string") ?? currency;
    return {
      currency: resolvedCurrency,
      offers,
    };
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
      }),
      redactKeys: ["origin", "destination"],
      workflow: "flightSearch",
    },
  },
  inputSchema: searchFlightsInputSchema,
  name: "searchFlights",
});
