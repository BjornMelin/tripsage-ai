/**
 * @fileoverview Duffel provider client for flight offer requests.
 */

import { type FlightSearchRequest, flightSearchRequestSchema } from "@schemas/flights";
import { getServerEnvVarWithFallback } from "@/lib/env/server";

/** The type of the Duffel offer response. */
type DuffelOfferResponse = unknown;

/**
 * Get the Duffel API key from the environment variables.
 *
 * @returns The Duffel API key.
 */
function getDuffelKey(): string | undefined {
  return (
    getServerEnvVarWithFallback("DUFFEL_ACCESS_TOKEN", undefined) ||
    getServerEnvVarWithFallback("DUFFEL_API_KEY", undefined)
  );
}

/**
 * Convert a camelCase object to a snake_case object.
 *
 * @param value - The object to convert.
 * @returns The converted object.
 */
function toSnakeCase(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(toSnakeCase);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, val]) => [
        key
          .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
          .replace(/__/g, "_")
          .toLowerCase(),
        toSnakeCase(val),
      ])
    );
  }
  return value;
}

/**
 * Error thrown when Duffel configuration is missing or invalid.
 */
class DuffelConfigError extends Error {
  readonly code = "duffel_not_configured";

  constructor(message = "Duffel API key is not configured") {
    super(message);
    this.name = "DuffelConfigError";
  }
}

/**
 * Execute a Duffel offer request.
 *
 * @param params - The flight search request parameters.
 * @returns The Duffel offer response.
 * @throws an Error with a structured message on HTTP failure.
 */
export async function fetchDuffelOffers(
  params: FlightSearchRequest
): Promise<DuffelOfferResponse> {
  const parsed = flightSearchRequestSchema.parse(params);
  const duffelKey = getDuffelKey();
  if (!duffelKey) {
    throw new DuffelConfigError();
  }

  type CamelSlice = {
    origin: string;
    destination: string;
    departureDate: string;
  };

  const slices: CamelSlice[] = [
    {
      departureDate: parsed.departureDate,
      destination: parsed.destination,
      origin: parsed.origin,
    },
  ];

  if (parsed.returnDate) {
    slices.push({
      departureDate: parsed.returnDate,
      destination: parsed.origin,
      origin: parsed.destination,
    });
  }

  const camelPayload = {
    cabinClass: parsed.cabinClass,
    maxConnections: parsed.nonstop ? 0 : 1,
    passengers: Array.from({ length: parsed.passengers }, () => ({ type: "adult" })),
    paymentCurrency: parsed.currency,
    returnOffers: true,
    slices,
  };

  const body = toSnakeCase(camelPayload) as Record<string, unknown>;

  // The response from the Duffel API.
  const res = await fetch("https://api.duffel.com/air/offer_requests", {
    body: JSON.stringify(body),
    headers: {
      authorization: `Bearer ${duffelKey}`,
      "content-type": "application/json",
      "duffel-version": "v2",
    },
    method: "POST",
  });

  if (!res.ok) {
    const text = await res.text();
    const err = new Error(`duffel_offer_request_failed:${res.status}:${text}`);
    (err as Error & { status?: number }).status = res.status;
    throw err;
  }

  return res.json();
}
