/**
 * @fileoverview Flight search tool using Duffel API v2 (offers request).
 */

import { tool } from "ai";
import { z } from "zod";

// Prefer DUFFEL_ACCESS_TOKEN (commonly used in templates), fall back to DUFFEL_API_KEY.
const DUFFEL_KEY = process.env.DUFFEL_ACCESS_TOKEN || process.env.DUFFEL_API_KEY;

export const searchFlights = tool({
  description:
    "Search flights using Duffel Offer Requests (simple one-way or round-trip).",
  execute: async ({
    origin,
    destination,
    departureDate,
    returnDate,
    passengers,
    cabin,
    currency,
  }) => {
    if (!DUFFEL_KEY) throw new Error("duffel_not_configured");

    type CamelSlice = { origin: string; destination: string; departureDate: string };
    const slicesCamel: CamelSlice[] = [{ departureDate, destination, origin }];
    if (returnDate)
      slicesCamel.push({
        departureDate: returnDate,
        destination: origin,
        origin: destination,
      });

    const camel = {
      cabinClass: cabin,
      maxConnections: 1,
      passengers: Array.from({ length: passengers }, () => ({ type: "adult" })),
      returnOffers: true,
      slices: slicesCamel,
    };

    const snake = (v: unknown): unknown => {
      if (Array.isArray(v)) return v.map(snake);
      if (v && typeof v === "object") {
        return Object.fromEntries(
          Object.entries(v as Record<string, unknown>).map(([k, val]) => [
            k
              .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
              .replace(/__/g, "_")
              .toLowerCase(),
            snake(val),
          ])
        );
      }
      return v;
    };
    const body = snake(camel) as Record<string, unknown>;

    const res = await fetch("https://api.duffel.com/air/offer_requests", {
      body: JSON.stringify(body),
      headers: {
        authorization: `Bearer ${DUFFEL_KEY}`,
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
    const offers = json?.data?.offers ?? json?.data ?? [];
    return {
      currency,
      offers,
    } as const;
  },
  inputSchema: z.object({
    cabin: z
      .enum(["economy", "premium_economy", "business", "first"])
      .default("economy"),
    currency: z.string().default("USD"),
    departureDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    destination: z.string().min(3),
    origin: z.string().min(3),
    passengers: z.number().int().min(1).max(9).default(1),
    returnDate: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/)
      .optional(),
  }),
});
